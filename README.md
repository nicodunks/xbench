# Xbench

**Measuring the Mandate of Heaven.** Seven days of firsthand opinion on X
about frontier AI models and the coding harnesses people run them in.

Live: https://nicodunks.github.io/xbench/

Xbench reads every post, one at a time, with a language model working from a
written contract, then a reviewer checks the flagged ones. Only firsthand
experience is scored. Every number on the page links back to the posts that
produced it.

## What's on the page

- **Sentiment** — one author, one stance per model per week, as positives
  minus negatives on a −100 to +100 scale.
- **Switching** — completed, first-person moves between models and between
  harnesses.
- **Head-to-head** — direct comparisons by people who used both, and
  XbenchPref, a Bradley-Terry rating on the Elo scale with bootstrap intervals.
- **Harnesses** — Claude Code, Codex and Grok Bot, scored apart from the
  models they run. Limits, quotas and subscription complaints land here.
- **Reasons** — every stance's reason filed under five dimensions for models
  (intelligence, speed, price, steerability, personality) and five for
  harnesses (limits, reliability, efficiency, agent behaviour, developer
  experience), as radars and per-model pages.
- **Methods, limitations and open questions.**

Tracked models are exact versions only. An unversioned name rolls up to a
family and is never scored as a specific model.

## Run it locally

```bash
python3 -m http.server 4173
```

Open `http://127.0.0.1:4173/`. The page is static: `index.html`, `xbench.css`,
`xbench.js`, and two JSON files under `data/labels-v2/`.

## How posts are labeled

1. `prepare_label_batches.py` splits the corpus into batches of 100.
2. Each batch is read by a language-model labeler against
   [`AGENT_CLASSIFICATION_PROMPT.md`](AGENT_CLASSIFICATION_PROMPT.md). No
   keyword rules. Every post gets a quoted reason and its stances,
   preferences and switches.
3. `validate_labels.py` checks coverage, order, canonical ids and reason
   uniqueness for every batch.
4. A reviewer re-reads flagged posts plus a sample per batch and writes
   full-record overrides to `data/labels-v2/overrides.jsonl`.
5. [`ASPECT_DIMENSIONS.md`](ASPECT_DIMENSIONS.md) maps each free-text reason
   to a dimension (`validate_aspect_map.py`).
6. [`QUOTA_AUDIT.md`](QUOTA_AUDIT.md) re-reads every model line about cost or
   limits and moves plan-limit complaints to the harness
   (`validate_quota_audit.py`, `apply_quota_audit.py`).
7. `build_release_v2.py` aggregates. `finalize_release_v2.py` checks coverage
   and privacy and writes a manifest with a digest of every input and output.

## Data

```
data/window.json                       the window, attention counts and taxonomy for this release
data/labels-v2/batches/                batch index: post ids, timestamps, language (no text)
data/labels-v2/labels/                 labeler output, one file per batch
data/labels-v2/overrides.jsonl         reviewer overrides, applied wholesale
data/labels-v2/excluded-authors.json   removed reply-bot and spam accounts, as hashed ids
data/labels-v2/aspect-map/             free-text reason → dimension
data/labels-v2/quota-audit/            cost-vs-limit decisions
data/labels-v2/public-summary.json     everything the page charts
data/labels-v2/public-evidence.json    every counted post: text, reason, link to X
data/labels-v2/release-manifest.json   coverage checks and sha256 of every file
```

The raw corpus (text of all 23,275 posts in the current window) is **not** in the repo. It
lives in `data/private/`, which is ignored. What is public is every post that
was counted, with its reason and a link, and every label for every post by id.
That is enough to audit any number on the page; it is not enough to rebuild
the release from scratch. If you need the corpus for research, open an issue.

Public files carry post text and links, never author or profile fields.
Quoted posts are reproduced under X's terms; see [LICENSE](LICENSE) for
removal requests.

## Known limits

Single labeler pass with roughly ten percent human review. One week of data,
ending a few hours after GPT-6 Astra launched. Models with fewer than 30
firsthand authors carry an asterisk. An English-only rerun leaves every model
rank unchanged. Pi and OpenCode are in the data but not on the page; their
samples were too thin.

## Running it again

Two guides for the agent that maintains this: [`X_API_GUIDE.md`](X_API_GUIDE.md)
for what to ask X for on a $10 day, and
[`AGENT_LABELING_GUIDE.md`](AGENT_LABELING_GUIDE.md) for how the labeling and
review pass is run.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The most useful contribution is a
disputed label with the post link and the contract clause it breaks.

## License

MIT for the code. Post texts belong to their authors.
