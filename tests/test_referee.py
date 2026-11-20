from pathlib import Path

from fightnight.referee import model_weights
from fightnight.team import Stage, Team


def test_model_weights_strip_provider_prefix_and_ignore_hosted():
    team = Team("t", [Stage("a", "map", model="ollama:qwen2.5:3b", prompt=Path("p")), Stage("b", "map", model="llama3.2:3b", prompt=Path("p")), Stage("c", "map", model="otari-ai:openai/gpt-oss-120b", prompt=Path("p"))], Path("t.yml"), "x")
    assert model_weights(team, {"qwen2.5:3b": 1.9, "llama3.2:3b": 2.0}) == 3.9
