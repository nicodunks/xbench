#!/usr/bin/env python3
"""Package public Xbench JSON for file:// previews without fetch/CORS."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "agent-rebuild"
payload = {
    "summary": json.loads((DATA / "public-summary.json").read_text()),
    "evidence": json.loads((DATA / "public-evidence.json").read_text()),
}
serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
# Escape characters that can terminate or confuse an inline/script context.
serialized = serialized.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
(DATA / "embedded-data.js").write_text("window.XBENCH_DATA=" + serialized + ";\n")
print(f"embedded {len(serialized):,} bytes")
