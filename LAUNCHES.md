# The Opus 5.5 window (labels-v3)

The page now runs from the launch of Claude Opus 5.5 (2026-09-22 16:31:03 UTC,
the snowflake time of @claudeai's announcement) to the last post pulled. Every
chart is the same chart as before, fed by `data/labels-v3/`; the first release
stays in `data/labels-v2/`. Opus 5.5 also gets a featured chapter: net
sentiment every twelve hours, with a switcher for GPT-6 Astra's own line.

## What was pulled

`collect_launch.py` talks to the X API through one ledger that caches every
response and refuses any request that could take spend past a hard cap.
Full-archive search, `-is:retweet`, exact-name queries from `data/launches.json`.

| pull | route | posts |
|---|---|---|
| Opus 5.5 | every clock hour since two days before launch, about 800 posts a day split by the hour's true volume (counts/all) | ~4,500 |
| Opus 5.5 | replies under the 40 most-replied roots, including the announcement | ~1,100 |
| Opus 5.5 | posts naming Opus or Claude since launch by first-release critics of Opus 5 and Claude Code | ~2,900 |
| GPT-6 Sol | hour-stratified, about 200 a day (shipped 29 minutes after Opus 5.5) | ~1,300 |
| Claude Code | hour-stratified, from two days before launch | ~1,800 |
| every other model, Codex | eight-hour slices of 10, plus one preference-word call | ~150 each |
| GPT-6 Astra, seven days | three-hour slices of 22, from Sep 20 16:31 UTC, for the featured switcher | ~1,260 |

X API spend: $98.73 of a $100 limit (the ledger's pessimistic count; a hard cap
of $99.50 was enforced in code). The account's prepaid credits ran out once at
about $92, before Kimi K3, Muse Spark 1.3 and Grok Bot were pulled; they appear
only where other posts mention them. Astra's seven-day pull came after a top-up.
About $12 went on pulls for a launch-history comparison that was dropped before
labeling (Opus 5 in July, Claude 3.5 Sonnet, GPT-5, Astra's first week); those
posts stay private and unused.

## How it was read

1. `prepare_launch_batches.py` cuts batches of 100 (`data/launches/batches/`).
2. Sonnet 5 labelers follow `AGENT_CLASSIFICATION_PROMPT.md` plus
   `LAUNCH_CLASSIFICATION_PROMPT.md`, which adds the era's model list, date
   rules for bare names ("Opus", "Sol"), `intensity`, `superlative`, a
   `dimension` on every line, and `vendor`. `validate_launch_labels.py` gates
   every file.
3. A Fable 5.1 reviewer read every flagged post, then ran a **firsthand
   audit**: every post carrying a firsthand line, in every batch, for every
   model, re-read against one bar. Launch-week hype ("Opus 5.5 is goated")
   was being counted as use; the audit downgraded roughly a quarter of
   firsthand lines, most of them on Opus 5.5, and applied the same bar to
   every rival. Overrides are append-only in `data/launches/overrides/`
   (the last line for a post wins).
4. `align_launch_labels.py` checks that each reason quotes its own post, which
   catches a record written under a neighbour's id. The remaining misses on
   inspection are translations; the audit rebuilt the few displaced records it
   found.
5. `nerf_candidates.py` + `NERF_CLAIMS.md`: a wide word net in many languages
   picks candidate posts, and a labeler decides each one: `claim` (it got
   worse since launch), `fears` (it will), `asks`, `denies`. A second pass
   widens the net and adds every post whose label reason already speaks of a
   decline. A Fable 5.1 reviewer then re-read every post in every nerf batch;
   414 read, 30 claims, 86 fears, 10 questions, 19 denials. The counts are in
   `public-summary.json` (`launch.featured.nerf`); the page does not chart them.
6. `build_launch.py` aggregates with the build_release_v2 rules and writes
   `data/labels-v3/public-summary.json` and `public-evidence.json`.

## Rules that are new in this release

- **Own sample.** A model's sentiment and reasons count only posts pulled by
  its own name search. Opus 5.5 was sampled about 25 times harder than the
  field, and its posts often praise it by knocking a rival; without this rule
  every rival would be scored mostly by Opus 5.5's audience. Head-to-head and
  switching still use every post, because comparisons are what they measure.
  Posts found only through the critics route never score.
- **Switches must happen in the window.** A reviewer read every counted
  switch and dated the move (`data/launches/switch_timing.jsonl`): "since
  June" or "months ago" is a real switch, but not this week's, and "going to
  X now" is not yet a move. 14 of 70 were dropped, 7 of them Claude Code and
  Codex moves made before launch.
- **Twelve-hour curve.** One vote per person per twelve hours, firsthand only,
  95% author bootstrap; steps with fewer than twelve people are hidden. A
  switcher shows the same line for GPT-6 Astra over the last seven days, from
  its own pull, with its first-Xbench score as the reference.
- **Events** on the curve are dated from the posts that announced them
  (Arena #1, the NerfBench result); Artificial Analysis has only a report date
  and is drawn dashed.

## Sensitivity

Opus 5.5's net does not depend on the route mix: hour-stratified sample only
+76 (1,396 people), all routes +76, without the critics route +75.

## Conflict of interest

The agent that built this release is Claude Opus 5.5, the model it measures.
It wrote the contracts, the pipeline and the page, and did not label or review
a post. Labels are Sonnet 5, review and audit are Fable 5.1, and every counted
post links to X.
