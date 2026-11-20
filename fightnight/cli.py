"""Commands behind `make fight`: init-env, wait-otari, keys, and the fight itself."""

from __future__ import annotations

import hashlib
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import card as cardmod
from . import ollama, specs
from .config import ENV_PATH, Settings, init_env, read_env_file
from .otari import Otari, OtariError
from .referee import Fighter, load_strategy, run_fight


def die(msg: str) -> None:
    print(f"\nerror: {msg}", file=sys.stderr)
    sys.exit(1)


def cmd_init_env() -> None:
    if init_env():
        print(f"wrote {ENV_PATH} with fresh keys. Fighters: edit FIGHTER_A / FIGHTER_B there to change models.")
    else:
        print(f"{ENV_PATH} already exists, leaving it alone.")


def cmd_wait_otari() -> None:
    s = Settings.load()
    try:
        Otari(s.otari_url).wait_healthy()
    except OtariError as e:
        die(str(e))
    print(f"Otari is up at {s.otari_url}")


def cmd_keys() -> None:
    env = read_env_file()
    print(f"dashboard:   {env.get('OTARI_URL', 'http://localhost:8000')}")
    print(f"admin key:   {env.get('OTARI_MASTER_KEY', '(no .env yet, run make fight)')}")
    print(f"fighter A:   {env.get('FIGHTER_A_KEY', '')}")
    print(f"fighter B:   {env.get('FIGHTER_B_KEY', '')}")


def otari_version() -> str:
    try:
        out = subprocess.run(["docker", "compose", "logs", "--no-color", "otari"], capture_output=True, text=True, timeout=10).stdout
        for line in out.splitlines():
            if "Otari v" in line:
                return line.split("Otari v", 1)[1].split()[0]
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def cmd_fight() -> None:
    s = Settings.load()
    if not (s.key_a and s.key_b and s.master_key):
        die("missing keys in .env. Delete .env and run `make fight` to generate a fresh one.")
    if s.fighter_a == s.fighter_b:
        print("note: both corners run the same model, so this fight measures variance, not models.")

    print("Otari Local Model Fight Night")
    print(f"  A: {s.fighter_a}    B: {s.fighter_b}    {s.rounds} rounds")

    # 1. Ollama on the host
    try:
        ollama_version = ollama.version(s.ollama_url)
        pulled = ollama.ensure(s.ollama_url, [s.fighter_a, s.fighter_b])
    except ollama.OllamaError as e:
        die(str(e))
    except Exception as e:  # httpx errors while pulling
        die(f"talking to Ollama at {s.ollama_url}: {e}")
    print(f"  Ollama {ollama_version}" + (f", pulled {', '.join(pulled)}" if pulled else ", models present"))

    # 2. Otari in Docker
    otari = Otari(s.otari_url, s.master_key)
    try:
        otari.wait_healthy()
        notes = otari.ensure_models("ollama", [s.fighter_a, s.fighter_b])
    except OtariError as e:
        die(str(e))
    print(f"  Otari {otari_version()} at {s.otari_url}" + (": " + "; ".join(notes) if notes else ", roster ready"))

    # 3. The strategy both fighters get
    strategy = load_strategy()
    strategy_sha = hashlib.sha256(strategy.encode()).hexdigest()[:12]
    print(f"  strategy.md sha {strategy_sha}, {len(strategy)} chars")

    a = Fighter("A", "fighter-a", s.fighter_a, s.key_a)
    b = Fighter("B", "fighter-b", s.fighter_b, s.key_b)
    seed = s.seed if s.seed is not None else random.SystemRandom().randrange(1, 10**6)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"  seed {seed}")

    try:
        rounds = run_fight(otari, a, b, strategy, s, seed)
    except OtariError as e:
        die(str(e))
    except KeyboardInterrupt:
        die("stopped. No fight card written.")

    usage_a = otari.key_usage(s.key_a, started)
    usage_b = otari.key_usage(s.key_b, started)
    gateway = {"otari_url": s.otari_url, "otari_version": otari_version(), "ollama_version": ollama_version}
    card = cardmod.build(rounds, a, b, usage_a, usage_b, specs.collect(), gateway, seed, s, strategy_sha)
    cardmod.write(card)

    print()
    print(f"{card['result']['winner']} wins, {card['result']['record']}.")
    print("wrote fight-card.md and fight-card.json (and fight-log.jsonl with every guess)")
    print(f"dashboard: {s.otari_url}  (admin key: make keys)")


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    cmd = args[0] if args else "fight"
    {
        "fight": cmd_fight,
        "init-env": cmd_init_env,
        "wait-otari": cmd_wait_otari,
        "keys": cmd_keys,
    }.get(cmd, lambda: die(f"unknown command {cmd!r}. Commands: fight, init-env, wait-otari, keys"))()
