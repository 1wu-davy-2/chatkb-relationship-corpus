#!/usr/bin/env python3
"""Remove Gutenberg books that passed the title whitelist but carry no
relationship/communication knowledge (novels, language textbooks, agriculture,
chemistry dialogues, travel logs, multi-volume miscellany).

Deletes record JSON + raw download + cleaned text together, so the manifest stays
consistent with what is on disk. Run after fetch_books.py, then rebuild.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "05_manifest" / "records"

# group: why the title is not usable knowledge for this corpus
OFF_TOPIC: dict[str, list[str]] = {
    "sentimental fiction, not a social manual": ["25493", "38723"],
    "essay/literary miscellany that only shares the word 'conversation'": [
        "2666", "2665", "21628", "3020", "53275", "53276", "53277", "12059", "60186",
    ],
    "language textbook / school dialogue": ["11748", "26908", "27804"],
    "agriculture and household husbandry": ["22973"],
    "travel narrative": ["78020"],
    "domestic-service etiquette for 19th-century servants": ["78121"],
    "ethnographic survey of 19th-century Egypt": ["70796"],
    "literary criticism (Margaret Fuller)": ["33944"],
    # Fourth batch fallout: sexology written about a child, plus titles that only
    # matched the broad "lady/advice" terms.
    "sexology about a child - excluded by the adults-only rule": ["28402"],
    "history of women's education, no interaction knowledge": ["49867"],
    "commencement address about college choice": ["2361"],
    "public-health and zymotic lectures, only tangentially about sex": ["1637"],
}


def main() -> int:
    removed = 0
    freed = 0
    for reason, ids in OFF_TOPIC.items():
        for book_id in ids:
            rec_path = RECORDS / f"gut_{book_id}.json"
            if not rec_path.exists():
                print(f"absent: {book_id}")
                continue
            rec = json.loads(rec_path.read_text(encoding="utf-8"))
            for key in ("raw_path", "text_path"):
                rel = rec.get(key)
                if not rel:
                    continue
                path = ROOT / rel
                if path.exists():
                    freed += path.stat().st_size
                    path.unlink()
            rec_path.unlink()
            removed += 1
            print(f"deleted [{reason}] {book_id} | {rec.get('title', '')[:60]}")
    remaining = len(list(RECORDS.glob("gut_*.json")))
    print(f"\nremoved={removed} freed={freed / 1024 / 1024:.2f} MB remaining_gut_records={remaining}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
