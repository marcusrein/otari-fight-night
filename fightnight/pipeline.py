"""Run a team file over rows. Four stage types, no code in the team file.

Rows flow through the stages in file order. A stage that a `route` names as a target is
owned by that route: it runs once, on its slice, and not again in the main sequence.
Models return rows as a JSON array; rows they lose or break stay as they were.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from .corrupt import COLUMNS
from .otari import ChatResult
from .team import Stage, Team

PROVIDERS = {"ollama", "otari-ai"}
PRIVATE_KEYS = {"drop", "flag", "_pos"}
MAX_TOKENS_PER_ROW = 120
_ARRAY = re.compile(r"\[\s*\{.*?\}\s*\]", re.S)

ChatFn = Callable[[str, list[dict], int], ChatResult]


@dataclass
class Call:
    stage: str
    model: str
    provider: str
    rows_in: int
    rows_out: int
    seconds: float
    prompt_tokens: int
    completion_tokens: int
    unparsed: int


@dataclass
class StageStats:
    name: str
    model: str
    requests: int = 0
    rows: int = 0
    seconds: float = 0.0
    unparsed: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    local_requests: int = 0


def qualify_model(model: str) -> str:
    """`qwen2.5:3b` -> `ollama:qwen2.5:3b`; a string that already names a provider is left alone."""
    head = model.split(":", 1)[0]
    return model if head in PROVIDERS else f"ollama:{model}"


def parse_rows(text: str) -> list[dict] | None:
    """The last JSON array of objects in a reply, fences and prose allowed."""
    candidates = _ARRAY.findall(text or "")
    for raw in reversed(candidates):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # greedy fallback: from this '[' to the last ']' in the text
            start = text.rfind(raw)
            end = text.rfind("]")
            try:
                data = json.loads(text[start:end + 1])
            except (json.JSONDecodeError, ValueError):
                continue
        if isinstance(data, list) and data and all(isinstance(x, dict) for x in data):
            return data
    return None


def local_share(calls: list[Call]) -> float:
    return sum(1 for c in calls if c.provider == "ollama") / len(calls) if calls else 1.0


def _sample_csv(sample: list[dict]) -> str:
    cols = [c for c in COLUMNS if c in (sample[0] if sample else {})] or COLUMNS
    lines = [",".join(cols)] + [",".join(str(r.get(c, "")) for c in cols) for r in sample]
    return "\n".join(lines)


def _public(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in PRIVATE_KEYS}


class Runner:
    def __init__(self, team: Team, sample: list[dict], chat: ChatFn, on_call: Callable[[Call], None]):
        self.team = team
        self.sample_text = _sample_csv(sample)
        self.chat = chat
        self.on_call = on_call
        self.stats: dict[str, StageStats] = {}
        self._prompts: dict[str, str] = {}

    def prompt(self, stage: Stage) -> str:
        key = str(stage.prompt)
        if key not in self._prompts:
            self._prompts[key] = stage.prompt.read_text().replace("{sample}", self.sample_text).strip()
        return self._prompts[key]

    def ask(self, stage: Stage, model: str, system: str, rows: list[dict], extra: str = "") -> tuple[list[dict], int]:
        """One request. Returns (rows after the model, unparsed count). Rows keep their order and count."""
        public = [_public(r) for r in rows]
        user = "Rows:\n" + json.dumps(public, ensure_ascii=False) + "\n\nReturn the corrected rows as a JSON array of objects with the same keys" + (extra or "") + "."
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        qualified = qualify_model(model)
        res = self.chat(qualified, messages, MAX_TOKENS_PER_ROW * len(rows) + 200)
        parsed = parse_rows(res.content)
        merged, unparsed = _merge(rows, parsed)
        st = self.stats.setdefault(stage.name, StageStats(stage.name, ", ".join(stage.all_models())))
        st.requests += 1
        st.seconds += res.seconds
        st.unparsed += unparsed
        st.prompt_tokens += res.prompt_tokens
        st.completion_tokens += res.completion_tokens
        provider = res.provider or qualified.split(":", 1)[0]
        st.local_requests += 1 if provider == "ollama" else 0
        self.on_call(Call(stage.name, model, provider, len(rows), len(parsed) if parsed else 0, res.seconds, res.prompt_tokens, res.completion_tokens, unparsed))
        return merged, unparsed

    def run_stage(self, stage: Stage, rows: list[dict]) -> list[dict]:
        if stage.type == "map":
            return self._map(stage, rows)
        if stage.type == "vote":
            return self._vote(stage, rows)
        if stage.type == "verify":
            return self._verify(stage, rows)
        if stage.type == "route":
            return self._route(stage, rows)
        raise ValueError(stage.type)

    def _batches(self, stage: Stage, rows: list[dict]):
        for i in range(0, len(rows), stage.batch):
            yield rows[i:i + stage.batch]

    def _map(self, stage: Stage, rows: list[dict]) -> list[dict]:
        out: list[dict] = []
        system = self.prompt(stage)
        for batch in self._batches(stage, rows):
            merged, _ = self.ask(stage, stage.model, system, batch, '. A row that should be removed gets "drop": true')
            out.extend(r for r in merged if not _truthy(r.get("drop")))
        self.stats[stage.name].rows += len(rows)
        return [_strip(r, {"drop"}) for r in out]

    def _vote(self, stage: Stage, rows: list[dict]) -> list[dict]:
        system = self.prompt(stage)
        out: list[dict] = []
        for batch in self._batches(stage, rows):
            answers = []
            for model in stage.models:
                merged, _ = self.ask(stage, model, system, batch, f', changing only "{stage.column}"')
                answers.append([str(r.get(stage.column, "")) for r in merged])
            for i, row in enumerate(batch):
                votes = [a[i] for a in answers]
                counts = Counter(votes)
                top = max(counts.values())
                winner = next(v for v in votes if counts[v] == top)  # first model breaks ties
                row[stage.column] = winner
                out.append(row)
        self.stats.setdefault(stage.name, StageStats(stage.name, ", ".join(stage.models))).rows += len(rows)
        return out

    def _verify(self, stage: Stage, rows: list[dict]) -> list[dict]:
        system = self.prompt(stage) + "\n\nReference sample of clean rows:\n" + self.sample_text
        extra = '. Fix what you can; a row you are unsure about gets "flag": true; a row that should be removed gets "drop": true'
        out: list[dict] = []
        for batch in self._batches(stage, rows):
            merged, _ = self.ask(stage, stage.model, system, batch, extra)
            out.extend(merged)
        for _ in range(stage.retry):
            flagged = [r for r in out if _truthy(r.get("flag"))]
            if not flagged:
                break
            for r in flagged:
                r.pop("flag", None)
            for batch in self._batches(stage, flagged):
                self.ask(stage, stage.model, system, batch, extra)  # mutates the row objects in place
        out = [r for r in out if not _truthy(r.get("drop"))]
        self.stats[stage.name].rows += len(rows)
        return [_strip(r, {"drop", "flag"}) for r in out]

    def _route(self, stage: Stage, rows: list[dict]) -> list[dict]:
        """Split rows by a column, run each target stage on its slice, merge back in original order."""
        slices: dict[str, list[dict]] = {}
        for i, row in enumerate(rows):
            row["_pos"] = i
            value = str(row.get(stage.by, "")).strip()
            target = stage.to.get(value) or stage.to.get("*") or ""
            slices.setdefault(target, []).append(row)
        merged: list[dict] = []
        for target, part in slices.items():
            merged.extend(part if target == "" else self.run_stage(self.team.stage(target), part))
        merged.sort(key=lambda r: r.get("_pos", 0))
        return [_strip(r, {"_pos"}) for r in merged]


def _truthy(v) -> bool:
    return v is True or str(v).strip().lower() in ("true", "yes", "1")


def _strip(row: dict, keys: set[str]) -> dict:
    return {k: v for k, v in row.items() if k not in keys}


def _merge(rows: list[dict], parsed: list[dict] | None) -> tuple[list[dict], int]:
    """Apply a model's answer to the rows it was sent.

    Same count: match by position (small models mangle ids more often than they reorder).
    Otherwise match by id; rows with no answer stay as they were and count as unparsed.
    Returned rows keep the original object's identity so callers can track them.
    """
    if not parsed:
        return rows, len(rows)
    if len(parsed) == len(rows):
        for row, ans in zip(rows, parsed):
            _apply(row, ans)
        return rows, 0
    by_id = {str(a.get("id", "")).strip(): a for a in parsed if str(a.get("id", "")).strip()}
    unparsed = 0
    for row in rows:
        ans = by_id.get(str(row.get("id", "")).strip())
        if ans is None:
            unparsed += 1
        else:
            _apply(row, ans)
    return rows, unparsed


def _apply(row: dict, ans: dict) -> None:
    rid = row.get("id")
    for k, v in ans.items():
        row[k] = v if not isinstance(v, (dict, list)) else json.dumps(v)
    row["id"] = rid  # the id is never the model's to change


def run_team(team: Team, rows: list[dict], sample: list[dict], chat: ChatFn, on_call: Callable[[Call], None]) -> tuple[list[dict], list[StageStats]]:
    runner = Runner(team, sample, chat, on_call)
    owned = {target for s in team.stages if s.type == "route" for target in s.to.values()}
    current = rows
    for stage in team.stages:
        if stage.name in owned:
            continue
        current = runner.run_stage(stage, current)
    order = [s.name for s in team.stages]
    stats = sorted(runner.stats.values(), key=lambda s: order.index(s.name))
    return [_strip(r, PRIVATE_KEYS) for r in current], stats
