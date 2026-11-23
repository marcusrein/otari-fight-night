import random
from pathlib import Path

from fightnight.corrupt import make_golden
from fightnight.integrity import prompt_leaks, referee_fingerprint
from fightnight.team import Stage, Team


def _team(tmp_path, text):
    p = tmp_path / "p.md"
    p.write_text(text)
    return Team("t", [Stage("a", "map", model="m", prompt=p)], tmp_path / "t.yml", "x")


def test_prompt_leaks_flags_dataset_ids_and_golden_rows(tmp_path):
    golden = make_golden(5, random.Random(1))
    g = golden[2]
    clean = _team(tmp_path, "Fix dates to YYYY-MM-DD. Vendors: Taco Lane -> dining.\n")
    assert prompt_leaks(clean, golden) == []
    with_ids = _team(tmp_path, "When you see T0003 the answer is 2026-01-27.\n")
    leaks = prompt_leaks(with_ids, golden)
    assert any("dataset id" in x for x in leaks)
    with_row = _team(tmp_path, f"Lookup: {g['vendor']},{g['amount']},{g['category']}\n")
    leaks = prompt_leaks(with_row, golden)
    assert any("golden row" in x for x in leaks)


def test_prompt_leaks_ignores_sample_ids(tmp_path):
    golden = make_golden(5, random.Random(7))  # a real fight never uses the sample's seed
    t = _team(tmp_path, "Example clean row: S0001,2026-10-28,Metro Transit,21.90,transport,paid by card\n")
    assert prompt_leaks(t, golden) == []


def test_referee_fingerprint_is_stable_and_names_files():
    a = referee_fingerprint()
    b = referee_fingerprint()
    assert a["code_sha256"] == b["code_sha256"] and len(a["code_sha256"]) == 12
    assert "grade.py" in a["files"] and "pipeline.py" in a["files"]
    assert "git" in a
