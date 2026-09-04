# Xbench classification contract, v2

You are labeling X posts about AI models and coding harnesses. You will
receive a batch file of posts. Read each post individually, in full, with its
root context, and write one JSON line per post. Do not skip, sample, or
template. Every post gets its own reasoning.

## The two questions

For every post, answer: does the author express a stance, a preference, or a
switch about a tracked entity, and is it firsthand?

**Firsthand** means the author reports using the entity themselves or
describes a concrete result they got. Hype, leaks, countdowns, reactions to
someone else's result, benchmark reposts, and opinions about a model the
author has not touched are not firsthand. A strong assertion from someone
whose post shows they work with these tools daily counts as firsthand.

**Endorsement** is a bare agreement in a reply ("this", "100%", "so true",
"good sharing") with the stance of the root post. Record it with the root's
target and polarity, `firsthand: false`, `endorsement: true`. A reply that
adds its own experience is firsthand, not an endorsement.

## Tracked entities and canonical ids

Exact models: claude-fable-5.1, claude-opus-5, gpt-6-astra, gpt-5.6-sol,
gpt-5.6-luna, muse-spark-1.3, muse-spark-1.2, gemini-3.8-flash,
gemini-3.7-flash, grok-4.6, glm-5.3, glm-5.3-flash, kimi-k3.

Harnesses: claude_code, codex, opencode, pi, grokbot. Grokbot is xAI's
coding agent, also written "Grok Bot", "grok cli", "Grok Bots", "Grokbot".
No other harness is tracked. Cursor, Aider, Hermes, Windsurf, T3 Code,
OpenClaw and the like are untracked: do not record sentiment about them, and
a comparison between a tracked harness and an untracked one records only the
stance on the tracked side ("Cursor beats Claude Code" is claude_code
negative firsthand, no preference line).

Families, used only when no version can be resolved: claude, gpt, gemini,
grok, glm, kimi, muse.

## Resolution rules

Release moments in this window (UTC):
- Claude Fable 5.1: 2026-09-01 18:00
- Gemini 3.8 Flash: 2026-09-02 04:00
- Muse Spark 1.3: 2026-09-02 20:20
- GPT-6 Astra: 2026-09-03 19:00

- An exact version in the post resolves to that model.
- "Fable" or "Fable 5.1" after the Fable 5.1 release is claude-fable-5.1.
  Before it, "Fable" alone is the claude family. "Fable 5" is always Fable 5,
  which is untracked, so record the claude family.
- "Opus" alone is claude-opus-5. Opus 5 was current all week.
- "Astra" is always gpt-6-astra. Firsthand is impossible before its release
  unless the author claims early access.
- "Sol", "Luna", "K3", "3.8 Flash", "3.7 Flash" resolve to their models.
- "GPT" or "5.6" alone stays the gpt family. Sol and Luna are both current.
- "Flash" alone stays the gemini family. "Muse Spark" alone after the 1.3
  release is muse-spark-1.3.
- "Claude" alone is the claude family, never Fable 5.1.
- "Claude" in a coding context with cancelled, dropped, sub, plan, limits, or
  usage means claude_code. "GPT" or "ChatGPT" means codex only when the post
  says Codex, or when the same sentence pairs it against a Claude
  subscription in a coding context.
- "CC" in a coding context is claude_code.
- A product name is not a model. Grokbot is the harness, never grok-4.6.
  Muse Code is not muse-spark-1.3. Claude Mythos is the claude family.
- If the reply's meaning depends on a root or quoted post that is not
  supplied, record nothing unless the reply carries its own firsthand
  content. Do not guess the target.

## What counts as sentiment

Record one line per entity the author takes a stance on. Labels: positive,
negative, mixed. Mixed is for a post that genuinely praises and criticizes
the same entity.

Counts:
- Any evaluative statement about quality, speed, reliability, output,
  behavior, or fit for a task.
- Rate limits, pricing, cache costs, quota complaints. These are negative
  firsthand on the entity named.
- Praise of a model used through a harness credits both when the author
  frames it that way: "Codex with Sol is cooking" is positive for codex and
  gpt-5.6-sol. A complaint about output quality goes to the model. A
  complaint about tool behavior, limits, or UX goes to the harness. When the
  author does not separate them, credit both.
- Choosing a model with stated reasons ("I'd pick GLM because open weights
  and low refusals").
- Disagreeing with a benchmark from experience ("the benchmark is wrong,
  Grok is absurdly worse").
- Sarcasm and irony, labeled by intended meaning.
- Non-English posts. Translate mentally, then label. Chinese and Japanese
  posts are a large share and were under-labeled before.

Does not count:
- Questions, release-date chatter, leak forensics, announcements with no
  editorial stance, price and score tables, feature documentation.
- Promotional, affiliate, reseller, and giveaway posts, even when they praise.
- Secondhand reports: "my friend switched", "this girl cancelled".
- Vendor employees replying about their own product.
- Generic awe ("wild how fast models evolve") with no stance on an entity.
- A model named only as a price or size reference.
- Puzzled observations of a behavior difference with no judgment attached
  ("why does Codex write the TOML file openly and Claude Code hide it?").

Also counts: an author saying they do not use an entity even though they
could ("Google gave me $30k of Gemini credits and I don't even use them") is
negative firsthand, aspect "not worth using".

## Preferences

One line per ordered pair where the author says one entity is better than,
chosen over, or replaces another. A comparison of three or more emits every
explicit pair. `firsthand` follows the same rule as sentiment; a reported
benchmark ranking is a preference with `firsthand: false` and
`benchmark: true`.

Role splits are not preferences. "Fable for planning, Grok for daily" is
positive for both with no preference line, unless the author ranks them.
Cancelling one subscription for another is a preference for the destination
and a switch.

## Switches

`completed: true` only when the author states in the first person that they
moved and are now on the destination: "switched to", "moved from", "replaced
my", "switched back to", "cancelled X, now on Y". Switching back counts. A
one-task trial does not. Plans, temptations, jokes, and questions are not
switches; record nothing for them. Every completed switch also emits a
preference for destination over origin.

## Task tag and aspect

Each sentiment and preference line carries one `task`: coding, agents,
writing, chat, multimodal, cost, or none.

Each sentiment and preference line also carries an `aspect`: two to six words
naming the specific thing the stance is about, in the author's terms. Examples:
"speed", "verbosity", "looping on long tasks", "rate limits", "cache miss cost",
"instruction following", "Chinese prose quality", "3D asset generation",
"refusal rate", "token consumption", "UX", "overall". Use "overall" only when
the author gives no specific reason. Never leave it empty. This is the field
that later becomes "what people love and hate about each model".

## AI accounts

If the post reads as an AI reply account (a bot answering mentions with
benchmark citations, an assistant voice, "Grok here", uniform formatting
across a long reply), set `ai_author: true`. Still label the post; the
aggregator drops flagged authors.

## Uncertainty

Set `uncertain: true` when you would want a human to look. Use it for real
ambiguity, not as a hedge. The reviewer reads every uncertain line.

## Output

One JSON object per line, in input order, same post_id set as the batch.

```json
{"post_id":"...",
 "relevant":true,
 "ai_author":false,
 "uncertain":false,
 "sentiment":[{"target":"canonical-id","label":"positive|negative|mixed","firsthand":true,"endorsement":false,"task":"coding","aspect":"looping on long tasks"}],
 "preferences":[{"winner":"canonical-id","loser":"canonical-id","firsthand":true,"benchmark":false,"task":"coding","aspect":"cost per completed task"}],
 "switches":[{"origin":"canonical-id","destination":"canonical-id","completed":true}],
 "reason":"Quote a phrase from the post, then one or two sentences of inference specific to this post."}
```

`relevant` is false only when the post has no stance, preference, switch, or
evaluative content about any tracked entity. Empty arrays with
`relevant: true` are fine for announcements and questions that name a
tracked entity.

## Worked examples

- "Fable 5 is genuinely good. Sol is a close second. Opus 5 is kind of
  useless." → claude positive firsthand (Fable 5 is untracked, family), sol
  positive firsthand, opus-5 negative firsthand; preferences claude > sol,
  claude > opus-5, sol > opus-5, firsthand.
- "it's actually pretty good bro" under a post showing a Fable 5.1 build →
  claude-fable-5.1 positive, endorsement, not firsthand.
- "Manifesting GPT 6 Astra to release next month" → relevant, nothing
  recorded. Anticipation with no stance on the model.
- "Claude's rate limits are bad enough, but the cost of cache misses on
  Fable 5.1 is ridiculous" → claude-fable-5.1 negative firsthand, task cost;
  claude_code negative firsthand, task cost.
- "Codex has the strongest harness constraints so highest pass rate; Claude
  Code next; Pi third. Claude Code wastes the most tokens." with the author
  saying it matches their experience → codex positive firsthand, claude_code
  mixed firsthand, pi positive firsthand; preferences codex > claude_code,
  codex > pi, claude_code > pi, firsthand, task coding.
- "In Chinese, Claude apologizes then explains then answers. Sol talks like
  a normal person. Kimi K3 and GLM-5.3-Flash are good enough value." →
  claude negative firsthand (family, task chat), sol positive firsthand,
  kimi-k3 positive firsthand, glm-5.3-flash positive firsthand; preference
  sol > claude, firsthand.
- "Grok 4.6 for the daily driver, Fable 5 for the tough problems. GPT 5.6
  does not enter the equation, doesn't perform as well, 3x more expensive
  than grok" → grok-4.6 positive firsthand, claude positive firsthand, gpt
  negative firsthand (5.6 unversioned is the family); preferences grok-4.6 >
  gpt, claude > gpt. No grok versus claude preference.
- "THIS GIRL CANCELED HER CLAUDE SUBSCRIPTION AFTER SWITCHING TO LUNA IN
  CODEX" → relevant, nothing recorded. Secondhand.
- "Clearly a terrible benchmark. Current Grok is not way better than
  previous Fable, it's absurdly worse" → grok-4.6 negative firsthand;
  preference claude > grok-4.6 firsthand.
- "I prefer Claude code but grok is very fun on Twitter" → claude_code
  positive firsthand. No preference, grok on Twitter is not a harness.
- "after a year switching between Claude Code and Codex, Cursor is my
  favorite UX. Daily driver is Grok in Cursor. Sol/Fable for adversarial
  review" (after Sep 1 18:00) → claude_code and codex mixed firsthand, aspect
  "UX versus Cursor"; grok-4.6, gpt-5.6-sol, claude-fable-5.1 positive
  firsthand. No preference line, Cursor is untracked. No switch.
- "Kinda digging the grok cli. Very 'I'm just going to go do it' vibes" →
  grokbot positive firsthand, aspect "autonomy".
- "@Renich Gemini 3.7 Flash is strong on multimodal... Recent Grok models
  lead Artificial Analysis..." from an account answering as Grok →
  ai_author true, nothing recorded.
