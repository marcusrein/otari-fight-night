# Fight card: Otari Local Model Fight Night

**B (qwen2.5:7b)** takes it, A 5 - 15 B. 20 rounds of Codebreaker, generated 2026-11-20T17:52:31+00:00.

## Machine

- OS: macOS 26.5.2 (arm64)
- CPU: Apple M2 Pro
- RAM: 16 GB
- GPU: Apple M2 Pro (unified memory)
- Ollama 0.40.2, Otari 0.54.0 at http://localhost:8000

## Fighters

| | A | B |
|---|---|---|
| Model | `llama3.1:8b` | `qwen2.5:7b` |
| Wins | 5 | 15 |
| Cracked | 0/20 | 0/20 |
| Avg guesses (fail = 11) | 11 | 11 |
| Avg guesses when cracked | n/a | n/a |
| Avg seconds per guess | 1.96 | 0.7 |
| Malformed replies | 16 | 3 |
| Timeouts | 0 | 0 |

## Otari usage (from the gateway's own log, per fighter key)

| | A | B |
|---|---|---|
| Requests | 200 | 200 |
| Errors | 0 | 0 |
| Prompt tokens | 90012 | 64703 |
| Completion tokens | 7840 | 1000 |
| Avg gateway latency (ms) | 1924 | 679 |
| Cost | $0.00 | $0.00 |

## Rules

4 digits from 1-6, repeats allowed, 10 guesses max, 60s per reply, 300 max tokens. Same secret for both fighters each round, played one after the other. Fewer guesses wins the round. If neither cracks it, the closer best guess wins (most exact, then most right digits). Only then does speed decide.

Seed `15620` (replay with `SEED=15620 make fight`). Strategy file sha256 `07331cf912c0`.

## Rounds

| # | Secret | A | B | Winner |
|---|---|---|---|---|
| 1 | 6213 | fail, best 1/2 (23.6s) | fail, best 1/2 (7.2s) | B |
| 2 | 3151 | fail, best 2/0 (8.7s) | fail, best 3/0 (6.2s) | B |
| 3 | 3561 | fail, best 3/0 (7.0s) | fail, best 1/1 (6.6s) | A |
| 4 | 4232 | fail, best 2/1 (6.0s) | fail, best 3/0 (7.0s) | B |
| 5 | 6245 | fail, best 1/2 (6.8s) | fail, best 1/2 (6.8s) | B |
| 6 | 3616 | fail, best 2/0 (19.9s) | fail, best 2/0 (7.1s) | B |
| 7 | 1211 | fail, best 2/0 (17.0s) | fail, best 3/0 (6.9s) | B |
| 8 | 3542 | fail, best 1/2 (48.1s) | fail, best 0/4 (6.8s) | A |
| 9 | 4246 | fail, best 1/1 (32.5s) | fail, best 2/0 (7.4s) | B |
| 10 | 3421 | fail, best 2/2 (15.5s) | fail, best 1/2 (7.1s) | A |
| 11 | 1566 | fail, best 1/1 (10.1s) | fail, best 3/0 (7.2s) | B |
| 12 | 2152 | fail, best 2/0 (19.3s) | fail, best 3/0 (7.5s) | B |
| 13 | 5254 | fail, best 3/0 (22.2s) | fail, best 2/0 (7.3s) | A |
| 14 | 6241 | fail, best 1/2 (20.2s) | fail, best 1/2 (7.2s) | B |
| 15 | 1463 | fail, best 2/1 (34.5s) | fail, best 1/2 (7.0s) | A |
| 16 | 3351 | fail, best 2/1 (13.6s) | fail, best 3/0 (8.1s) | B |
| 17 | 5521 | fail, best 1/1 (9.9s) | fail, best 1/1 (6.9s) | B |
| 18 | 5432 | fail, best 1/2 (50.4s) | fail, best 2/2 (6.8s) | B |
| 19 | 1252 | fail, best 2/1 (8.5s) | fail, best 3/0 (6.7s) | B |
| 20 | 3526 | fail, best 1/3 (17.8s) | fail, best 3/0 (6.9s) | B |
