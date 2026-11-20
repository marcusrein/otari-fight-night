import random
import re

from fightnight.corrupt import CATEGORIES, COLUMNS, PRESETS, corrupt, make_golden, read_csv, write_csv


def test_golden_is_seeded_and_clean():
    a = make_golden(50, random.Random(3))
    b = make_golden(50, random.Random(3))
    assert a == b
    assert len(a) == 50
    assert [k for k in a[0]] == COLUMNS
    for row in a:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["date"])
        assert re.fullmatch(r"\d+\.\d{2}", row["amount"])
        assert row["category"] in CATEGORIES
        assert row["vendor"] == row["vendor"].strip() and row["vendor"]
    assert len({r["id"] for r in a}) == 50


def test_corrupt_keeps_ids_and_adds_junk():
    golden = make_golden(100, random.Random(5))
    ids = {r["id"] for r in golden}
    easy = corrupt(golden, random.Random(1), "easy")
    brutal = corrupt(golden, random.Random(1), "brutal")
    for rows in (easy, brutal):
        for r in rows:
            assert r["id"] == "" or r["id"] in ids
        assert any(r["id"] == "" for r in rows), "junk rows expected"
        assert set(r["id"] for r in rows if r["id"]) == ids, "every golden id survives"
    assert len(brutal) > len(easy) > 100
    assert set(PRESETS) == {"easy", "medium", "brutal"}
    # it actually corrupted something
    assert sum(1 for g, m in zip(golden, easy) if g != m) > 0


def test_csv_roundtrip(tmp_path):
    rows = make_golden(5, random.Random(0))
    p = tmp_path / "x.csv"
    write_csv(p, rows, COLUMNS)
    assert read_csv(p) == rows
