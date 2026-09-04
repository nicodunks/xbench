# Xbench

A seven-day read of what people on X say, firsthand, about frontier AI models and
the coding harnesses they run them in. Attention, sentiment, aspects, direct
preference, and switching, one post at a time.

Live page: open `concept-v2.html` from a local server.

```bash
python3 -m http.server 4173
```

Then visit `http://127.0.0.1:4173/concept-v2.html`.

## What it measures

- **Attention** — exact-name mention counts per model over the window.
- **Sentiment** — one author, one stance per model per week, firsthand only,
  reported as positives minus negatives on a −100 to +100 scale.
- **Aspects** — every stance carries a reason; reasons are filed under five
  dimensions for models (intelligence, speed, price, steerability, personality)
  and five for harnesses (limits, reliability, efficiency, agent behaviour,
  developer experience).
- **Preference** — direct comparisons by people who used both, and XbenchPref,
  a Bradley-Terry rating on the Elo scale with bootstrap intervals.
- **Switching** — completed, first-person moves between models or between
  harnesses.

Tracked models are exact versions only; an unversioned name rolls up to a
family and is never scored as a specific model. Tracked harnesses: Claude Code,
Codex, OpenCode, Pi, Grok Bot. Limits, quotas and subscription complaints count
against the harness, never the model.

## How posts are labeled

1. `prepare_label_batches.py` splits the corpus into batches of 100.
2. Each batch is read by a language-model labeler against
   `AGENT_CLASSIFICATION_PROMPT.md`. No keyword rules. Every post gets a quoted
   reason and a set of stances, preferences and switches.
3. `validate_labels.py` checks coverage, order, canonical ids and reason
   uniqueness for every batch.
4. A reviewer re-reads flagged posts plus a sample per batch and writes
   full-record overrides to `data/labels-v2/overrides.jsonl`.
5. `ASPECT_DIMENSIONS.md` maps each free-text reason to a dimension
   (`validate_aspect_map.py`).
6. `QUOTA_AUDIT.md` re-reads every model line about cost or limits and moves
   plan-limit complaints to the harness (`validate_quota_audit.py`,
   `apply_quota_audit.py`).
7. `build_release_v2.py` aggregates; `finalize_release_v2.py` checks coverage
   and privacy and writes a manifest with file digests;
   `build_embedded_data_v2.py` bundles the public JSON for `file://` use.

Rebuild everything:

```bash
python3 validate_labels.py && python3 validate_aspect_map.py && python3 validate_quota_audit.py \
  && python3 build_release_v2.py && python3 finalize_release_v2.py && python3 build_embedded_data_v2.py
```

`review_labels.py` prints flagged and sampled posts for a batch in a compact
form for review.

## Data layout

```
data/agent-rebuild/corpus.jsonl        the 7-day corpus (post text, ids, timestamps; no profile fields)
data/labels-v2/batches/                labeler inputs
data/labels-v2/labels/                 labeler outputs, one file per batch
data/labels-v2/overrides.jsonl         reviewer overrides, applied wholesale
data/labels-v2/excluded-authors.json   reply bots and spam accounts removed
data/labels-v2/aspect-map/             free-text aspect → dimension
data/labels-v2/quota-audit/            cost vs limit decisions
data/labels-v2/public-summary.json     everything the page charts
data/labels-v2/public-evidence.json    every counted post with its reason and an X link
data/labels-v2/release-manifest.json   coverage checks and sha256 of every input and output
```

Public files contain post text and links, never author or profile fields.

## Known limits

Single labeler pass with roughly ten percent human review. One week of data.
Small samples are marked with an asterisk on the page. An English-only rerun
leaves every model rank unchanged.

## v1

`concept.html` and `data/agent-rebuild/` are the earlier release and are kept
as-is for comparison. `build_agent_release.py`, `finalize_agent_release.py` and
`build_embedded_data.py` belong to it.
