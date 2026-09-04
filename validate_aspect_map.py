#!/usr/bin/env python3
"""Check aspect-map outputs: one line per input string, same order, valid dimension id."""
import json, sys, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parent
D = ROOT / "data" / "labels-v2" / "aspect-map"
MODEL = {"intelligence", "speed", "price", "steerability", "personality", "overall", "other"}
HARNESS = {"limits", "reliability", "efficiency", "agent", "dx", "overall", "other"}
names = sys.argv[1:] or [Path(p).name for p in sorted(glob.glob(str(D / "batches" / "*.jsonl")))]
bad = 0
for name in names:
    inp = [json.loads(l) for l in (D / "batches" / name).read_text().split("\n") if l]
    out_path = D / "maps" / name
    if not out_path.exists():
        print(f"{name}: MISSING"); bad += 1; continue
    out = [json.loads(l) for l in out_path.read_text().split("\n") if l]
    vocab = MODEL if name.startswith("model") else HARNESS
    errs = []
    if [r["aspect"] for r in inp] != [r.get("aspect") for r in out]:
        errs.append("order or coverage differs from input")
    for r in out:
        if r.get("dimension") not in vocab:
            errs.append(f"bad dimension {r.get('dimension')!r} for {r.get('aspect')!r}")
    from collections import Counter
    c = Counter(r.get("dimension") for r in out)
    status = "ok" if not errs else "errors"
    print(f"{name}: {status} {dict(c)}")
    for e in errs[:8]: print("   !", e)
    bad += bool(errs)
print("batches with errors:", bad)
sys.exit(1 if bad else 0)
