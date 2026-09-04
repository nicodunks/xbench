#!/usr/bin/env python3
"""Split corpus.jsonl into labeling batches for the v2 classification run.

Each batch is a compact JSONL of the fields a labeler needs. Batches are
transport units only. Output goes to data/labels-v2/batches/.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "data" / "agent-rebuild" / "corpus.jsonl"
OUT = ROOT / "data" / "labels-v2"
BATCH = 100


def main() -> None:
    rows = [json.loads(l) for l in CORPUS.read_text().split("\n") if l]
    rows.sort(key=lambda r: (r["created_at"], r["post_id"]))
    (OUT / "batches").mkdir(parents=True, exist_ok=True)
    (OUT / "labels").mkdir(parents=True, exist_ok=True)
    for old in (OUT / "batches").glob("batch-*.jsonl"):
        old.unlink()
    manifest = []
    for i in range(0, len(rows), BATCH):
        part = rows[i:i + BATCH]
        name = f"batch-{i // BATCH:03d}.jsonl"
        lines = []
        for r in part:
            lines.append(json.dumps({
                "post_id": r["post_id"],
                "created_at": r["created_at"],
                "lang": r.get("lang"),
                "is_reply": bool(r.get("is_comment")),
                "text": r.get("text", ""),
                "root_text": r.get("root_text", "") or None,
            }, ensure_ascii=False))
        (OUT / "batches" / name).write_text("\n".join(lines) + "\n")
        manifest.append({"file": name, "posts": len(part)})
    (OUT / "batch-manifest.json").write_text(json.dumps(
        {"batch_size": BATCH, "posts": len(rows), "batches": manifest}, indent=2) + "\n")
    print(f"{len(rows)} posts -> {len(manifest)} batches")


if __name__ == "__main__":
    main()
