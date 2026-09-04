#!/usr/bin/env python3
"""Aggregate one-pass agent judgments into the public Xbench release."""
from __future__ import annotations

import glob
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
AGENT = DATA / "agent-rebuild"
OLD = json.loads((DATA / "rolling-7d" / "public-summary.json").read_text())
MODEL_ORDER = OLD["taxonomy"]["tracked_model_ids"]

ALIASES = {
    "claude fable 5.1": "claude-fable-5.1", "claude-fable-5.1": "claude-fable-5.1",
    "claude opus 5": "claude-opus-5", "claude-opus-5": "claude-opus-5",
    "gpt-6 astra": "gpt-6-astra", "gpt 6 astra": "gpt-6-astra", "gpt-6-astra": "gpt-6-astra",
    "gpt-5.6 sol": "gpt-5.6-sol", "gpt 5.6 sol": "gpt-5.6-sol", "gpt-5.6-sol": "gpt-5.6-sol",
    "gpt-5.6 luna": "gpt-5.6-luna", "gpt 5.6 luna": "gpt-5.6-luna", "gpt-5.6-luna": "gpt-5.6-luna",
    "muse spark 1.3": "muse-spark-1.3", "muse-spark-1.3": "muse-spark-1.3",
    "muse spark 1.2": "muse-spark-1.2", "muse-spark-1.2": "muse-spark-1.2",
    "gemini 3.8 flash": "gemini-3.8-flash", "gemini-3.8-flash": "gemini-3.8-flash",
    "gemini 3.7 flash": "gemini-3.7-flash", "gemini-3.7-flash": "gemini-3.7-flash",
    "grok 4.6": "grok-4.6", "grok-4.6": "grok-4.6",
    "glm 5.3": "glm-5.3", "glm-5.3": "glm-5.3",
    "glm 5.3 flash": "glm-5.3-flash", "glm-5.3-flash": "glm-5.3-flash",
    "kimi k3": "kimi-k3", "kimi-k3": "kimi-k3",
    "claude code": "claude_code", "claude-code": "claude_code", "claude_code": "claude_code",
    "openai codex": "codex", "codex": "codex",
}
SCORE = {"positive": 1, "mixed": 0, "negative": -1}


def norm(value):
    return ALIASES.get(str(value or "").strip().lower())


def percentile(values, p):
    values = sorted(values)
    if not values:
        return None
    x = (len(values) - 1) * p
    lo, hi = int(x), min(int(x) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (x - lo)


def wilson(k, n, z=1.959963984540054):
    if not n:
        return [0, 1]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - r, 4), round(c + r, 4)]


def collapsed_label(rows):
    score = sum(SCORE[r["label"]] for r in rows)
    return "positive" if score > 0 else "negative" if score < 0 else "mixed"


def bt_fit(events, nodes, ridge=.08, max_iter=100, tol=1e-9):
    """Convergent Newton fit for ridge-regularized Bradley–Terry."""
    index = {node: i for i, node in enumerate(nodes)}
    theta = np.zeros(len(nodes))
    for _ in range(max_iter):
        grad = -ridge * theta
        hess = -ridge * np.eye(len(nodes))
        for event in events:
            wi, li = index[event["winner"]], index[event["loser"]]
            z = float(np.clip(theta[wi] - theta[li], -30, 30))
            p = 1 / (1 + math.exp(-z))
            grad[wi] += 1 - p
            grad[li] -= 1 - p
            q = p * (1 - p)
            hess[wi, wi] -= q; hess[li, li] -= q
            hess[wi, li] += q; hess[li, wi] += q
        step = np.linalg.solve(-hess, grad)
        theta += step
        theta -= theta.mean()
        if float(np.max(np.abs(step))) < tol:
            break
    return {node: float(theta[index[node]]) for node in nodes}


def ratings(events):
    nodes = list(MODEL_ORDER)
    base = bt_fit(events, nodes)
    authors = sorted({e["author_id"] for e in events})
    by_author = defaultdict(list)
    for event in events:
        by_author[event["author_id"]].append(event)
    rng = random.Random("xbench-agent-v1")
    samples = {node: [] for node in nodes}
    for _ in range(500):
        draw = [e for _ in authors for e in by_author[rng.choice(authors)]] if authors else []
        fit = bt_fit(draw, nodes) if draw else {node: 0 for node in nodes}
        for node in nodes:
            samples[node].append(1000 + 400 / math.log(10) * fit[node])
    return sorted([
        {"model": node, "rating": round(1000 + 400 / math.log(10) * base[node]),
         "low_95": round(percentile(samples[node], .025)),
         "high_95": round(percentile(samples[node], .975))}
        for node in nodes
    ], key=lambda row: -row["rating"])


def main():
    corpus = {}
    for line in (AGENT / "corpus.jsonl").read_text().split("\n"):
        if not line:
            continue
        row = json.loads(line); corpus[row["post_id"]] = row
    labels = {}
    files = sorted(glob.glob(str(AGENT / "primary-*.jsonl")))
    for path in files:
        for line in Path(path).read_text().split("\n"):
            if not line:
                continue
            row = json.loads(line)
            required = {"post_id", "relevant", "entities", "sentiment", "preferences", "switches", "evidence_types", "reason"}
            if not required <= set(row) or not isinstance(row["relevant"], bool):
                raise ValueError(f"invalid classification contract in {path}: {row.get('post_id')}")
            if any(not isinstance(row[key], list) for key in ("entities", "sentiment", "preferences", "switches", "evidence_types")):
                raise ValueError(f"invalid classification arrays in {path}: {row.get('post_id')}")
            if row["post_id"] in labels:
                raise ValueError(f'duplicate label {row["post_id"]}')
            labels[row["post_id"]] = row
    if set(labels) != set(corpus):
        raise ValueError(f"classification incomplete: {len(labels)}/{len(corpus)}")

    start = datetime.fromisoformat(OLD["window"]["start"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(OLD["window"]["end"].replace("Z", "+00:00"))
    width = (end - start) / 7
    def day_index(created):
        return max(0, min(6, int((datetime.fromisoformat(created.replace("Z", "+00:00")) - start) / width)))

    sentiment_messages = []
    preferences = []
    switches = []
    for post_id, decision in labels.items():
        raw = corpus[post_id]
        base = {"post_id": post_id, "author_id": raw.get("author_id"), "created_at": raw["created_at"],
                "conversation_id": raw.get("conversation_id"), "is_comment": raw.get("is_comment"),
                "day_index": day_index(raw["created_at"]), "text": raw.get("text", ""),
                "reason": decision.get("reason", ""), "evidence_types": decision.get("evidence_types", [])}
        if not decision["relevant"]:
            continue
        for item in decision.get("sentiment", []):
            target = norm(item.get("target")); label = item.get("label")
            if target in MODEL_ORDER + ["claude_code", "codex"] and label in SCORE and item.get("confidence") in {"high", "medium"}:
                sentiment_messages.append({**base, "target": target, "label": label,
                    "stage": item.get("stage", "unspecified"), "confidence": item.get("confidence")})
        for item in decision.get("preferences", []):
            winner, loser = norm(item.get("winner")), norm(item.get("loser"))
            if winner and loser and winner != loser and item.get("confidence") in {"high", "medium"}:
                preferences.append({**base, "winner": winner, "loser": loser,
                    "scope": item.get("scope", "unspecified"), "confidence": item.get("confidence")})
        for item in decision.get("switches", []):
            origin, destination = norm(item.get("origin")), norm(item.get("destination"))
            if item.get("completed") is True and origin and destination and origin != destination and item.get("confidence") in {"high", "medium"}:
                switches.append({**base, "origin": origin, "destination": destination,
                    "confidence": item.get("confidence")})

    # One author/target/day, then one author/target/week. All message evidence remains public.
    daily_groups = defaultdict(list)
    for row in sentiment_messages:
        daily_groups[(row["author_id"], row["target"], row["day_index"])].append(row)
    daily = []
    for key, rows in daily_groups.items():
        chosen = max(rows, key=lambda x: x["created_at"])
        daily.append({**chosen, "label": collapsed_label(rows), "message_count": len(rows)})
    weekly_groups = defaultdict(list)
    for row in daily:
        weekly_groups[(row["author_id"], row["target"])].append(row)
    weekly = []
    for key, rows in weekly_groups.items():
        chosen = max(rows, key=lambda x: x["created_at"])
        weekly.append({**chosen, "label": collapsed_label(rows), "message_count": sum(x["message_count"] for x in rows)})

    def sentiment_row(target):
        rows = [r for r in weekly if r["target"] == target]
        counts = Counter(r["label"] for r in rows); n = len(rows)
        history = []
        for day in range(7):
            ds = [r for r in daily if r["target"] == target and r["day_index"] == day]
            dc = Counter(r["label"] for r in ds); dn = len(ds)
            history.append({"day_index": day, "n": dn, "positive": dc["positive"], "mixed": dc["mixed"],
                            "negative": dc["negative"], "net_sentiment": round((dc["positive"]-dc["negative"])/dn,4) if dn else None})
        latest, prior = history[6]["net_sentiment"], history[5]["net_sentiment"]
        stages = Counter(r.get("stage", "unspecified") for r in rows)
        return {"model": target, "clean_directional": {"n": n, "message_n": sum(r["message_count"] for r in rows),
                "positive": counts["positive"], "mixed": counts["mixed"], "negative": counts["negative"],
                "net_sentiment": round((counts["positive"]-counts["negative"])/n,4) if n else None},
                "stages": dict(stages), "daily": history,
                "latest_24h_delta_points": round((latest-prior)*100,1) if latest is not None and prior is not None else None}

    model_sentiment = [sentiment_row(target) for target in MODEL_ORDER]
    model_sentiment.sort(key=lambda x: (x["clean_directional"]["net_sentiment"] if x["clean_directional"]["net_sentiment"] is not None else -9), reverse=True)
    harness_sentiment = [sentiment_row("claude_code"), sentiment_row("codex")]

    primary_scopes = {"direct_preference", "experience_comparison", "recommendation"}
    model_pref_raw = [p for p in preferences if p["winner"] in MODEL_ORDER and p["loser"] in MODEL_ORDER and p["scope"] in primary_scopes]
    harness_pref_raw = [p for p in preferences if {p["winner"], p["loser"]} == {"claude_code", "codex"} and p["scope"] in primary_scopes]
    benchmark_raw = [p for p in preferences if p["winner"] in MODEL_ORDER and p["loser"] in MODEL_ORDER and p["scope"] == "benchmark_outcome"]

    def dedupe_pref(rows):
        groups = defaultdict(list)
        for row in rows:
            groups[(row["author_id"], tuple(sorted((row["winner"], row["loser"]))))].append(row)
        out = []
        for _, items in groups.items():
            direction = Counter((x["winner"], x["loser"]) for x in items)
            if len(direction) == 1 or direction.most_common(2)[0][1] > direction.most_common(2)[1][1]:
                winning_direction = direction.most_common(1)[0][0]
                out.append(max((x for x in items if (x["winner"],x["loser"]) == winning_direction), key=lambda x:x["created_at"]))
        return out
    model_events = dedupe_pref(model_pref_raw)
    harness_events = dedupe_pref(harness_pref_raw)

    pair_groups = defaultdict(list)
    for event in model_events:
        pair_groups[tuple(sorted((event["winner"], event["loser"])))].append(event)
    battles = []
    for pair, rows in pair_groups.items():
        votes = Counter(r["winner"] for r in rows); n = len(rows)
        battles.append({"models": list(pair), "votes": dict(votes), "n": n,
                        "evidence_ids": [r["post_id"] for r in rows]})
    battles.sort(key=lambda x: -x["n"])

    switch_events = {}
    for row in switches:
        switch_events.setdefault((row["author_id"], row["origin"], row["destination"]), row)
    switch_rows = list(switch_events.values())
    model_switch_rows = [r for r in switch_rows if r["origin"] in MODEL_ORDER and r["destination"] in MODEL_ORDER]
    flows = Counter(f'{r["origin"]} -> {r["destination"]}' for r in model_switch_rows)
    harness_switches = [r for r in switch_rows if {r["origin"],r["destination"]} == {"claude_code","codex"}]

    hc = Counter(x["winner"] for x in harness_events)
    summary = {
        "schema_version": "3.0", "source": "Official X API v2 stored corpus",
        "window": OLD["window"],
        "corpus": {"unique_posts": len(corpus), "unique_authors": len({r.get("author_id") for r in corpus.values() if r.get("author_id")}),
                   "comments": sum(bool(r.get("is_comment")) for r in corpus.values()), "classified_posts": len(labels)},
        "recorded_spend_usd": OLD["recorded_spend_usd"], "attention": OLD["attention"],
        "sentiment": {"definition": "Expressed stance; one author/model/week; all languages and evidence stages retained.", "models": model_sentiment},
        "preference": {"definition": "Direct preference, experience comparison, or recommendation; benchmark outcomes separate.",
            "clean_unique_votes": len(model_events), "distinct_authors": len({e["author_id"] for e in model_events}),
            "head_to_head": battles, "xbenchpref": {"method": "Converged ridge-regularized Bradley–Terry; author bootstrap 95% intervals", "ratings": ratings(model_events)},
            "benchmark_outcomes": len(dedupe_pref(benchmark_raw))},
        "switching": {"definition": "Completed first-person moves; one author/edge/week.",
            "verified_completed_switches": sum(flows.values()), "by_origin_destination": dict(flows),
            "daily_counts": [sum(r["day_index"]==d for r in model_switch_rows) for d in range(7)],
            "latest_24h_change": sum(r["day_index"]==6 for r in model_switch_rows)-sum(r["day_index"]==5 for r in model_switch_rows)},
        "harnesses": {"definition": "Claude Code and Codex are classified as harnesses, independently for sentiment, preference and switching.",
            "sentiment": harness_sentiment, "strict": {"n": len(harness_events), "votes": dict(hc)},
            "switches": {"n": len(harness_switches), "by_direction": dict(Counter(f'{r["origin"]} -> {r["destination"]}' for r in harness_switches))}},
        "taxonomy": OLD["taxonomy"],
    }

    def public_record(row, **extra):
        return {"post_id": row["post_id"], "text": row["text"], "created_at": row["created_at"],
                "conversation_id": row.get("conversation_id"), "url": f'https://x.com/i/web/status/{row["post_id"]}', **extra}
    evidence = {
        "schema_version": "2.0",
        "sentiment": [public_record(r, model=r["target"], sentiment=r["label"], stage=r.get("stage")) for r in sentiment_messages if r["target"] in MODEL_ORDER],
        "preference": [public_record(r, winner=r["winner"], loser=r["loser"], evidence_kind=r["scope"], day_index=r["day_index"]) for r in model_events],
        "switching": [public_record(r, origin=r["origin"], destination=r["destination"], day_index=r["day_index"]) for r in model_switch_rows],
        "harness": [public_record(r, winner=r["winner"], loser=r["loser"], evidence_kind=r["scope"], day_index=r["day_index"]) for r in harness_events],
        "harness_sentiment": [public_record(r, target=r["target"], sentiment=r["label"], stage=r.get("stage")) for r in sentiment_messages if r["target"] in {"claude_code","codex"}],
        "harness_switching": [public_record(r, origin=r["origin"], destination=r["destination"], day_index=r["day_index"]) for r in harness_switches],
    }
    (AGENT / "public-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (AGENT / "public-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"corpus": summary["corpus"], "model_sentiment_n": sum(x["clean_directional"]["n"] for x in model_sentiment),
                      "sentiment_messages": len(evidence["sentiment"]), "model_preferences": len(model_events),
                      "model_switches": summary["switching"]["verified_completed_switches"], "harness_sentiment": {x["model"]:x["clean_directional"]["n"] for x in harness_sentiment},
                      "harness_preferences": len(harness_events), "harness_switches": len(harness_switches)}, indent=2))


if __name__ == "__main__":
    main()
