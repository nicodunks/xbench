#!/usr/bin/env python3
"""Alignment check for launch labels: each record's reason must quote its own post.

Catches the one failure the structural validator cannot see: a record written
under a neighbouring post's id. For every record with a sentiment, preference
or switch line, the first quoted phrase in the reason (straight or curly
quotes, at least 6 characters) must appear in that post's text or root text,
ignoring case, whitespace and punctuation. Prints the misses.

    python3 align_launch_labels.py            # every labeled batch
"""
from __future__ import annotations

import glob
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUB = ROOT / "data" / "launches"
PRIV = ROOT / "data" / "private" / "launch" / "batches"
QUOTE = re.compile(r"[\"“”'‘’「『]([^\"“”「」『』]{6,}?)[\"“”'‘’」』]")


def norm(s: str) -> str:
    return re.sub(r"[\W_]+", "", s.lower())


def main():
    misses, checked = [], 0
    for path in sorted(glob.glob(str(PUB / "labels" / "L-*.jsonl"))):
        name = Path(path).name
        src = {json.loads(l)["post_id"]: json.loads(l) for l in (PRIV / name).read_text().split("\n") if l}
        for line in Path(path).read_text().split("\n"):
            if not line.strip():
                continue
            r = json.loads(line)
            if not (r.get("sentiment") or r.get("preferences") or r.get("switches")):
                continue
            m = QUOTE.search(r.get("reason", ""))
            if not m:
                continue
            checked += 1
            post = src.get(r["post_id"], {})
            raw = html.unescape((post.get("text") or "") + " " + (post.get("root_text") or ""))
            latin = sum(c.isascii() for c in raw if c.isalpha()) / max(1, sum(c.isalpha() for c in raw))
            if latin < 0.5 and all(c.isascii() for c in m.group(1)):
                continue  # an English reason quoting a translated post; nothing to match
            hay = norm(raw)
            # quotes elide with "..." or "…"; every fragment of 6+ characters must be in the post
            frags = [norm(f)[:40] for f in re.split(r"\.{2,}|…", m.group(1)) if len(norm(f)) >= 6]
            if frags and not all(f in hay for f in frags):
                misses.append((name, r["post_id"], m.group(1)[:60], (post.get("text") or "")[:80].replace("\n", " ")))
    for n, pid, q, t in misses:
        print(f"{n} {pid}\n   quote: {q}\n   post:  {t}")
    print(f"{checked} records checked, {len(misses)} quotes not found in their own post")
    sys.exit(1 if misses else 0)


if __name__ == "__main__":
    main()
