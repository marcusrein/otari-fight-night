"""Settings come from .env (created by `make fight` on first run) and the environment."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

ENV_PATH = Path(".env")
EXAMPLE_PATH = Path(".env.example")


def read_env_file(path: Path = ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def new_otari_key() -> str:
    """Otari API keys are 'tk-' plus at least 47 url-safe characters."""
    return "tk-" + secrets.token_urlsafe(48)


def init_env(example: Path = EXAMPLE_PATH, target: Path = ENV_PATH) -> bool:
    """Write .env from .env.example with fresh keys. Returns False if .env already exists."""
    if target.exists():
        return False
    text = example.read_text()
    text = text.replace("OTARI_MASTER_KEY=__GENERATED__", f"OTARI_MASTER_KEY=sk-otari-admin-{secrets.token_urlsafe(24)}")
    text = text.replace("FIGHTER_A_KEY=__GENERATED__", f"FIGHTER_A_KEY={new_otari_key()}")
    text = text.replace("FIGHTER_B_KEY=__GENERATED__", f"FIGHTER_B_KEY={new_otari_key()}")
    target.write_text(text)
    return True


@dataclass
class Settings:
    fighter_a: str
    fighter_b: str
    master_key: str
    key_a: str
    key_b: str
    otari_url: str
    ollama_url: str
    rounds: int
    seed: int | None
    max_guesses: int
    timeout_seconds: float
    max_tokens: int
    code_length: int
    max_digit: int

    @classmethod
    def load(cls) -> "Settings":
        env = {**read_env_file(), **os.environ}

        def get(name: str, default: str = "") -> str:
            return env.get(name, default) or default

        seed_raw = get("SEED")
        return cls(
            fighter_a=get("FIGHTER_A", "llama3.2:3b"),
            fighter_b=get("FIGHTER_B", "qwen2.5:3b"),
            master_key=get("OTARI_MASTER_KEY"),
            key_a=get("FIGHTER_A_KEY"),
            key_b=get("FIGHTER_B_KEY"),
            otari_url=get("OTARI_URL", "http://localhost:8000").rstrip("/"),
            ollama_url=get("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
            rounds=int(get("ROUNDS", "20")),
            seed=int(seed_raw) if seed_raw else None,
            max_guesses=int(get("MAX_GUESSES", "10")),
            timeout_seconds=float(get("TIMEOUT_SECONDS", "60")),
            max_tokens=int(get("MAX_TOKENS", "300")),
            code_length=int(get("CODE_LENGTH", "4")),
            max_digit=int(get("MAX_DIGIT", "6")),
        )
