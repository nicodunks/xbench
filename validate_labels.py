#!/usr/bin/env python3
"""Structural validation and yield report for v2 label batches.

Checks coverage, schema, canonical ids, reason uniqueness, and prints per-batch
yield so a reviewer can spot a batch that under-labeled. Semantic decisions are
never made here; this only guards the contract shape.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V2 = ROOT / "data" / "labels-v2"

MODELS = {"claude-fable-5.1", "claude-opus-5", "gpt-6-astra", "gpt-5.6-sol", "gpt-5.6-luna",
          "muse-spark-1.3", "muse-spark-1.2", "gemini-3.8-flash", "gemini-3.7-flash", "grok-4.6",
          "glm-5.3", "glm-5.3-flash", "kimi-k3"}
HARNESSES = {"claude_code", "codex", "opencode", "pi", "grokbot"}
FAMILIES = {"claude", "gpt", "gemini", "grok", "glm", "kimi", "muse"}
LABELS = {"positive", "negative", "mixed"}
TASKS = {"coding", "agents", "writing", "chat", "multimodal", "cost", "none"}
ID_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789-_.")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().split("\n") if l.strip()]


CANONICAL = MODELS | HARNESSES | FAMILIES


def check_id(value, errors, where):
    if not isinstance(value, str) or not value or set(value) - ID_CHARS:
        errors.append(f"{where}: bad id {value!r}")
    elif value not in CANONICAL:
        errors.append(f"{where}: non-canonical id {value!r}")


def validate_batch(name: str) -> dict:
    inp = read_jsonl(V2 / "batches" / name)
    out_path = V2 / "labels" / name
    if not out_path.exists():
        return {"batch": name, "status": "missing"}
    out = read_jsonl(out_path)
    errors: list[str] = []
    in_ids = [r["post_id"] for r in inp]
    out_ids = [r.get("post_id") for r in out]
    if in_ids != out_ids:
        if set(in_ids) == set(out_ids) and len(out_ids) == len(set(out_ids)):
            errors.append("order differs from input")
        else:
            errors.append(f"coverage mismatch: {len(set(in_ids) & set(out_ids))}/{len(in_ids)} matched, {len(out_ids)-len(set(out_ids))} duplicates")
    reasons = Counter(r.get("reason", "") for r in out)
    for reason, n in reasons.items():
        if n > 1:
            errors.append(f"reason repeated {n}x: {reason[:80]!r}")
    stats = Counter({k: 0 for k in ("relevant", "uncertain", "ai_author", "sentiment", "sentiment_firsthand", "sentiment_endorsement", "harness_sentiment", "preferences", "harness_preferences", "switches")})
    for r in out:
        pid = r.get("post_id")
        for key in ("relevant", "ai_author", "uncertain"):
            if not isinstance(r.get(key), bool):
                errors.append(f"{pid}: {key} not bool")
        if not isinstance(r.get("reason"), str) or len(r.get("reason", "")) < 15:
            errors.append(f"{pid}: reason missing or too short")
        for key in ("sentiment", "preferences", "switches"):
            if not isinstance(r.get(key), list):
                errors.append(f"{pid}: {key} not a list"); continue
        stats["relevant"] += bool(r.get("relevant"))
        stats["uncertain"] += bool(r.get("uncertain"))
        stats["ai_author"] += bool(r.get("ai_author"))
        for s in r.get("sentiment", []):
            check_id(s.get("target"), errors, f"{pid} sentiment")
            if s.get("label") not in LABELS: errors.append(f"{pid}: bad label {s.get('label')!r}")
            if not isinstance(s.get("firsthand"), bool): errors.append(f"{pid}: sentiment firsthand not bool")
            if not isinstance(s.get("endorsement"), bool): errors.append(f"{pid}: sentiment endorsement not bool")
            if s.get("task") not in TASKS: errors.append(f"{pid}: bad task {s.get('task')!r}")
            if not isinstance(s.get("aspect"), str) or not 1 <= len(s["aspect"]) <= 60: errors.append(f"{pid}: sentiment aspect missing")
            stats["sentiment"] += 1
            stats["sentiment_firsthand"] += bool(s.get("firsthand"))
            stats["sentiment_endorsement"] += bool(s.get("endorsement"))
            if s.get("target") in HARNESSES: stats["harness_sentiment"] += 1
        for p in r.get("preferences", []):
            check_id(p.get("winner"), errors, f"{pid} pref"); check_id(p.get("loser"), errors, f"{pid} pref")
            if p.get("winner") == p.get("loser"): errors.append(f"{pid}: preference winner == loser")
            if not isinstance(p.get("firsthand"), bool): errors.append(f"{pid}: pref firsthand not bool")
            if not isinstance(p.get("benchmark"), bool): errors.append(f"{pid}: pref benchmark not bool")
            if p.get("task") not in TASKS: errors.append(f"{pid}: bad task {p.get('task')!r}")
            if not isinstance(p.get("aspect"), str) or not 1 <= len(p["aspect"]) <= 60: errors.append(f"{pid}: preference aspect missing")
            stats["preferences"] += 1
            if {p.get("winner"), p.get("loser")} & HARNESSES: stats["harness_preferences"] += 1
        for s in r.get("switches", []):
            check_id(s.get("origin"), errors, f"{pid} switch"); check_id(s.get("destination"), errors, f"{pid} switch")
            if not isinstance(s.get("completed"), bool): errors.append(f"{pid}: switch completed not bool")
            stats["switches"] += bool(s.get("completed"))
    return {"batch": name, "status": "ok" if not errors else "errors", "posts": len(inp),
            "errors": errors, **stats}


def main() -> None:
    names = sorted(p.name for p in (V2 / "batches").glob("batch-*.jsonl"))
    if len(sys.argv) > 1:
        names = [n for n in names if n in sys.argv[1:]]
    total = Counter(); bad = 0
    print("batch      status  rel  sent  fh  end  pref  sw  harnS harnP  unc  ai")
    for name in names:
        r = validate_batch(name)
        if r["status"] == "missing":
            print(f"{name}  missing"); continue
        print(f"{name}  {r['status']:6}  {r['relevant']:3}  {r['sentiment']:4}  {r['sentiment_firsthand']:3}  {r['sentiment_endorsement']:3}  {r['preferences']:4}  {r['switches']:2}  {r['harness_sentiment']:4}  {r['harness_preferences']:4}  {r['uncertain']:3}  {r['ai_author']:2}")
        for e in r["errors"][:8]:
            print("    !", e)
        if r["errors"]: bad += 1
        for k, v in r.items():
            if isinstance(v, int) and k != "posts": total[k] += v
    print("\nTOTAL", dict(total), "batches with errors:", bad)


if __name__ == "__main__":
    main()
