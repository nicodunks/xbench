# Contributing

Xbench is small and opinionated, and the most useful contribution is a
correction. Every counted post is on the page with its reason and a link, so
if a label is wrong you can point at it.

## Dispute a label

1. Find the post on the page. Every evidence card links to X and shows the
   labeler's quoted reason.
2. Open an issue titled `label: <post_id>` with what you think the record
   should be and why. Quote the post. The contract in
   `AGENT_CLASSIFICATION_PROMPT.md` is the standard; argue from it.
3. If you want to submit the fix yourself, append a full replacement record to
   `data/labels-v2/overrides.jsonl` (same shape as a label line, with a
   `reason` that starts with `Reviewer:`), then run:

   ```bash
   python3 validate_labels.py
   ```

   Overrides replace the labeler's record wholesale, so include every field.

Dimension mistakes (a reason filed under the wrong dimension) go in
`data/labels-v2/aspect-map/maps/` the same way: add a line mapping the exact
aspect string to the right dimension in a new file named `*-fix.jsonl`, and run
`python3 validate_aspect_map.py`.

## Rebuild the release

The raw corpus (post text for every pulled post) is not in the repo; see the
README. Without it you can still validate every label file and read every
public output. With it, in `data/private/corpus.jsonl`:

```bash
python3 validate_labels.py && python3 validate_aspect_map.py && python3 validate_quota_audit.py \
  && python3 build_release_v2.py && python3 finalize_release_v2.py
```

`finalize_release_v2.py` refuses to write a manifest if any label is missing,
any override targets an unknown post, or any public file carries an author
field.

## Add a model or harness

1. Add the canonical id to `AGENT_CLASSIFICATION_PROMPT.md` (models are exact
   versions; harnesses are tools), to `validate_labels.py`, and to the
   `MODELS` / `HARNESSES` lists in `build_release_v2.py`.
2. Add a display name and logo key in `xbench.js`, and a logo SVG in
   `assets/logos/` if the vendor is new.
3. Relabel only the batches that mention it. Do not relabel the corpus.

## Run the page

```bash
python3 -m http.server 4173
```

Then open `http://127.0.0.1:4173/`. The page fetches the two JSON files in
`data/labels-v2/`, so it needs a server rather than `file://`.

## Style

Plain Python, no framework, one file per stage. Vanilla JS and CSS, no build
step. Keep copy short; the page explains itself with numbers, not paragraphs.
Every number on the page must be traceable to `public-summary.json` or
`public-evidence.json`.
