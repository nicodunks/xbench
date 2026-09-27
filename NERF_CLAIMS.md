# Nerf claims

"Did they nerf it?" follows every launch. This contract decides, post by post,
whether the author claims that Opus 5.5 got worse after it shipped.

A word net (nerf, quantized, lobotomized, dumber, degraded, throttled, "not the
same", 降智, 变笨, 量化, 劣化, and so on; see `nerf_candidates.py`) only chooses
which posts to read. It never decides. You read each post and answer.

## The question

Does the author claim that Opus 5.5, **after its release**, became worse than it
was earlier: nerfed, quantized, throttled, lobotomized, "dumber today",
"not the same model as launch day", silently swapped or degraded?

- `claim`: true when the author asserts or strongly suspects a post-launch
  decline in Opus 5.5 itself. Their own experience ("5.5 has been dumb since
  this morning") and a clear suspicion ("feels quantized today") both count.
- `claim`: false for everything else, including:
  - a fear or plea about a future nerf → false, but set `fears` true;
  - a question with no stance of its own ("did they nerf opus 5.5?") →
    false, but set `asks` true;
  - denying or mocking the claim ("people saying it's nerfed are coping") →
    false, set `denies` true;
  - Opus 5.5 being worse than another model, or than expectations, with no
    change over time;
  - nerf claims about other models (Opus 5, Fable, Sol) or about Claude Code
    limits or pricing (limits are not the model);
  - pre-launch posts, jokes with no claim, and outage reports ("it's down").
- `fears`: true when the author expects or dreads a nerf that has not
  happened yet: "use it before they nerf it", "please don't quantize 5.5",
  "give it two weeks". Not a claim; a separate signal. False otherwise.
- `firsthand`: true when the claim rests on the author's own use.
- `quote`: the phrase from the post that carries the claim (under 15 words),
  or "" when `claim`, `asks`, `denies` and `fears` are all false.

## Output

One JSON object per input line, same order:

    {"post_id": "...", "claim": false, "fears": false, "asks": false, "denies": false, "firsthand": false, "quote": ""}
