#!/usr/bin/env python3
import json, sys, glob
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parent
D = ROOT / "data" / "labels-v2" / "quota-audit"
KINDS = {"model_cost", "quota", "both", "unrelated"}
H = {"claude_code", "codex", "opencode", "pi", "grokbot", None}
names = sys.argv[1:] or [Path(p).name for p in sorted(glob.glob(str(D / "batches" / "*.jsonl")))]
bad = 0
for name in names:
    inp = [json.loads(l) for l in (D / "batches" / name).read_text().split("\n") if l]
    out_path = D / "decisions" / name
    if not out_path.exists():
        print(f"{name}: MISSING"); bad += 1; continue
    out = [json.loads(l) for l in out_path.read_text().split("\n") if l]
    errs = []
    if [(r["post_id"], r["line"]) for r in inp] != [(str(r.get("post_id")), r.get("line")) for r in out]:
        errs.append("order or coverage differs from input")
    for r in out:
        if r.get("kind") not in KINDS: errs.append(f"bad kind {r.get('kind')!r} on {r.get('post_id')}")
        if r.get("harness") not in H: errs.append(f"bad harness {r.get('harness')!r} on {r.get('post_id')}")
        if r.get("kind") in ("quota", "both") and "harness" not in r: errs.append(f"missing harness on {r.get('post_id')}")
    c = Counter((r.get("kind"), r.get("harness")) for r in out)
    print(f"{name}: {'ok' if not errs else 'errors'} {dict(c)}")
    for e in errs[:8]: print("   !", e)
    bad += bool(errs)
print("batches with errors:", bad)
sys.exit(1 if bad else 0)
