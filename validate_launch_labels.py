#!/usr/bin/env python3
"""Structural validation for launch label batches (LAUNCH_CLASSIFICATION_PROMPT.md).

    python3 validate_launch_labels.py            # every batch
    python3 validate_launch_labels.py L-004.jsonl
    python3 validate_launch_labels.py --overrides [L-004.jsonl]   # reviewer override files

Guards shape and era ids only; no semantic decision is made here.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUB = ROOT / "data" / "launches"

V2_MODELS = {"claude-fable-5.1", "claude-opus-5", "gpt-6-astra", "gpt-5.6-sol", "gpt-5.6-luna", "muse-spark-1.3", "muse-spark-1.2",
             "gemini-3.8-flash", "gemini-3.7-flash", "grok-4.6", "glm-5.3", "glm-5.3-flash", "kimi-k3"}
HARNESSES = {"claude_code", "codex", "opencode", "pi", "grokbot"}
FAMILIES = {"claude", "gpt", "gemini", "grok", "glm", "kimi", "muse"}
ERAS = {
    "opus-5.5": {"claude-opus-5.5", "claude-opus-5", "claude-fable-5.1", "gpt-6-sol", "gpt-6-luna", "gpt-6-astra", "gpt-5.6-sol",
                 "gpt-5.6-luna", "grok-4.7", "grok-4.6", "gemini-3.8-flash", "glm-5.3", "glm-5.3-flash", "kimi-k3", "muse-spark-1.3"} | HARNESSES | FAMILIES,
    "opus-5": {"claude-opus-5", "claude_code", "codex", "claude"},
    "gpt-5": {"gpt-5", "codex", "gpt"},
    "claude-3.5-sonnet": {"claude-3.5-sonnet", "claude"},
    "astra": V2_MODELS | HARNESSES | FAMILIES,
}
LABELS = {"positive", "negative", "mixed"}
MODEL_DIMS = {"intelligence", "speed", "price", "steerability", "personality", "overall", "other"}
HARNESS_DIMS = {"limits", "reliability", "efficiency", "agent", "dx", "overall", "other"}
TASKS = {"coding", "agents", "writing", "chat", "multimodal", "cost", "none"}


def jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().split("\n") if l.strip()]


def validate(name: str, overrides: bool = False) -> dict:
    inp = jsonl(PUB / "batches" / name)
    out_path = PUB / ("overrides" if overrides else "labels") / name
    if not out_path.exists():
        return {"batch": name, "status": "missing"}
    out = jsonl(out_path)
    era = inp[0]["era"]; ok_ids = ERAS[era]
    errors: list[str] = []
    if overrides:
        if not {r.get("post_id") for r in out} <= {r["post_id"] for r in inp}:
            errors.append("override targets a post outside this batch")
        if any(not str(r.get("reason", "")).startswith("Reviewer:") for r in out):
            errors.append("override reason must start with 'Reviewer:'")
    elif [r["post_id"] for r in inp] != [r.get("post_id") for r in out]:
        errors.append(f"coverage/order mismatch: {len({r['post_id'] for r in inp} & {r.get('post_id') for r in out})}/{len(inp)} matched")
    if overrides:  # later lines supersede earlier ones for the same post; only the live records must be distinct
        out = list({r.get("post_id"): r for r in out}.values())
    for reason, n in Counter(r.get("reason", "") for r in out).items():
        if n > 1:
            errors.append(f"reason repeated {n}x: {reason[:70]!r}")
    st = Counter({k: 0 for k in ("sent", "fh", "sup", "pref", "sw", "uncertain", "vendor", "ai")})
    for r in out:
        pid = r.get("post_id")
        for k in ("relevant", "ai_author", "vendor", "uncertain"):
            if not isinstance(r.get(k), bool):
                errors.append(f"{pid}: {k} not bool")
        if not isinstance(r.get("reason"), str) or len(r.get("reason", "")) < 15:
            errors.append(f"{pid}: reason missing or short")
        for k in ("sentiment", "preferences", "switches"):
            if not isinstance(r.get(k), list):
                errors.append(f"{pid}: {k} not a list"); r[k] = []
        st["uncertain"] += bool(r.get("uncertain")); st["vendor"] += bool(r.get("vendor")); st["ai"] += bool(r.get("ai_author"))
        for s in r["sentiment"]:
            if s.get("target") not in ok_ids: errors.append(f"{pid}: {s.get('target')!r} not tracked in era {era}")
            if s.get("label") not in LABELS: errors.append(f"{pid}: bad label {s.get('label')!r}")
            for k in ("firsthand", "endorsement", "superlative"):
                if not isinstance(s.get(k), bool): errors.append(f"{pid}: sentiment {k} not bool")
            if s.get("intensity") not in (1, 2, 3): errors.append(f"{pid}: intensity {s.get('intensity')!r}")
            if s.get("task") not in TASKS: errors.append(f"{pid}: bad task {s.get('task')!r}")
            if not isinstance(s.get("aspect"), str) or not 1 <= len(s["aspect"]) <= 60: errors.append(f"{pid}: aspect missing")
            want = None if s.get("target") in FAMILIES else HARNESS_DIMS if s.get("target") in HARNESSES else MODEL_DIMS
            if (want is None and s.get("dimension") is not None) or (want is not None and s.get("dimension") not in want):
                errors.append(f"{pid}: dimension {s.get('dimension')!r} wrong for {s.get('target')!r}")
            st["sent"] += 1; st["fh"] += bool(s.get("firsthand")); st["sup"] += bool(s.get("superlative"))
        for p in r["preferences"]:
            for k in ("winner", "loser"):
                if p.get(k) not in ok_ids: errors.append(f"{pid}: pref {k} {p.get(k)!r} not tracked in era {era}")
            if p.get("winner") == p.get("loser"): errors.append(f"{pid}: winner == loser")
            for k in ("firsthand", "benchmark"):
                if not isinstance(p.get(k), bool): errors.append(f"{pid}: pref {k} not bool")
            if p.get("task") not in TASKS: errors.append(f"{pid}: bad task {p.get('task')!r}")
            if not isinstance(p.get("aspect"), str) or not 1 <= len(p["aspect"]) <= 60: errors.append(f"{pid}: pref aspect missing")
            wd = None if p.get("winner") in FAMILIES else HARNESS_DIMS if p.get("winner") in HARNESSES else MODEL_DIMS
            if wd is not None and p.get("dimension") not in wd: errors.append(f"{pid}: pref dimension {p.get('dimension')!r}")
            st["pref"] += 1
        for s in r["switches"]:
            for k in ("origin", "destination"):
                if s.get(k) not in ok_ids: errors.append(f"{pid}: switch {k} {s.get(k)!r} not tracked")
            if not isinstance(s.get("completed"), bool): errors.append(f"{pid}: switch completed not bool")
            st["sw"] += bool(s.get("completed"))
    return {"batch": name, "era": era, "status": "ok" if not errors else "errors", "errors": errors, **st}


def main():
    ov = "--overrides" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--overrides"]
    names = sorted(p.name for p in (PUB / "batches").glob("L-*.jsonl"))
    if args:
        names = [n for n in names if n in args]
    elif ov:
        names = [n for n in names if (PUB / "overrides" / n).exists()]
    bad = 0; total = Counter()
    for n in names:
        r = validate(n, ov)
        if r["status"] == "missing":
            print(f"{n} missing"); continue
        print(f"{n} {r['era']:17} {r['status']:6} sent {r['sent']:3} fh {r['fh']:3} sup {r['sup']:2} pref {r['pref']:2} sw {r['sw']} unc {r['uncertain']} vendor {r['vendor']} ai {r['ai']}")
        for e in r["errors"][:8]:
            print("   !", e)
        bad += bool(r["errors"])
        total.update({k: v for k, v in r.items() if isinstance(v, int)})
    print("TOTAL", dict(total), "batches with errors:", bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
