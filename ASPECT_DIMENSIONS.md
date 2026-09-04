# Aspect dimensions

Every sentiment and preference line in labels-v2 carries a free-text `aspect`
(2–6 words) written by the labeler. This contract maps each distinct aspect
string onto one fixed dimension so aspects can be counted and compared across
models and harnesses. The free text is kept as evidence; the dimension is the
roll-up.

Map each string to exactly one dimension. Choose the dimension the author is
really judging. When a string names two things, pick the dominant one. Read the
string as a person's reason for liking or disliking the thing; the polarity is
stored separately, so "slow" and "fast" both map to speed.

## Model dimensions (targets are exact model versions)

| id | name | covers |
|---|---|---|
| intelligence | Intelligence | reasoning, capability, code quality, output quality, correctness, benchmark standing, regression or improvement versus a prior version, task success ("built the app", "solved the bug"), creative or design output quality |
| speed | Speed | generation speed, thinking time, latency, tokens per second, "took all day" |
| price | Price | API price, cost per task, value for money, cost efficiency, cheap or expensive, index-score-versus-cost |
| steerability | Steerability | instruction following, staying on task, scope creep, ignoring constraints, needing many reprompts, controllability |
| personality | Personality | tone, verbosity, "Claudespeak", moralizing, nagging, refusals, safety filters, sycophancy, style of writing or chat |
| overall | Overall | bare praise or dislike with no aspect: "overall", "overall quality", "overall preference", "goated", "mid" |
| other | Other | anything that fits none of the above (availability, access, rollout, regional access, licensing, privacy) |

## Harness dimensions (targets are claude_code, codex, opencode, pi, grokbot)

| id | name | covers |
|---|---|---|
| limits | Limits and quota | weekly caps, 5-hour windows, plan burn, rate limits, subscription value and cancellations driven by limits, "not worth $200" |
| reliability | Reliability | outages, downtime, hangs, crashes, errors, stalled sessions, bugs in the tool itself |
| efficiency | Token and context efficiency | token waste, context burn, compaction quality, memory across sessions, skills persistence, long-session handling |
| agent | Agent behaviour | autonomy, "just goes and does it", planning mode, scope creep, permission prompts, task completion on complex work, quality of the agent loop, comparisons of which harness got the job done |
| dx | Developer experience | UI, app or CLI design, setup, onboarding, integrations, MCP, IDE fit, sandboxing, model choice and routing |
| overall | Overall | bare praise or dislike with no aspect |
| other | Other | anything that fits none of the above |

## Output

One JSON object per input string, same order as the input file:

    {"aspect": "<exact input string>", "dimension": "<id>"}

Use `other` sparingly. Use `overall` only when the string carries no aspect at
all. Never invent a dimension id.
