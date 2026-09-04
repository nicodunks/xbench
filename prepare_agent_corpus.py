#!/usr/bin/env python3
"""Merge every already-purchased, in-window X post for agent classification.

This stage performs no semantic filtering. It only enforces the frozen release
window, deduplicates X post IDs, preserves provenance, and attaches conversation
context when that context exists in the stored corpus.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = DATA / "agent-rebuild"
WINDOW = json.loads((DATA / "rolling-7d" / "public-summary.json").read_text())["window"]

SOURCE_FILES = [
    *(DATA / "rolling-7d" / f"day-{i}.json" for i in range(7)),
    DATA / "rolling-7d" / "event-thread-expansion.json",
    *(DATA / "rolling-24h" / f"round-{i}.json" for i in range(1, 6)),
    DATA / "harnesses-24h" / "capture.json",
    DATA / "harnesses-24h" / "cc-codex-choosers.json",
    DATA / "harnesses-24h" / "cc-codex-thread-expansion.json",
]


def merge_post(current: dict | None, incoming: dict, source: str) -> dict:
    if current is None:
        current = dict(incoming)
        current["_sources"] = []
    # Prefer populated fields and the longest stored text/context representation.
    for key, value in incoming.items():
        if value is None or value == "" or value == []:
            continue
        if key in {"text", "_root_text"}:
            if len(str(value)) > len(str(current.get(key, ""))):
                current[key] = value
        elif key == "public_metrics":
            prior = current.get(key, {})
            current[key] = {k: max(prior.get(k, 0), v) for k, v in value.items()}
        elif key not in current or current[key] in (None, "", []):
            current[key] = value
    if source not in current["_sources"]:
        current["_sources"].append(source)
    return current


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    posts: dict[str, dict] = {}
    source_stats = []
    for path in SOURCE_FILES:
        doc = json.loads(path.read_text())
        kept = 0
        for post in doc.get("posts", []):
            created = post.get("created_at", "")
            if not post.get("id") or not (WINDOW["start"] <= created <= WINDOW["end"]):
                continue
            kept += 1
            posts[post["id"]] = merge_post(posts.get(post["id"]), post, str(path.relative_to(ROOT)))
        source_stats.append({"file": str(path.relative_to(ROOT)), "in_window_posts": kept})

    roots = {
        p["id"]: p for p in posts.values()
        if p.get("id") == p.get("conversation_id")
    }
    records = []
    for post in sorted(posts.values(), key=lambda p: (p.get("created_at", ""), p["id"])):
        root = roots.get(post.get("conversation_id"))
        records.append({
            "post_id": post["id"],
            "author_id": post.get("author_id"),
            "created_at": post.get("created_at"),
            "lang": post.get("lang"),
            "conversation_id": post.get("conversation_id"),
            "is_comment": post.get("id") != post.get("conversation_id"),
            "text": post.get("text", ""),
            "root_text": root.get("text", "") if root and root["id"] != post["id"] else post.get("_root_text", ""),
            "referenced_tweets": post.get("referenced_tweets", []),
            "sources": post.get("_sources", []),
        })

    # Local JSONL keeps iteration simple and streamable. Batches are transport
    # units only; they have no semantic meaning and never influence a label.
    corpus_path = OUT / "corpus.jsonl"
    corpus_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    batch_size = 400
    for old in OUT.glob("batch-*.json"):
        old.unlink()
    batches = []
    for index in range(0, len(records), batch_size):
        part = records[index:index + batch_size]
        name = f"batch-{index // batch_size:03d}.json"
        (OUT / name).write_text(json.dumps({"records": part}, ensure_ascii=False, indent=2) + "\n")
        batches.append({"file": name, "records": len(part)})

    manifest = {
        "schema_version": "1.0",
        "source": "Stored official X API responses only",
        "semantic_filtering": "none",
        "window": WINDOW,
        "unique_posts": len(records),
        "source_files": source_stats,
        "batches": batches,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
