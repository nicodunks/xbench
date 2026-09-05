# How Xbench labels posts

A guide for the agent that runs a labeling pass. It explains how the release
on the page was produced so the next pass matches it. The contract itself is
[`AGENT_CLASSIFICATION_PROMPT.md`](AGENT_CLASSIFICATION_PROMPT.md); this file
is about how to run it.

## Roles

- **Labeler**: a Claude Sonnet subagent, one per batch of 100 posts. It reads
  the contract, reads every post, writes one JSON record per post, runs the
  validator, and reports three lines. It never sees more than its batch.
- **Reviewer**: Claude Fable 5.1, the orchestrator. It launches labelers ten at
  a time, reads every post a labeler flagged as uncertain or AI-authored plus
  five random posts per batch, and writes full replacement records to
  `data/labels-v2/overrides.jsonl`. The reviewer's judgment is final.
- **Validator**: `validate_labels.py`, run by the labeler before it reports and
  by the reviewer over everything at the end. No batch ships with errors.

The split matters. Labeling is cheap and parallel; judgment is expensive and
serial. Put the expensive model where the judgment is.

## Sequence

1. `python3 prepare_label_batches.py` cuts the private corpus into batches.
   Full batches with text go to `data/private/batches/`; the public index goes
   to `data/labels-v2/batches/`.
2. Launch labelers with the prompt below, ten in flight, launching the next as
   each one finishes. A batch of 100 takes a Sonnet labeler five to ten
   minutes.
3. As each batch lands, run `python3 review_labels.py batch-NNN.jsonl` and
   read it. Write overrides for anything wrong. Don't fix the label file; the
   override replaces the record wholesale and keeps the audit trail.
4. When all batches are in: `python3 validate_labels.py` over everything, then
   an alignment check that every recorded target appears in the post or its
   root (spelling variants aside), then `python3 build_release_v2.py`.
5. Map any new aspect strings to dimensions (`ASPECT_DIMENSIONS.md`) and run
   the quota audit over new cost lines (`QUOTA_AUDIT.md`). Both are the same
   pattern: a small contract, batches of strings, a validator, Sonnet
   subagents.
6. `python3 finalize_release_v2.py`, commit, push.

## The labeler prompt

Use it verbatim, changing only the batch number. Every rule in it was added
because a labeler got it wrong without it.

> You are a labeler for Xbench. Read the contract at
> AGENT_CLASSIFICATION_PROMPT.md in full first. Then read every line of
> data/private/batches/batch-NNN.jsonl.
>
> Label each post individually according to the contract. Write the results to
> data/labels-v2/labels/batch-NNN.jsonl as one JSON object per line, in the
> same order as the input, with exactly the output schema in the contract,
> including the `aspect` field on every sentiment and preference line. Every
> post_id in the input must appear exactly once in the output.
>
> Rules you must not break:
> - Decide the reason first, quoting a phrase from the post, then derive
>   labels. Every reason must be specific to its post. No two reasons may be
>   identical.
> - Do not use keyword rules or regex to decide anything. Read meaning. Do not
>   write scripts that label posts.
> - Do not skip posts because they are short, replies, non-English, or lack a
>   model name in their own text. Use root_text when present. If root_text is
>   null and the reply's meaning depends on it, record nothing and say so.
> - Use only canonical ids from the contract. Tracked harnesses are
>   claude_code, codex, opencode, pi, grokbot and nothing else. "Grok Build"
>   and "grok cli" are grokbot, never the grok-4.6 model. "Oh My Pi" / "omp"
>   is the pi harness. "@bot" in a coding context usually means Grok Bot.
>   Model names that match no canonical id are untracked: record nothing for
>   them rather than mapping to a family or a nearby version.
> - Recommendations, rankings, poll answers or hype with no described use are
>   recorded but NOT firsthand. Pre-release speculation records nothing.
>   Admiring someone else's output or test is secondhand: record nothing.
>   Proxy failures, billing disputes and free-tier terms are not stances on
>   the model. News, fact-checks, security disclosures and punditry are not
>   stances from use. An outage the author hit is negative firsthand on
>   reliability. Switches are model-to-model or harness-to-harness only.
> - Set uncertain: true only for genuine ambiguity you would want a human to
>   check.
> - Before writing, spot-check that the reason on every tenth line quotes text
>   from the post with that post_id.
>
> Write the file with a single Write call. Then run
> `python3 validate_labels.py batch-NNN.jsonl` and fix errors until it reports
> ok. Report three lines: the validator's summary, the count of uncertain
> posts, and the three hardest calls in one sentence each.

## What the reviewer looks for

The labelers are good at reading posts and bad at knowing where the line is.
Nearly every override falls into one of these:

- **Stated, not used.** "X is better than Y" with no use described was marked
  firsthand. Downgrade to firsthand false.
- **Endorsing hype.** "solid" under a promotional root was recorded as an
  endorsement. There is no firsthand stance to endorse; record nothing.
- **Plan limits on the model.** "Fable burns my Max plan" landed on Fable. It
  belongs on Claude Code. The quota audit catches these in bulk, but catch
  them in review too.
- **Untracked versions rolled up.** Sonnet 5, Opus 4.6, GLM 5.2 became a
  family or a neighbour. They record nothing.
- **Wrong thing blamed.** A proxy dropping thinking blocks, a reseller outage,
  a data-retention clause on a free tier. None of these are the model.
- **AI reply accounts.** Formatted, citation-heavy replies in an assistant
  voice. Flag `ai_author`; the aggregator drops the account if most of its
  posts are flagged. High-volume ones go in `excluded-authors.json` by hash.
- **Displaced records.** Once, a labeler wrote one post's record under the
  next post's id. The alignment check exists for this. Run it.

Reviewer overrides start their reason with `Reviewer:` and quote the post,
same as a label.

## Numbers from the first release, as a baseline

134 batches, 13,398 posts, about 100 Sonnet-minutes per 1,000 posts. Yield
per batch of 100: 40 to 70 stances, 25 to 40% on harnesses, 5 to 20 flagged
uncertain. 641 reviewer overrides in total, about 5% of posts. If a batch
comes back with zero uncertain posts or a hundred, read the whole batch.
