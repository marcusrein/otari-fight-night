"""The referee: makes the messy file, runs stock then your team, grades both. Plain code."""

from __future__ import annotations

import hashlib
import json
import random
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .corrupt import COLUMNS, corrupt, make_golden, read_csv, write_csv
from .grade import Grade, grade
from .otari import ChatResult, Otari
from .pipeline import Call, StageStats, local_share, run_team
from .team import Team

DATA_DIR = Path("data")
SAMPLE_PATH = DATA_DIR / "sample.csv"


@dataclass
class TeamResult:
    team: Team
    grade: Grade
    stages: list[StageStats]
    seconds: float
    requests: int
    local_share: float
    weights_gb: float
    usage: dict


@dataclass
class FightResult:
    seed: int
    preset: str
    rows: int
    messy_rows: int
    dataset_sha: str
    stock: TeamResult
    team: TeamResult


def make_dataset(seed: int, rows: int, preset: str, out_dir: Path = DATA_DIR) -> tuple[list[dict], list[dict], str]:
    """Write data/golden.csv and data/messy.csv; return (golden, messy, sha of messy)."""
    out_dir.mkdir(exist_ok=True)
    golden = make_golden(rows, random.Random(seed))
    messy = corrupt(golden, random.Random(seed + 1), preset)
    write_csv(out_dir / "golden.csv", golden, COLUMNS)
    write_csv(out_dir / "messy.csv", messy, COLUMNS)
    sha = hashlib.sha256((out_dir / "messy.csv").read_bytes()).hexdigest()[:12]
    return golden, messy, sha


def load_sample() -> list[dict]:
    return read_csv(SAMPLE_PATH) if SAMPLE_PATH.exists() else make_golden(20, random.Random(1))


def chat_via(otari: Otari, api_key: str, timeout: float) -> Callable[[str, list[dict], int], ChatResult]:
    def chat(model: str, messages: list[dict], max_tokens: int) -> ChatResult:
        return otari.chat(api_key, model, messages, max_tokens, timeout)

    return chat


def run_one(team: Team, messy: list[dict], golden: list[dict], sample: list[dict], chat, log, sizes: dict[str, float], usage_fn=None, label: str = "") -> TeamResult:
    calls: list[Call] = []
    t0 = datetime.now(timezone.utc)

    def on_call(c: Call) -> None:
        calls.append(c)
        log({"team": label or team.name, **asdict(c)})
        line = f"  {label or team.name}: {c.stage} {c.model} request {len(calls)}, {c.rows_in} rows, {c.seconds:.1f}s  (total {sum(x.seconds for x in calls):.0f}s)"
        if sys.stdout.isatty():
            print("\r" + line.ljust(100), end="", flush=True)
        else:
            print(line, flush=True)

    cleaned, stages = run_team(team, [dict(r) for r in messy], sample, chat, on_call)
    if sys.stdout.isatty():
        print()
    g = grade(golden, cleaned) if golden else Grade(accuracy=0.0)
    usage = usage_fn(t0.isoformat(timespec="seconds")) if usage_fn else {}
    return TeamResult(
        team=team,
        grade=g,
        stages=stages,
        seconds=round(sum(c.seconds for c in calls), 1),
        requests=len(calls),
        local_share=local_share(calls),
        weights_gb=round(sum(sizes.get(m, 0.0) for m in team.models()), 2),
        usage=usage,
    ), cleaned


def run_fight(settings, otari: Otari, team: Team, stock: Team, sizes: dict[str, float], log_path: Path = Path("fight-log.jsonl")) -> FightResult:
    seed = settings.seed if settings.seed is not None else random.SystemRandom().randrange(1, 10**6)
    golden, messy, sha = make_dataset(seed, settings.rows, settings.preset)
    sample = load_sample()
    print(f"  dataset: {len(golden)} clean rows -> {len(messy)} messy rows, preset {settings.preset}, seed {seed}")
    with log_path.open("w") as f:
        def log(row: dict) -> None:
            f.write(json.dumps(row) + "\n")

        results = {}
        for label, t, key in (("stock", stock, settings.key_stock), ("team", team, settings.key_team)):
            usage_fn = (lambda since, k=key: otari.key_usage(k, since)) if otari else None
            r, cleaned = run_one(t, messy, golden, sample, chat_via(otari, key, settings.timeout_seconds), log, sizes, usage_fn, label=label)
            write_csv(DATA_DIR / f"{label}.clean.csv", cleaned, COLUMNS)
            print(f"  {label} ({t.name}): {r.grade.accuracy * 100:.1f}% in {r.seconds:.0f}s, {r.requests} requests, {r.weights_gb} GB of models, dup kept {r.grade.dup_kept}, dropped {r.grade.dropped}, junk kept {r.grade.junk_kept}")
            results[label] = r
    return FightResult(seed=seed, preset=settings.preset, rows=len(golden), messy_rows=len(messy), dataset_sha=sha, stock=results["stock"], team=results["team"])


def clean_file(team: Team, path: Path, sample: list[dict], chat, on_call) -> Path:
    """Run a team on any CSV. Rows get an id for the pipeline and lose it again on the way out."""
    rows = read_csv(path)
    columns = list(rows[0].keys()) if rows else []
    had_id = "id" in columns
    for i, r in enumerate(rows):
        if not had_id:
            r["id"] = f"R{i + 1:05d}"
    cleaned, _ = run_team(team, rows, sample, chat, on_call)
    out = path.with_name(path.stem + ".clean.csv")
    write_csv(out, cleaned, columns if had_id else [c for c in columns if c != "id"])
    return out
