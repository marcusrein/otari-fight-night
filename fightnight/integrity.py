"""Integrity signals for the fight card. None of these stop a determined cheat; the organizer's
rerun on a seed nobody has seen does that. They make the cheap tricks visible on the card."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

from .corrupt import COLUMNS
from .team import Team

_DATASET_ID = re.compile(r"\bT\d{4}\b")  # golden ids; the shipped sample uses S0001.. on purpose
CODE_FILES = ("corrupt.py", "grade.py", "pipeline.py", "referee.py", "team.py", "card.py", "otari.py", "integrity.py")


def referee_fingerprint() -> dict:
    """sha256 over the referee's own source, plus the git commit when there is one. A card made
    with an edited grader shows a code sha the organizers do not recognize."""
    here = Path(__file__).parent
    digest = hashlib.sha256()
    for name in CODE_FILES:
        p = here / name
        if p.exists():
            digest.update(name.encode() + b"\0" + p.read_bytes() + b"\0")
    git = "unknown"
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5, cwd=here).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "fightnight"], capture_output=True, text=True, timeout=5, cwd=here).stdout.strip()
        if head:
            git = head + (" (modified)" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        pass
    return {"code_sha256": digest.hexdigest()[:12], "git": git, "files": list(CODE_FILES)}


def prompt_leaks(team: Team, golden: list[dict]) -> list[str]:
    """Signs that a prompt carries the answer key: dataset ids, or a golden row's vendor, amount
    and category together on one line. Public knowledge (vendor to category, formats) is allowed
    and does not trip this."""
    notes: list[str] = []
    seen: set[Path] = set()
    rows = {(g["vendor"], g["amount"], g["category"]) for g in golden}
    for st in team.stages:
        if st.prompt is None or st.prompt in seen:
            continue
        seen.add(st.prompt)
        text = st.prompt.read_text(errors="replace")
        ids = sorted(set(_DATASET_ID.findall(text)))
        if ids:
            notes.append(f"{st.prompt.name}: mentions dataset id(s) {', '.join(ids[:5])}{'...' if len(ids) > 5 else ''}")
        hits = 0
        for line in text.splitlines():
            for vendor, amount, category in rows:
                if vendor in line and amount in line and category in line:
                    hits += 1
                    break
        if hits:
            notes.append(f"{st.prompt.name}: {hits} line(s) match a golden row of this dataset")
    return notes


def prompt_bytes(team: Team) -> int:
    return sum(st.prompt.stat().st_size for st in {s.prompt: s for s in team.stages if s.prompt}.values())
