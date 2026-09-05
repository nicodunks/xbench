#!/usr/bin/env python3
"""Assemble the private corpus for the current window from day files.

Sources, merged by post id (longest text wins, metrics take the max):
  data/private/corpus-seed.jsonl   the original seven-day pull (frozen)
  data/private/days/*.json         one file per 24-hour cell from collect_daily.py

The window is the last seven cells: the latest day-file end, back seven cells
of the seed's cell length. Writes data/private/corpus.jsonl (posts inside the
window only) and updates the window in data/window.json.
"""
from __future__ import annotations

import glob
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRIV = ROOT / "data" / "private"
SEED = PRIV / "corpus-seed.jsonl"
OUT = PRIV / "corpus.jsonl"
WINDOW = ROOT / "data" / "window.json"


def parse(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    if not SEED.exists() and OUT.exists():
        OUT.rename(SEED)
    posts = {}
    for line in SEED.read_text().split("\n"):
        if line:
            r = json.loads(line); posts[r["post_id"]] = r
    days = sorted(glob.glob(str(PRIV / "days" / "*.json")))
    ends = []
    for path in days:
        d = json.loads(Path(path).read_text())
        if not d.get("complete"):
            print("skipping incomplete", path); continue
        ends.append(parse(d["window"]["end"]))
        for p in d["posts"].values():
            rec = {"post_id": p["id"], "author_id": p.get("author_id"), "created_at": p["created_at"], "lang": p.get("lang"),
                   "conversation_id": p.get("conversation_id"), "is_comment": p.get("conversation_id") not in (None, p["id"]),
                   "text": p.get("text", ""), "root_text": p.get("_root_text", ""), "referenced_tweets": p.get("referenced_tweets", []),
                   "sources": [str(Path(path).relative_to(ROOT))], "routes": p.get("_routes", [])}
            old = posts.get(p["id"])
            if old is None:
                posts[p["id"]] = rec
            else:
                if len(rec["text"]) > len(old.get("text", "")): old["text"] = rec["text"]
                if len(rec["root_text"] or "") > len(old.get("root_text") or ""): old["root_text"] = rec["root_text"]
                old["sources"] = sorted(set(old.get("sources", []) + rec["sources"]))
    win = json.loads(WINDOW.read_text())
    seed_start, seed_end = parse(win["window"]["start"]), parse(win["window"]["end"])
    cell = (seed_end - seed_start) / 7
    end = max([seed_end] + ends)
    start = end - cell * 7
    kept = [p for p in posts.values() if start <= parse(p["created_at"]) < end]
    kept.sort(key=lambda p: p["created_at"])
    with OUT.open("w") as f:
        for p in kept:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    win["window"] = {"start": iso(start), "end": iso(end), "cells": 7, "kind": "rolling_7_cells"}
    win["corpus"] = {"unique_posts": len(kept), "unique_authors": len({p.get("author_id") for p in kept}),
                     "comments": sum(1 for p in kept if p.get("is_comment"))}
    WINDOW.write_text(json.dumps(win, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"window": win["window"], "posts_in_window": len(kept), "all_posts_known": len(posts),
                      "day_files": len(days)}, indent=2))


if __name__ == "__main__":
    main()
