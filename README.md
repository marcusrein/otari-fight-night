# Otari Fight Night

Two teams of local models. One messy spreadsheet. One gateway. Whose split of the job cleans it best on your machine?

Run [Otari](https://github.com/mozilla-ai/otari) on your own machine as the router in front of a small
team of Ollama models, point the team at a deliberately terrible CSV, and get a fight card that says
how your team did against the stock team on the same file, on the same hardware. Nothing leaves your
machine unless you decide it should, and the card proves it from Otari's own usage log.

```
Otari Fight Night: CSV cleanup
  stock: teams/stock.yml (qwen2.5:3b)
  yours: team.yml (qwen2.5:3b, llama3.2:3b)
  dataset: 100 clean rows -> 114 messy rows, preset medium, seed 48121
  stock (stock): 71.4% in 142s, 20 requests, 1.93 GB of models, dup kept 1, dropped 0, junk kept 2
  team (triage-and-route): 78.9% in 201s, 31 requests, 3.95 GB of models, dup kept 0, dropped 0, junk kept 1

triage-and-route 78.9% vs stock 71.4%: +7.5 points.
```

## You need

- [Ollama](https://ollama.com) running on the host (`ollama serve`, or the app)
- Docker (Desktop or Engine with compose)
- [uv](https://docs.astral.sh/uv/)
- `make` (macOS and Linux have it; Windows see below)

## Run it

```bash
make fight
```

First run: writes `.env` with generated keys, starts Otari, pulls the models your team files name
(the defaults are about 2 GB each), switches them on in Otari, generates the messy file, runs the
stock team, runs yours, grades both, writes the card. A quick check:

```bash
ROWS=20 make fight
```

No `make`? The same thing is three commands:

```
uv run fight.py init-env
docker compose up -d
uv run fight.py
```

## What you get

- `fight-card.md`: machine specs, stock vs yours (net repair, delta, problems fixed, clean cells
  broken, duplicates kept, rows dropped, junk kept, seconds, requests, model weights loaded,
  repair per GB, share of requests served locally), Otari's own per-key usage, and a
  stage-by-stage table for your team. This is what you
  submit.
- `fight-card.json`: the same data for the community "what runs on what" table.
- `fight-log.jsonl`: every request (stage, model, provider, rows in and out, seconds, tokens).
- `data/team.clean.csv` and `data/stock.clean.csv` next to `data/messy.csv` and `data/golden.csv`,
  so you can diff what each team got wrong.
- The Otari dashboard at http://localhost:8000 with one API key per team. Sign in with the admin
  key from `make keys`.

## The one lever: `team.yml`

Rows flow through stages in order. Four stage types, no code:

```yaml
name: triage-and-route
stages:
  - name: triage          # tag each row with what is wrong with it
    type: map
    model: qwen2.5:3b
    batch: 15
    prompt: prompts/triage.md
  - name: route           # send each tag to a specialist
    type: route
    by: tag
    to: {junk: junk, date: dates, "*": cleaner}
  - name: junk
    type: map
    model: qwen2.5:3b
    batch: 20
    prompt: prompts/clean.md
  - name: dates
    type: map
    model: llama3.2:3b
    batch: 10
    prompt: prompts/dates.md
  - name: cleaner
    type: map
    model: qwen2.5:3b
    batch: 5
    prompt: prompts/clean.md
  - name: check           # a second model re-reads everything against the clean sample
    type: verify
    model: llama3.2:3b
    batch: 10
    prompt: prompts/check.md
    retry: 1
```

| Type | What it does | Knobs |
|---|---|---|
| `map` | One model gets rows in batches and returns them corrected. It may add keys (like `tag`) or mark junk and duplicates `"drop": true`. | `model`, `batch`, `prompt` |
| `route` | Splits rows by a column's value and sends each group to a named stage. Those stages run only on their group. `"*"` catches the rest. | `by`, `to` |
| `vote` | Several models answer for one column. Majority wins, ties go to the first model. | `models`, `column`, `prompt`, `batch` |
| `verify` | One model re-checks rows with the clean sample in view. Rows it marks `"flag": true` are re-sent `retry` times. | `model`, `prompt`, `batch`, `retry` |

Prompts are markdown files. `{sample}` in a prompt is replaced by 20 clean reference rows. The
referee reads the last JSON array in each reply. Things the models cannot do, by design: change an
id, or delete a real row. A `drop` is honored only for a row with no id (junk) or an id another row
shares (a duplicate). The card counts how often a model tried anyway.

Any model Ollama can pull works and is pulled on first use. Both teams' models are loaded
during a fight, so pick a set that fits your RAM.

| RAM | Fits |
|---|---|
| 8 GB | one 3B model, or two 1B-2B |
| 16 GB | two 3B, or one 7B/8B |
| 32 GB or a real GPU | 7B/8B pairs, a 14B |

## Bring your own CSV

```bash
make clean FILE=~/Downloads/bank-export.csv
```

Runs your team on any CSV and writes `bank-export.clean.csv` beside it. No grading, no golden
file. This is the tool you keep after the fight. Without an id column the referee assigns ids on
the way in, so models may remove exact duplicate rows, repeated header rows and empty rows, and
nothing else: a row with data in it is never deleted on a model's say-so. Prompts that know about dates, vendors and
categories will need editing for other shapes of data, which is the point.

## Rules and scoring

The messy file is generated from a seed: 50 synthetic transaction rows by default (`ROWS=` for more) (id, date, vendor, amount,
category, note) with seven date formats, random casing and spacing, currency symbols, category
synonyms, exact and near duplicates, blanks, curly quotes, swapped columns, and junk rows
(repeated headers, a TOTAL row, dashes). `PRESET=easy|medium|brutal` sets the rates.

Score is net repair: of the problems in the messy file (every cell that differs from the golden
file, each extra duplicate copy, each junk row), how many the team fixed, minus clean cells it
broke, as a percentage of the problems. Comparison is exact, so `03/14/2026` is not credit for
`2026-03-14`. Doing nothing scores 0. Wrecking clean data goes negative. A real row dropped
counts as five broken cells. The card also shows per-column repair rates for both teams.

The headline is the delta: your team minus the stock team, same file, same machine. Raw scores are
not comparable across machines, and the card does not pretend they are. `SEED=12345 make fight`
replays the exact file. `ROWS`, `PRESET`, `TEAM`, `STOCK`, `TIMEOUT_SECONDS` are all in `.env`.

## Judging

Out of 100, scored from the card, the team file, the log and your write-up:

| Criterion | Points | What judges look for |
|---|---|---|
| Beat the stock team | 30 | The net-repair delta on your machine, and whether it holds on a second seed |
| Architecture story | 25 | Why this split. The log should show the stages mattered |
| Pound for pound | 20 | Net repair per GB of local model weights, and seconds |
| Show and tell | 15 | A write-up, post or 60-second video worth sharing |
| Friction log | 10 | Three specific things that slowed you down |

The scoring seed is announced when submissions close. The top five team files are rerun live on
the host machine for the bracket, so a bracket team has to fit in 16 GB.

## Stretch goals

- **Frontier through the same gateway.** With an [otari.ai](https://otari.ai) key in `.env` as
  `OTARI_AI_KEY`, any stage can use `model: otari-ai:openai/gpt-oss-120b`. Same team file, same
  referee, same dashboard. Those requests cost money, and the card's "requests served locally"
  drops below 100%, which judges will notice. Hosted reasoning models spend the per-request token
  budget thinking, so check the "broken rows" column before you trust a hosted stage. The interesting version is a stage that touches
  no rows at all: a coach that reads the scores and rewrites a prompt. Not built yet; that is
  round two.
- **Connectors.** A Sheets export or a bank download is a CSV. If you wire a real source up,
  show it in the video.

## Submit

Fill in [SUBMISSION.md](SUBMISSION.md): fight card, team file and prompts, three friction bullets,
and a link to your write-up or video.

## How it is wired

```
fight.py ──► Otari (Docker, :8000) ──► Ollama (host, :11434)
   │             one scoped key per team          └─► otari.ai (optional, hosted provider)
   └── referee: makes the messy file, runs stock then yours, grades, writes the card
```

- `docker-compose.yml` runs Otari and points it at the host's Ollama.
- `otari.yml` declares the `ollama` hosted provider and the two scoped keys. You should never
  need to edit it.
- `fightnight/corrupt.py` makes golden and messy files. `fightnight/grade.py` scores. Both plain
  code, both tested.
- `fightnight/pipeline.py` runs a team file. `fightnight/team.py` validates one.
- `fightnight/otari.py` is the only code that talks to Otari: chat through the team keys, and
  an admin step before a fight that switches the models on under the provider, because a hosted
  provider declared in config starts with an empty roster. Every response's `otari-provider`
  header is what the "requests served locally" share is computed from. A timeout or gateway
  error on one request keeps those rows as they were and counts the request as failed; a
  424 or 401 (misconfiguration) stops the fight with the message.
- `fightnight/card.py` builds the card, pulling per-key usage from
  `GET /api/v1/key/usage/summary`.

## Troubleshooting

- **Ollama is not answering**: start it. `ollama serve` or open the app. On Linux make sure Docker
  can reach `host.docker.internal` (compose maps it to the host gateway).
- **Otari did not answer within 60s**: `docker compose logs otari`. A bad `.env` stops it at
  startup.
- **424 provider_not_configured**: the model is not switched on in Otari. `make fight` does this
  for you, so run it rather than calling the API by hand.
- **Slow**: 3B models write about one row per second. `ROWS=20` for iteration, bigger batches for
  fewer round trips, smaller batches when a model loses rows.
- **Fresh start**: `make reset` removes the containers, the Otari database, the generated data
  and the cards. Delete `.env` too if you want new keys.

## Tests

```bash
make test
```

Generator, grader, team loader, pipeline (with a fake gateway), card. No model needed.

## License

Apache 2.0.
