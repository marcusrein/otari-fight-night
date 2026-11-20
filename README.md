# Otari Fight Night

Two local models. One referee. One gateway. Who cracks the code first?

Run [Otari](https://github.com/mozilla-ai/otari) on your own machine in front of two
Ollama models, pit them against each other in 20 rounds of Codebreaker (Mastermind), and
walk away with a fight card that says which model suits your hardware. Nothing leaves your
machine and nothing costs money.

```
Round 7/20  (secret 3516)
  A llama3.1:8b        1234(1/1) 1356(2/2) 3516(4/0)  cracked in 3, 1.4s
  B qwen2.5:7b         1221(1/0) 2321(1/1) 1331(2/0) 4331(1/0) 1431(1/1) 2431(1/1) 1241(1/0) 3241(1/2) 1341(1/0) 2341(1/1)  failed, best 2/0, 2.5s
  -> A wins   [A 4 - 3 B]
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

First run: writes `.env` with generated keys, starts Otari, pulls the two default
models (about 5 GB each, they need 16 GB of RAM together), switches them on in Otari, plays
20 rounds. On an 8 GB machine set the 3B pair in `.env` first (table below). Later runs skip the
slow parts. A quick two-round check:

```bash
ROUNDS=2 make fight
```

No `make`? The same thing is three commands:

```
uv run fight.py init-env
docker compose up -d
uv run fight.py
```

## What you get

- `fight-card.md`: machine specs, both fighters' record, average guesses and seconds per
  guess, malformed replies and timeouts, plus what Otari logged per fighter key. This is
  what you submit.
- `fight-card.json`: the same data for the community "what runs on what" table.
- `fight-log.jsonl`: every guess, raw reply and timing, if you want to dig.
- The Otari dashboard at http://localhost:8000 with one API key per fighter. Sign in with
  the admin key from `make keys`.

## The one lever

Edit `strategy.md`. It is the system prompt both fighters get. Add a worked example, a
scratchpad, a constraint checklist, a fixed opening. The referee reads the last four
digits 1-6 in a reply as the guess, so models can think out loud if the prompt lets them.
Its hash is printed on the fight card so a submission ties to an exact prompt.

## Change fighters

Edit `FIGHTER_A` and `FIGHTER_B` in `.env`. Any model Ollama can pull. Both are kept in
memory at once, so pick a pair that fits your RAM.

| RAM | Pair that fits |
|---|---|
| 8 GB | `llama3.2:3b` vs `qwen2.5:3b` |
| 16 GB (default) | `llama3.1:8b` vs `qwen2.5:7b` |
| 32 GB or a real GPU | `llama3.1:70b`-class or `qwen2.5:32b` vs anything |

Honest warning from the reference machine: with the plain prompt, 3B models never crack a
4-digit code and 7B models rarely do. That is the point. The fight card still ranks them on
how close they got, and the first good edit to `strategy.md` is where the cracks start.

Thinking models (`qwen3`, `deepseek-r1`) tend to burn the 60 second limit reasoning
about digits. Try them, but that is your experiment, not the default.

## Rules

Four digits from 1 to 6, repeats allowed. Ten guesses max. Sixty seconds per reply, and a
reply with no valid guess in it burns a guess. Both fighters play the same secret each
round, one after the other so the machine is not shared. Fewer guesses wins the round. When
neither cracks it, the fighter whose best guess got closer wins (most exact digits, then
most right digits in any position). Only a real tie comes down to speed. Twenty rounds. The secrets come from a seed printed on the
card, so `SEED=12345 make fight` replays the same codes against a different pair.

Everything is tunable in `.env`: `ROUNDS`, `SEED`, `MAX_GUESSES`, `TIMEOUT_SECONDS`,
`MAX_TOKENS`. Twist the game itself with `CODE_LENGTH` and `MAX_DIGIT` (classic is 4 and 6;
`CODE_LENGTH=3 MAX_DIGIT=4` is a 64-code warm-up, `CODE_LENGTH=5 MAX_DIGIT=8` is brutal). The
card records whatever you played.

## Submit

Fill in [SUBMISSION.md](SUBMISSION.md): fight card, strategy file, three friction bullets,
and a link to your write-up or 60-second video.

## How it is wired

```
fight.py ──► Otari (Docker, :8000) ──► Ollama (host, :11434)
   │             two aliases, two scoped keys
   └── referee: holds the secret, scores, times, writes the card
```

- `docker-compose.yml` runs Otari and points it at the host's Ollama.
- `otari.yml` declares the `ollama` hosted provider, aliases `fighter-a` / `fighter-b`,
  and one scoped API key per fighter. You should never need to edit it.
- `fightnight/referee.py` plays the game. `fightnight/game.py` is the rules, with tests.
- `fightnight/otari.py` is the only code that talks to Otari: chat through the fighter
  keys, and one admin step before round one that switches the models on under the
  provider, because a hosted provider from config starts with an empty roster.
- `fightnight/card.py` builds the card, pulling per-key usage from
  `GET /api/v1/key/usage/summary`.

## Troubleshooting

- **Ollama is not answering**: start it. `ollama serve` or open the app. On Linux make
  sure it listens on `0.0.0.0` or that Docker can reach `host.docker.internal`.
- **Otari did not answer within 60s**: `docker compose logs otari`. A bad `.env` (missing
  key) stops it at startup.
- **424 provider_not_configured**: the model is not switched on in Otari. `make fight`
  does this for you, so run it rather than calling the API by hand.
- **Fresh start**: `make clean` removes the containers, the Otari database and the cards.
  Delete `.env` too if you want new keys.

## Tests

```bash
make test
```

Covers the scorer, the guess parser and round comparison. No model needed.

## License

Apache 2.0.
