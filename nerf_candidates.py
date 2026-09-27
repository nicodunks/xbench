#!/usr/bin/env python3
"""Pick the Opus 5.5 posts worth reading for nerf claims (NERF_CLAIMS.md) and cut them into batches.

The word net is recall only: every candidate is read and judged by a labeler.
Writes data/private/launch/nerf/N-NNN.jsonl (text, private) and data/labels-v3/nerf/batches/ (ids).
    python3 nerf_candidates.py            # build batches
    python3 nerf_candidates.py --validate # check every label file
    python3 nerf_candidates.py --extend   # second pass: wider net, every pull, and posts whose label reason already
                                          # speaks of a decline; adds batches after the existing ones
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRIV = ROOT / "data" / "private" / "launch"
PUB = ROOT / "data" / "labels-v3" / "nerf"
T0 = "2026-09-22T16:31:03"
NET = re.compile(
    r"nerf|quanti[sz]|lobotom|dumb|stupid|dumber|worse|degrad|regress|downgrad|gimp|throttl|lazy|lazier|not the same|different model|"
    r"changed|swap|secretly|silently|nerv|was better|getting worse|fell off|falling off|dropped off|went downhill|brain ?dead|"
    r"降智|变笨|变蠢|量化|阉割|劣化|弱化|退化|缩水|降级|变差|バカ|劣化|弱体化|量子化|ナーフ|頭悪|悪くなった|nerfado|nerfeado|piorou|empeor|schlechter|dümmer",
    re.I)
BATCH = 100
WIDER = re.compile(r"lighter|feels off|not as good|first (day|few days|20h|hours)|launch day|honeymoon|quality (dropped|drop)|slower today|"
                   r"worse today|dumber today|smarter at launch|gaslit|a\/b|ab test|serving a|smaller model|distill|"
                   r"质量下降|不如刚|刚出的时候|刚发布|变慢|前几天|最初|最初は|初日", re.I)
NAMED = re.compile(r"opus|claude|5\.5", re.I)
DECLINE = re.compile(r"nerf|degrad|quantiz|lighter|downgrad|worse (since|than (at )?launch|today)|not the same|dumber|throttl|lobotom", re.I)


def extend():
    """Candidates the first net missed: the wider net over every pull that names Opus or Claude, plus every post whose
    launch label already reads as a decline. Only posts not read before; new batches continue the numbering."""
    import glob
    have = set()
    for b in (PUB / "batches").glob("N-*.jsonl"):
        have |= {json.loads(l)["post_id"] for l in b.read_text().split("\n") if l}
    stores = {}
    for sid in ["opus-5.5", "gpt-6-sol", "claude-code-post"] + [p.stem for p in PRIV.glob("now-*.json")]:
        path = PRIV / f"{sid}.json"
        if path.exists():
            stores.update({k: v for k, v in json.loads(path.read_text())["posts"].items() if not v.get("_parent_only")})
    labels = {}
    for path in sorted(glob.glob(str(ROOT / "data" / "launches" / "labels" / "L-*.jsonl"))) + sorted(glob.glob(str(ROOT / "data" / "launches" / "overrides" / "L-*.jsonl"))):
        for l in Path(path).read_text().split("\n"):
            if l.strip():
                r = json.loads(l); labels[r["post_id"]] = r
    pick = set()
    for pid, p in stores.items():
        if pid in have or p["created_at"] < T0:
            continue
        t = p.get("text", "")
        if NAMED.search(t) and (NET.search(t) or WIDER.search(t)):
            pick.add(pid)
        r = labels.get(pid)
        if r and any(x.get("target") == "claude-opus-5.5" and DECLINE.search((x.get("aspect") or "") + " " + r.get("reason", "")) for x in r.get("sentiment", [])):
            pick.add(pid)
    rows = []
    for pid in pick:
        p = stores[pid]
        parent = next((r["id"] for r in p.get("referenced_tweets") or [] if r.get("type") in ("replied_to", "quoted")), None)
        ctx = (stores.get(parent) or stores.get(p.get("conversation_id")) or {}).get("text")
        rows.append({"post_id": pid, "created_at": p["created_at"], "lang": p.get("lang"), "text": p.get("text", ""),
                     "root_text": ctx if ctx and ctx != p.get("text") else None})
    rows.sort(key=lambda r: r["created_at"])
    first = len(list((PUB / "batches").glob("N-*.jsonl")))
    for i in range(0, len(rows), BATCH):
        name = f"N-{first + i // BATCH:03d}.jsonl"
        part = rows[i:i + BATCH]
        (PRIV / "nerf" / name).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in part) + "\n")
        (PUB / "batches" / name).write_text("\n".join(json.dumps({"post_id": r["post_id"], "created_at": r["created_at"]}) for r in part) + "\n")
    print(f"{len(rows)} more candidates -> batches N-{first:03d}..")


def main():
    PUB.mkdir(parents=True, exist_ok=True); (PUB / "batches").mkdir(exist_ok=True); (PUB / "labels").mkdir(exist_ok=True)
    (PRIV / "nerf").mkdir(parents=True, exist_ok=True)
    posts = json.loads((PRIV / "opus-5.5.json").read_text())["posts"]
    rows = []
    for p in posts.values():
        if p.get("_parent_only") or p["created_at"] < T0:
            continue
        parent = next((r["id"] for r in p.get("referenced_tweets") or [] if r.get("type") in ("replied_to", "quoted")), None)
        ctx = (posts.get(parent) or posts.get(p.get("conversation_id")) or {}).get("text") if (parent or p.get("conversation_id") != p["id"]) else None
        if NET.search(p.get("text", "")):
            rows.append({"post_id": p["id"], "created_at": p["created_at"], "lang": p.get("lang"), "text": p.get("text", ""),
                         "root_text": ctx if ctx and ctx != p.get("text") else None})
    rows.sort(key=lambda r: r["created_at"])
    for i in range(0, len(rows), BATCH):
        name = f"N-{i // BATCH:03d}.jsonl"
        part = rows[i:i + BATCH]
        (PRIV / "nerf" / name).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in part) + "\n")
        (PUB / "batches" / name).write_text("\n".join(json.dumps({"post_id": r["post_id"], "created_at": r["created_at"]}) for r in part) + "\n")
    print(f"{len(rows)} candidates of {len(posts)} posts -> {(len(rows) + BATCH - 1) // BATCH} batches")


def validate():
    bad = 0
    for b in sorted((PUB / "batches").glob("N-*.jsonl")):
        ids = [json.loads(l)["post_id"] for l in b.read_text().split("\n") if l]
        out = PUB / "labels" / b.name
        if not out.exists():
            print(b.name, "missing"); continue
        lab = [json.loads(l) for l in out.read_text().split("\n") if l.strip()]
        errs = []
        if [r.get("post_id") for r in lab] != ids:
            errs.append("coverage/order mismatch")
        for r in lab:
            for k in ("claim", "fears", "asks", "denies", "firsthand"):
                if not isinstance(r.get(k), bool):
                    errs.append(f"{r.get('post_id')}: {k} not bool")
            if not isinstance(r.get("quote"), str):
                errs.append(f"{r.get('post_id')}: quote missing")
            if (r.get("claim") or r.get("fears") or r.get("asks") or r.get("denies")) and not r.get("quote"):
                errs.append(f"{r.get('post_id')}: flagged without a quote")
        print(b.name, "ok" if not errs else "errors", f"claims {sum(bool(r.get('claim')) for r in lab)} fears {sum(bool(r.get('fears')) for r in lab)} asks {sum(bool(r.get('asks')) for r in lab)} denies {sum(bool(r.get('denies')) for r in lab)}")
        for e in errs[:6]:
            print("   !", e)
        bad += bool(errs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    validate() if "--validate" in sys.argv else extend() if "--extend" in sys.argv else main()
