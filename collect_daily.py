#!/usr/bin/env python3
"""Pull one 24-hour cell of X posts for Xbench. See X_API_GUIDE.md.

    python3 collect_daily.py                      # cell ending three minutes ago
    python3 collect_daily.py --start 2026-09-03T22:37:18Z --end 2026-09-04T22:37:18Z
    python3 collect_daily.py --budget 20
    python3 collect_daily.py --start ... --end ... --routes backfill   # harness names, pairs, parents, conversations only

Writes data/private/days/<start>.json and saves after every request, so a
rerun resumes. Costs are counted pessimistically: every returned post and
every counts call is $0.005, duplicates included.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DAYS = ROOT / "data" / "private" / "days"
API = "https://api.x.com/2"
PRICE = 0.005
FIELDS = "id,text,author_id,created_at,conversation_id,lang,public_metrics,referenced_tweets"

MODELS = {
    "claude-fable-5.1": '("Claude Fable 5.1" OR "Fable 5.1")',
    "claude-opus-5": '("Claude Opus 5" OR "Opus 5")',
    "gpt-6-astra": '("GPT-6 Astra" OR "GPT 6 Astra")',
    "gpt-5.6-sol": '("GPT-5.6 Sol" OR "GPT 5.6 Sol" OR "Sol 5.6")',
    "gpt-5.6-luna": '("GPT-5.6 Luna" OR "GPT 5.6 Luna" OR "Luna 5.6")',
    "muse-spark-1.3": '("Muse Spark 1.3" OR "MuseSpark 1.3")',
    "muse-spark-1.2": '("Muse Spark 1.2" OR "MuseSpark 1.2")',
    "gemini-3.8-flash": '("Gemini 3.8 Flash" OR "Gemini Flash 3.8")',
    "gemini-3.7-flash": '("Gemini 3.7 Flash" OR "Gemini Flash 3.7")',
    "grok-4.6": '("Grok 4.6")',
    "glm-5.3": '(("GLM 5.3" OR "GLM-5.3") -("GLM 5.3 Flash" OR "GLM-5.3-Flash"))',
    "glm-5.3-flash": '("GLM 5.3 Flash" OR "GLM-5.3-Flash")',
    "kimi-k3": '("Kimi K3" OR "Kimi-K3")',
}
HARNESSES = {
    "claude_code": ('("Claude Code")', 4, 15),
    "codex": ('(Codex)', 4, 15),
    "grokbot": ('("Grok Bot" OR "Grok Build" OR "grok cli" OR grokbot)', 4, 15),
    "opencode": ('(OpenCode)', 1, 10),
    "pi": ('("Oh My Pi" OR ohmypi OR "pi coding agent")', 1, 10),
}
PREF = '(prefer OR preferred OR "better than" OR beats OR "wins over" OR versus OR vs OR "would choose")'
SWITCH = '(switched OR switching OR "moved from" OR ditched OR replacing OR "now using" OR migrated OR "left for" OR cancelled)'
PAIRS = {
    "claude_code-codex": ('(("Claude Code" "Codex") OR ("Claude Code" (prefer OR versus OR vs OR switch)) OR (Codex (prefer OR versus OR vs OR switch)))', 4, 30),
    "grokbot-claude_code": ('(("Grok Bot" OR "Grok Build") "Claude Code")', 1, 20),
    "grokbot-codex": ('(("Grok Bot" OR "Grok Build") Codex)', 1, 20),
}
NAME_HINTS = ["fable", "opus", "astra", "sol", "luna", "muse", "gemini", "grok", "glm", "kimi", "claude code", "codex", "opencode", "pi"]


def exclusions() -> str:
    """-from: clauses for accounts the release already excludes (reply bots, spam). Private file, ids only."""
    p = ROOT / "data" / "private" / "excluded-author-ids.json"
    if not p.exists():
        return ""
    return " ".join(f"-from:{i}" for i in json.loads(p.read_text()))


def env_token() -> str:
    for line in (ROOT / ".env").read_text().split("\n"):
        if line.startswith("X_BEARER_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("X_BEARER_TOKEN not found in .env")


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


class Collector:
    def __init__(self, start: datetime, end: datetime, budget: float, token: str, routes: str = "all"):
        self.start, self.end, self.budget, self.token, self.routes = start, end, budget, token, routes
        self.exclude = exclusions()
        # Posts already held for this window (the frozen seed), so backfill can find their roots and parents.
        self.seed = {}
        seed_path = ROOT / "data" / "private" / "corpus-seed.jsonl"
        if not seed_path.exists():
            seed_path = ROOT / "data" / "private" / "corpus.jsonl"
        if seed_path.exists():
            for line in seed_path.read_text().split("\n"):
                if line:
                    r = json.loads(line)
                    t = parse(r["created_at"])
                    if start <= t < end:
                        self.seed[r["post_id"]] = r
        DAYS.mkdir(parents=True, exist_ok=True)
        self.path = DAYS / f"{iso(start).replace(':', '')}.json"
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
        else:
            self.state = {"window": {"start": iso(start), "end": iso(end)}, "posts": {}, "routes": {},
                          "counts": {}, "cost_usd": 0.0, "raw_returns": 0, "count_calls": 0, "complete": False}

    # ---- plumbing ----
    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False))
        tmp.replace(self.path)

    def get(self, path: str, params: dict) -> dict:
        url = f"{API}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode("utf-8", "replace")
            if e.code == 429:
                reset = int(e.headers.get("x-rate-limit-reset", "0") or 0)
                wait = max(15, min(900, reset - int(time.time()) + 2)) if reset else 60
                print(f"429; waiting {wait}s", file=sys.stderr); time.sleep(wait)
                return self.get(path, params)
            if e.code == 401:
                sys.exit("401 token rejected")
            if e.code == 402:
                sys.exit("402 no API credits")
            if e.code == 400:
                print(f"400 skipped: {body[:160]}", file=sys.stderr)
                return {"data": [], "meta": {}, "_error": body[:200]}
            raise RuntimeError(f"HTTP {e.code} {body}")

    def over_budget(self, reads: int) -> bool:
        return self.state["cost_usd"] + reads * PRICE > self.budget

    def route_key(self, kind: str, **kw) -> str:
        return hashlib.sha1(json.dumps({"kind": kind, **kw}, sort_keys=True).encode()).hexdigest()[:16]

    def add_posts(self, data: list[dict], route: str):
        for p in data:
            rec = self.state["posts"].get(p["id"])
            if rec is None:
                rec = {**p, "_routes": []}
                self.state["posts"][p["id"]] = rec
            else:
                if len(p.get("text", "")) > len(rec.get("text", "")):
                    rec["text"] = p["text"]
                pm, npm = rec.get("public_metrics", {}), p.get("public_metrics", {})
                for k, v in npm.items():
                    pm[k] = max(pm.get(k, 0), v)
                rec["public_metrics"] = pm
            if route not in rec["_routes"]:
                rec["_routes"].append(route)

    def search(self, kind: str, query: str, start: datetime, end: datetime, n: int, **meta) -> int:
        # Conversation routes end at "now", which changes on every resume; key them by root so a rerun never re-pulls a thread.
        key = self.route_key(kind, query=query, n=n) if kind == "conversation" else self.route_key(kind, query=query, start=iso(start), end=iso(end), n=n)
        if key in self.state["routes"]:
            return 0
        if self.over_budget(n):
            self.stopped = True
            return -1
        data = self.get("/tweets/search/recent", {
            "query": f"{query} -is:retweet {self.exclude}".strip(), "start_time": iso(start), "end_time": iso(end),
            "max_results": max(10, min(100, n)), "sort_order": "recency", "tweet.fields": FIELDS})
        posts = data.get("data", [])
        self.add_posts(posts, kind)
        self.state["raw_returns"] += len(posts)
        self.state["cost_usd"] = round(self.state["cost_usd"] + len(posts) * PRICE, 4)
        self.state["routes"][key] = {"kind": kind, "query": query, "start": iso(start), "end": iso(end),
                                     "requested": n, "returned": len(posts),
                                     "next_token": bool(data.get("meta", {}).get("next_token")), **meta}
        self.save(); time.sleep(1.6)
        return len(posts)

    def slices(self, k: int) -> list[tuple[datetime, datetime]]:
        step = (self.end - self.start) / k
        return [(self.start + step * i, self.start + step * (i + 1)) for i in range(k)]

    # ---- routes ----
    def counts(self):
        for model, q in MODELS.items():
            if model in self.state["counts"] or self.over_budget(1):
                continue
            d = self.get("/tweets/counts/recent", {"query": f"{q} -is:retweet", "start_time": iso(self.start),
                                                   "end_time": iso(self.end), "granularity": "day"})
            self.state["counts"][model] = d.get("meta", {}).get("total_tweet_count", 0)
            self.state["count_calls"] += 1
            self.state["cost_usd"] = round(self.state["cost_usd"] + PRICE, 4)
            self.save(); time.sleep(0.1)

    def exact_names(self):
        for model, q in MODELS.items():
            c = self.state["counts"].get(model, 0)
            k = 8 if c > 3000 else 6 if c > 1000 else 4
            for s, e in self.slices(k):
                if self.search("model_name", q, s, e, 15, model=model) < 0:
                    return
        for h, (q, k, n) in HARNESSES.items():
            for s, e in self.slices(k):
                if self.search("harness_name", q, s, e, n, harness=h) < 0:
                    return

    def candidates(self):
        for model, q in MODELS.items():
            for s, e in self.slices(2):
                if self.search("preference", f"{q} {PREF}", s, e, 12, model=model) < 0:
                    return
        for model, q in MODELS.items():
            if self.search("switching", f"{q} {SWITCH}", self.start, self.end, 12, model=model) < 0:
                return
        for pair, (q, k, n) in PAIRS.items():
            for s, e in self.slices(k):
                if self.search("harness_pair", q, s, e, n, pair=pair) < 0:
                    return

    def conversations(self, max_roots: int = 32, per_root: int = 20):
        posts = self.state["posts"]
        pool = {**{k: {"id": v["post_id"], "conversation_id": v.get("conversation_id"), "created_at": v["created_at"],
                       "text": v.get("text", ""), "public_metrics": {"reply_count": (v.get("public_metrics") or {}).get("reply_count", 1)}} for k, v in self.seed.items()},
                **posts}
        roots = [p for p in pool.values() if p["id"] == p.get("conversation_id")
                 and p.get("public_metrics", {}).get("reply_count", 0) > 0
                 and any(h in p.get("text", "").lower() for h in NAME_HINTS)]
        roots.sort(key=lambda p: -p["public_metrics"]["reply_count"])
        now = datetime.now(timezone.utc) - timedelta(minutes=3)
        floor = now - timedelta(days=7) + timedelta(minutes=30)  # X recent search reaches back seven days
        for r in roots[:max_roots]:
            start = max(parse(r["created_at"]), floor)
            if start >= now:
                continue
            if self.search("conversation", f"conversation_id:{r['id']}", start, now, per_root, root=r["id"]) < 0:
                return

    def missing_parents(self, cap: int = 400):
        posts = self.state["posts"]
        known = set(posts) | set(self.seed)
        want = []
        candidates = list(posts.values()) + [{"referenced_tweets": v.get("referenced_tweets", [])} for v in self.seed.values() if not v.get("root_text")]
        for p in candidates:
            for ref in p.get("referenced_tweets", []) or []:
                if ref.get("type") in ("replied_to", "quoted") and ref["id"] not in known and ref["id"] not in want:
                    want.append(ref["id"])
        want = want[:cap]
        for i in range(0, len(want), 100):
            chunk = want[i:i + 100]
            key = self.route_key("parents", ids=chunk)
            if key in self.state["routes"]:
                continue
            if self.over_budget(len(chunk)):
                self.stopped = True; continue
            d = self.get("/tweets", {"ids": ",".join(chunk), "tweet.fields": FIELDS})
            got = d.get("data", [])
            for p in got:
                p["_parent_only"] = True
            self.add_posts(got, "parent_lookup")
            self.state["raw_returns"] += len(got)
            self.state["cost_usd"] = round(self.state["cost_usd"] + len(got) * PRICE, 4)
            self.state["routes"][key] = {"kind": "parents", "requested": len(chunk), "returned": len(got)}
            self.save(); time.sleep(0.1)

    def attach_roots(self):
        posts = self.state["posts"]
        for p in posts.values():
            cid = p.get("conversation_id")
            if cid and cid != p["id"] and cid in posts:
                p["_root_text"] = posts[cid].get("text", "")

    def harness_only(self):
        for h, (q, k, n) in HARNESSES.items():
            for s_, e_ in self.slices(k):
                if self.search("harness_name", q, s_, e_, n, harness=h) < 0:
                    return
        for pair, (q, k, n) in PAIRS.items():
            for s_, e_ in self.slices(k):
                if self.search("harness_pair", q, s_, e_, n, pair=pair) < 0:
                    return

    def run(self):
        steps = {"all": (self.counts, self.exact_names, self.candidates, self.conversations, self.missing_parents),
                 "backfill": (self.harness_only, self.conversations, self.missing_parents)}[self.routes]
        self.stopped = False
        for step in steps:
            step()
        self.attach_roots()
        self.state["complete"] = not self.stopped
        self.state["routes_mode"] = self.routes
        self.save()
        s = self.state
        kinds = {}
        for r in s["routes"].values():
            k = kinds.setdefault(r["kind"], [0, 0]); k[0] += 1; k[1] += r.get("returned", 0)
        print(json.dumps({"file": str(self.path.relative_to(ROOT)), "window": s["window"],
                          "unique_posts": len(s["posts"]), "raw_returns": s["raw_returns"],
                          "count_calls": s["count_calls"], "cost_usd": s["cost_usd"],
                          "routes": {k: {"calls": v[0], "returned": v[1]} for k, v in kinds.items()},
                          "counts": s["counts"]}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start"); ap.add_argument("--end"); ap.add_argument("--budget", type=float, default=10.0)
    ap.add_argument("--routes", choices=["all", "backfill"], default="all")
    a = ap.parse_args()
    end = parse(a.end) if a.end else datetime.now(timezone.utc) - timedelta(minutes=3)
    start = parse(a.start) if a.start else end - timedelta(hours=24)
    Collector(start, end, a.budget, env_token(), a.routes).run()


if __name__ == "__main__":
    main()
