"""Build the fight card from the rounds the referee played and what Otari logged."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from .referee import Fighter, Round, fmt


def _side(rounds: list[Round], corner: str) -> list:
    return [r.a if corner == "a" else r.b for r in rounds]


def fighter_stats(rounds: list[Round], corner: str, fighter: Fighter, usage: dict) -> dict:
    plays = _side(rounds, corner)
    other = "b" if corner == "a" else "a"
    guesses = [g for p in plays for g in p.guesses]
    timed = [g.seconds for g in guesses if not g.timed_out]
    totals = usage.get("totals", {})
    return {
        "corner": corner.upper(),
        "model": fighter.model,
        "otari_alias": fighter.alias,
        "wins": sum(1 for r in rounds if r.winner == corner),
        "losses": sum(1 for r in rounds if r.winner == other),
        "ties": sum(1 for r in rounds if r.winner == "tie"),
        "cracked": sum(1 for p in plays if p.cracked),
        "avg_guesses": round(mean(p.score for p in plays), 2) if plays else None,
        "avg_guesses_when_cracked": round(mean(p.score for p in plays if p.cracked), 2) if any(p.cracked for p in plays) else None,
        "avg_seconds_per_guess": round(mean(timed), 2) if timed else None,
        "total_seconds": round(sum(p.seconds for p in plays), 1),
        "malformed_replies": sum(p.malformed for p in plays),
        "timeouts": sum(p.timeouts for p in plays),
        "otari_usage": {
            "requests": totals.get("request_count"),
            "errors": totals.get("error_count"),
            "prompt_tokens": totals.get("prompt_tokens"),
            "completion_tokens": totals.get("completion_tokens"),
            "avg_gateway_latency_ms": round(totals["avg_latency_ms"]) if totals.get("avg_latency_ms") is not None else None,
            "cost_usd": totals.get("cost"),
        },
    }


def build(rounds, a, b, usage_a, usage_b, specs, gateway, seed, settings, strategy_sha) -> dict:
    fa = fighter_stats(rounds, "a", a, usage_a)
    fb = fighter_stats(rounds, "b", b, usage_b)
    if fa["wins"] > fb["wins"]:
        winner = f"A ({a.model})"
    elif fb["wins"] > fa["wins"]:
        winner = f"B ({b.model})"
    else:
        winner = "draw"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "game": {"name": "Codebreaker", "code_length": settings.code_length, "digits": f"1-{settings.max_digit}", "rounds": len(rounds), "max_guesses": settings.max_guesses, "timeout_seconds": settings.timeout_seconds, "max_tokens": settings.max_tokens, "seed": seed},
        "strategy_sha256": strategy_sha,
        "machine": specs,
        "gateway": gateway,
        "fighters": [fa, fb],
        "result": {"winner": winner, "record": f"A {fa['wins']} - {fb['wins']} B" + (f" ({fa['ties']} tied)" if fa["ties"] else "")},
        "rounds": [{"n": r.n, "secret": fmt(r.secret), "a": _play_row(r.a), "b": _play_row(r.b), "winner": r.winner} for r in rounds],
    }


def _na(v):
    return "n/a" if v is None else v


def _play_row(p) -> dict:
    return {"score": p.score, "cracked": p.cracked, "best_exact": p.best[0], "best_misplaced": p.best[1] - p.best[0], "seconds": round(p.seconds, 1)}


def _row(label, fa, fb, key, f=lambda v: v):
    return f"| {label} | {_na(f(fa[key]))} | {_na(f(fb[key]))} |"


def _round_cell(p: dict) -> str:
    if p["cracked"]:
        return f"{p['score']} ({p['seconds']}s)"
    return f"fail, best {p['best_exact']}/{p['best_misplaced']} ({p['seconds']}s)"


def render_md(card: dict) -> str:
    fa, fb = card["fighters"]
    m = card["machine"]
    g = card["game"]
    gw = card["gateway"]
    ua, ub = fa["otari_usage"], fb["otari_usage"]
    gpu = m.get("gpu", "") + (f" ({m['gpu_note']})" if m.get("gpu_note") else "")
    lines = [
        "# Fight card: Otari Local Model Fight Night",
        "",
        f"**{card['result']['winner']}** takes it, {card['result']['record']}. {g['rounds']} rounds of Codebreaker, generated {card['generated_at']}.",
        "",
        "## Machine",
        "",
        f"- OS: {m.get('os')} ({m.get('arch')})",
        f"- CPU: {m.get('cpu')}",
        f"- RAM: {m.get('ram_gb')} GB",
        f"- GPU: {gpu}",
        f"- Ollama {gw.get('ollama_version')}, Otari {gw.get('otari_version')} at {gw.get('otari_url')}",
        "",
        "## Fighters",
        "",
        "| | A | B |",
        "|---|---|---|",
        _row("Model", fa, fb, "model", lambda v: f"`{v}`"),
        _row("Wins", fa, fb, "wins"),
        _row("Cracked", fa, fb, "cracked", lambda v: f"{v}/{g['rounds']}"),
        _row(f"Avg guesses (fail = {g['max_guesses'] + 1})", fa, fb, "avg_guesses"),
        _row("Avg guesses when cracked", fa, fb, "avg_guesses_when_cracked"),
        _row("Avg seconds per guess", fa, fb, "avg_seconds_per_guess"),
        _row("Malformed replies", fa, fb, "malformed_replies"),
        _row("Timeouts", fa, fb, "timeouts"),
        "",
        "## Otari usage (from the gateway's own log, per fighter key)",
        "",
        "| | A | B |",
        "|---|---|---|",
        f"| Requests | {ua['requests']} | {ub['requests']} |",
        f"| Errors | {ua['errors']} | {ub['errors']} |",
        f"| Prompt tokens | {ua['prompt_tokens']} | {ub['prompt_tokens']} |",
        f"| Completion tokens | {ua['completion_tokens']} | {ub['completion_tokens']} |",
        f"| Avg gateway latency (ms) | {ua['avg_gateway_latency_ms']} | {ub['avg_gateway_latency_ms']} |",
        f"| Cost | ${ua['cost_usd'] or 0:.2f} | ${ub['cost_usd'] or 0:.2f} |",
        "",
        "## Rules",
        "",
        f"{g['code_length']} digits from {g['digits']}, repeats allowed, {g['max_guesses']} guesses max, {g['timeout_seconds']:.0f}s per reply, {g['max_tokens']} max tokens. Same secret for both fighters each round, played one after the other. Fewer guesses wins the round. If neither cracks it, the closer best guess wins (most exact, then most right digits). Only then does speed decide.",
        "",
        f"Seed `{g['seed']}` (replay with `SEED={g['seed']} make fight`). Strategy file sha256 `{card['strategy_sha256']}`.",
        "",
        "## Rounds",
        "",
        "| # | Secret | A | B | Winner |",
        "|---|---|---|---|---|",
    ]
    for r in card["rounds"]:
        sa = _round_cell(r["a"])
        sb = _round_cell(r["b"])
        lines.append(f"| {r['n']} | {r['secret']} | {sa} | {sb} | {r['winner'].upper() if r['winner'] != 'tie' else 'tie'} |")
    lines.append("")
    return "\n".join(lines)


def write(card: dict, md_path: Path = Path("fight-card.md"), json_path: Path = Path("fight-card.json")) -> None:
    md_path.write_text(render_md(card))
    json_path.write_text(json.dumps(card, indent=2) + "\n")
