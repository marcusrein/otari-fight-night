"""The referee holds the secret, scores guesses and keeps time. It is plain code."""

from __future__ import annotations

import json
import random
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

from .config import Settings
from .game import Rules, compare_rounds, make_secret, parse_guess, score
from .otari import Otari, OtariError

_COMMENT = re.compile(r"<!--.*?-->", re.S)


@dataclass
class Fighter:
    corner: str  # "A" or "B"
    alias: str  # Otari alias: fighter-a / fighter-b
    model: str
    api_key: str


@dataclass
class Guess:
    n: int
    raw: str
    guess: list[int] | None
    exact: int | None
    misplaced: int | None
    seconds: float
    prompt_tokens: int
    completion_tokens: int
    malformed: bool = False
    timed_out: bool = False


@dataclass
class Play:
    corner: str
    model: str
    cracked: bool
    score: int
    seconds: float
    guesses: list[Guess] = field(default_factory=list)

    @property
    def malformed(self) -> int:
        return sum(1 for g in self.guesses if g.malformed)

    @property
    def timeouts(self) -> int:
        return sum(1 for g in self.guesses if g.timed_out)


@dataclass
class Round:
    n: int
    secret: list[int]
    a: Play
    b: Play
    winner: str  # "a", "b" or "tie"


def load_strategy(path: Path = Path("strategy.md")) -> str:
    """strategy.md minus HTML comments is the system prompt both fighters get."""
    text = path.read_text()
    return _COMMENT.sub("", text).strip()


def fmt(code: list[int] | None) -> str:
    return "".join(map(str, code)) if code else "----"


def rules_for(s: Settings) -> Rules:
    return Rules(code_length=s.code_length, max_digit=s.max_digit)


def play_round(otari: Otari, fighter: Fighter, secret: list[int], strategy: str, s: Settings, log) -> Play:
    rules = rules_for(s)
    n_digits = rules.code_length
    messages = [
        {"role": "system", "content": strategy},
        {"role": "user", "content": f"New game. The code is {n_digits} digits, each 1-{rules.max_digit}. You have {s.max_guesses} guesses. Make your first guess."},
    ]
    play = Play(corner=fighter.corner, model=fighter.model, cracked=False, score=s.max_guesses + 1, seconds=0.0)
    for n in range(1, s.max_guesses + 1):
        left = s.max_guesses - n
        try:
            res = otari.chat(fighter.api_key, fighter.alias, messages, s.max_tokens, s.timeout_seconds)
        except httpx.TimeoutException:
            g = Guess(n, "", None, None, None, s.timeout_seconds, 0, 0, timed_out=True)
            play.guesses.append(g)
            play.seconds += g.seconds
            log(fighter, secret, g)
            messages.append({"role": "user", "content": f"No reply within {s.timeout_seconds:.0f} seconds. That cost a guess. {left} left. Reply with exactly {n_digits} digits 1-{rules.max_digit}."})
            continue
        play.seconds += res.seconds
        guess = parse_guess(res.content, rules)
        if guess is None:
            g = Guess(n, res.content, None, None, None, res.seconds, res.prompt_tokens, res.completion_tokens, malformed=True)
            play.guesses.append(g)
            log(fighter, secret, g)
            messages.append({"role": "assistant", "content": res.content[:600]})
            messages.append({"role": "user", "content": f"Invalid guess, that cost a guess. {left} left. Reply with exactly {n_digits} digits 1-{rules.max_digit} and nothing else."})
            continue
        exact, misplaced = score(secret, guess)
        g = Guess(n, res.content, guess, exact, misplaced, res.seconds, res.prompt_tokens, res.completion_tokens)
        play.guesses.append(g)
        log(fighter, secret, g)
        if exact == n_digits:
            play.cracked = True
            play.score = n
            break
        messages.append({"role": "assistant", "content": res.content[:600]})
        messages.append({"role": "user", "content": f"Guess {fmt(guess)}: {exact} exact, {misplaced} misplaced. {left} guesses left. Next guess."})
    return play


def describe(play: Play) -> str:
    parts = []
    for g in play.guesses:
        if g.timed_out:
            parts.append("TIMEOUT")
        elif g.malformed:
            parts.append("BAD")
        else:
            parts.append(f"{fmt(g.guess)}({g.exact}/{g.misplaced})")
    tail = f"cracked in {play.score}" if play.cracked else "failed"
    return f"{' '.join(parts)}  {tail}, {play.seconds:.1f}s"


def run_fight(otari: Otari, a: Fighter, b: Fighter, strategy: str, s: Settings, seed: int, log_path: Path = Path("fight-log.jsonl")) -> list[Round]:
    rng = random.Random(seed)
    rules = rules_for(s)
    rounds: list[Round] = []
    wins = {"a": 0, "b": 0, "tie": 0}
    log_file = log_path.open("w")

    def log(fighter: Fighter, secret: list[int], g: Guess) -> None:
        row = {"round": len(rounds) + 1, "corner": fighter.corner, "model": fighter.model, "secret": fmt(secret), **asdict(g)}
        log_file.write(json.dumps(row) + "\n")
        log_file.flush()

    try:
        for n in range(1, s.rounds + 1):
            secret = make_secret(rng, rules)
            print(f"\nRound {n}/{s.rounds}  (secret {fmt(secret)})")
            pa = play_round(otari, a, secret, strategy, s, log)
            print(f"  A {a.model:<18} {describe(pa)}")
            pb = play_round(otari, b, secret, strategy, s, log)
            print(f"  B {b.model:<18} {describe(pb)}")
            winner = compare_rounds((pa.score, pa.seconds), (pb.score, pb.seconds))
            wins[winner] += 1
            verdict = {"a": f"A wins", "b": f"B wins", "tie": "tie"}[winner]
            print(f"  -> {verdict}   [A {wins['a']} - {wins['b']} B" + (f", {wins['tie']} tied" if wins["tie"] else "") + "]")
            rounds.append(Round(n, secret, pa, pb, winner))
    finally:
        log_file.close()
    return rounds
