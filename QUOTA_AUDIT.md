# Quota audit

The v2 contract says subscription caps, usage windows and rate limits count
against the harness a person is using, never against the model. The labelers
did not always apply this when a post named a model and a limit but no harness.
This audit re-reads every model sentiment line whose aspect touches price,
cost, tokens, usage or limits and decides what the author was actually judging.

Read the post text (and root_text when present). Decide one `kind`:

- `model_cost` — the model's own price or appetite: API rate, cost per task,
  cost per token, value for money, "burns tokens", "token hungry", "uses 3x
  the tokens of Sol", "cheap", "expensive". Stays on the model.
- `quota` — a plan or subscription constraint: weekly limit, 5-hour window,
  "usage running out", "hit my cap", "Pro/Max plan burn", "not available on my
  plan", credits on a subscription. Moves to the harness.
- `both` — the post clearly says both things: the model eats tokens AND that
  drains a plan limit. Keep a model line for token appetite and add a harness
  line for the limit.
- `unrelated` — the aspect is not about cost, tokens or limits at all (it was
  swept in by a keyword). Leave the line as it is.

When `kind` is `quota` or `both`, set `harness`:

- the harness named or clearly in use in the post: `claude_code`, `codex`,
  `opencode`, `pi`, `grokbot`;
- if none is named: a Claude model on a Claude plan in a coding or agent
  context is `claude_code`; a GPT model on a ChatGPT/OpenAI plan is `codex`
  only when the context is coding (repo, CLI, agent, app build), otherwise
  `null`;
- any other vendor's plan (GLM, Kimi, Muse, Gemini, Grok model plans) has no
  tracked harness: `null`.

A `quota` line with `harness: null` is dropped from the model and recorded
nowhere. That is correct: it is a plan complaint about an untracked product.

Output one JSON object per input line, same order:

    {"post_id": "...", "line": <int>, "kind": "model_cost|quota|both|unrelated", "harness": "<id>|null", "note": "<under 15 words quoting the post>"}
