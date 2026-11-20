import json
from pathlib import Path

from fightnight.otari import ChatResult
from fightnight.pipeline import Call, local_share, parse_rows, qualify_model, run_team
from fightnight.team import load_team

ROWS = [{"id": f"T{i:04d}", "date": "2026-01-0%d" % (i % 9 + 1), "vendor": "V", "amount": "1.00", "category": "dining", "note": ""} for i in range(1, 11)]
SAMPLE = ROWS[:2]


def team_from(tmp_path: Path, text: str, prompts=("p",)):
    (tmp_path / "prompts").mkdir(exist_ok=True)
    for p in prompts:
        (tmp_path / "prompts" / f"{p}.md").write_text("Clean these rows. Sample:\n{sample}\n")
    f = tmp_path / "team.yml"
    f.write_text(text)
    return load_team(f)


class FakeChat:
    """Answers with a function of (model, batch rows). Records every call."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def __call__(self, model, messages, max_tokens):
        rows = json.loads(messages[-1]["content"].split("Rows:\n", 1)[1].split("\n\nReturn", 1)[0])
        self.calls.append((model, rows))
        text = self.answer(model, rows)
        provider = model.split(":")[0]
        return ChatResult(content=text, prompt_tokens=10, completion_tokens=5, seconds=0.1, request_id=None, provider=provider, model=model)


def echo(model, rows):
    return json.dumps(rows)


def test_parse_rows_from_fence_and_prose():
    rows = [{"id": "a", "x": "1"}]
    assert parse_rows("Here you go:\n```json\n" + json.dumps(rows) + "\n```\nDone.") == rows
    assert parse_rows("sure " + json.dumps(rows)) == rows
    assert parse_rows("[1, 2] and then " + json.dumps(rows)) == rows  # last array wins
    assert parse_rows("no json here") is None
    assert parse_rows("[1, 2, 3]") is None  # not objects


def test_qualify_model():
    assert qualify_model("qwen2.5:3b") == "ollama:qwen2.5:3b"
    assert qualify_model("llama3.2") == "ollama:llama3.2"
    assert qualify_model("otari-ai:openai/gpt-4o-mini") == "otari-ai:openai/gpt-4o-mini"
    assert qualify_model("ollama:qwen2.5:3b") == "ollama:qwen2.5:3b"


def test_map_batches_and_keeps_rows_on_bad_json(tmp_path):
    team = team_from(tmp_path, "stages:\n  - {name: m, type: map, model: a, batch: 4, prompt: prompts/p.md}\n")
    calls = []

    def answer(model, rows):
        if rows[0]["id"] == "T0005":
            return "I cannot do that"
        return json.dumps([{**r, "vendor": "Fixed"} for r in rows])

    chat = FakeChat(answer)
    out, stats = run_team(team, [dict(r) for r in ROWS], SAMPLE, chat, calls.append)
    assert len(chat.calls) == 3
    assert [r["vendor"] for r in out] == ["Fixed"] * 4 + ["V"] * 4 + ["Fixed"] * 2
    assert [r["id"] for r in out] == [r["id"] for r in ROWS]
    assert stats[0].requests == 3 and stats[0].unparsed == 4 and stats[0].rows == 10
    assert len(calls) == 3 and isinstance(calls[0], Call) and calls[1].unparsed == 4
    assert "sample" not in chat.calls[0][0]  # prompt rendering happened in the system message
    assert "T0001" in chat.calls[0]  [1][0]["id"]


def test_map_prompt_gets_sample_and_rows_have_no_private_keys(tmp_path):
    team = team_from(tmp_path, "stages:\n  - {name: m, type: map, model: a, batch: 10, prompt: prompts/p.md}\n")
    seen = {}

    def answer(model, rows):
        seen["keys"] = set(rows[0])
        return json.dumps(rows)

    chat = FakeChat(answer)

    class Spy(FakeChat):
        def __call__(self, model, messages, max_tokens):
            seen["system"] = messages[0]["content"]
            return super().__call__(model, messages, max_tokens)

    run_team(team, [dict(r) for r in ROWS], SAMPLE, Spy(answer), lambda c: None)
    assert "T0001" in seen["system"] and "{sample}" not in seen["system"]
    assert seen["keys"] == set(ROWS[0])


def test_map_drop_on_real_row_is_refused_and_position_match_beats_rid(tmp_path):
    team = team_from(tmp_path, "stages:\n  - {name: m, type: map, model: a, batch: 10, prompt: prompts/p.md}\n")

    def answer(model, rows):
        out = [dict(r) for r in rows]
        out[0]["drop"] = True
        out[1]["id"] = "GARBLED"  # model mangled the id but count matches, so position wins
        out[1]["vendor"] = "ByPosition"
        return json.dumps(out)

    out, stats = run_team(team, [dict(r) for r in ROWS], SAMPLE, FakeChat(answer), lambda c: None)
    assert len(out) == 10, "a real row with a unique id is never deleted on a model's say-so"
    assert stats[0].refused_drops == 1
    assert out[1]["id"] == "T0002" and out[1]["vendor"] == "ByPosition"
    assert all("drop" not in r for r in out)


def test_map_short_reply_matches_by_id(tmp_path):
    team = team_from(tmp_path, "stages:\n  - {name: m, type: map, model: a, batch: 10, prompt: prompts/p.md}\n")

    def answer(model, rows):
        return json.dumps([{**rows[3], "vendor": "OnlyThisOne"}])

    out, stats = run_team(team, [dict(r) for r in ROWS], SAMPLE, FakeChat(answer), lambda c: None)
    assert len(out) == 10
    assert out[3]["vendor"] == "OnlyThisOne" and out[0]["vendor"] == "V"
    assert stats[0].unparsed == 9


def test_route_splits_and_merges_in_original_order(tmp_path):
    team = team_from(tmp_path, """
stages:
  - {name: triage, type: map, model: t, batch: 10, prompt: prompts/p.md}
  - {name: route, type: route, by: tag, to: {odd: oddfix, "*": other}}
  - {name: oddfix, type: map, model: o, batch: 10, prompt: prompts/p.md}
  - {name: other, type: map, model: e, batch: 10, prompt: prompts/p.md}
""")

    def answer(model, rows):
        if model.endswith(":t"):
            return json.dumps([{**r, "tag": "odd" if int(r["id"][1:]) % 2 else "even"} for r in rows])
        return json.dumps([{**r, "vendor": model.split(":")[-1]} for r in rows])

    chat = FakeChat(answer)
    out, stats = run_team(team, [dict(r) for r in ROWS], SAMPLE, chat, lambda c: None)
    assert [r["id"] for r in out] == [r["id"] for r in ROWS]
    assert [r["vendor"] for r in out] == ["o", "e"] * 5
    models_called = [m for m, _ in chat.calls]
    assert models_called == ["ollama:t", "ollama:o", "ollama:e"], "route targets run once, on their slice only"
    assert [s.name for s in stats] == ["triage", "oddfix", "other"]
    assert stats[1].rows == 5 and stats[2].rows == 5


def test_vote_majority_and_tie_keeps_first(tmp_path):
    team = team_from(tmp_path, "stages:\n  - {name: v, type: vote, models: [a, b, c], column: category, prompt: prompts/p.md}\n")
    votes = {"a": "dining", "b": "groceries", "c": "groceries"}

    def answer(model, rows):
        return json.dumps([{**r, "category": votes[model.split(":")[-1]]} for r in rows])

    out, stats = run_team(team, [dict(r) for r in ROWS], SAMPLE, FakeChat(answer), lambda c: None)
    assert all(r["category"] == "groceries" for r in out)
    assert stats[0].requests == 3 and stats[0].model == "a, b, c"

    votes.update({"a": "dining", "b": "groceries", "c": "rent"})  # three-way tie: first model wins
    out, _ = run_team(team, [dict(r) for r in ROWS], SAMPLE, FakeChat(answer), lambda c: None)
    assert all(r["category"] == "dining" for r in out)


def test_verify_retries_flagged_rows_once(tmp_path):
    team = team_from(tmp_path, "stages:\n  - {name: chk, type: verify, model: a, batch: 10, prompt: prompts/p.md, retry: 1}\n")
    seen_batches = []

    def answer(model, rows):
        seen_batches.append([r["id"] for r in rows])
        out = []
        for r in rows:
            r = dict(r)
            if r["id"] in ("T0002", "T0007") and len(seen_batches) == 1:
                r["flag"] = True
            else:
                r["vendor"] = "Checked"
            out.append(r)
        return json.dumps(out)

    out, stats = run_team(team, [dict(r) for r in ROWS], SAMPLE, FakeChat(answer), lambda c: None)
    assert seen_batches[1] == ["T0002", "T0007"]
    assert all(r["vendor"] == "Checked" for r in out) and all("flag" not in r for r in out)
    assert stats[0].requests == 2


def test_local_share_counts_provider(tmp_path):
    team = team_from(tmp_path, """
stages:
  - {name: a, type: map, model: qwen2.5:3b, batch: 5, prompt: prompts/p.md}
  - {name: b, type: map, model: otari-ai:openai/gpt-4o-mini, batch: 5, prompt: prompts/p.md}
""")
    calls = []
    run_team(team, [dict(r) for r in ROWS], SAMPLE, FakeChat(echo), calls.append)
    assert local_share(calls) == 0.5
    assert calls[0].provider == "ollama" and calls[-1].provider == "otari-ai"


def test_drop_is_only_honored_for_junk_or_duplicates(tmp_path):
    team = team_from(tmp_path, "stages:\n  - {name: m, type: map, model: a, batch: 10, prompt: prompts/p.md}\n")
    rows = [dict(r) for r in ROWS[:4]]
    rows.append(dict(ROWS[0]))  # duplicate id T0001
    rows.append({"id": "", "date": "TOTAL", "vendor": "", "amount": "9", "category": "", "note": ""})  # junk

    def answer(model, rows):
        return json.dumps([{**r, "drop": True} for r in rows])  # model wants to delete everything

    out, stats = run_team(team, rows, SAMPLE, FakeChat(answer), lambda c: None)
    ids = [r["id"] for r in out]
    assert ids == ["T0001", "T0002", "T0003", "T0004"], "junk and one duplicate removed, real rows kept"
    assert stats[0].refused_drops == 4


def test_verify_drop_guard_applies_too(tmp_path):
    team = team_from(tmp_path, "stages:\n  - {name: v, type: verify, model: a, batch: 10, prompt: prompts/p.md}\n")

    def answer(model, rows):
        return json.dumps([{**r, "drop": True} for r in rows])

    out, _ = run_team(team, [dict(r) for r in ROWS], SAMPLE, FakeChat(answer), lambda c: None)
    assert len(out) == 10
