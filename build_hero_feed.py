#!/usr/bin/env python3
"""Pick the posts for the hero mural and attach their authors' public handle and avatar.

This is the only place Xbench stores anything about an author. The selection is
firsthand stances only, one post per author, spread across models and harnesses,
newest first within each. User lookups cost $0.01 each (GET /2/users?ids=).

    python3 build_hero_feed.py            # 150 posts
    python3 build_hero_feed.py --n 200

Writes data/labels-v2/hero.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V2 = ROOT / "data" / "labels-v2"
CORPUS = ROOT / "data" / "private" / "corpus.jsonl"


def token() -> str:
    for line in (ROOT / ".env").read_text().split("\n"):
        if line.startswith("X_BEARER_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("X_BEARER_TOKEN not found in .env")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=150); a = ap.parse_args()
    ev = json.loads((V2 / "public-evidence.json").read_text())
    rows = [dict(r, kind="model") for r in ev["sentiment"] if r["firsthand"]] + \
           [dict(r, kind="harness") for r in ev["harness_sentiment"] if r["firsthand"]]
    authors = {}
    for line in CORPUS.read_text().split("\n"):
        if line:
            r = json.loads(line); authors[r["post_id"]] = r.get("author_id")
    # one post per author; spread across targets by round-robin, newest first, skip very short posts
    by_target = defaultdict(list)
    for r in sorted(rows, key=lambda r: r["created_at"], reverse=True):
        if len(r["text"]) < 60 or not authors.get(r["post_id"]):
            continue
        by_target[r.get("model") or r.get("harness")].append(r)
    picked, seen_authors, seen_posts = [], set(), set()
    while len(picked) < a.n and any(by_target.values()):
        for t in list(by_target):
            while by_target[t]:
                r = by_target[t].pop(0)
                aid = authors[r["post_id"]]
                if aid in seen_authors or r["post_id"] in seen_posts:
                    continue
                seen_authors.add(aid); seen_posts.add(r["post_id"]); picked.append(r); break
            if len(picked) >= a.n:
                break
    ids = [authors[r["post_id"]] for r in picked]
    users = {}
    tok = token()
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        q = urllib.parse.urlencode({"ids": ",".join(chunk), "user.fields": "username,name,profile_image_url"})
        req = urllib.request.Request(f"https://api.x.com/2/users?{q}", headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            for u in json.load(resp).get("data", []):
                users[u["id"]] = u
        time.sleep(1)
    out = []
    for r in picked:
        u = users.get(authors[r["post_id"]])
        if not u:
            continue
        out.append({"post_id": r["post_id"], "url": r["url"], "created_at": r["created_at"], "text": r["text"],
                    "target": r.get("model") or r.get("harness"), "sentiment": r["sentiment"], "aspect": r.get("aspect", ""),
                    "username": u["username"], "name": u.get("name", ""),
                    "avatar": (u.get("profile_image_url") or "").replace("_normal", "_bigger")})
    (V2 / "hero.json").write_text(json.dumps({"n": len(out), "note": "Hero mural only. One firsthand post per author, spread across targets. Handles and avatars are public profile fields fetched for these posts alone.", "posts": out}, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"picked": len(picked), "with_user": len(out), "lookups": len(ids), "cost_usd": round(len(ids) * 0.01, 2),
                      "targets": len({p["target"] for p in out})}, indent=2))


if __name__ == "__main__":
    main()
