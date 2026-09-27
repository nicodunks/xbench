#!/usr/bin/env python3
"""Cohorts from the main release (Aug 29 - Sep 5) for the Opus 5.5 follow-up.

An author's cohort is fixed by what they said before Opus 5.5 existed:
  opus5_neg / opus5_pos / opus5_mixed   collapsed firsthand stance on claude-opus-5
  cc_limits_neg                        firsthand negative on Claude Code limits
  cc_to_codex                          completed switch Claude Code -> Codex
Writes data/private/launch/cohorts.json (author ids, private) and
data/private/launch/cohort-authors.json (the union, for the from: queries).
"""
from __future__ import annotations

import glob
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V2 = ROOT / "data" / "labels-v2"
OUT = ROOT / "data" / "private" / "launch"
SCORE = {"positive": 1, "mixed": 0, "negative": -1}


def jsonl(p):
    return [json.loads(l) for l in Path(p).read_text().split("\n") if l]


def load_release():
    corpus = {r["post_id"]: r for r in jsonl(ROOT / "data" / "private" / "corpus.jsonl")}
    labels = {}
    for p in sorted(glob.glob(str(V2 / "labels" / "batch-*.jsonl"))):
        for r in jsonl(p):
            labels[r["post_id"]] = r
    labels = {k: v for k, v in labels.items() if k in corpus}
    for r in jsonl(V2 / "overrides.jsonl"):
        if r["post_id"] in labels:
            labels[r["post_id"]] = r
    flags = defaultdict(list)
    for pid, r in labels.items():
        flags[corpus[pid].get("author_id")].append(bool(r.get("ai_author")))
    excluded = {a for a, f in flags.items() if a and sum(f) * 2 > len(f)}
    hashed = {x["author_sha256"] for x in json.loads((V2 / "excluded-authors.json").read_text())}
    excluded |= {a for a in flags if a and hashlib.sha256(str(a).encode()).hexdigest() in hashed}
    return corpus, labels, excluded


def main():
    corpus, labels, excluded = load_release()
    aspect_map = {}
    for p in glob.glob(str(V2 / "aspect-map" / "maps" / "harness*.jsonl")):
        for r in jsonl(p):
            aspect_map[r["aspect"].strip().lower()] = r["dimension"]
    opus = defaultdict(int); opus_seen = set(); cc_lim = set(); switch = set()
    for pid, r in labels.items():
        a = corpus[pid].get("author_id")
        if not a or a in excluded or not r.get("relevant"):
            continue
        for s in r.get("sentiment", []):
            if not s.get("firsthand"):
                continue
            if s["target"] == "claude-opus-5":
                opus[a] += SCORE[s["label"]]; opus_seen.add(a)
            if s["target"] == "claude_code" and s["label"] == "negative" and aspect_map.get((s.get("aspect") or "").strip().lower()) == "limits":
                cc_lim.add(a)
        for s in r.get("switches", []):
            if s.get("completed") and s["origin"] == "claude_code" and s["destination"] == "codex":
                switch.add(a)
    cohorts = {"opus5_neg": sorted(a for a in opus_seen if opus[a] < 0), "opus5_pos": sorted(a for a in opus_seen if opus[a] > 0),
               "opus5_mixed": sorted(a for a in opus_seen if opus[a] == 0), "cc_limits_neg": sorted(cc_lim), "cc_to_codex": sorted(switch)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cohorts.json").write_text(json.dumps(cohorts))
    union = sorted(set().union(*cohorts.values()))
    (OUT / "cohort-authors.json").write_text(json.dumps(union))
    print({k: len(v) for k, v in cohorts.items()}, "union", len(union))


if __name__ == "__main__":
    main()
