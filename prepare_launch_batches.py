#!/usr/bin/env python3
"""Cut launch pulls into labeling batches of 100, one era per batch.

Private batches (with text) go to data/private/launch/batches/; a text-free
index goes to data/launches/batches/. Pass store ids to batch only those. Parent-only posts are context, not
sample, and are never labeled. Incremental: a post already in a batch keeps it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRIV = ROOT / "data" / "private" / "launch"
PUB = ROOT / "data" / "launches"
BATCH = 100
# launch store -> era in LAUNCH_CLASSIFICATION_PROMPT.md, in labeling priority order
FIELD = [l["id"] for l in json.loads((ROOT / "data" / "launches.json").read_text())["launches"] if l["role"] in ("field", "trend")]
# the Opus 5.5 window only: the launch pull, its same-day rival, Claude Code, and every other current model
ERAS = [("opus-5.5", "opus-5.5"), ("gpt-6-sol", "opus-5.5"), ("claude-code-post", "opus-5.5"), *[(f, "opus-5.5") for f in FIELD]]


def main():
    (PRIV / "batches").mkdir(parents=True, exist_ok=True)
    (PUB / "batches").mkdir(parents=True, exist_ok=True)
    (PUB / "labels").mkdir(parents=True, exist_ok=True)
    have = set()
    existing = sorted((PUB / "batches").glob("L-*.jsonl"))
    for p in existing:
        have |= {json.loads(l)["post_id"] for l in p.read_text().split("\n") if l}
    n = len(existing)
    seen_era = {}
    only = set(sys.argv[1:])
    for store_id, era in ERAS:
        if only and store_id not in only:
            continue
        path = PRIV / f"{store_id}.json"
        if not path.exists():
            continue
        posts = json.loads(path.read_text())["posts"]
        rows = []
        for p in posts.values():
            if p.get("_parent_only") or p["id"] in have or seen_era.get(p["id"]):
                continue
            seen_era[p["id"]] = era
            parent_id = next((r["id"] for r in p.get("referenced_tweets") or [] if r.get("type") in ("replied_to", "quoted")), None)
            ctx = posts.get(parent_id) or posts.get(p.get("conversation_id")) if (parent_id or p.get("conversation_id") != p["id"]) else None
            rows.append({"post_id": p["id"], "era": era, "created_at": p["created_at"], "lang": p.get("lang"),
                         "is_reply": p.get("conversation_id") not in (None, p["id"]),
                         "text": p.get("text", ""), "root_text": (ctx or {}).get("text") if ctx and ctx["id"] != p["id"] else None})
        rows.sort(key=lambda r: (r["created_at"], r["post_id"]))
        for i in range(0, len(rows), BATCH):
            part = rows[i:i + BATCH]
            name = f"L-{n:03d}.jsonl"; n += 1
            (PRIV / "batches" / name).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in part) + "\n")
            (PUB / "batches" / name).write_text("\n".join(json.dumps({k: r[k] for k in ("post_id", "era", "created_at", "lang", "is_reply")}) for r in part) + "\n")
            have |= {r["post_id"] for r in part}
        print(f"{store_id:18} era {era:18} {len(rows):5} posts")
    print(f"{n} batches total")


if __name__ == "__main__":
    main()
