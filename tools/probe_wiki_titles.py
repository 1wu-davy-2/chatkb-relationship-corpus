#!/usr/bin/env python3
"""Probe candidate Chinese Wikipedia titles before adding them to WIKI.

Writes nothing; run it after editing CANDIDATES so a typo or a non-existent
article cannot become a wrong-article download. The search fallback only accepts
an exact normalised title, so probing here is how a missing article is found
early: 爱情三角理论, 上升点 and 马斯特斯和约翰逊 have no standalone zh article.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("tools").resolve()))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import fetch_zh as fz  # noqa: E402

CANDIDATES = (
    # round 2: replacements for wrong-article entries found in the audit.
    # Batch 7 and the round-1 probe are recorded in the 2026-10-26 notes in
    # 00_readme/许可与来源说明.md.
    "应对",
    "因应",
    "拒绝敏感",
    "愧疚",
    "罪疚感",
    "婚恋市场",
    "擇偶",
    "物質主義",
    "辩证行为治疗",
    "辯證行為治療",
    "理财",
    "金融知识",
    "空间关系学",
    "影响力",
    "性别认同",
    "跨性别",
    "约会",
    "追求",
)


def main() -> int:
    for title in CANDIDATES:
        found = fz.wiki_page(title)
        if found is None:
            print(f"MISSING  {title}")
            time.sleep(1.2)
            continue
        page = found[1]
        extract = fz.clean_lines(page.get("extract") or "")
        marker = "OK     " if len(extract) >= 400 else "SHORT  "
        print(f"{marker} {title} -> {page.get('title')} ({len(extract)} chars)")
        time.sleep(1.2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
