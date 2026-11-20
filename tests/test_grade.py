import random

from fightnight.corrupt import make_golden
from fightnight.grade import grade, normalize


def test_normalize_dates_and_amounts():
    for raw in ("03/14/2026", "14 Mar 2026", "2026.03.14", "March 14, 2026", "14/03/2026", " 2026-03-14 "):
        assert normalize("date", raw) == "2026-03-14", raw
    assert normalize("amount", "$1,234.5") == "1234.50"
    assert normalize("amount", "1234") == "1234.00"
    assert normalize("amount", "USD 12.345") == "12.35"
    assert normalize("category", " Food & Dining ") == "food & dining"
    assert normalize("vendor", "  Acme  Corp ") == "Acme Corp"
    assert normalize("date", "not a date") == "not a date"


def test_grade_perfect_is_one():
    golden = make_golden(10, random.Random(1))
    g = grade(golden, [dict(r) for r in golden])
    assert g.accuracy == 1.0
    assert g.dup_kept == 0 and g.dropped == 0 and g.junk_kept == 0
    assert all(v == 1.0 for v in g.per_column.values())
    assert set(g.per_column) == {"date", "vendor", "amount", "category", "note"}


def test_grade_duplicate_and_dropped_and_junk():
    golden = make_golden(10, random.Random(1))
    cleaned = [dict(r) for r in golden]
    cleaned.append(dict(golden[0]))  # duplicate kept
    cleaned.pop(1)  # one dropped
    cleaned.append({"id": "", "date": "TOTAL", "vendor": "", "amount": "999", "category": "", "note": ""})
    g = grade(golden, cleaned)
    assert g.dup_kept == 1 and g.dropped == 1 and g.junk_kept == 1
    # 10 ids x 5 cells; id 0 scores 0 (dup), id 1 scores 0 (dropped), junk costs a full row
    assert abs(g.accuracy - (8 * 5) / (10 * 5 + 5)) < 1e-9
    assert g.rows_out == len(cleaned)


def test_grade_tolerates_formatting_differences():
    golden = make_golden(3, random.Random(2))
    cleaned = [dict(r) for r in golden]
    cleaned[0]["amount"] = "$" + cleaned[0]["amount"]
    cleaned[1]["category"] = cleaned[1]["category"].upper()
    assert grade(golden, cleaned).accuracy == 1.0


def test_grade_never_crashes_on_garbage():
    golden = make_golden(4, random.Random(2))
    g = grade(golden, [{"id": golden[0]["id"]}, {"nonsense": 1}, {"id": None}])
    assert 0.0 <= g.accuracy < 1.0
    assert g.dropped == 3
