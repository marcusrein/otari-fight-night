"""Codebreaker (Mastermind) rules. Plain code, no model judges another."""

from __future__ import annotations

import random
import re
from collections import Counter
from dataclasses import dataclass

CODE_LENGTH = 4
DIGITS = (1, 2, 3, 4, 5, 6)
FAIL_SCORE = 11  # max guesses + 1; what a fighter scores when it does not crack the code


@dataclass(frozen=True)
class Rules:
    """The shape of the code. Defaults are classic: 4 digits from 1-6."""

    code_length: int = CODE_LENGTH
    max_digit: int = DIGITS[-1]

    @property
    def digits(self) -> tuple[int, ...]:
        return tuple(range(1, self.max_digit + 1))

    @property
    def pattern(self) -> re.Pattern:
        d = f"[1-{self.max_digit}]"
        return re.compile(rf"(?<![0-9]){d}(?:[\s,\-]*{d}){{{self.code_length - 1}}}(?![0-9])")


CLASSIC = Rules()


def make_secret(rng: random.Random, rules: Rules = CLASSIC) -> list[int]:
    """A fresh secret: rules.code_length digits from rules.digits, repeats allowed."""
    return [rng.choice(rules.digits) for _ in range(rules.code_length)]


def score(secret: list[int], guess: list[int]) -> tuple[int, int]:
    """Return (exact, misplaced): right digit in the right place, and right digit in the wrong place."""
    exact = sum(1 for s, g in zip(secret, guess) if s == g)
    common = sum((Counter(secret) & Counter(guess)).values())
    return exact, common - exact


def parse_guess(text: str, rules: Rules = CLASSIC) -> list[int] | None:
    """Pull a guess out of a model reply.

    The last group of exactly code_length digits in range (separated by nothing,
    spaces, commas or dashes) is the guess. A longer run of digits is not a guess.
    Anything else returns None and the referee counts the reply as malformed.
    """
    matches = rules.pattern.findall(text or "")
    if not matches:
        return None
    return [int(c) for c in matches[-1] if c.isdigit()]


def compare_rounds(a: tuple[int, float], b: tuple[int, float]) -> str:
    """Decide a round from (score, seconds) per fighter. Lower score wins, then faster time."""
    if a[0] != b[0]:
        return "a" if a[0] < b[0] else "b"
    if a[1] != b[1]:
        return "a" if a[1] < b[1] else "b"
    return "tie"
