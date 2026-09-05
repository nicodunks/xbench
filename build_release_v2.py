#!/usr/bin/env python3
"""Aggregate v2 labels (firsthand / endorsement / aspect schema) into the public release.

Reads data/labels-v2/labels/batch-*.jsonl plus the corpus, applies the
author-level exclusions and dedup rules, and writes public-summary.json and
public-evidence.json under data/labels-v2/. Attention numbers are carried over
from the stored X count queries; no new X calls happen here.
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
V2 = DATA / "labels-v2"
OLD = json.loads((DATA / "window.json").read_text())
MODELS = OLD["taxonomy"]["tracked_model_ids"]
HARNESSES = ["claude_code", "codex", "opencode", "pi", "grokbot"]
FAMILIES = ["claude", "gpt", "gemini", "grok", "glm", "kimi", "muse"]
SCORE = {"positive": 1, "mixed": 0, "negative": -1}


def percentile(values, p):
    values = sorted(values)
    if not values:
        return None
    x = (len(values) - 1) * p
    lo, hi = int(x), min(int(x) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (x - lo)


def bt_fit(events, nodes, ridge=.08, max_iter=100, tol=1e-9):
    index = {node: i for i, node in enumerate(nodes)}
    theta = np.zeros(len(nodes))
    for _ in range(max_iter):
        grad = -ridge * theta
        hess = -ridge * np.eye(len(nodes))
        for e in events:
            wi, li = index[e["winner"]], index[e["loser"]]
            z = float(np.clip(theta[wi] - theta[li], -30, 30))
            p = 1 / (1 + math.exp(-z)); q = p * (1 - p)
            grad[wi] += 1 - p; grad[li] -= 1 - p
            hess[wi, wi] -= q; hess[li, li] -= q; hess[wi, li] += q; hess[li, wi] += q
        step = np.linalg.solve(-hess, grad)
        theta += step; theta -= theta.mean()
        if float(np.max(np.abs(step))) < tol:
            break
    return {n: float(theta[index[n]]) for n in nodes}


def ratings(events, nodes):
    if not events:
        return []
    base = bt_fit(events, nodes)
    authors = sorted({e["author_id"] for e in events})
    by_author = defaultdict(list)
    for e in events:
        by_author[e["author_id"]].append(e)
    rng = random.Random("xbench-v2")
    samples = {n: [] for n in nodes}
    for _ in range(500):
        draw = [e for _ in authors for e in by_author[rng.choice(authors)]]
        fit = bt_fit(draw, nodes)
        for n in nodes:
            samples[n].append(1000 + 400 / math.log(10) * fit[n])
    return sorted([{"model": n, "rating": round(1000 + 400 / math.log(10) * base[n]),
                    "low_95": round(percentile(samples[n], .025)), "high_95": round(percentile(samples[n], .975)),
                    "votes": sum(1 for e in events if n in (e["winner"], e["loser"]))}
                   for n in nodes], key=lambda r: -r["rating"])


def collapsed(rows):
    s = sum(SCORE[r["label"]] for r in rows)
    return "positive" if s > 0 else "negative" if s < 0 else "mixed"


def main():
    corpus = {}
    corpus_path = DATA / "private" / "corpus.jsonl"
    if not corpus_path.exists():
        raise SystemExit("data/private/corpus.jsonl is not distributed with the repo; see README (Data) to rebuild.")
    for line in corpus_path.read_text().split("\n"):
        if line:
            r = json.loads(line); corpus[r["post_id"]] = r
    labels = {}
    for path in sorted(glob.glob(str(V2 / "labels" / "batch-*.jsonl"))):
        for line in Path(path).read_text().split("\n"):
            if line:
                r = json.loads(line)
                if r["post_id"] in labels:
                    raise ValueError(f"duplicate label {r['post_id']}")
                labels[r["post_id"]] = r
    missing = set(corpus) - set(labels)
    if missing:
        raise ValueError(f"labels incomplete: {len(missing)} corpus posts unlabeled")
    labels = {pid: labels[pid] for pid in corpus}
    # Reviewer overrides replace the labeler's record wholesale.
    overrides_path = V2 / "overrides.jsonl"
    overrides = 0
    if overrides_path.exists():
        for line in overrides_path.read_text().split("\n"):
            if line:
                r = json.loads(line)
                if r["post_id"] not in labels:
                    continue  # reviewed while in an earlier window; kept for the record
                labels[r["post_id"]] = {**r, "overridden": True}; overrides += 1

    # Quota audit: model lines re-read to separate the model's own cost from plan limits (QUOTA_AUDIT.md).
    audit = Counter()
    for path in sorted(glob.glob(str(V2 / "quota-audit" / "decisions" / "*.jsonl"))):
        for line in Path(path).read_text().split("\n"):
            if line:
                d = json.loads(line); audit["lines_read"] += 1
                if d["kind"] in ("quota", "both"):
                    audit["moved_to_harness" if d.get("harness") else "dropped_untracked_plan"] += 1

    # Author exclusion: an author is dropped when the labeler flagged most of their posts as AI-authored.
    by_author = defaultdict(list)
    for pid, r in labels.items():
        by_author[corpus[pid].get("author_id")].append(bool(r.get("ai_author")))
    excluded_authors = {a for a, flags in by_author.items() if a and sum(flags) * 2 > len(flags)}
    # Reviewer exclusions: high-volume reply bots and spam accounts whose posts the
    # per-post labeler only partly flagged. Listed with reasons in excluded-authors.json.
    reviewer_excluded_path = V2 / "excluded-authors.json"
    if reviewer_excluded_path.exists():
        hashed = {row["author_sha256"] for row in json.loads(reviewer_excluded_path.read_text())}
        for a in {p.get("author_id") for p in corpus.values() if p.get("author_id")}:
            if hashlib.sha256(str(a).encode()).hexdigest() in hashed:
                excluded_authors.add(str(a))

    # Aspect dimensions: free-text aspects mapped onto a fixed vocabulary (ASPECT_DIMENSIONS.md).
    MODEL_DIMS = ["intelligence", "speed", "price", "steerability", "personality", "overall", "other"]
    HARNESS_DIMS = ["limits", "reliability", "efficiency", "agent", "dx", "overall", "other"]
    aspect_map = {"model": {}, "harness": {}}
    for path in sorted(glob.glob(str(V2 / "aspect-map" / "maps" / "*.jsonl"))):
        kind = "model" if Path(path).name.startswith("model") else "harness"
        for line in Path(path).read_text().split("\n"):
            if line:
                r = json.loads(line); aspect_map[kind][r["aspect"].strip().lower()] = r["dimension"]
    unmapped = Counter()
    def dimension(target, aspect):
        if target in FAMILIES:
            return None
        kind = "harness" if target in HARNESSES else "model"
        key = (aspect or "overall").strip().lower()
        d = aspect_map[kind].get(key)
        if d is None:
            unmapped[kind] += 1; d = "overall" if key in ("overall", "") else "other"
        return d

    start = datetime.fromisoformat(OLD["window"]["start"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(OLD["window"]["end"].replace("Z", "+00:00"))
    width = (end - start) / 7
    def day_index(created):
        return max(0, min(6, int((datetime.fromisoformat(created.replace("Z", "+00:00")) - start) / width)))

    sentiment, preferences, switches = [], [], []
    for pid, d in labels.items():
        raw = corpus[pid]
        if raw.get("author_id") in excluded_authors or not d.get("relevant"):
            continue
        base = {"post_id": pid, "author_id": raw.get("author_id"), "created_at": raw["created_at"],
                "conversation_id": raw.get("conversation_id"), "is_comment": raw.get("is_comment"),
                "day_index": day_index(raw["created_at"]), "text": raw.get("text", ""), "reason": d.get("reason", "")}
        for s in d.get("sentiment", []):
            sentiment.append({**base, "target": s["target"], "label": s["label"], "firsthand": bool(s.get("firsthand")),
                              "endorsement": bool(s.get("endorsement")), "task": s.get("task", "none"), "aspect": s.get("aspect", "overall"),
                              "dimension": dimension(s["target"], s.get("aspect"))})
        for p in d.get("preferences", []):
            preferences.append({**base, "winner": p["winner"], "loser": p["loser"], "firsthand": bool(p.get("firsthand")),
                                "benchmark": bool(p.get("benchmark")), "task": p.get("task", "none"), "aspect": p.get("aspect", "overall"),
                                "dimension": dimension(p["winner"], p.get("aspect"))})
        for s in d.get("switches", []):
            if s.get("completed") is True and s["origin"] != s["destination"]:
                switches.append({**base, "origin": s["origin"], "destination": s["destination"]})

    # One author / target / week. Firsthand wins over endorsement when an author has both.
    weekly_groups = defaultdict(list)
    for r in sentiment:
        weekly_groups[(r["author_id"], r["target"])].append(r)
    weekly = []
    for rows in weekly_groups.values():
        chosen = max(rows, key=lambda x: (x["firsthand"], x["created_at"]))
        weekly.append({**chosen, "label": collapsed(rows), "firsthand": any(x["firsthand"] for x in rows),
                       "endorsement": all(x["endorsement"] for x in rows), "message_count": len(rows)})
    daily_groups = defaultdict(list)
    for r in sentiment:
        daily_groups[(r["author_id"], r["target"], r["day_index"])].append(r)
    daily = [{**max(rows, key=lambda x: x["created_at"]), "label": collapsed(rows), "firsthand": any(x["firsthand"] for x in rows)}
             for rows in daily_groups.values()]

    def block(rows):
        c = Counter(r["label"] for r in rows); n = len(rows)
        return {"n": n, "positive": c["positive"], "mixed": c["mixed"], "negative": c["negative"],
                "net_sentiment": round((c["positive"] - c["negative"]) / n, 4) if n else None}

    def sentiment_row(target):
        rows = [r for r in weekly if r["target"] == target]
        fh = [r for r in rows if r["firsthand"]]
        endorse = [r for r in rows if r["endorsement"]]
        history = []
        for day in range(7):
            ds = [r for r in daily if r["target"] == target and r["day_index"] == day and r["firsthand"]]
            history.append({"day_index": day, **block(ds)})
        aspects = defaultdict(Counter)
        for r in sentiment:
            if r["target"] == target and r["firsthand"]:
                aspects[r["label"]][r["aspect"].strip().lower()] += 1
        tasks = Counter(r["task"] for r in rows if r["firsthand"])
        # One author / target / dimension / week, firsthand only.
        dim_groups = defaultdict(list); dim_aspects = defaultdict(lambda: defaultdict(Counter))
        for r in sentiment:
            if r["target"] == target and r["firsthand"]:
                dim_groups[(r["author_id"], r["dimension"])].append(r)
                dim_aspects[r["dimension"]][r["label"]][r["aspect"].strip().lower()] += 1
        dim_rows = defaultdict(list)
        for (author, dim), items in dim_groups.items():
            dim_rows[dim].append({"label": collapsed(items)})
        dims = HARNESS_DIMS if target in HARNESSES else MODEL_DIMS
        dimensions = {d: {**block(dim_rows.get(d, [])),
                          "top_aspects": {k: dim_aspects[d][k].most_common(4) for k in ("positive", "negative")}} for d in dims}
        return {"model": target, "firsthand": block(fh), "all_expressed": block(rows), "endorsements": block(endorse),
                "daily_firsthand": history, "tasks": dict(tasks), "dimensions": dimensions,
                "aspects": {k: aspects[k].most_common(15) for k in ("positive", "negative", "mixed")}}

    model_sentiment = sorted([sentiment_row(m) for m in MODELS],
                             key=lambda x: (x["firsthand"]["net_sentiment"] if x["firsthand"]["net_sentiment"] is not None else -9), reverse=True)
    family_sentiment = [sentiment_row(f) for f in FAMILIES]
    harness_sentiment = [sentiment_row(h) for h in HARNESSES]

    def dedupe_pref(rows):
        groups = defaultdict(list)
        for r in rows:
            groups[(r["author_id"], tuple(sorted((r["winner"], r["loser"]))))].append(r)
        out = []
        for items in groups.values():
            direction = Counter((x["winner"], x["loser"]) for x in items)
            top = direction.most_common(2)
            if len(top) == 1 or top[0][1] > top[1][1]:
                win = top[0][0]
                out.append(max((x for x in items if (x["winner"], x["loser"]) == win), key=lambda x: x["created_at"]))
        return out

    opinion = [p for p in preferences if not p["benchmark"]]
    model_events = dedupe_pref([p for p in opinion if p["winner"] in MODELS and p["loser"] in MODELS and p["firsthand"]])
    model_events_all = dedupe_pref([p for p in opinion if p["winner"] in MODELS and p["loser"] in MODELS])
    harness_events = dedupe_pref([p for p in opinion if p["winner"] in HARNESSES and p["loser"] in HARNESSES])
    harness_vs_field = dedupe_pref([p for p in opinion if ({p["winner"], p["loser"]} & set(HARNESSES)) and not ({p["winner"], p["loser"]} <= set(HARNESSES))])
    benchmark_events = dedupe_pref([p for p in preferences if p["benchmark"] and p["winner"] in MODELS and p["loser"] in MODELS])

    def battles(events):
        pairs = defaultdict(list)
        for e in events:
            pairs[tuple(sorted((e["winner"], e["loser"])))].append(e)
        out = [{"models": list(pair), "votes": dict(Counter(r["winner"] for r in rows)), "n": len(rows),
                "evidence_ids": [r["post_id"] for r in rows]} for pair, rows in pairs.items()]
        return sorted(out, key=lambda x: -x["n"])

    switch_rows = list({(r["author_id"], r["origin"], r["destination"]): r for r in switches}.values())
    model_switches = [r for r in switch_rows if r["origin"] in MODELS and r["destination"] in MODELS]
    harness_switches = [r for r in switch_rows if r["origin"] in HARNESSES and r["destination"] in HARNESSES]

    summary = {
        "schema_version": "4.0", "release": "labels-v2", "source": "Official X API v2 stored corpus",
        "window": OLD["window"],
        "corpus": {"unique_posts": len(corpus), "unique_authors": len({r.get("author_id") for r in corpus.values() if r.get("author_id")}),
                   "comments": sum(bool(r.get("is_comment")) for r in corpus.values()), "classified_posts": len(labels), "reviewer_overrides": overrides,
                   "excluded_ai_authors": len(excluded_authors),
                   "excluded_posts": sum(1 for p in corpus.values() if p.get("author_id") in excluded_authors),
                   "quota_audit": dict(audit)},
        "recorded_spend_usd": OLD["recorded_spend_usd"], "attention": OLD["attention"],
        "sentiment": {"definition": "Firsthand stance: the author used the model or reports a concrete result. One author per model per week. Endorsements are bare agreements with someone else's stance and are shown separately.",
                      "models": model_sentiment, "families": family_sentiment},
        "preference": {"definition": "Stated preferences between exact models, firsthand only, benchmark reposts excluded. One author, one vote per matchup.",
                       "firsthand_votes": len(model_events), "all_votes": len(model_events_all),
                       "distinct_authors": len({e["author_id"] for e in model_events}),
                       "head_to_head": battles(model_events),
                       "xbenchpref": {"method": "Ridge-regularized Bradley-Terry on firsthand votes; author bootstrap 95% intervals", "ratings": ratings(model_events, list(MODELS))},
                       "benchmark_reposts": len(benchmark_events)},
        "switching": {"definition": "First-person completed moves between exact models; one author per edge per week.",
                      "verified_completed_switches": len(model_switches),
                      "by_origin_destination": dict(Counter(f'{r["origin"]} -> {r["destination"]}' for r in model_switches)),
                      "daily_counts": [sum(r["day_index"] == d for r in model_switches) for d in range(7)]},
        "harnesses": {"definition": "Claude Code, Codex, OpenCode, Pi and Grokbot. Sentiment, preference and switching kept separate from models.",
                      "tracked": HARNESSES, "sentiment": harness_sentiment,
                      "head_to_head": battles(harness_events), "votes": len(harness_events),
                      "ratings": ratings(harness_events, HARNESSES) if len(harness_events) >= 5 else [],
                      "vs_field": battles(harness_vs_field),
                      "switches": {"n": len(harness_switches), "by_direction": dict(Counter(f'{r["origin"]} -> {r["destination"]}' for r in harness_switches))}},
        "taxonomy": {**OLD["taxonomy"], "harness_ids": HARNESSES, "family_ids": FAMILIES},
        "dimensions": {"definition": "Free-text aspects mapped onto a fixed vocabulary by a separate LLM pass (ASPECT_DIMENSIONS.md); one author per target per dimension per week, firsthand only.",
                       "model": [["intelligence", "Intelligence"], ["speed", "Speed"], ["price", "Price"], ["steerability", "Steerability"], ["personality", "Personality"], ["overall", "Overall"], ["other", "Other"]],
                       "harness": [["limits", "Limits and quota"], ["reliability", "Reliability"], ["efficiency", "Token and context efficiency"], ["agent", "Agent behaviour"], ["dx", "Developer experience"], ["overall", "Overall"], ["other", "Other"]],
                       "unmapped_aspects": dict(unmapped)},
    }

    def public(row, **extra):
        return {"post_id": row["post_id"], "text": row["text"], "created_at": row["created_at"],
                "conversation_id": row.get("conversation_id"), "url": f'https://x.com/i/web/status/{row["post_id"]}',
                "reason": row.get("reason", ""), **extra}
    evidence = {
        "schema_version": "3.0",
        "sentiment": [public(r, model=r["target"], sentiment=r["label"], firsthand=r["firsthand"], endorsement=r["endorsement"], task=r["task"], aspect=r["aspect"], dimension=r["dimension"])
                      for r in sentiment if r["target"] in MODELS],
        "family_sentiment": [public(r, family=r["target"], sentiment=r["label"], firsthand=r["firsthand"], endorsement=r["endorsement"], task=r["task"], aspect=r["aspect"])
                             for r in sentiment if r["target"] in FAMILIES],
        "preference": [public(r, winner=r["winner"], loser=r["loser"], firsthand=r["firsthand"], task=r["task"], aspect=r["aspect"], day_index=r["day_index"]) for r in model_events_all],
        "switching": [public(r, origin=r["origin"], destination=r["destination"], day_index=r["day_index"]) for r in model_switches],
        "harness_sentiment": [public(r, harness=r["target"], sentiment=r["label"], firsthand=r["firsthand"], endorsement=r["endorsement"], task=r["task"], aspect=r["aspect"], dimension=r["dimension"])
                              for r in sentiment if r["target"] in HARNESSES],
        "harness": [public(r, winner=r["winner"], loser=r["loser"], firsthand=r["firsthand"], task=r["task"], aspect=r["aspect"], dimension=r["dimension"], day_index=r["day_index"]) for r in harness_events + harness_vs_field],
        "harness_switching": [public(r, origin=r["origin"], destination=r["destination"], day_index=r["day_index"]) for r in harness_switches],
    }
    (V2 / "public-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (V2 / "public-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "excluded_ai_authors": len(excluded_authors),
        "unmapped_aspects": dict(unmapped),
        "sentiment_lines": len(sentiment),
        "model_firsthand_authors": {m["model"]: m["firsthand"]["n"] for m in model_sentiment},
        "harness_firsthand_authors": {m["model"]: m["firsthand"]["n"] for m in harness_sentiment},
        "model_pref_votes_firsthand": len(model_events), "model_pref_votes_all": len(model_events_all),
        "harness_pref_votes": len(harness_events), "harness_vs_field_votes": len(harness_vs_field),
        "model_switches": len(model_switches), "harness_switches": len(harness_switches),
    }, indent=2))


if __name__ == "__main__":
    main()
