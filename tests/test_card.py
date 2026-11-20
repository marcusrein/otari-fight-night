from pathlib import Path
from types import SimpleNamespace

from fightnight.card import build, render_md
from fightnight.grade import Grade
from fightnight.pipeline import StageStats
from fightnight.referee import FightResult, TeamResult
from fightnight.team import Stage, Team


def _team(name, model):
    return Team(name=name, stages=[Stage(name="clean", type="map", model=model, prompt=Path("p.md"))], path=Path(f"{name}.yml"), sha256="abc123def456")


def _result(name, model, acc, local=1.0, cracked_cols=None):
    pct = round(acc * 100, 1)
    grade = Grade(repair_pct=pct, problems=200, fixed=int(acc * 200), broken=3, accuracy=acc, per_column={"date": pct, "vendor": pct, "amount": pct, "category": pct, "note": pct}, dup_kept=1, dropped=2, junk_kept=0, rows_out=298)
    stats = [StageStats("clean", model, requests=30, rows=300, seconds=40.0, unparsed=3, prompt_tokens=1000, completion_tokens=500, local_requests=int(30 * local))]
    usage = {"totals": {"request_count": 30, "error_count": 0, "prompt_tokens": 1000, "completion_tokens": 500, "avg_latency_ms": 1333.3, "cost": 0.0}}
    return TeamResult(team=_team(name, model), grade=grade, stages=stats, seconds=40.0, requests=30, local_share=local, weights_gb=1.9, usage=usage)


def _fight(team_acc=0.82, stock_acc=0.61, local=1.0):
    return FightResult(seed=42, preset="medium", rows=300, messy_rows=340, dataset_sha="feedbeef", stock=_result("stock", "qwen2.5:3b", stock_acc), team=_result("my-team", "llama3.2:3b", team_acc, local))


def test_card_delta_and_local_share():
    card = build(_fight(), {"os": "testOS", "arch": "x", "cpu": "c", "ram_gb": 16, "gpu": "g", "gpu_note": ""}, {"otari_url": "u", "otari_version": "v", "ollama_version": "o"})
    assert card["result"]["delta_points"] == 21.0
    assert card["result"]["winner"] == "my-team"
    assert card["team"]["repair_pct"] == 82.0 and card["stock"]["repair_pct"] == 61.0
    assert card["team"]["repair_per_gb"] == round(82.0 / 1.9, 1)
    assert card["team"]["local_requests_pct"] == 100.0
    assert card["team"]["problems"] == 200 and card["team"]["broken"] == 3
    assert card["dataset"] == {"seed": 42, "preset": "medium", "rows": 300, "messy_rows": 340, "sha256": "feedbeef"}
    assert card["team"]["sha256"] == "abc123def456"


def test_render_has_stage_table_and_no_None():
    md = render_md(build(_fight(local=0.5), {"os": "t", "arch": "x", "cpu": "c", "ram_gb": 16, "gpu": "g", "gpu_note": ""}, {"otari_url": "u", "otari_version": "v", "ollama_version": "o"}))
    assert "None" not in md
    assert "| clean | llama3.2:3b | 30 | 300 | 40.0 | 3 |" in md
    assert "+21.0" in md
    assert "50%" in md  # local requests
    assert "Repair rate per column, stock" in md and "Repair rate per column, yours" in md
    assert "SEED=42" in md


def test_render_marks_stock_win():
    md = render_md(build(_fight(team_acc=0.5, stock_acc=0.6), {"os": "t", "arch": "x", "cpu": "c", "ram_gb": 16, "gpu": "g", "gpu_note": ""}, {"otari_url": "u", "otari_version": "v", "ollama_version": "o"}))
    assert "-10.0" in md and "stock" in md.lower()


def test_render_shows_small_hosted_costs():
    from fightnight.card import _usd
    assert _usd(0) == "$0.00" and _usd(None) == "$0.00"
    assert _usd(0.000773) == "$0.0008"
    assert _usd(1.5) == "$1.50"
