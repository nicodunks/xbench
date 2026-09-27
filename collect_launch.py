#!/usr/bin/env python3
"""Launch-anchored X pulls for Xbench Launches. See LAUNCHES.md.

Every request goes through one ledger (data/private/launch/ledger.json) that
caches the response by a hash of its path and params, so a rerun never pays
twice, and that refuses any request which could take total spend past the cap.

    python3 collect_launch.py test                   # one 10-post full-archive call
    python3 collect_launch.py counts                 # hourly counts around every launch
    python3 collect_launch.py sample opus-5.5 --posts-per-day 900
    python3 collect_launch.py conversations opus-5.5 --roots 40 --per-root 30
    python3 collect_launch.py cohort opus-5.5
    python3 collect_launch.py parents opus-5.5 --cap 300 --named "opus|5\\.5|claude"
    python3 collect_launch.py status

Costs are counted pessimistically: $0.005 per returned post, $0.01 per
full-archive counts call, duplicates included.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRIV = ROOT / "data" / "private" / "launch"
LEDGER = PRIV / "ledger.json"
API = "https://api.x.com/2"
POST_PRICE, COUNT_PRICE = 0.005, 0.01
CAP_USD = 99.5  # hard ceiling across every run; the owner's limit is $100
FIELDS = "id,text,author_id,created_at,conversation_id,lang,public_metrics,referenced_tweets"
LAUNCHES = json.loads((ROOT / "data" / "launches.json").read_text())["launches"]


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def token() -> str:
    for line in (ROOT / ".env").read_text().split("\n"):
        if line.startswith("X_BEARER_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("X_BEARER_TOKEN not found in .env")


def exclusions() -> str:
    p = ROOT / "data" / "private" / "excluded-author-ids.json"
    return " ".join(f"-from:{i}" for i in json.loads(p.read_text())) if p.exists() else ""


class Ledger:
    def __init__(self):
        PRIV.mkdir(parents=True, exist_ok=True)
        (PRIV / "cache").mkdir(exist_ok=True)
        self.state = json.loads(LEDGER.read_text()) if LEDGER.exists() else {"spend_usd": 0.0, "calls": 0, "posts": 0, "log": []}
        self.tok = None

    def save(self):
        tmp = LEDGER.with_suffix(".tmp"); tmp.write_text(json.dumps(self.state, indent=1)); tmp.replace(LEDGER)

    def get(self, path: str, params: dict, worst_case_usd: float, label: str) -> dict:
        key = hashlib.sha1(json.dumps({"p": path, **params}, sort_keys=True).encode()).hexdigest()[:20]
        cached = PRIV / "cache" / f"{key}.json"
        if cached.exists():
            return json.loads(cached.read_text())
        if self.state["spend_usd"] + worst_case_usd > CAP_USD:
            raise SystemExit(f"cap: ${self.state['spend_usd']:.2f} spent, request could add ${worst_case_usd:.2f}, cap ${CAP_USD}")
        self.tok = self.tok or token()
        url = f"{API}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.tok}"})
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req, timeout=40) as r:
                    data = json.load(r); break
            except urllib.error.HTTPError as e:
                body = e.read()[:400].decode("utf-8", "replace")
                if e.code == 429:
                    reset = int(e.headers.get("x-rate-limit-reset", "0") or 0)
                    wait = max(5, min(900, reset - int(time.time()) + 2)) if reset else 30
                    print(f"429, waiting {wait}s", file=sys.stderr); time.sleep(wait); continue
                if e.code in (401, 402, 403):
                    raise SystemExit(f"HTTP {e.code}: {body}")
                if e.code == 400:
                    print(f"400 skipped [{label}]: {body[:200]}", file=sys.stderr)
                    data = {"data": [], "meta": {}, "_error": body[:300]}; break
                if e.code >= 500 and attempt < 5:
                    time.sleep(5 * (attempt + 1)); continue
                raise
        cost = COUNT_PRICE if "counts" in path else len(data.get("data", []) or []) * POST_PRICE
        self.state["spend_usd"] = round(self.state["spend_usd"] + cost, 4)
        self.state["calls"] += 1
        if "counts" not in path:
            self.state["posts"] += len(data.get("data", []) or [])
        self.state["log"].append({"at": iso(datetime.now(timezone.utc)), "label": label, "cost": round(cost, 4)})
        cached.write_text(json.dumps(data, ensure_ascii=False))
        self.save()
        time.sleep(1.1)  # full-archive search allows one request a second
        return data


class Store:
    """Posts pulled for one launch, merged by id with the routes that found them."""

    def __init__(self, launch_id: str):
        self.path = PRIV / f"{launch_id}.json"
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {"posts": {}}

    def add(self, posts: list[dict], route: str, **meta):
        for p in posts or []:
            rec = self.state["posts"].setdefault(p["id"], {**p, "_routes": []})
            if len(p.get("text", "")) > len(rec.get("text", "")):
                rec["text"] = p["text"]
            tag = route + (":" + ",".join(f"{k}={v}" for k, v in meta.items()) if meta else "")
            if tag not in rec["_routes"]:
                rec["_routes"].append(tag)

    def save(self):
        tmp = self.path.with_suffix(".tmp"); tmp.write_text(json.dumps(self.state, ensure_ascii=False)); tmp.replace(self.path)


def launch(lid: str) -> dict:
    for l in LAUNCHES:
        if l["id"] == lid:
            return l
    sys.exit(f"unknown launch {lid}")


def search(led: Ledger, query: str, start: datetime, end: datetime, n: int, label: str) -> list[dict]:
    q = f"{query} -is:retweet {exclusions()}".strip()
    if len(q) > 1024:  # the exclusion list is a courtesy; the aggregator drops those authors anyway
        q = f"{query} -is:retweet"
    d = led.get("/tweets/search/all", {"query": q, "start_time": iso(start), "end_time": iso(end),
                                       "max_results": max(10, min(500, n)), "sort_order": "recency", "tweet.fields": FIELDS},
                worst_case_usd=max(10, n) * POST_PRICE, label=label)
    return d.get("data", []) or []


def cmd_test(led: Ledger, a):
    l = launch("opus-5.5"); t0 = parse(l["t0"])
    got = search(led, l["query"], t0 + timedelta(hours=1), t0 + timedelta(hours=2), 10, "test")
    print(json.dumps({"returned": len(got), "spend_usd": led.state["spend_usd"],
                      "sample": [g["text"][:120] for g in got[:3]]}, ensure_ascii=False, indent=1))


def cmd_counts(led: Ledger, a):
    """Hourly volume from two days before each launch to six days after (or now)."""
    now = datetime.now(timezone.utc) - timedelta(minutes=2)
    out_path = ROOT / "data" / "private" / "launch" / "counts.json"
    out = json.loads(out_path.read_text()) if out_path.exists() else {}
    for l in LAUNCHES:
        if a.only and l["id"] not in a.only:
            continue
        t0 = parse(l["t0"]); start, end = t0 - timedelta(days=2), min(t0 + timedelta(days=6), now)
        buckets, next_token = [], None
        while True:
            params = {"query": f"{l['query']} -is:retweet", "start_time": iso(start), "end_time": iso(end), "granularity": "hour"}
            if next_token:
                params["next_token"] = next_token
            d = led.get("/tweets/counts/all", params, COUNT_PRICE, f"counts {l['id']}")
            buckets += d.get("data", []) or []
            next_token = (d.get("meta") or {}).get("next_token")
            if not next_token:
                break
        buckets.sort(key=lambda b: b["start"])
        out[l["id"]] = {"query": l["query"], "t0": l["t0"], "hours": [[b["start"], b["tweet_count"]] for b in buckets]}
        total = sum(b["tweet_count"] for b in buckets)
        print(f"{l['id']:22} {len(buckets):4} hours  {total:8} posts")
    out_path.write_text(json.dumps(out, indent=1))
    print(f"spend ${led.state['spend_usd']:.2f}")


def cmd_sample(led: Ledger, a):
    """Hour-stratified sample: each day gets a post budget, split across its hours by true volume (min 10 a call)."""
    l = launch(a.launch); t0 = parse(l["t0"]); store = Store(l["id"])
    counts = json.loads((PRIV / "counts.json").read_text())[l["id"]]["hours"]
    now = datetime.now(timezone.utc) - timedelta(minutes=2)
    hours = [(parse(h), c) for h, c in counts]
    for day in range(a.first_day, a.last_day + 1):
        ds, de = t0 + timedelta(days=day), min(t0 + timedelta(days=day + 1), now)
        if ds >= de:
            break
        # hour buckets are clock hours; the day starts at t0's minute, so walk clock hours overlapping [ds, de)
        cells = [(max(h, ds), min(h + timedelta(hours=1), de), c) for h, c in hours if h + timedelta(hours=1) > ds and h < de]
        total = sum(c for _, _, c in cells) or 1
        frac = (de - ds) / timedelta(days=1)
        budget = a.posts_per_day * frac
        pulled = 0
        for s, e, c in cells:
            if c == 0 or e <= s:
                continue
            n = min(c, max(10, round(budget * c / total)), 100)
            got = search(led, l["query"], s, e, n, f"sample {l['id']} d{day}")
            store.add(got, "sample", day=day); pulled += len(got)
        store.save()
        print(f"{l['id']} day {day}: {pulled} posts, {len(store.state['posts'])} held, spend ${led.state['spend_usd']:.2f}")


def cmd_field(led: Ledger, a):
    """Every other current model in the Opus 5.5 window: fixed slices, a few posts each, plus one preference-candidate call."""
    now = datetime.now(timezone.utc) - timedelta(minutes=2)
    pref = '(prefer OR preferred OR "better than" OR beats OR versus OR vs OR "switched to")'
    for l in LAUNCHES:
        if l["role"] not in ("field", "trend") or (a.only and l["id"] not in a.only):
            continue
        t0 = parse(l["t0"]); store = Store(l["id"]); s = t0; pulled = 0
        while s < now:
            e = min(s + timedelta(hours=a.slice_hours), now)
            got = search(led, l["query"], s, e, a.per_slice, f"field {l['id']}")
            store.add(got, "sample", day=math.floor((s - t0) / timedelta(days=1))); pulled += len(got); s = e
        if a.pref:
            got = search(led, f"{l['query']} {pref}", t0, now, a.pref, f"field-pref {l['id']}")
            store.add(got, "preference"); pulled += len(got)
        store.save()
        print(f"{l['id']:24} {pulled:4} posts, spend ${led.state['spend_usd']:.2f}")


def cmd_conversations(led: Ledger, a):
    """Replies under the most-replied roots in the sample: where 'I tried it' lives."""
    l = launch(a.launch); t0 = parse(l["t0"]); store = Store(l["id"])
    posts = store.state["posts"]
    hint = l["hint"].lower()
    roots = [p for p in posts.values() if p["id"] == p.get("conversation_id") and hint in p.get("text", "").lower()
             and (p.get("public_metrics") or {}).get("reply_count", 0) >= a.min_replies]
    for extra in l.get("extra_roots", []):
        if extra not in [r["id"] for r in roots]:
            roots.insert(0, {"id": extra, "created_at": l["t0"], "public_metrics": {"reply_count": 10**6}})
    roots.sort(key=lambda p: -(p.get("public_metrics") or {}).get("reply_count", 0))
    horizon = min(t0 + timedelta(days=a.days), datetime.now(timezone.utc) - timedelta(minutes=2))
    done = 0
    for r in roots[:a.roots]:
        start = max(parse(r["created_at"]), t0 - timedelta(days=2))
        if start >= horizon:
            continue
        got = search(led, f"conversation_id:{r['id']}", start, horizon, a.per_root, f"conv {l['id']}")
        store.add(got, "conversation", root=r["id"]); done += 1
        store.save()
    print(f"{done} threads, {len(posts)} held, spend ${led.state['spend_usd']:.2f}")


def cmd_cohort(led: Ledger, a):
    """Every post since launch naming Opus or Claude by authors who took a firsthand stance on Opus 5 in the main release."""
    l = launch(a.launch); t0 = parse(l["t0"]); store = Store(l["id"])
    ids = json.loads((PRIV / "cohort-authors.json").read_text())
    end = min(t0 + timedelta(days=a.days), datetime.now(timezone.utc) - timedelta(minutes=2))
    chunk, chunks = [], []
    for i in ids:
        trial = chunk + [i]
        if len(" OR ".join(f"from:{x}" for x in trial)) + 120 > 1024:
            chunks.append(chunk); chunk = [i]
        else:
            chunk = trial
    if chunk:
        chunks.append(chunk)
    for c in chunks:
        q = "(" + " OR ".join(f"from:{x}" for x in c) + ") " + l["cohort_terms"]
        next_token, pages = None, 0
        while pages < 2:
            params = {"query": f"{q} -is:retweet", "start_time": iso(t0), "end_time": iso(end),
                      "max_results": 100, "sort_order": "recency", "tweet.fields": FIELDS}
            if next_token:
                params["next_token"] = next_token
            d = led.get("/tweets/search/all", params, 100 * POST_PRICE, f"cohort {l['id']}")
            store.add(d.get("data", []) or [], "cohort"); pages += 1
            next_token = (d.get("meta") or {}).get("next_token")
            if not next_token:
                break
        store.save()
    print(f"{len(chunks)} cohort queries, {len(store.state['posts'])} held, spend ${led.state['spend_usd']:.2f}")


def cmd_parents(led: Ledger, a):
    """Fetch the post each sampled reply answers or quotes, when we do not hold it. The labeler needs it to know the target."""
    l = launch(a.launch); store = Store(l["id"]); posts = store.state["posts"]
    want = []
    named = re.compile(a.named, re.I) if a.named else None
    for p in posts.values():
        if p.get("_parent_only"):
            continue
        if named and named.search(p.get("text", "")):
            continue  # the post names its target itself; context is a luxury
        for ref in p.get("referenced_tweets") or []:
            if ref.get("type") in ("replied_to", "quoted") and ref["id"] not in posts and ref["id"] not in want:
                want.append(ref["id"])
    want = want[:a.cap]
    for i in range(0, len(want), 100):
        chunk = want[i:i + 100]
        d = led.get("/tweets", {"ids": ",".join(chunk), "tweet.fields": FIELDS}, len(chunk) * POST_PRICE, f"parents {l['id']}")
        got = d.get("data", []) or []
        for g in got:
            g["_parent_only"] = True
        store.add(got, "parent")
        store.save()
    print(f"{len(want)} parents asked, {len(posts)} held, spend ${led.state['spend_usd']:.2f}")


def cmd_status(led: Ledger, a):
    by = {}
    for e in led.state["log"]:
        k = e["label"].split(" d")[0]
        by[k] = round(by.get(k, 0) + e["cost"], 3)
    print(json.dumps({"spend_usd": led.state["spend_usd"], "cap": CAP_USD, "calls": led.state["calls"],
                      "posts": led.state["posts"], "by_route": by}, indent=1))
    for l in LAUNCHES:
        s = PRIV / f"{l['id']}.json"
        if s.exists():
            print(f"  {l['id']:22} {len(json.loads(s.read_text())['posts']):6} posts held")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["test", "counts", "sample", "field", "conversations", "cohort", "parents", "status"])
    ap.add_argument("launch", nargs="?")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--posts-per-day", type=int, default=600)
    ap.add_argument("--first-day", type=int, default=-1)
    ap.add_argument("--last-day", type=int, default=5)
    ap.add_argument("--roots", type=int, default=30)
    ap.add_argument("--per-root", type=int, default=30)
    ap.add_argument("--min-replies", type=int, default=3)
    ap.add_argument("--days", type=int, default=6)
    ap.add_argument("--cap", type=int, default=600)
    ap.add_argument("--slice-hours", type=float, default=8)
    ap.add_argument("--per-slice", type=int, default=10)
    ap.add_argument("--pref", type=int, default=20)
    ap.add_argument("--named", help="skip replies whose own text matches this regex")
    a = ap.parse_args()
    led = Ledger()
    {"test": cmd_test, "counts": cmd_counts, "sample": cmd_sample, "field": cmd_field, "conversations": cmd_conversations,
     "cohort": cmd_cohort, "parents": cmd_parents, "status": cmd_status}[a.cmd](led, a)


if __name__ == "__main__":
    main()
