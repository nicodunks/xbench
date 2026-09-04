#!/usr/bin/env python3
"""Package the labels-v2 public JSON for file:// previews of concept-v2.html."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "labels-v2"
payload = {
    "summary": json.loads((DATA / "public-summary.json").read_text()),
    "evidence": json.loads((DATA / "public-evidence.json").read_text()),
}
serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
serialized = serialized.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
(DATA / "embedded-data.js").write_text("window.XBENCH_DATA_V2=" + serialized + ";\n")
print(f"embedded {len(serialized):,} bytes")
