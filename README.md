# Xbench

Seven-day view of AI-model attention, sentiment, preference, and switching on X.

Open `concept.html`, or run:

```bash
python3 -m http.server 4173
```

Then visit `http://127.0.0.1:4173/concept.html`.

Current release data is in `data/agent-rebuild/`.

## v2 viewer (LLM-labeled release)

`concept-v2.html` reads `data/labels-v2/` (one language-model pass per post against
`AGENT_CLASSIFICATION_PROMPT.md`, reviewer overrides applied). The v1 viewer and
`data/agent-rebuild/` are untouched.

Rebuild the v2 data and its embedded bundle:

```bash
python3 build_release_v2.py && python3 finalize_release_v2.py && python3 build_embedded_data_v2.py
```

Then open `http://127.0.0.1:4173/concept-v2.html`.

