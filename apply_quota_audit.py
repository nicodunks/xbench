#!/usr/bin/env python3
"""Turn quota-audit decisions into reviewer overrides.

For each decision:
  model_cost / unrelated -> no change
  quota  -> remove the model line; add a harness line (same label, aspect
            rewritten as a limits aspect) when a harness is set, else drop
  both   -> keep the model line with aspect 'token consumption'; add the
            harness line as above
Overrides replace the whole record, built from the current effective label
(labels + earlier overrides). Appends to overrides.jsonl; idempotent per post.
"""
import json, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parent
V2 = ROOT / "data" / "labels-v2"
labels = {}
for p in sorted(glob.glob(str(V2 / "labels" / "batch-*.jsonl"))):
    for line in Path(p).read_text().split("\n"):
        if line:
            o = json.loads(line); labels[o["post_id"]] = o
existing = 0
for line in (V2 / "overrides.jsonl").read_text().split("\n"):
    if line:
        o = json.loads(line); labels[o["post_id"]] = o; existing += 1
decisions = {}
for p in sorted(glob.glob(str(V2 / "quota-audit" / "decisions" / "*.jsonl"))):
    for line in Path(p).read_text().split("\n"):
        if line:
            d = json.loads(line); decisions.setdefault(str(d["post_id"]), []).append(d)
changed, dropped, moved, kept_both = [], 0, 0, 0
for pid, ds in decisions.items():
    acts = [d for d in ds if d["kind"] in ("quota", "both")]
    if not acts:
        continue
    rec = json.loads(json.dumps(labels[pid]))
    sent = rec["sentiment"]
    by_line = {d["line"]: d for d in acts}
    new_sent, extra = [], []
    for i, s in enumerate(sent):
        d = by_line.get(i)
        if not d:
            new_sent.append(s); continue
        limit_aspect = "usage limits" if d["kind"] == "quota" else "plan burn from token use"
        if d.get("harness"):
            extra.append({"target": d["harness"], "label": s["label"], "firsthand": s.get("firsthand", False),
                          "endorsement": s.get("endorsement", False), "task": s.get("task", "coding"), "aspect": limit_aspect})
            moved += 1
        else:
            dropped += 1
        if d["kind"] == "both":
            new_sent.append({**s, "aspect": "token consumption"}); kept_both += 1
    # avoid duplicate harness lines for the same target
    seen = {(x["target"]) for x in new_sent}
    for e in extra:
        if e["target"] not in seen:
            new_sent.append(e); seen.add(e["target"])
    notes = "; ".join(f"line {d['line']}: {d['kind']} -> {d.get('harness') or 'dropped'} ({d.get('note','')})" for d in acts)
    rec["sentiment"] = new_sent
    rec["reason"] = f"Reviewer (quota audit): {notes}. Original: {rec.get('reason','')}"[:900]
    changed.append(rec)
with open(V2 / "overrides.jsonl", "a") as f:
    for rec in changed:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(json.dumps({"decisions": sum(len(v) for v in decisions.values()), "posts_changed": len(changed),
                  "lines_moved_to_harness": moved, "lines_dropped": dropped, "both_kept": kept_both,
                  "overrides_before": existing, "overrides_after": existing + len(changed)}, indent=2))
