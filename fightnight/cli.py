"""Commands behind the Makefile: fight (default), clean FILE, gen, init-env, wait-otari, keys."""

from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

from . import card as cardmod
from . import ollama, specs
from .config import ENV_PATH, Settings, init_env, read_env_file
from .otari import Otari, OtariError
from .referee import DATA_DIR, chat_via, clean_file, load_sample, make_dataset, run_fight
from .team import Team, TeamError, load_team


def die(msg: str) -> None:
    print(f"\nerror: {msg}", file=sys.stderr)
    sys.exit(1)


def cmd_init_env() -> None:
    if init_env():
        print(f"wrote {ENV_PATH} with fresh keys.")
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
    print(f"team key:    {env.get('TEAM_KEY', '')}")
    print(f"stock key:   {env.get('STOCK_KEY', '')}")


def cmd_gen() -> None:
    s = Settings.load()
    seed = s.seed if s.seed is not None else random.SystemRandom().randrange(1, 10**6)
    golden, messy, sha = make_dataset(seed, s.rows, s.preset)
    print(f"wrote {DATA_DIR / 'golden.csv'} ({len(golden)} rows) and {DATA_DIR / 'messy.csv'} ({len(messy)} rows), preset {s.preset}, seed {seed}, sha {sha}")


def otari_version() -> str:
    try:
        out = subprocess.run(["docker", "compose", "logs", "--no-color", "otari"], capture_output=True, text=True, timeout=10).stdout
        for line in out.splitlines():
            if "Otari v" in line:
                return line.split("Otari v", 1)[1].split()[0]
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _teams(s: Settings, need_stock: bool) -> tuple[Team, Team | None]:
    try:
        team = load_team(s.team_path)
        stock = load_team(s.stock_path) if need_stock else None
    except (TeamError, FileNotFoundError) as e:
        die(f"team file: {e}")
    return team, stock


def _prepare(s: Settings, models: list[str]) -> tuple[Otari, dict[str, float], str]:
    """Ollama has the models, Otari is up and serves them. Returns (otari, sizes, ollama_version)."""
    if not (s.key_team and s.key_stock and s.master_key):
        die("missing keys in .env. Delete .env and run `make fight` to generate a fresh one.")
    local = [m for m in models if m.split(":", 1)[0] not in ("otari-ai",) and not m.startswith("ollama:")] + [m.removeprefix("ollama:") for m in models if m.startswith("ollama:")]
    try:
        ollama_version = ollama.version(s.ollama_url)
        pulled = ollama.ensure(s.ollama_url, local)
        sizes = ollama.sizes(s.ollama_url)
    except ollama.OllamaError as e:
        die(str(e))
    except Exception as e:
        die(f"talking to Ollama at {s.ollama_url}: {e}")
    print(f"  Ollama {ollama_version}" + (f", pulled {', '.join(pulled)}" if pulled else ", models present"))
    otari = Otari(s.otari_url, s.master_key)
    try:
        otari.wait_healthy()
        notes = otari.ensure_models("ollama", local)
        if s.otari_ai_key:
            notes.append(otari.ensure_otari_ai(s.otari_ai_key))
    except OtariError as e:
        die(str(e))
    print(f"  Otari {otari_version()} at {s.otari_url}" + (": " + "; ".join(notes) if notes else ", roster ready"))
    return otari, sizes, ollama_version


def cmd_fight() -> None:
    s = Settings.load()
    team, stock = _teams(s, need_stock=True)
    print("Otari Fight Night: CSV cleanup")
    print(f"  stock: {s.stock_path} ({', '.join(stock.models())})")
    print(f"  yours: {s.team_path} ({', '.join(team.models())})")
    otari, sizes, ollama_version = _prepare(s, stock.models() + team.models())
    try:
        result = run_fight(s, otari, team, stock, sizes)
    except OtariError as e:
        die(str(e))
    except KeyboardInterrupt:
        die("stopped. No fight card written.")
    gateway = {"otari_url": s.otari_url, "otari_version": otari_version(), "ollama_version": ollama_version}
    card = cardmod.build(result, specs.collect(), gateway)
    cardmod.write(card)
    d = card["result"]["delta_points"]
    print()
    print(f"{card['team']['name']} {card['team']['accuracy_pct']}% vs stock {card['stock']['accuracy_pct']}%: {'+' if d >= 0 else ''}{d} points.")
    print("wrote fight-card.md, fight-card.json, fight-log.jsonl and data/{stock,team}.clean.csv")
    print(f"dashboard: {s.otari_url}  (admin key: make keys)")


def cmd_clean(path_arg: str | None) -> None:
    if not path_arg:
        die("usage: make clean FILE=path/to/your.csv")
    path = Path(path_arg)
    if not path.exists():
        die(f"{path} not found")
    s = Settings.load()
    team, _ = _teams(s, need_stock=False)
    otari, _, _ = _prepare(s, team.models())
    n = [0]

    def on_call(c) -> None:
        n[0] += 1
        print(f"  {c.stage} {c.model} request {n[0]}, {c.rows_in} rows, {c.seconds:.1f}s", flush=True)

    try:
        out = clean_file(team, path, load_sample(), chat_via(otari, s.key_team, s.timeout_seconds), on_call)
    except OtariError as e:
        die(str(e))
    print(f"wrote {out}")


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    cmd = args[0] if args else "fight"
    if cmd == "clean":
        return cmd_clean(args[1] if len(args) > 1 else None)
    {
        "fight": cmd_fight,
        "gen": cmd_gen,
        "init-env": cmd_init_env,
        "wait-otari": cmd_wait_otari,
        "keys": cmd_keys,
    }.get(cmd, lambda: die(f"unknown command {cmd!r}. Commands: fight, clean FILE, gen, init-env, wait-otari, keys"))()
