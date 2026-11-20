# Fight card: Otari Local Model Fight Night

**B (qwen2.5:3b)** takes it, A 3 - 17 B. 20 rounds of Codebreaker, generated 2026-11-20T17:41:22+00:00.

## Machine

- OS: macOS 26.5.2 (arm64)
- CPU: Apple M2 Pro
- RAM: 16 GB
- GPU: Apple M2 Pro (unified memory)
- Ollama 0.40.2, Otari 0.54.0 at http://localhost:8000

## Fighters

| | A | B |
|---|---|---|
| Model | `llama3.2:3b` | `qwen2.5:3b` |
| Wins | 3 | 17 |
| Cracked | 0/20 | 0/20 |
| Avg guesses (fail = 11) | 11 | 11 |
| Avg guesses when cracked | n/a | n/a |
| Avg seconds per guess | 0.35 | 0.22 |
| Malformed replies | 0 | 1 |
| Timeouts | 0 | 0 |

## Otari usage (from the gateway's own log, per fighter key)

| | A | B |
|---|---|---|
| Requests | 200 | 200 |
| Errors | 0 | 0 |
| Prompt tokens | 73779 | 64700 |
| Completion tokens | 3109 | 1000 |
| Avg gateway latency (ms) | 334 | 203 |
| Cost | $0.00 | $0.00 |

## Rules

4 digits from 1-6, repeats allowed, 10 guesses max, 60s per reply, 300 max tokens. Same secret for both fighters each round, played one after the other. Fewer guesses wins the round. If neither cracks it, the closer best guess wins (most exact, then most right digits). Only then does speed decide.

Seed `810218` (replay with `SEED=810218 make fight`). Strategy file sha256 `07331cf912c0`.

## Rounds

| # | Secret | A | B | Winner |
|---|---|---|---|---|
| 1 | 4116 | fail, best 2/0 (3.2s) | fail, best 1/2 (2.1s) | A |
| 2 | 3263 | fail, best 1/1 (3.2s) | fail, best 2/0 (2.2s) | B |
| 3 | 3241 | fail, best 1/1 (3.2s) | fail, best 2/2 (2.1s) | B |
| 4 | 5133 | fail, best 2/0 (3.4s) | fail, best 2/0 (2.1s) | B |
| 5 | 1245 | fail, best 1/3 (3.2s) | fail, best 2/1 (2.1s) | B |
| 6 | 2566 | fail, best 1/1 (3.5s) | fail, best 2/0 (2.5s) | B |
| 7 | 6532 | fail, best 3/0 (3.9s) | fail, best 3/0 (2.2s) | B |
| 8 | 2366 | fail, best 1/1 (3.1s) | fail, best 2/0 (2.3s) | B |
| 9 | 4123 | fail, best 2/1 (3.4s) | fail, best 3/0 (2.4s) | B |
| 10 | 3634 | fail, best 1/2 (3.3s) | fail, best 1/2 (2.3s) | B |
| 11 | 1522 | fail, best 1/1 (3.6s) | fail, best 2/0 (2.2s) | B |
| 12 | 2315 | fail, best 1/2 (3.2s) | fail, best 3/0 (2.2s) | B |
| 13 | 3613 | fail, best 1/1 (3.3s) | fail, best 2/0 (2.2s) | B |
| 14 | 5666 | fail, best 1/1 (4.7s) | fail, best 1/1 (2.2s) | B |
| 15 | 3153 | fail, best 2/0 (3.2s) | fail, best 2/0 (2.3s) | B |
| 16 | 3554 | fail, best 2/1 (3.4s) | fail, best 2/0 (2.1s) | A |
| 17 | 1665 | fail, best 0/2 (3.1s) | fail, best 2/0 (2.2s) | B |
| 18 | 5521 | fail, best 3/0 (3.9s) | fail, best 2/1 (2.2s) | A |
| 19 | 6353 | fail, best 2/0 (3.2s) | fail, best 2/0 (2.1s) | B |
| 20 | 1556 | fail, best 1/0 (5.9s) | fail, best 3/0 (2.3s) | B |
