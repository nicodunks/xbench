#!/usr/bin/env python3
"""Validate and freeze the one-pass Xbench agent release."""
from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "agent-rebuild"


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().split("\n") if line]


corpus = jsonl(DATA / "corpus.jsonl")
inputs = []
outputs = []
batch_checks = []
for input_name in sorted(glob.glob(str(DATA / "batch-*.json"))):
    index = Path(input_name).stem.split("-")[-1]
    output_name = DATA / f"primary-{index}.jsonl"
    batch = json.loads(Path(input_name).read_text())["records"]
    labels = jsonl(output_name)
    input_ids = {str(row["post_id"]) for row in batch}
    output_ids = {str(row["post_id"]) for row in labels}
    if input_ids != output_ids or len(output_ids) != len(labels):
        raise ValueError(f"classification coverage failed for batch {index}")
    inputs.extend(batch)
    outputs.extend(labels)
    batch_checks.append({"batch": index, "posts": len(batch), "status": "pass"})

corpus_ids = {str(row["post_id"]) for row in corpus}
output_ids = {str(row["post_id"]) for row in outputs}
if len(corpus_ids) != len(corpus) or corpus_ids != output_ids or len(outputs) != len(output_ids):
    raise ValueError("full-corpus one-pass coverage failed")

summary = json.loads((DATA / "public-summary.json").read_text())
evidence = json.loads((DATA / "public-evidence.json").read_text())
for section, rows in evidence.items():
    if not isinstance(rows, list):
        continue
    for row in rows:
        if set(row) & {"author_id", "username", "name", "profile_image_url"}:
            raise ValueError(f"public identity field found in {section}")

sentiment = summary["sentiment"]["models"]
scores = [row["clean_directional"]["net_sentiment"] for row in sentiment]
if scores != sorted(scores, reverse=True):
    raise ValueError("sentiment rows are not sorted best to worst")
if len(summary["preference"]["xbenchpref"]["ratings"]) != 13:
    raise ValueError("XbenchPref does not include all tracked models")

files = [
    "corpus.jsonl", "public-summary.json", "public-evidence.json", "embedded-data.js",
    *[Path(path).name for path in sorted(glob.glob(str(DATA / "primary-*.jsonl")))],
]
files += ["AGENT_CLASSIFICATION_PROMPT.md", "prepare_agent_corpus.py",
          "build_agent_release.py", "build_embedded_data.py", "concept.html", "concept.css", "concept.js"]

def digest(name: str) -> str:
    path = (DATA / name) if (DATA / name).exists() else (ROOT / name)
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest = {
    "schema_version": "1.0",
    "release": "xbench-agent-one-pass-v1",
    "window": summary["window"],
    "source": summary["source"],
    "recorded_x_api_spend_usd": summary["recorded_spend_usd"],
    "classification": {
        "policy": "one semantic pass per post",
        "posts": len(outputs),
        "batches": len(batch_checks),
        "coverage": "pass",
        "batch_checks": batch_checks,
    },
    "public_counts": {
        "model_sentiment_authors": sum(row["clean_directional"]["n"] for row in sentiment),
        "model_sentiment_messages": len(evidence["sentiment"]),
        "model_preferences": summary["preference"]["clean_unique_votes"],
        "model_switches": summary["switching"]["verified_completed_switches"],
        "harness_preferences": summary["harnesses"]["strict"]["n"],
        "harness_switches": summary["harnesses"]["switches"]["n"],
    },
    "privacy": "Public evidence contains post text and X links, but no author/profile fields.",
    "sha256": {name: digest(name) for name in files},
}
(DATA / "release-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
