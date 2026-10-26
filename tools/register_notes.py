#!/usr/bin/env python3
"""Register 03_notes/*.md as corpus records so build_corpus.py can chunk them.

The notes are original writing under the repository's proprietary license.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "03_notes"
RECORDS = ROOT / "05_manifest" / "records"
RECORDS.mkdir(parents=True, exist_ok=True)

LICENSE = "Proprietary - All Rights Reserved (see LICENSE)"

TOPICS = {
    "00_使用说明与边界.md": ["usage", "boundaries", "scope"],
    "01_核心原则.md": ["principles", "communication", "mindset"],
    "02_聊天基本功.md": ["chat_skills", "conversation", "listening", "questions", "humor"],
    "03_情绪与依恋.md": ["emotion", "attachment", "validation", "empathy"],
    "04_关系阶段与场景.md": ["relationship_stages", "dating", "scenarios"],
    "05_年龄与生活阶段.md": ["life_stage", "age_groups", "college", "adults"],
    "06_性格话题与破冰.md": ["personality", "icebreaker", "zodiac", "mbti", "topics"],
    "07_金钱边界与反诈骗.md": ["money", "boundaries", "scam", "gifts", "safety"],
    "08_反操控与安全.md": ["manipulation", "gaslighting", "pua_defense", "coercion", "safety"],
    "09_实战示例与练习.md": ["practice", "examples", "scripts", "drills"],
    "10_性沟通与同意.md": ["sexuality", "consent", "safer_sex", "communication", "health", "safety"],
    "11_星座生肖与玄学话题.md": ["zodiac", "astrology", "belief", "barnum", "scam", "icebreaker"],
    "README.md": ["index"],
}


def main() -> int:
    count = 0
    for path in sorted(NOTES.glob("*.md")):
        raw = path.read_text(encoding="utf-8", errors="replace")
        title_match = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path.stem
        record = {
            "doc_id": f"note_{path.stem}",
            "source": "original_note",
            "source_type": "original_note",
            "content_role": "original_note",
            "title": title,
            "url": "",
            "language": "zh",
            "license": LICENSE,
            "license_url": "",
            "license_file": "LICENSE",
            "topics": TOPICS.get(path.name, ["notes"]),
            "excerpt_only": False,
            "raw_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "text_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "raw_bytes": path.stat().st_size,
            "text_chars": len(raw),
            "text_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }
        (RECORDS / f"note_{path.stem}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        count += 1
        print(f"registered note_{path.stem} ({len(raw)} chars)")
    print(f"total notes registered: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
