# Fight card: Otari Local Model Fight Night

**B (qwen2.5:3b)** takes it, A 2 - 18 B. 20 rounds of Codebreaker, generated 2026-11-20T17:26:12+00:00.

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
| Wins | 2 | 18 |
| Cracked | 1/20 | 0/20 |
| Avg guesses (fail = 11) | 10.55 | 11 |
| Avg guesses when cracked | 2 | n/a |
| Avg seconds per guess | 0.46 | 0.25 |
| Malformed replies | 0 | 0 |
| Timeouts | 0 | 0 |

## Otari usage (from the gateway's own log, per fighter key)

| | A | B |
|---|---|---|
| Requests | 192 | 200 |
| Errors | 0 | 0 |
| Prompt tokens | 73566 | 62500 |
| Completion tokens | 4453 | 1000 |
| Avg gateway latency (ms) | 445 | 230 |
| Cost | $0.00 | $0.00 |

## Rules

4 digits from 1-6, repeats allowed, 10 guesses max, 60s per reply, 300 max tokens. Same secret for both fighters each round, played one after the other. Fewer guesses wins the round, faster total time breaks ties.

Seed `810218` (replay with `SEED=810218 make fight`). Strategy file sha256 `935d8143edb2`.

## Rounds

| # | Secret | A | B | Winner |
|---|---|---|---|---|
| 1 | 4116 | fail (11.0s) | fail (4.1s) | B |
| 2 | 3263 | fail (4.5s) | fail (8.5s) | A |
| 3 | 3241 | fail (4.2s) | fail (2.0s) | B |
| 4 | 5133 | fail (2.2s) | fail (1.9s) | B |
| 5 | 1245 | 2 (0.9s) | fail (1.9s) | A |
| 6 | 2566 | fail (4.4s) | fail (2.0s) | B |
| 7 | 6532 | fail (3.6s) | fail (2.0s) | B |
| 8 | 2366 | fail (3.5s) | fail (2.1s) | B |
| 9 | 4123 | fail (3.7s) | fail (2.1s) | B |
| 10 | 3634 | fail (7.8s) | fail (2.1s) | B |
| 11 | 1522 | fail (2.2s) | fail (2.1s) | B |
| 12 | 2315 | fail (3.5s) | fail (2.1s) | B |
| 13 | 3613 | fail (4.0s) | fail (2.2s) | B |
| 14 | 5666 | fail (6.5s) | fail (2.0s) | B |
| 15 | 3153 | fail (8.1s) | fail (2.1s) | B |
| 16 | 3554 | fail (2.2s) | fail (1.9s) | B |
| 17 | 1665 | fail (5.4s) | fail (2.0s) | B |
| 18 | 5521 | fail (4.3s) | fail (2.1s) | B |
| 19 | 6353 | fail (3.9s) | fail (2.1s) | B |
| 20 | 1556 | fail (3.5s) | fail (2.0s) | B |
