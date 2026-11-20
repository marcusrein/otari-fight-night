from types import SimpleNamespace

from fightnight.card import build, render_md
from fightnight.referee import Fighter, Guess, Play, Round


def _play(corner, model, cracked, score, seconds, malformed=0):
    guesses = [Guess(i + 1, "1234", [1, 2, 3, 4], 1, 0, seconds / max(score, 1), 10, 2) for i in range(min(score, 10))]
    for i in range(malformed):
        guesses[i].malformed = True
        guesses[i].guess = None
    return Play(corner, model, cracked, score, seconds, guesses)


def _card(cracked_a=True):
    a = Fighter("A", "fighter-a", "model-a", "k")
    b = Fighter("B", "fighter-b", "model-b", "k")
    rounds = [
        Round(1, [1, 2, 3, 4], _play("A", "model-a", cracked_a, 3 if cracked_a else 11, 4.0), _play("B", "model-b", False, 11, 9.0, malformed=1), "a"),
        Round(2, [6, 6, 1, 2], _play("A", "model-a", cracked_a, 5 if cracked_a else 11, 7.0), _play("B", "model-b", False, 11, 3.0), "a" if cracked_a else "b"),
    ]
    usage = {"totals": {"request_count": 20, "error_count": 0, "prompt_tokens": 100, "completion_tokens": 20, "avg_latency_ms": 123.4, "cost": 0.0}}
    settings = SimpleNamespace(max_guesses=10, timeout_seconds=60.0, max_tokens=300, code_length=4, max_digit=6)
    return build(rounds, a, b, usage, usage, {"os": "testOS", "arch": "x", "cpu": "c", "ram_gb": 1, "gpu": "g", "gpu_note": ""}, {"otari_url": "u", "otari_version": "v", "ollama_version": "o"}, 42, settings, "abc123")


def test_build_counts_wins_and_cracks():
    card = _card()
    fa, fb = card["fighters"]
    assert (fa["wins"], fb["wins"]) == (2, 0)
    assert fa["cracked"] == 2 and fb["cracked"] == 0
    assert fa["avg_guesses"] == 4.0 and fa["avg_guesses_when_cracked"] == 4.0
    assert fb["avg_guesses_when_cracked"] is None
    assert fb["malformed_replies"] == 1
    assert card["result"]["record"] == "A 2 - 0 B"
    assert card["result"]["winner"].startswith("A")


def test_render_handles_missing_values_and_cost():
    md = render_md(_card(cracked_a=False))
    assert "| Avg guesses when cracked | n/a | n/a |" in md
    assert "| Cost | $0.00 | $0.00 |" in md
    assert "None" not in md
    assert "SEED=42" in md
