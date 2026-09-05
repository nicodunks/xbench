# How Xbench pulls from the X API

A guide for the agent that runs a collection day. Budget is $10 a day unless
told otherwise; it can flex by hand. This is about what to ask X for and why,
not a job spec. Run it manually.

## Ground rules

- Official X API v2 only, application-only Bearer auth from `.env`
  (`X_BEARER_TOKEN`). No scraping, no browser automation, no third-party
  archives.
- Two endpoints: `GET /2/tweets/search/recent` for posts, `GET /2/tweets`
  (by ids) for missing parents. Counts (`/2/tweets/counts/recent`) are
  optional; the page no longer charts attention.
- Never request user expansions. `author_id` comes with the post and is all
  the pipeline needs. No usernames, bios, locations, images, follower counts.
- Pricing as of September 2026: $0.005 per returned post and per counts call,
  deduplicated by X within a UTC day. Check the console before trusting this.
- Save after every request. Key each request by a hash of its query and
  window so a rerun skips what it already has. A 429 stops the run; resume
  later.

## The day

Pull one 24-hour cell, ending three minutes before now so you are never on
X's moving seven-day boundary. Write it to `data/private/days/YYYY-MM-DD.json`.
The page is always the last seven day files. A post is labeled once, on the
day it is pulled; only overrides change it later.

Every content request uses `-is:retweet`, `sort_order=recency`, and the
standard fields: `id,text,author_id,created_at,conversation_id,lang,
public_metrics,referenced_tweets`. Recency sort favours the end of any
window, so split windows into slices rather than asking for more per call.

## Routes, in order

Roughly 2,000 reads a day. Stop issuing content requests when the budget is
within one call of the cap.

1. **Exact-name search, per model.** Four slices of the day, 15 posts each.
   One query per model, never one giant query: it hits the length limit and
   the loud model eats the results. 13 models × 4 × 15 = 780.

   ```
   ("Claude Fable 5.1" OR "Fable 5.1")
   ("Claude Opus 5" OR "Opus 5")
   ("GPT-6 Astra" OR "GPT 6 Astra")
   ("GPT-5.6 Sol" OR "GPT 5.6 Sol" OR "Sol 5.6")
   ("GPT-5.6 Luna" OR "GPT 5.6 Luna" OR "Luna 5.6")
   ("Muse Spark 1.3" OR "MuseSpark 1.3")
   ("Muse Spark 1.2" OR "MuseSpark 1.2")
   ("Gemini 3.8 Flash" OR "Gemini Flash 3.8")
   ("Gemini 3.7 Flash" OR "Gemini Flash 3.7")
   ("Grok 4.6")
   (("GLM 5.3" OR "GLM-5.3") -("GLM 5.3 Flash" OR "GLM-5.3-Flash"))
   ("GLM 5.3 Flash" OR "GLM-5.3-Flash")
   ("Kimi K3" OR "Kimi-K3")
   ```

2. **Exact-name search, per harness.** The first release never did this and
   got its harness posts by accident. Four slices of 15 for Claude Code,
   Codex and Grok Bot (`"Grok Bot" OR "Grok Build" OR "grok cli"`); one
   slice of 10 each for OpenCode and Pi so they stay in the data. About 200.

3. **Preference candidates, per model.** The model query AND
   `(prefer OR preferred OR "better than" OR beats OR "wins over" OR versus OR vs OR "would choose")`,
   two slices of 12. About 310. These words change what is pulled, not what
   is counted; the labeler still decides.

4. **Switching candidates, per model.** The model query AND
   `(switched OR switching OR "moved from" OR ditched OR replacing OR "now using" OR migrated OR "left for" OR cancelled)`,
   one call of 12. About 160.

5. **Harness pairs.** Claude Code vs Codex, four slices of 30:

   ```
   (("Claude Code" "Codex") OR ("Claude Code" (prefer OR versus OR vs OR switch)) OR (Codex (prefer OR versus OR vs OR switch)))
   ```

   Plus one call of 20 each for Grok Bot vs Claude Code and Grok Bot vs
   Codex. About 160.

6. **Conversation expansion.** From everything above, take roots (post id
   equals conversation id, names a tracked thing, has replies), rank by reply
   count, take the top 32, and pull `conversation_id:<id>` at 20 each. Window
   from the root's timestamp to now, not to the end of the cell; replies keep
   arriving for a day or two. Up to 640. This is where the "I tried it and
   it's terrible" replies come from.

7. **Missing parents.** Every reply or quote whose parent is not in the
   corpus: fetch the parents by id, 100 per call, up to 400 a day. About $2
   for the single biggest quality gain available. Without the root, the
   labeler has to record nothing.

Skip counts unless you want the attention series back; 13 calls is 7 cents.

## What to keep

Dedupe by post id across routes and days, keeping the longest text and the
max of each public metric. Record which routes found each post. Attach the
root's text to every reply whose root you have. Keep `author_id` for the
one-author-one-vote rule; strip it from anything public.

## What the corpus is

A budget-constrained, query-stratified pull. Not a random sample of X and not
every matching post. Good for the specific things the page measures:
firsthand stances, direct comparisons, completed switches, and the threads
under them. Say that on the page and in the manifest.

## Cost sanity

The first release: 13,398 posts for $59.66 over seven days, about 1,900 raw
reads a day, 13% of returns were duplicates across routes. At $10 a day you
get roughly the same density with better roots and real harness coverage. At
$20 you roughly double it and the preference intervals tighten. Nothing here
needs more than that.
