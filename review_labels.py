#!/usr/bin/env python3
"""Build the reviewer's reading list from v2 label batches.

Selects every line marked uncertain or ai_author plus a seeded random sample
of the rest, and prints post text, root, and labels in a compact form. The
reviewer reads these and applies overrides via data/labels-v2/overrides.jsonl.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V2 = ROOT / "data" / "labels-v2"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().split("\n") if l.strip()]


def fmt(post: dict, label: dict) -> str:
    sig = []
    for s in label.get("sentiment", []):
        sig.append(f"S {s['target']} {s['label']}{' fh' if s.get('firsthand') else ''}{' endorse' if s.get('endorsement') else ''} [{s.get('aspect')}]")
    for p in label.get("preferences", []):
        sig.append(f"P {p['winner']} > {p['loser']}{' fh' if p.get('firsthand') else ''}{' bench' if p.get('benchmark') else ''} [{p.get('aspect')}]")
    for s in label.get("switches", []):
        sig.append(f"SW {s['origin']} -> {s['destination']} {'done' if s.get('completed') else 'not'}")
    flags = ("irrelevant" if not label.get("relevant") else "relevant, none") if not sig else "; ".join(sig)
    extra = (" UNCERTAIN" if label.get("uncertain") else "") + (" AI" if label.get("ai_author") else "")
    text = post.get("text", "").replace("\n", " ")[:300]
    root = (post.get("root_text") or "")[:160].replace("\n", " ")
    out = f"[{label['post_id']}] {text}"
    if root:
        out += f"\n   root: {root}"
    out += f"\n   -> {flags}{extra}\n   why: {label.get('reason', '')[:200]}\n"
    return out


def main() -> None:
    names = sys.argv[1:] or sorted(p.name for p in (V2 / "labels").glob("batch-*.jsonl"))
    rng = random.Random("xbench-review")
    for name in names:
        posts = {r["post_id"]: r for r in read_jsonl(V2 / "batches" / name)}
        labels = read_jsonl(V2 / "labels" / name)
        flagged = [l for l in labels if l.get("uncertain") or l.get("ai_author")]
        rest = [l for l in labels if not (l.get("uncertain") or l.get("ai_author"))]
        sample = rng.sample(rest, min(5, len(rest)))
        print(f"===== {name}: {len(flagged)} flagged, {len(sample)} sampled =====")
        for l in flagged + sample:
            print(fmt(posts[l["post_id"]], l))


if __name__ == "__main__":
    main()
