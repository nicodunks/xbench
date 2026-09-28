#!/usr/bin/env python3
"""Build the labels-v3 release: every tracked model, measured from the moment Opus 5.5 shipped.

Same rules and same output schema as build_release_v2.py (one author per
target per window, firsthand only for the headline, ridge Bradley-Terry with an
author bootstrap), so the main page's charts render it unchanged. The window
runs from the Opus 5.5 launch (2026-09-22 16:31 UTC) to the last post pulled.
A `launch` block adds what only this page shows: Opus 5.5 day by day, Opus 5
then and Opus 5.5 now, the first release's critics, and Claude Code before and
after, and nerf claims over time (NERF_CLAIMS.md). Writes data/labels-v3/public-summary.json
and public-evidence.json, which the main page reads.
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from build_release_v2 import collapsed, ratings
from launch_cohorts import load_release

ROOT = Path(__file__).resolve().parent
PRIV = ROOT / "data" / "private" / "launch"
PUB = ROOT / "data" / "launches"
OUT = ROOT / "data" / "labels-v3"
V2 = ROOT / "data" / "labels-v2"
LAUNCHES = {l["id"]: l for l in json.loads((ROOT / "data" / "launches.json").read_text())["launches"]}
T0 = datetime.fromisoformat(LAUNCHES["opus-5.5"]["t0"].replace("Z", "+00:00"))
FOCUS = "claude-opus-5.5"
MODELS = ["claude-opus-5.5", "claude-opus-5", "claude-fable-5.1", "gpt-6-sol", "gpt-6-luna", "gpt-6-astra", "gpt-5.6-sol", "gpt-5.6-luna",
          "grok-4.7", "grok-4.6", "gemini-3.8-flash", "glm-5.3", "glm-5.3-flash", "kimi-k3", "muse-spark-1.3"]
HARNESSES = ["claude_code", "codex", "opencode", "pi", "grokbot"]
FAMILIES = ["claude", "gpt", "gemini", "grok", "glm", "kimi", "muse"]
STORES = ["opus-5.5", "gpt-6-sol", "claude-code-post"] + [k for k, l in LAUNCHES.items() if l["role"] in ("field", "trend")]
# Own-sample rule: a model's sentiment and reasons count only posts pulled by that model's own query. Opus 5.5 was
# sampled ~25x harder than the field, and its posts often praise it by knocking a rival; without this rule every
# rival's score would be mostly Opus 5.5's audience. Targets with no pull of their own fall back to every post.
# Posts found only through the author cohort route (first-release critics, selected by who they are) never score.
OWN = {"claude-opus-5.5": {"opus-5.5"}, "gpt-6-sol": {"gpt-6-sol"}, "claude_code": {"claude-code-post"},
       **{l["name"]: {k} for k, l in LAUNCHES.items() if l["role"] == "field"}}
OWN["gpt-6-astra"] |= {"trend-gpt-6-astra"}  # Astra's seven-day pull for the featured switcher is also its own sample
MODEL_DIMS = ["intelligence", "speed", "price", "steerability", "personality", "overall", "other"]
HARNESS_DIMS = ["limits", "reliability", "efficiency", "agent", "dx", "overall", "other"]


def parse(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def jsonl(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text().split("\n") if l.strip()] if p.exists() else []


def block(rows):
    c = Counter(r["label"] for r in rows); n = len(rows)
    return {"n": n, "positive": c["positive"], "mixed": c["mixed"], "negative": c["negative"],
            "net_sentiment": round((c["positive"] - c["negative"]) / n, 4) if n else None}


def dedupe_pref(rows):
    """One vote per author per pair; an author split evenly on a pair casts none (build_release_v2 rule)."""
    groups = defaultdict(list)
    for r in rows:
        groups[(r["author_id"], tuple(sorted((r["winner"], r["loser"]))))].append(r)
    out = []
    for items in groups.values():
        top = Counter((x["winner"], x["loser"]) for x in items).most_common(2)
        if len(top) == 1 or top[0][1] > top[1][1]:
            out.append(max((x for x in items if (x["winner"], x["loser"]) == top[0][0]), key=lambda x: x.get("created_at", "")))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # ---------- posts in the window ----------
    posts = {}
    for sid in STORES:
        path = PRIV / f"{sid}.json"
        if not path.exists():
            continue
        for pid, p in json.loads(path.read_text())["posts"].items():
            if p.get("_parent_only") or parse(p["created_at"]) < T0:
                continue
            rec = posts.setdefault(pid, {**p, "_routes": []})
            rec["_routes"] = sorted(set(rec["_routes"]) | set(p.get("_routes", [])) | {f"store:{sid}"})
    end = max(parse(p["created_at"]) for p in posts.values())
    days = math.ceil((end - T0) / timedelta(days=1))

    labels = {}
    for path in sorted(glob.glob(str(PUB / "labels" / "L-*.jsonl"))):
        for r in jsonl(path):
            labels[r["post_id"]] = r
    for path in sorted(glob.glob(str(PUB / "overrides" / "*.jsonl"))):
        for r in jsonl(path):
            if r["post_id"] in labels:
                labels[r["post_id"]] = {**r, "overridden": True}
    labeled = {pid: labels[pid] for pid in posts if pid in labels}

    corpus_main, labels_main, excluded_main = load_release()
    flags = defaultdict(list)
    for pid, r in labeled.items():
        flags[posts[pid].get("author_id")].append(bool(r.get("ai_author")))
    excluded = set(excluded_main) | {a for a, f in flags.items() if a and sum(f) * 2 > len(f)}
    hashed = {x["author_sha256"] for x in json.loads((V2 / "excluded-authors.json").read_text())}
    excluded |= {p.get("author_id") for p in posts.values() if p.get("author_id") and hashlib.sha256(str(p["author_id"]).encode()).hexdigest() in hashed}

    def day_index(created):
        return max(0, min(days - 1, math.floor((parse(created) - T0) / timedelta(days=1))))

    sentiment, preferences, switches = [], [], []
    vendor_posts = 0
    for pid, d in labeled.items():
        raw = posts[pid]
        if d.get("vendor"):
            vendor_posts += 1
            continue
        if raw.get("author_id") in excluded or not d.get("relevant"):
            continue
        base = {"post_id": pid, "author_id": raw.get("author_id"), "created_at": raw["created_at"], "conversation_id": raw.get("conversation_id"),
                "day_index": day_index(raw["created_at"]), "text": raw.get("text", ""), "reason": d.get("reason", "")}
        for s in d.get("sentiment", []):
            if s["target"] not in MODELS + HARNESSES + FAMILIES:
                continue
            sentiment.append({**base, "target": s["target"], "label": s["label"], "firsthand": bool(s.get("firsthand")), "endorsement": bool(s.get("endorsement")),
                              "task": s.get("task", "none"), "aspect": s.get("aspect", "overall"), "intensity": s.get("intensity"),
                              "superlative": bool(s.get("superlative")), "dimension": None if s["target"] in FAMILIES else s.get("dimension") or "other",
                              "own": s["target"] not in OWN or (any(f"store:{sid}" in raw["_routes"] for sid in OWN[s["target"]])
                                                                and any(not r.startswith(("cohort", "store:")) for r in raw["_routes"]))})
        for p in d.get("preferences", []):
            preferences.append({**base, "winner": p["winner"], "loser": p["loser"], "firsthand": bool(p.get("firsthand")), "benchmark": bool(p.get("benchmark")),
                                "task": p.get("task", "none"), "aspect": p.get("aspect", "overall"), "dimension": p.get("dimension")})
        for s in d.get("switches", []):
            if s.get("completed") is True and s["origin"] != s["destination"]:
                switches.append({**base, "origin": s["origin"], "destination": s["destination"]})

    all_sentiment = sentiment
    sentiment = [r for r in all_sentiment if r["own"]]
    # ---------- the v2 aggregation, same rules ----------
    by_target = defaultdict(list)
    for r in sentiment:
        by_target[(r["author_id"], r["target"])].append(r)
    weekly = []
    for rows in by_target.values():
        chosen = max(rows, key=lambda x: (x["firsthand"], x["created_at"]))
        weekly.append({**chosen, "label": collapsed(rows), "firsthand": any(x["firsthand"] for x in rows),
                       "endorsement": all(x["endorsement"] for x in rows), "message_count": len(rows)})
    by_day = defaultdict(list)
    for r in sentiment:
        by_day[(r["author_id"], r["target"], r["day_index"])].append(r)
    daily = [{**max(rows, key=lambda x: x["created_at"]), "label": collapsed(rows), "firsthand": any(x["firsthand"] for x in rows)} for rows in by_day.values()]

    def sentiment_row(target):
        rows = [r for r in weekly if r["target"] == target]
        fh = [r for r in rows if r["firsthand"]]
        history = [{"day_index": d, **block([r for r in daily if r["target"] == target and r["day_index"] == d and r["firsthand"]])} for d in range(days)]
        aspects = defaultdict(Counter)
        dim_groups = defaultdict(list)
        dim_aspects = defaultdict(lambda: defaultdict(Counter))
        for r in sentiment:
            if r["target"] == target and r["firsthand"]:
                aspects[r["label"]][r["aspect"].strip().lower()] += 1
                dim_groups[(r["author_id"], r["dimension"])].append(r)
                dim_aspects[r["dimension"]][r["label"]][r["aspect"].strip().lower()] += 1
        dim_rows = defaultdict(list)
        for (_, dim), items in dim_groups.items():
            dim_rows[dim].append({"label": collapsed(items)})
        dims = HARNESS_DIMS if target in HARNESSES else MODEL_DIMS
        return {"model": target, "firsthand": block(fh), "all_expressed": block(rows), "endorsements": block([r for r in rows if r["endorsement"]]),
                "daily_firsthand": history, "tasks": dict(Counter(r["task"] for r in fh)),
                "dimensions": {d: {**block(dim_rows.get(d, [])), "top_aspects": {k: dim_aspects[d][k].most_common(4) for k in ("positive", "negative")}} for d in dims},
                "aspects": {k: aspects[k].most_common(15) for k in ("positive", "negative", "mixed")}}

    model_sentiment = sorted([sentiment_row(m) for m in MODELS], key=lambda x: (x["firsthand"]["net_sentiment"] if x["firsthand"]["net_sentiment"] is not None else -9), reverse=True)
    harness_sentiment = [sentiment_row(h) for h in HARNESSES]

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
        return sorted([{"models": list(pair), "votes": dict(Counter(r["winner"] for r in rows)), "n": len(rows), "evidence_ids": [r["post_id"] for r in rows]}
                       for pair, rows in pairs.items()], key=lambda x: -x["n"])

    # A switch counts on this page only if the move happened in the window: switch_timing.jsonl is a reviewer's read of
    # every counted switch ("since June" and "months ago" are real switches, but not this week's).
    timing = {(t["post_id"], t["origin"], t["destination"]): t["timing"] for t in jsonl(PUB / "switch_timing.jsonl")}
    switches = [r for r in switches if timing.get((r["post_id"], r["origin"], r["destination"]), "window") == "window"]
    switch_rows = list({(r["author_id"], r["origin"], r["destination"]): r for r in switches}.values())
    model_switches = [r for r in switch_rows if r["origin"] in MODELS and r["destination"] in MODELS]
    harness_switches = [r for r in switch_rows if r["origin"] in HARNESSES and r["destination"] in HARNESSES]
    rated_models = [m for m in MODELS if any(m in (e["winner"], e["loser"]) for e in model_events)]

    # ---------- what only this page shows ----------
    focus_row = next(m for m in model_sentiment if m["model"] == FOCUS)
    rank_by_day = []
    for d in range(days):
        field = []
        for m in MODELS:
            b = block([r for r in daily if r["target"] == m and r["day_index"] == d and r["firsthand"]])
            if b["n"] >= 15:
                field.append([m, b["net_sentiment"], b["n"]])
        field.sort(key=lambda x: -x[1])
        rank_by_day.append({"day_index": d, "rank": next((i + 1 for i, f in enumerate(field) if f[0] == FOCUS), None), "of": len(field), "field": field})

    aspect_map = {"model": {}, "harness": {}}
    for path in glob.glob(str(V2 / "aspect-map" / "maps" / "*.jsonl")):
        kind = "model" if Path(path).name.startswith("model") else "harness"
        for r in jsonl(path):
            aspect_map[kind][r["aspect"].strip().lower()] = r["dimension"]
    main_lines, main_prefs, main_switches = [], [], []
    for pid, r in labels_main.items():
        c = corpus_main[pid]
        if not r.get("relevant") or c.get("author_id") in excluded_main:
            continue
        for s in r.get("sentiment", []):
            kind = "harness" if s["target"] in HARNESSES else "model"
            main_lines.append({"author_id": c.get("author_id"), "target": s["target"], "label": s["label"], "firsthand": bool(s.get("firsthand")),
                               "dimension": aspect_map[kind].get((s.get("aspect") or "overall").strip().lower(), "overall")})
        main_prefs += [{"author_id": c.get("author_id"), **p} for p in r.get("preferences", []) if not p.get("benchmark")]
        main_switches += [{"author_id": c.get("author_id"), **s} for s in r.get("switches", []) if s.get("completed") and s["origin"] != s["destination"]]

    def overall(lines, target, dim=None):
        g = defaultdict(list)
        for x in lines:
            if x["target"] == target and x["firsthand"] and (dim is None or x["dimension"] == dim):
                g[x["author_id"]].append(x)
        return block([{"label": collapsed(v)} for v in g.values()])

    then_now = {"opus_5_then": {"window": "Aug 29 to Sep 5, first Xbench", **overall(main_lines, "claude-opus-5"),
                                "dimensions": {d: overall(main_lines, "claude-opus-5", d) for d in MODEL_DIMS}},
                "opus_5_5_now": {"window": "since launch", **focus_row["firsthand"],
                                 "dimensions": {d: {k: v for k, v in focus_row["dimensions"][d].items() if k != "top_aspects"} for d in MODEL_DIMS}},
                "opus_5_now": {"window": "since launch", **overall(sentiment, "claude-opus-5")}}

    cohorts = json.loads((PRIV / "cohorts.json").read_text())
    by55, bycc = defaultdict(list), defaultdict(list)
    for x in all_sentiment:
        if x["firsthand"] and x["target"] == FOCUS:
            by55[x["author_id"]].append(x)
        if x["firsthand"] and x["target"] == "claude_code":
            bycc[x["author_id"]].append(x)
    cohort_out = {}
    for name, ids in cohorts.items():
        ids = [i for i in ids if i not in excluded]
        cohort_out[name] = {"size": len(ids),
                            "opus_5_5": block([{"label": collapsed(by55[a])} for a in ids if a in by55]),
                            "claude_code": block([{"label": collapsed(bycc[a])} for a in ids if a in bycc]),
                            "came_back": len({s["author_id"] for s in switch_rows if s["author_id"] in ids and s["destination"] in ("claude_code", FOCUS)})}

    def cc_side(lines, prefs, sws):
        pv = dedupe_pref([p for p in prefs if {p["winner"], p["loser"]} == {"claude_code", "codex"}])
        s = {(x["author_id"], x["origin"], x["destination"]) for x in sws}
        return {"limits": overall(lines, "claude_code", "limits"), "overall": overall(lines, "claude_code"),
                "preference": {"claude_code": sum(p["winner"] == "claude_code" for p in pv), "codex": sum(p["winner"] == "codex" for p in pv)},
                "switches": {"to_codex": sum(1 for _, o, d in s if o == "claude_code" and d == "codex"),
                             "to_claude_code": sum(1 for _, o, d in s if o == "codex" and d == "claude_code")}}

    sup = [r for r in sentiment if r["target"] == FOCUS and r["firsthand"] and r["superlative"]]
    launch = {"t0": LAUNCHES["opus-5.5"]["t0"], "days": days, "focus": FOCUS, "rank_by_day": rank_by_day, "then_now": then_now, "cohorts": cohort_out,
              "claude_code": {"before": cc_side(main_lines, main_prefs, main_switches), "after": cc_side(sentiment, opinion, switch_rows)},
              "superlatives": {"positive_authors": len({r["author_id"] for r in sup if r["label"] == "positive"}),
                               "negative_authors": len({r["author_id"] for r in sup if r["label"] == "negative"}), "of": focus_row["firsthand"]["n"]},
              "sampling": {"posts_by_store": {sid: sum(1 for p in posts.values() if f"store:{sid}" in p["_routes"]) for sid in STORES}}}
    # ---------- featured: Opus 5.5 net sentiment in 12-hour steps, and nerf claims on the same clock ----------
    import random
    step = timedelta(hours=12)
    n_steps = math.ceil((end - T0) / step)
    def boot(votes, draws=1000):
        if len(votes) < 5:
            return None, None
        rng = random.Random("xbench-v3"); vals = []
        for _ in range(draws):
            smp = [votes[rng.randrange(len(votes))] for _ in votes]
            vals.append((smp.count("positive") - smp.count("negative")) / len(smp))
        vals.sort()
        return round(vals[25], 4), round(vals[974], 4)
    def trend(rows, start):
        """Net sentiment in 12-hour steps from `start` to the end of the window, one vote per person per step."""
        out = []
        for i in range(math.ceil((end - start) / step)):
            a, b = start + i * step, min(start + (i + 1) * step, end)
            g = defaultdict(list)
            for r in rows:
                if r["firsthand"] and a <= parse(r["created_at"]) < b:
                    g[r["author_id"]].append(r)
            votes = [collapsed(v) for v in g.values()]
            lo, hi = boot(votes)
            asp = defaultdict(Counter)
            for v in g.values():
                for r in v:
                    asp[r["label"]][r["aspect"].strip().lower()] += 1
            out.append({"start": a.strftime("%Y-%m-%dT%H:%M:%SZ"), "end": b.strftime("%Y-%m-%dT%H:%M:%SZ"), "partial": b < a + step,
                        **block([{"label": v} for v in votes]), "low": lo, "high": hi,
                        "top_positive": asp["positive"].most_common(3), "top_negative": asp["negative"].most_common(3)})
        return out

    curve = trend([r for r in sentiment if r["target"] == FOCUS], T0)

    # The switcher's other lines: a model's own pull over the last seven days, same rules, including days before T0.
    TRENDS = {"gpt-6-astra": ["trend-gpt-6-astra", "now-gpt-6-astra"]}
    trends, trend_evidence = {}, []
    for target, sids in TRENDS.items():
        pool = {}
        for sid in sids:
            path = PRIV / f"{sid}.json"
            if path.exists():
                pool.update({k: v for k, v in json.loads(path.read_text())["posts"].items() if not v.get("_parent_only")})
        start = end - timedelta(days=7)
        rows = []
        for pid, p in pool.items():
            r = labels.get(pid)
            if not r or r.get("vendor") or not r.get("relevant") or p.get("author_id") in excluded or parse(p["created_at"]) < start:
                continue
            for x in r.get("sentiment", []):
                if x["target"] == target:
                    rows.append({"post_id": pid, "author_id": p.get("author_id"), "created_at": p["created_at"], "label": x["label"],
                                 "firsthand": bool(x.get("firsthand")), "aspect": x.get("aspect", "overall"), "text": p.get("text", ""),
                                 "reason": r.get("reason", "")})
        c = trend(rows, start)
        if sum(b["n"] for b in c) == 0:
            continue
        g = defaultdict(list)
        for x in rows:
            if x["firsthand"]:
                g[x["author_id"]].append(x)
        trends[target] = {"start": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "curve": c, "overall": block([{"label": collapsed(v)} for v in g.values()]),
                          "first_xbench": next((m["firsthand"]["net_sentiment"] for m in json.loads((V2 / "public-summary.json").read_text())["sentiment"]["models"] if m["model"] == target), None)}
        trend_evidence += [{"post_id": x["post_id"], "text": x["text"], "created_at": x["created_at"], "url": f"https://x.com/i/web/status/{x['post_id']}",
                            "reason": x["reason"], "model": target, "sentiment": x["label"], "firsthand": True, "aspect": x["aspect"]} for x in rows if x["firsthand"]]
    nerf = {"buckets": [], "claims": []}
    nlabels = {}
    for path in sorted(glob.glob(str(ROOT / "data" / "labels-v3" / "nerf" / "labels" / "N-*.jsonl"))):
        for r in jsonl(path):
            nlabels[r["post_id"]] = r
    # claims can come from any pull that names Opus or Claude (the second nerf pass reads them all)
    opus_posts = {}
    for sid in STORES:
        path = PRIV / f"{sid}.json"
        if path.exists():
            opus_posts.update({k: v for k, v in json.loads(path.read_text())["posts"].items() if not v.get("_parent_only")})
    focus_store = json.loads((PRIV / "opus-5.5.json").read_text())["posts"]
    speakers = defaultdict(set)
    for p in focus_store.values():
        t = parse(p["created_at"])
        if not p.get("_parent_only") and T0 <= t <= end and p.get("author_id") not in excluded:
            speakers[math.floor((t - T0) / step)].add(p.get("author_id"))
    for i in range(n_steps):
        claims = {opus_posts[pid].get("author_id") for pid, r in nlabels.items() if r.get("claim") and pid in opus_posts
                  and math.floor((parse(opus_posts[pid]["created_at"]) - T0) / step) == i and opus_posts[pid].get("author_id") not in excluded}
        asks = {opus_posts[pid].get("author_id") for pid, r in nlabels.items() if r.get("asks") and pid in opus_posts
                and math.floor((parse(opus_posts[pid]["created_at"]) - T0) / step) == i}
        fears = {opus_posts[pid].get("author_id") for pid, r in nlabels.items() if r.get("fears") and pid in opus_posts
                 and math.floor((parse(opus_posts[pid]["created_at"]) - T0) / step) == i and opus_posts[pid].get("author_id") not in excluded}
        nerf["buckets"].append({"i": i, "claims": len(claims), "fears": len(fears), "asks": len(asks), "speakers": len(speakers[i]),
                                "rate": round(len(claims) / len(speakers[i]), 4) if speakers[i] else None})
    nerf["claims"] = sorted([{"post_id": pid, "text": opus_posts[pid].get("text", ""), "created_at": opus_posts[pid]["created_at"],
                              "url": f"https://x.com/i/web/status/{pid}", "quote": r.get("quote", ""), "firsthand": bool(r.get("firsthand")),
                              "kind": "claim" if r.get("claim") else "fears" if r.get("fears") else "asks" if r.get("asks") else "denies"}
                             for pid, r in nlabels.items() if pid in opus_posts and (r.get("claim") or r.get("fears") or r.get("asks") or r.get("denies"))
                             and opus_posts[pid].get("author_id") not in excluded], key=lambda x: x["created_at"])
    nerf["read"] = len(nlabels)
    launch["featured"] = {"step_hours": 12, "curve": curve, "nerf": nerf, "trends": trends,
                          "reference": {"opus_5_first_xbench": then_now["opus_5_then"]["net_sentiment"], "opus_5_5_window": focus_row["firsthand"]["net_sentiment"]}}
    authors = {p.get("author_id") for p in posts.values() if p.get("author_id")}
    summary = {
        "schema_version": "4.0", "release": "labels-v3", "source": "Official X API v2, full-archive search",
        "window": {"start": LAUNCHES["opus-5.5"]["t0"], "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "cells": days, "kind": "since_launch"},
        "corpus": {"unique_posts": len(posts), "unique_authors": len(authors), "comments": sum(1 for p in posts.values() if p.get("conversation_id") not in (None, p["id"])),
                   "classified_posts": len(labeled), "reviewer_overrides": sum(1 for r in labeled.values() if r.get("overridden")),
                   "excluded_ai_authors": len(excluded & authors), "excluded_posts": sum(1 for p in posts.values() if p.get("author_id") in excluded),
                   "vendor_posts": vendor_posts, "quota_audit": {}, "x_spend_usd": json.loads((PRIV / "ledger.json").read_text())["spend_usd"]},
        "sentiment": {"definition": "Firsthand stance since Opus 5.5 launched: the author used the model or reports a concrete result. One author per model. Each model is scored from posts pulled by its own name search (own-sample rule).",
                      "own_sample": {t: sorted(sids) for t, sids in OWN.items()},
                      "models": model_sentiment, "families": [sentiment_row(f) for f in FAMILIES]},
        "preference": {"definition": "Stated preferences between exact models since launch, firsthand only, benchmark reposts excluded. One author, one vote per matchup.",
                       "firsthand_votes": len(model_events), "all_votes": len(model_events_all), "distinct_authors": len({e["author_id"] for e in model_events}),
                       "head_to_head": battles(model_events),
                       "xbenchpref": {"method": "Ridge-regularized Bradley-Terry on firsthand votes; author bootstrap 95% intervals", "ratings": ratings(model_events, rated_models)},
                       "benchmark_reposts": len(benchmark_events)},
        "switching": {"definition": "First-person completed moves between exact models since launch; one author per edge.",
                      "verified_completed_switches": len(model_switches),
                      "by_origin_destination": dict(Counter(f'{r["origin"]} -> {r["destination"]}' for r in model_switches)),
                      "daily_counts": [sum(r["day_index"] == d for r in model_switches) for d in range(days)]},
        "harnesses": {"definition": "Claude Code, Codex, OpenCode, Pi and Grok Bot since launch.", "tracked": HARNESSES, "sentiment": harness_sentiment,
                      "head_to_head": battles(harness_events), "votes": len(harness_events),
                      "ratings": ratings(harness_events, HARNESSES) if len(harness_events) >= 5 else [], "vs_field": battles(harness_vs_field),
                      "switches": {"n": len(harness_switches), "by_direction": dict(Counter(f'{r["origin"]} -> {r["destination"]}' for r in harness_switches))}},
        "taxonomy": {"tracked_model_ids": MODELS, "harness_ids": HARNESSES, "family_ids": FAMILIES},
        "dimensions": {"definition": "Each labeler line carries a fixed dimension (ASPECT_DIMENSIONS.md); one author per target per dimension, firsthand only.",
                       "model": [["intelligence", "Intelligence"], ["speed", "Speed"], ["price", "Price"], ["steerability", "Steerability"], ["personality", "Personality"], ["overall", "Overall"], ["other", "Other"]],
                       "harness": [["limits", "Limits and quota"], ["reliability", "Reliability"], ["efficiency", "Token and context efficiency"], ["agent", "Agent behaviour"], ["dx", "Developer experience"], ["overall", "Overall"], ["other", "Other"]]},
        "launch": launch,
    }

    def public(row, **extra):
        return {"post_id": row["post_id"], "text": row["text"], "created_at": row["created_at"], "conversation_id": row.get("conversation_id"),
                "url": f'https://x.com/i/web/status/{row["post_id"]}', "reason": row.get("reason", ""), **extra}
    evidence = {
        "schema_version": "3.0",
        "sentiment": [public(r, model=r["target"], sentiment=r["label"], firsthand=r["firsthand"], endorsement=r["endorsement"], task=r["task"], aspect=r["aspect"],
                             dimension=r["dimension"], intensity=r["intensity"], superlative=r["superlative"], day_index=r["day_index"]) for r in sentiment if r["target"] in MODELS],
        "family_sentiment": [public(r, family=r["target"], sentiment=r["label"], firsthand=r["firsthand"], endorsement=r["endorsement"], task=r["task"], aspect=r["aspect"])
                             for r in sentiment if r["target"] in FAMILIES],
        "preference": [public(r, winner=r["winner"], loser=r["loser"], firsthand=r["firsthand"], task=r["task"], aspect=r["aspect"], day_index=r["day_index"]) for r in model_events_all],
        "switching": [public(r, origin=r["origin"], destination=r["destination"], day_index=r["day_index"]) for r in model_switches],
        "harness_sentiment": [public(r, harness=r["target"], sentiment=r["label"], firsthand=r["firsthand"], endorsement=r["endorsement"], task=r["task"], aspect=r["aspect"],
                                     dimension=r["dimension"], day_index=r["day_index"]) for r in sentiment if r["target"] in HARNESSES],
        "harness": [public(r, winner=r["winner"], loser=r["loser"], firsthand=r["firsthand"], task=r["task"], aspect=r["aspect"], dimension=r["dimension"], day_index=r["day_index"])
                    for r in harness_events + harness_vs_field],
        "harness_switching": [public(r, origin=r["origin"], destination=r["destination"], day_index=r["day_index"]) for r in harness_switches],
        "featured_trends": trend_evidence,
    }
    for rows in evidence.values():
        if isinstance(rows, list):
            assert not any(set(r) & {"author_id", "username", "name"} for r in rows), "author field in public evidence"
    # hero mural: firsthand stances only, one post per author, round-robin across models and harnesses so no one
    # target (least of all the heavily sampled Opus 5.5) fills the wall; no author fields (the v2 feed paid for
    # handle lookups, this one does not).
    pools = defaultdict(list)
    for r in sorted(evidence["sentiment"] + evidence["harness_sentiment"], key=lambda r: r["created_at"], reverse=True):
        if r["firsthand"]:
            pools[r.get("model") or r.get("harness")].append(r)
    hero, seen_posts = [], set()
    while len(hero) < 150 and any(pools.values()):
        for t in sorted(pools):
            while pools[t] and pools[t][0]["post_id"] in seen_posts:
                pools[t].pop(0)
            if pools[t]:
                r = pools[t].pop(0); seen_posts.add(r["post_id"])
                hero.append({"post_id": r["post_id"], "url": r["url"], "created_at": r["created_at"], "text": r["text"],
                             "target": r.get("model") or r.get("harness"), "sentiment": r["sentiment"], "aspect": r.get("aspect", "")})
    (OUT / "hero.json").write_text(json.dumps({"n": len(hero), "note": "firsthand stances, round-robin across targets, newest first; no author fields", "posts": hero}, ensure_ascii=False) + "\n")
    (OUT / "public-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n")
    (OUT / "public-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False) + "\n")
    print(json.dumps({"window": summary["window"], "labeled": f"{len(labeled)}/{len(posts)}",
                      "models": [(m["model"], m["firsthand"]["n"], m["firsthand"]["net_sentiment"]) for m in model_sentiment],
                      "pref_votes": len(model_events), "switches": len(model_switches), "harness_votes": len(harness_events)}))


if __name__ == "__main__":
    main()
