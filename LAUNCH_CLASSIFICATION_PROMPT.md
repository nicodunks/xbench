# Xbench Launches: classification contract

This is the v2 contract ([`AGENT_CLASSIFICATION_PROMPT.md`](AGENT_CLASSIFICATION_PROMPT.md))
applied to a launch window. Read that file first and follow every rule in it,
except where this file replaces a rule. Each batch belongs to one **era**,
named in the batch's first line. The era decides which ids you may record and
how bare names resolve.

## What changes from v2

1. **Tracked ids come from the era**, not from the v2 list. A model outside the
   era's list records nothing, even if v2 tracks it.
2. **Two extra fields on every sentiment line:**
   - `intensity`: 1, 2 or 3. 1 is mild or hedged ("pretty decent", "a bit
     slow"). 2 is a clear stance ("really good", "worse than before"). 3 is
     strong: superlatives, all-caps enthusiasm, "unusable", "I'm cancelling".
   - `superlative`: true only when the author places the entity at an extreme
     beyond this week: "best model I've ever used", "the best release since
     3.5 Sonnet", "Claude is back", "AGI", "worst model they've shipped".
     Ordinary strong praise ("insanely good") is intensity 3 with
     superlative false.
3. **Dimension on every sentiment and preference line.** `dimension` is one id
   from [`ASPECT_DIMENSIONS.md`](ASPECT_DIMENSIONS.md): for a model target
   intelligence, speed, price, steerability, personality, overall, other; for a
   harness target limits, reliability, efficiency, agent, dx, overall, other;
   for a family target null. For a preference, use the winner's kind. Pick
   the dimension the aspect is really about, as that file says.
4. **Vendor staff.** A post by someone who says or clearly shows they work at
   the vendor of the entity (Anthropic staff on Claude, OpenAI on GPT, and so
   on), including "we shipped", "our new model", is `vendor: true` on the
   post. Record their lines as usual; the aggregator drops them.
5. **Pre-release.** A post before the era's launch moment about the launching
   model is speculation and records nothing, unless the author says they had
   early access and describes use. Early testers are firsthand.
6. **Price and limits.** As v2: the model's own price and token appetite stay
   on the model; plan caps, five-hour windows and weekly limits go to the
   harness (claude_code for a Claude model in a coding context).

## Eras

### `opus-5.5` (2026-09-20 to 2026-09-28)

Launch moments (UTC): Grok 4.7 2026-09-21 15:00. Claude Opus 5.5
2026-09-22 16:31. GPT-6 Sol and GPT-6 Luna 2026-09-22 17:00.

Models: claude-opus-5.5, claude-opus-5, claude-fable-5.1, gpt-6-sol,
gpt-6-luna, gpt-6-astra, gpt-5.6-sol, gpt-5.6-luna, grok-4.7, grok-4.6,
gemini-3.8-flash, glm-5.3, glm-5.3-flash, kimi-k3, muse-spark-1.3.
Harnesses: claude_code, codex, opencode, pi, grokbot.
Families: claude, gpt, gemini, grok, glm, kimi, muse.

Resolution:
- "Opus 5.5", "Opus-5.5", "claude-opus-5-5" are claude-opus-5.5. After the
  launch moment, "Opus" alone and "the new Opus" are claude-opus-5.5 unless
  the post says 5 or clearly means the old model ("Opus 5 was terrible, this
  one is great" is one line each).
- "Opus 5" is claude-opus-5. Watch for "5.5 vs 5" comparisons: they are a
  preference line claude-opus-5.5 over or under claude-opus-5.
- "GPT-6 Sol", "Sol 6", and "Sol" alone after 17:00 on Sep 22 when the post
  is about the new OpenAI release are gpt-6-sol. "5.6 Sol" is gpt-5.6-sol.
  Bare "Sol" with no way to tell which is the gpt family. Luna the same way.
- "Grok 4.7" is grok-4.7; "Grok" alone is the grok family; Grok Bot, Grok
  Build and grok cli are grokbot.
- Claude Code changed its default model to Opus 5.5 and raised usage limits
  on launch day. "Claude Code with 5.5 is flying" is positive for both
  claude-opus-5.5 and claude_code. A comment on the new limits is claude_code,
  aspect about limits.

### `opus-5` (2026-07-22 to 2026-07-30)

Launch moment: Claude Opus 5, 2026-07-24 17:00.
Models: claude-opus-5 only. Harnesses: claude_code, codex. Family: claude.
"Opus" alone after the launch moment is claude-opus-5. Every other model
records nothing.

### `gpt-5` (2025-08-05 to 2025-08-13)

Launch moment: GPT-5, 2025-08-07 17:00.
Models: gpt-5 only ("GPT-5", "GPT-5 Thinking", "GPT-5 Pro" and "GPT5" all
count; "GPT-5 mini" and "nano" record nothing). Harnesses: codex. Family: gpt.
The ChatGPT model router, the removal of GPT-4o and the launch-stream charts
were the talk of that week: a complaint about the router's choices or about
the model's output is gpt-5; a complaint about losing 4o is gpt-5 negative only
when the author says GPT-5 is worse for them.

### `claude-3.5-sonnet` (2024-06-18 to 2024-06-26)

Launch moment: Claude 3.5 Sonnet, 2024-06-20 14:00.
Models: claude-3.5-sonnet only ("Claude 3.5 Sonnet", "Sonnet 3.5", "3.5
Sonnet", and "Sonnet" alone after the launch moment). Family: claude.
Artifacts was released with it: praise for Artifacts is positive for
claude-3.5-sonnet when the author credits the model's output.

### `astra` (2026-09-03 to 2026-09-09)

Launch moment: GPT-6 Astra, 2026-09-03 19:00. It reached Pro and Codex users on
2026-09-04. Tracked ids exactly as in the v2 contract (13 models, 5 harnesses).

## Output

The v2 schema plus `intensity`, `superlative` and `dimension` on sentiment lines, `dimension` on preference lines, and `vendor` on the post:

```json
{"post_id":"...","relevant":true,"ai_author":false,"vendor":false,"uncertain":false,
 "sentiment":[{"target":"claude-opus-5.5","label":"positive","firsthand":true,"endorsement":false,
               "intensity":3,"superlative":true,"task":"coding","aspect":"one-shot refactor quality","dimension":"intelligence"}],
 "preferences":[{"winner":"claude-opus-5.5","loser":"gpt-6-sol","firsthand":true,"benchmark":false,"task":"coding","aspect":"fewer steps per task","dimension":"intelligence"}],
 "switches":[{"origin":"codex","destination":"claude_code","completed":true}],
 "reason":"Quote a phrase from the post, then one or two sentences specific to it."}
```

## Worked examples (opus-5.5 era)

- "ok opus 5.5 just one-shot a migration opus 5 choked on for two days. claude
  is so back" → claude-opus-5.5 positive firsthand, intensity 3, superlative
  true ("claude is so back"), aspect "one-shot migration"; claude-opus-5
  negative firsthand, intensity 2, aspect "failed migration"; preference
  claude-opus-5.5 > claude-opus-5 firsthand, task coding.
- "Opus 5.5 is #1 on Arena, huge" → relevant, nothing firsthand: a benchmark
  report. Record claude-opus-5.5 positive, firsthand false.
- "cancelled codex, back on claude code now that 5.5 is the default and the
  limits aren't a joke" → claude_code positive firsthand, aspect "limits";
  claude-opus-5.5 positive firsthand, aspect "default model"; codex negative
  is not stated, record nothing for it; switch codex -> claude_code completed;
  preference claude_code > codex.
- "5.5 still writes 'You're absolutely right!' every other message" →
  claude-opus-5.5 negative firsthand, intensity 2, aspect "sycophancy".
- "Tomorrow's Opus is going to be insane, leaks look crazy" (Sep 21) →
  relevant, nothing recorded. Pre-release.
- "Been testing Opus 5.5 for two weeks under NDA, it is the best model I have
  ever used" (Sep 22, 16:40) → claude-opus-5.5 positive firsthand, intensity
  3, superlative true. Early tester.
- "we shipped opus 5.5 today and I'm so proud of the team" → vendor true,
  claude-opus-5.5 positive, firsthand false.
