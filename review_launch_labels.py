#!/usr/bin/env python3
"""The reviewer's reading list for launch batches: every uncertain, AI-flagged
or vendor-flagged post, every superlative line, plus five seeded random posts.

    python3 review_launch_labels.py L-004.jsonl L-005.jsonl
    python3 review_launch_labels.py --firsthand L-004.jsonl   # audit: every post with a firsthand line
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUB = ROOT / "data" / "launches"
PRIV = ROOT / "data" / "private" / "launch" / "batches"


def jsonl(p):
    return [json.loads(l) for l in Path(p).read_text().split("\n") if l.strip()]


def fmt(post, lab):
    sig = []
    for s in lab.get("sentiment", []):
        sig.append(f"S {s['target']} {s['label']}{' fh' if s.get('firsthand') else ''}{' endorse' if s.get('endorsement') else ''}"
                   f" i{s.get('intensity')}{' SUP' if s.get('superlative') else ''} [{s.get('aspect')} / {s.get('dimension')}]")
    for p in lab.get("preferences", []):
        sig.append(f"P {p['winner']} > {p['loser']}{' fh' if p.get('firsthand') else ''}{' bench' if p.get('benchmark') else ''} [{p.get('aspect')}]")
    for s in lab.get("switches", []):
        sig.append(f"SW {s['origin']} -> {s['destination']} {'done' if s.get('completed') else 'not'}")
    flags = "".join(f" {k.upper()}" for k in ("uncertain", "ai_author", "vendor") if lab.get(k))
    out = f"[{lab['post_id']}] {post['created_at'][:16]} {post['text'][:420]!s}".replace("\n", " ")
    if post.get("root_text"):
        out += "\n   root: " + post["root_text"][:220].replace("\n", " ")
    out += f"\n   -> {'; '.join(sig) or ('relevant, none' if lab.get('relevant') else 'irrelevant')}{flags}\n   why: {lab.get('reason', '')[:240]}\n"
    return out


def main():
    rng = random.Random("xbench-launch-review")
    audit = "--firsthand" in sys.argv
    for name in [a for a in sys.argv[1:] if not a.startswith("--")]:
        posts = {r["post_id"]: r for r in jsonl(PRIV / name)}
        labels = jsonl(PUB / "labels" / name)
        over = {r["post_id"]: r for r in jsonl(PUB / "overrides" / name)} if (PUB / "overrides" / name).exists() else {}
        labels = [over.get(l["post_id"], l) for l in labels]  # the current record: a reviewer override wins
        if audit:
            # every post that carries a firsthand stance or preference, as the record stands now
            pick = [l for l in labels if any(s.get("firsthand") for s in l.get("sentiment", []) + l.get("preferences", []))
                    or l.get("uncertain") or any(s.get("superlative") for s in l.get("sentiment", []))]
            print(f"===== {name}: {len(pick)} posts with a firsthand line (audit) =====")
            for l in pick:
                print(("[OVERRIDDEN] " if l["post_id"] in over else "") + fmt(posts[l["post_id"]], l))
            continue
        pick = [l for l in labels if l.get("uncertain") or l.get("ai_author") or l.get("vendor") or any(s.get("superlative") for s in l.get("sentiment", []))]
        rest = [l for l in labels if l not in pick]
        sample = rng.sample(rest, min(5, len(rest)))
        print(f"===== {name} (era {posts[labels[0]['post_id']]['era']}): {len(pick)} flagged, {len(sample)} random =====")
        for l in pick + sample:
            print(fmt(posts[l["post_id"]], l))


if __name__ == "__main__":
    main()
