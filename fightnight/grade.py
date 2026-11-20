"""Score a cleaned CSV against the golden one. Plain code, by id."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from .corrupt import COLUMNS

SCORED = [c for c in COLUMNS if c != "id"]
_DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y.%m.%d", "%d %b %Y", "%B %d, %Y", "%m/%d/%y", "%Y%m%d", "%b %d, %Y", "%d %B %Y", "%Y/%m/%d"]
_AMOUNT = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


@dataclass
class Grade:
    accuracy: float
    per_column: dict[str, float] = field(default_factory=dict)
    dup_kept: int = 0
    dropped: int = 0
    junk_kept: int = 0
    rows_out: int = 0


def normalize(col: str, value) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if col == "date":
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        # 14/03/2026 with day first already covered; try swapping when month > 12 fails above
        return text
    if col == "amount":
        m = _AMOUNT.search(text)
        if m:
            try:
                return f"{float(m.group().replace(',', '')):.2f}"
            except ValueError:
                return text
        return text
    if col == "category":
        return text.lower()
    return text


def grade(golden: list[dict], cleaned: list[dict]) -> Grade:
    by_id: dict[str, list[dict]] = {}
    junk = 0
    for row in cleaned:
        if not isinstance(row, dict):
            junk += 1
            continue
        rid = row.get("id")
        rid = str(rid).strip() if rid is not None else ""
        if not rid:
            junk += 1
            continue
        by_id.setdefault(rid, []).append(row)

    total_cells = len(golden) * len(SCORED) + junk * len(SCORED)
    correct_cells = 0
    col_correct = {c: 0 for c in SCORED}
    dup_kept = dropped = 0
    golden_ids = set()
    for g in golden:
        golden_ids.add(g["id"])
        rows = by_id.get(g["id"], [])
        if not rows:
            dropped += 1
            continue
        if len(rows) > 1:
            dup_kept += len(rows) - 1
            continue  # a duplicated id scores zero
        row = rows[0]
        for c in SCORED:
            if normalize(c, row.get(c, "")) == normalize(c, g[c]):
                correct_cells += 1
                col_correct[c] += 1
    # rows with ids the golden never had are junk too
    junk += sum(len(v) for k, v in by_id.items() if k not in golden_ids)
    total_cells = len(golden) * len(SCORED) + junk * len(SCORED)
    n = max(len(golden), 1)
    return Grade(
        accuracy=correct_cells / total_cells if total_cells else 0.0,
        per_column={c: col_correct[c] / n for c in SCORED},
        dup_kept=dup_kept,
        dropped=dropped,
        junk_kept=junk,
        rows_out=len(cleaned),
    )
