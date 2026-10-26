#!/usr/bin/env python3
"""Drop Wikipedia text files that add no knowledge, and remove their records.

Two classes: redirects where two requested titles landed on the same article,
and wrong articles produced by the old prefix-matching search fallback. Slugs
whose row in fetch_zh.py was rewritten to a probe-verified title are deleted
here and re-fetched by the next `fetch_zh.py --only wiki` run (it skips slugs
that already have a text file).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "02_text" / "zh_wikipedia"
RAW = ROOT / "01_raw" / "zh_wikipedia"
RECORDS = ROOT / "05_manifest" / "records"

# slug to delete -> why (kept duplicate in parentheses)
DROP = {
    "anorgasmia": "redirects to 性高潮 (orgasm kept)",
    "marital_intimacy": "redirects to 人类性行为 (human_sexual_activity kept)",
    "courtesy": "redirects to 礼仪 (etiquette kept)",
    "paidui": "redirects to 约会 (dating kept)",
    "divorce_cooling_off": "redirects to 离婚 (divorce kept)",
    "introversion": "same article as extraversion",
    "romance": "redirects to 爱情 (love kept)",
    "triangular_theory_of_love": "redirects to 爱情 (love kept)",
    "marriage_system": "redirects to 婚姻 (marriage kept)",
    "marriage_registration": "redirects to 婚姻 (marriage kept)",
    "anti_domestic_violence_law": "redirects to 家庭暴力 (domestic_violence kept; full law text is in zh_official)",
    "chinese_zodiac_legend": "redirects to 生肖 (chinese_zodiac kept)",
    "affair": "same article as extramarital_affair (婚外情 -> 外遇)",
    "ascendant_point": "wrong article: fallback search returned 上升2号, a mountain peak",
    "masters_johnson": "wrong article: fallback search returned 威廉姆斯车队, a Formula 1 team",
    # 2026-10-26 audit of all 272 wiki titles: these rows were requested as a
    # psychology/relationship concept but landed on an unrelated article.
    # The four marked "refetched" keep the same slug under a probe-verified
    # title; the rest have no usable zh article, so the row is gone from WIKI
    # and the concept is covered by the EPMC layer or a neighbouring entry.
    "stress": "wrong article: 压强 (physics pressure); refetched as 心理压力",
    "happiness": "wrong article: 中国最具幸福感城市 (a city ranking); refetched as 幸福",
    "coping": "wrong article: 国务院联防联控机制 (COVID press body); refetched as 因应",
    "unrequited_love": "wrong article: 蓝天下的单相思 (a film); refetched as 暗恋",
    "proxemics": "wrong article name for the slug: 人际吸引; refetched as interpersonal_attraction",
    "reciprocity": "wrong article: 互惠生 (au pair); social_exchange_theory covers the concept",
    "compliance": "wrong article: 女性顺从; obedience and persuasion cover influence",
    "rejection": "wrong article: 色情性拒绝 (a paraphilia); ostracism covers exclusion",
    "john_gottman": "wrong article: 约翰 (英格兰) (King John); Gottman's studies are in EPMC",
    "materialism": "wrong article: 後物質主義 (Inglehart's post-materialism); consumerism kept",
    "financial_literacy": "wrong article: 金融科技 (fintech); personal_finance covers 理财",
    "dialectical_behavior_therapy": "wrong article: 辩证法 (dialectics); no standalone zh article",
    "mental_health_literacy": "wrong article: 心理師 (the profession); psychological_counseling kept",
    "guilt": "wrong article: 幸存者内疚 (survivor guilt only); 内疚 is a 100-char stub",
    "marriage_customs": "wrong article: 印度教婚俗 (Hindu customs); bride_price and dowry kept",
    "marriage_market": "wrong article: 婚姻監禮人 (marriage witnesses); marriage_squeeze kept",
    "narcissistic_personality": "same article as narcissistic_personality_disorder",
}


def main() -> int:
    freed = 0
    for slug, reason in DROP.items():
        text_path = TEXT / f"{slug}.txt"
        if not text_path.exists():
            print(f"absent: {slug}")
            continue
        freed += text_path.stat().st_size
        text_path.unlink()
        raw_path = RAW / f"{slug}.json"
        if raw_path.exists():
            raw_path.unlink()
        record_path = RECORDS / f"wiki_{slug}.json"
        if record_path.exists():
            rec = json.loads(record_path.read_text(encoding="utf-8"))
            record_path.unlink()
            print(f"dropped {slug} | {rec.get('title', '')[:30]} | {reason}")
        else:
            print(f"dropped {slug} | (no record) | {reason}")
    print(f"\nfreed={freed / 1024:.0f} KB remaining_wiki_texts={len(list(TEXT.glob('*.txt')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
