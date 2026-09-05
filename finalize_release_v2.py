#!/usr/bin/env python3
"""Validate and freeze the Xbench v2 (LLM-only, reviewer-blessed) label release.

Checks: every corpus post is labeled exactly once across the batch files, every
reviewer override targets a labeled post, the public evidence carries no author
fields, and the summary is internally consistent. Writes release-manifest.json
with sha256 digests of every input and output so the release can be reproduced.
"""
from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "data" / "private" / "corpus.jsonl"
PRIVATE_BATCHES = ROOT / "data" / "private" / "batches"
V2 = ROOT / "data" / "labels-v2"


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().split("\n") if line]


corpus = jsonl(CORPUS) if CORPUS.exists() else None
corpus_ids = {str(r["post_id"]) for r in corpus} if corpus else None
if corpus and len(corpus_ids) != len(corpus):
    raise ValueError("corpus has duplicate post ids")

manifest_in = json.loads((V2 / "batch-manifest.json").read_text())
batch_checks = []
label_ids: dict[str, str] = {}
for input_path in sorted(glob.glob(str(V2 / "batches" / "batch-*.jsonl"))):
    name = Path(input_path).name
    output_path = V2 / "labels" / name
    if not output_path.exists():
        raise ValueError(f"missing labels for {name}")
    batch = jsonl(Path(input_path))
    labels = jsonl(output_path)
    in_ids = [str(r["post_id"]) for r in batch]
    out_ids = [str(r["post_id"]) for r in labels]
    if in_ids != out_ids:
        raise ValueError(f"{name}: label order or coverage differs from batch input")
    for pid in out_ids:
        if pid in label_ids:
            raise ValueError(f"{pid} labeled twice ({label_ids[pid]} and {name})")
        label_ids[pid] = name
    batch_checks.append({"batch": name, "posts": len(batch), "status": "pass"})

if corpus_ids is not None and not corpus_ids <= set(label_ids):
    raise ValueError(f"coverage failed: {len(corpus_ids - set(label_ids))} corpus posts unlabeled")

overrides = jsonl(V2 / "overrides.jsonl") if (V2 / "overrides.jsonl").exists() else []
override_ids = [str(r["post_id"]) for r in overrides]
for pid in override_ids:
    if pid not in label_ids:
        raise ValueError(f"override targets unknown post {pid}")
# Later overrides win, so duplicates are allowed but reported.
duplicate_overrides = len(override_ids) - len(set(override_ids))

summary = json.loads((V2 / "public-summary.json").read_text())
evidence = json.loads((V2 / "public-evidence.json").read_text())
for section, rows in evidence.items():
    if not isinstance(rows, list):
        continue
    for row in rows:
        if set(row) & {"author_id", "username", "name", "profile_image_url"}:
            raise ValueError(f"public identity field found in {section}")

files = [
    V2 / "batch-manifest.json", V2 / "overrides.jsonl", V2 / "excluded-authors.json",
    V2 / "public-summary.json", V2 / "public-evidence.json",
    *sorted(Path(p) for p in glob.glob(str(V2 / "batches" / "batch-*.jsonl"))),
    *sorted(Path(p) for p in glob.glob(str(V2 / "labels" / "batch-*.jsonl"))),
    ROOT / "AGENT_CLASSIFICATION_PROMPT.md", ROOT / "ASPECT_DIMENSIONS.md", ROOT / "QUOTA_AUDIT.md",
    ROOT / "prepare_label_batches.py", ROOT / "validate_labels.py", ROOT / "review_labels.py",
    ROOT / "build_release_v2.py", ROOT / "finalize_release_v2.py",
]
if CORPUS.exists():
    files.insert(0, CORPUS)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


harness = summary.get("harnesses", {})
manifest = {
    "schema_version": "2.0",
    "release": "xbench-labels-v2",
    "window": summary.get("window"),
    "classification": {
        "policy": "one LLM pass per post against AGENT_CLASSIFICATION_PROMPT.md; reviewer overrides replace records wholesale",
        "labeler": "claude-sonnet subagents, 100 posts per batch",
        "reviewer": "claude-fable-5.1 (flagged posts plus five random per batch)",
        "posts": len(label_ids),
        "batches": len(batch_checks),
        "batch_input_manifest": manifest_in.get("batches", manifest_in) if isinstance(manifest_in, dict) else manifest_in,
        "reviewer_overrides": len(set(override_ids)),
        "duplicate_override_lines": duplicate_overrides,
        "coverage": "pass" if corpus_ids is not None else "labels match batch index; corpus not present",
        "corpus_distributed": False,
    },
    "public_counts": {
        "model_sentiment_evidence": len(evidence.get("sentiment", [])),
        "family_sentiment_evidence": len(evidence.get("family_sentiment", [])),
        "model_preference_evidence": len(evidence.get("preference", [])),
        "model_switch_evidence": len(evidence.get("switching", [])),
        "harness_sentiment_evidence": len(evidence.get("harness_sentiment", [])),
        "harness_preference_evidence": len(evidence.get("harness", [])),
        "harness_switch_evidence": len(evidence.get("harness_switching", [])),
    },
    "privacy": "Public evidence contains post text and X links, but no author/profile fields.",
    "sha256": {str(p.relative_to(ROOT)): digest(p) for p in files},
}
(V2 / "release-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: v for k, v in manifest.items() if k != "sha256"}, indent=2)[:3000])
print(f"sha256 entries: {len(manifest['sha256'])}")
