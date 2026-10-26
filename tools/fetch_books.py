#!/usr/bin/env python3
"""Download public-domain books from Project Gutenberg.

Two groups:
- Chinese classics on love, marriage, family advice and social wisdom.
- English public-domain etiquette / conversation / courtship manuals.

Discovery uses gutenberg.org HTML pages (the gutendex mirror times out from
here). Only texts that pass a relevance whitelist and an explicit-content
blocklist are kept. Gutenberg boilerplate is stripped; provenance goes into the
file header.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "01_raw" / "gutenberg"
TEXT_DIR = ROOT / "02_text" / "gutenberg"
RECORDS = ROOT / "05_manifest" / "records"
LOG_PATH = ROOT / "05_manifest" / "fetch_books.log"
USER_AGENT = "ChatKBResearch/1.0 (personal study corpus; local use)"

ZH_BROWSE = "https://www.gutenberg.org/browse/languages/zh"
EN_SEARCH = "https://www.gutenberg.org/ebooks/search/"

for d in (RAW_DIR, TEXT_DIR, RECORDS):
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("books")

# Chinese relevance whitelist: love/marriage memoirs, social wisdom, family
# advice, poetry about love, classics of manners.
ZH_INCLUDE = (
    "紅樓夢", "红楼梦", "聊齋", "聊斋", "浮生六記", "浮生六记", "影梅庵", "秋燈瑣憶", "秋灯琐忆",
    "香畹樓", "香畹楼", "詩經", "诗经", "楚辭", "楚辞", "樂府", "乐府", "古詩十九首", "古诗十九首",
    "花間集", "花间集", "納蘭", "纳兰", "唐詩", "唐诗", "宋詞", "宋词", "元曲", "西廂", "西厢",
    "牡丹亭", "長生殿", "长生殿", "桃花扇", "世說新語", "世说新语", "顏氏家訓", "颜氏家训",
    "朱子家訓", "朱子家训", "增廣賢文", "增广贤文", "菜根譚", "菜根谭", "小窗幽記", "小窗幽记",
    "幽夢影", "幽梦影", "圍爐夜話", "围炉夜话", "格言聯璧", "格言联璧", "名賢集", "名贤集",
    "老殘遊記", "老残游记", "儒林外史", "海上花列傳", "海上花列传", "孽海花", "禮記", "礼记",
    "論語", "论语", "孟子", "大學", "中庸", "孝經", "孝经", "曾國藩", "曾国藩", "家書", "家书",
    "儀禮", "仪礼", "周禮", "周礼", "兒女英雄傳", "儿女英雄传", "再生緣", "再生缘", "鏡花緣", "镜花缘",
    "二十年目睹之怪现状", "二十年目睹之怪現状", "官場現形記", "官场现形记", "今古奇觀", "今古奇观",
    "三言", "二拍", "初刻拍案驚奇", "警世通言", "醒世恆言", "喻世明言", "玉梨魂", "雪鴻淚史",
    # 第二批：情愛/世情小說、蒙學與家訓、格言小品、詩詞曲、才子佳人
    "情史", "玉簪記", "玉簪记", "琵琶記", "琵琶记", "拜月亭", "牆頭馬上", "墙头马上",
    "漢宮秋", "汉宫秋", "竇娥冤", "窦娥冤", "鶯鶯傳", "莺莺传", "霍小玉傳", "霍小玉传",
    "李娃傳", "李娃传", "遊仙窟", "游仙窟", "太平廣記", "太平广记", "搜神記", "搜神记",
    "子不語", "子不语", "閱微草堂筆記", "阅微草堂笔记", "夜雨秋燈錄", "夜雨秋灯录",
    "淞隱漫錄", "淞隐漫录", "廣陵潮", "广陵潮", "比目魚", "比目鱼", "豆棚閒話", "豆棚闲话",
    "宋詞三百首", "宋词三百首", "元曲選", "元曲选", "樂府詩集", "乐府诗集", "古文觀止", "古文观止",
    "千家詩", "千家诗", "三字經", "三字经", "千字文", "弟子規", "弟子规", "幼學瓊林", "幼学琼林",
    "女誡", "女诫", "列女傳", "列女传", "曾國藩家書", "曾国藩家书", "大學", "中庸", "孝經",
    "孝经", "儀禮", "仪礼", "周禮", "周礼", "楚辭", "楚辞", "花間集", "花间集", "納蘭詞",
    "纳兰词", "古詩十九首", "古诗十九首", "增廣賢文", "增广贤文", "小窗幽記", "小窗幽记",
    "幽夢影", "幽梦影", "格言聯璧", "格言联璧", "名賢集", "名贤集", "再生緣", "再生缘",
    "孽海花", "二刻拍案驚奇", "二刻拍案惊奇", "平山冷燕", "玉嬌梨", "玉娇梨", "好逑傳",
    "好逑传", "定情人", "兩交婚", "两交婚", "山水情", "型世言", "石點頭", "石点头",
)

# Explicit erotic classics are excluded on purpose: they are public domain but do
# not serve a communication/relationship study corpus.
BLOCK = (
    "金瓶梅", "肉蒲團", "肉蒲团", "燈草和尚", "灯草和尚", "品花寶鑑", "品花宝鉴", "癡婆妖傳",
    "绣榻野史", "繡榻野史", "昭陽趣史", "浪史", "弁而钗", "宜春香质", "如意君传", "僧尼孽海",
    "株林野史", "浓情快史", "巫山艳史", "青楼梦", "青樓夢", "风月梦", "風月夢", "九尾龟",
    "九尾龜", "欢喜冤家", "歡喜冤家", "贪欢报", "貪歡報", "春灯迷史", "春燈迷史", "杏花天",
    "桃花影", "碧玉楼", "碧玉樓", "怡情阵", "怡情陣", "巫梦缘", "巫夢緣", "春情野史",
    "補紅樓夢", "补红楼梦",
)

# Editions already superseded by another copy in the corpus, plus child-focused
# English manners books that do not serve an adult communication corpus.
SKIP_IDS = {
    "54756", "25202",
    "24139", "25377", "23850", "56291", "39040",
    "54495", "33188", "14408", "34200",
    "24162", "25381", "7418", "7419",
    "7260", "7270", "7271", "7272", "7273",
    "24185", "25231",
}

# English search queries aimed at public-domain social/relationship manuals.
# English search queries aimed at public-domain social/relationship manuals.
# The fourth-batch queries come first: they are the newest layer, and searching
# them before the broad etiquette terms keeps a small --max-books run focused.
EN_QUERIES = (
    # Fourth batch (2026-10-26): public-domain sexology / marriage-hygiene
    # scholarship and occult-belief histories. Scholarly titles only — the
    # erotica blocklist below stays in force.
    "psychology of sex", "sex education", "marriage hygiene", "psychology of love",
    "sexual morality", "sex life", "astrology", "zodiac", "palmistry", "occult",
    "history of witchcraft", "demons",
    "etiquette", "courtship", "conversation", "manners", "politeness", "marriage",
    "love letters", "how to behave", "social life", "gentleman", "lady", "home life",
    "engagement", "flirtation", "wooing", "art of pleasing", "advice to young",
    "letters to", "friendship", "courtship and marriage", "letter writing",
    "art of conversation", "self-culture", "conduct of life", "hostess", "table",
    "dancing", "dress", "tact", "sympathy", "wedding", "wife", "husband",
    "family life", "character", "cheerfulness", "courtship letters",
)
EN_INCLUDE = (
    "etiquette", "conversation", "courtship", "manners", "politeness", "marriage", "letter",
    "how to behave", "how to talk", "social", "gentleman", "lady", "lover", "love letters",
    "art of pleasing", "art of conversation", "good form", "society", "flirtation", "wooing",
    "wife", "husband", "home life", "family", "engagement", "friendship", "courtship",
    "advice", "conduct", "behavior", "behaviour", "courtship", "matchmaking", "ball",
    "dancing", "hostess", "guest", "table", "dress", "tact", "charm", "sympathy",
    # Public-domain sexuality scholarship and occult-belief history.
    "psychology of sex", "sexual psychology", "sex education", "sexual education",
    "marriage hygiene", "psychology of love", "sexual morality", "sexual life",
    "sex life", "problem of marriage", "sexual instincts",
    "astrology", "zodiac", "palmistry", "chiromancy", "occult", "witchcraft",
    "divination", "horoscope", "phrenology", "spiritualism",
)

# Titles in this tuple are tagged into their own provenance group so the
# sexuality / belief layer stays separable from the etiquette layer.
EN_SEX_TERMS = (
    "psychology of sex", "sexual psychology", "sex education", "sexual education",
    "marriage hygiene", "psychology of love", "sexual morality", "sexual life",
    "sex life", "sexual instincts", "problem of marriage",
)
EN_BELIEF_TERMS = (
    "astrology", "zodiac", "palmistry", "chiromancy", "occult", "witchcraft",
    "divination", "horoscope", "phrenology", "spiritualism",
)
EN_BLOCK = (
    "pornograph", "erotica", "kama sutra", "arabian nights", "decameron", "fanny hill",
    "memoirs of a woman of pleasure", "sexual psychopath", "cama sutra", "perfumed garden",
    # Explicit / fiction guards for the new sexuality queries: public domain but
    # not knowledge content.
    "erotic", "masoch", "sade", "venus in furs", "three weeks", "my secret life",
    "woman on top", "gamiani", "aretno", "spicy", "naughty", "lady chatterley",
    "autobiography of a flea", "amorous", "wantons", "whored", "lecher",
    # Minor-adjacent titles are never acceptable, including historical sexology
    # written about children.
    "child", "children", "adolescent", "juvenile", "infant",
    # Fiction that shares vocabulary with the new belief queries.
    "witchcraft fiction", "the occult", "witch boy", "black forest",
    # Title-keyword noise: works that merely mention conversation/social life.
    "napoleon", "emperor", "autocrat of the breakfast", "1601",
    "cathedral", "prairie", "husbandman", "chemistry", "boarding school",
    "breakfast-table", "every-day book", "nona", "servant", "egyptians",
    "how to observe", "imaginary conversations", "polite conversation",
    "lives and letters",
    # Historical/philological editions with no modern social use.
    "early english meals", "babees", "renaissance courtesy", "galateo", "tea drinking",
    "medieval manners", "anglo-saxon", "old english",
)

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en,zh;q=0.8"})

START_RE = re.compile(r"\*{3}\s*START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*{3}", re.IGNORECASE | re.DOTALL)
END_RE = re.compile(r"\*{3}\s*END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*{3}", re.IGNORECASE | re.DOTALL)


def clean_lines(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t\u3000]+", " ", line).rstrip()
        if line.strip():
            lines.append(line.strip())
    return "\n".join(lines)


def strip_gutenberg(text: str) -> str:
    m = START_RE.search(text)
    if m:
        text = text[m.end():]
    m = END_RE.search(text)
    if m:
        text = text[:m.start()]
    return clean_lines(text)


def decode_best(raw: bytes) -> str:
    """Gutenberg text files are UTF-8, but a few legacy ones are GB18030/Big5."""
    for enc in ("utf-8", "utf-8-sig", "gb18030", "big5"):
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if text.count("\ufffd") <= max(5, len(text) // 20000):
            return text
    return raw.decode("utf-8", errors="replace")


def matches(text: str, terms: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(t.lower() in low for t in terms)


def blocked(text: str) -> bool:
    return matches(text, BLOCK) or matches(text, EN_BLOCK)


def text_urls(book_id: int) -> list[str]:
    return [
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
        f"https://www.gutenberg.org/ebooks/{book_id}.txt",
    ]


def slugify(book: dict) -> str:
    title_key = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "_", book.get("title") or "")[:40].strip("_").lower()
    return f"gut_{book['id']}_{title_key or 'untitled'}"


def save_book(book: dict, lang: str, group: str, topics: list[str]) -> bool:
    book_id = int(book["id"])
    if str(book_id) in SKIP_IDS:
        return False
    record_path = RECORDS / f"gut_{book_id}.json"
    if record_path.exists():
        return False
    raw = b""
    used_url = ""
    for url in text_urls(book_id):
        try:
            resp = session.get(url, timeout=120)
            if resp.ok and resp.content:
                raw, used_url = resp.content, url
                break
        except Exception as exc:
            log.warning("download failed %s %s: %s", book_id, url, exc)
    if not raw:
        log.warning("no text for %s", book_id)
        return False
    text = decode_best(raw)
    body = strip_gutenberg(text)
    min_chars = 8000 if lang == "zh" else 20000
    if len(body) < min_chars:
        log.info("skip %s: too short (%s chars)", book_id, len(body))
        return False
    title = clean_lines(book.get("title") or f"Gutenberg {book_id}")
    slug = slugify(book)
    header = "\n".join([
        f"TITLE: {title}",
        f"GUTENBERG_ID: {book_id}",
        f"LANGUAGE: {lang}",
        f"GROUP: {group}",
        f"URL: https://www.gutenberg.org/ebooks/{book_id}",
        f"DOWNLOAD_URL: {used_url}",
        "LICENSE: Project Gutenberg License (text believed to be in the public domain in the United States)",
        "LICENSE_URL: https://www.gutenberg.org/policy/license.html",
        "NOTE: Check your own country's copyright term before redistributing.",
        f"TOPICS: {', '.join(topics)}",
        f"RETRIEVED: {datetime.now(timezone.utc).isoformat()}",
        "",
        "---",
        "",
        body,
    ])
    raw_path = RAW_DIR / f"{book_id}.txt"
    raw_path.write_bytes(raw)
    text_path = TEXT_DIR / f"{slug}.txt"
    text_path.write_text(header, encoding="utf-8")
    record = {
        "doc_id": f"gut_{book_id}",
        "source": "gutenberg",
        "source_type": "public_domain_book",
        "group": group,
        "title": title,
        "gutenberg_id": str(book_id),
        "url": f"https://www.gutenberg.org/ebooks/{book_id}",
        "download_url": used_url,
        "language": lang,
        "license": "Project Gutenberg License (public domain in the US)",
        "license_url": "https://www.gutenberg.org/policy/license.html",
        "topics": topics,
        "raw_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
        "text_path": str(text_path.relative_to(ROOT)).replace("\\", "/"),
        "raw_bytes": len(raw),
        "text_chars": len(header),
        "text_sha256": hashlib.sha256(header.encode("utf-8")).hexdigest(),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("saved %s | %s | %s chars | %s", book_id, lang, len(header), title[:70])
    return True


def _anchor_title(a) -> str:
    node = a.select_one(".title, span.title, .subtitle")
    text = node.get_text(" ") if node else a.get_text(" ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^\d+[.)]\s*", "", text)
    return text[:200]


def gutenberg_listing(url: str, params: dict | None = None) -> list[dict]:
    """Scrape a Gutenberg browse/search page into [{id, title}] records."""
    try:
        resp = session.get(url, params=params or {}, timeout=120)
        resp.raise_for_status()
    except Exception as exc:
        log.warning("listing failed %s %s: %s", url, params, exc)
        return []
    soup = BeautifulSoup(resp.content, "lxml")
    books: list[dict] = []
    seen: set[int] = set()
    for a in soup.select("a[href*='/ebooks/']"):
        m = re.search(r"/ebooks/(\d+)/?$", (a.get("href") or "").strip())
        if not m:
            continue
        book_id = int(m.group(1))
        if book_id in seen:
            continue
        title = _anchor_title(a)
        if len(title) < 2:
            continue
        seen.add(book_id)
        books.append({"id": book_id, "title": title})
    return books


def collect_zh() -> list[tuple[dict, str, str, list[str]]]:
    books = gutenberg_listing(ZH_BROWSE)
    log.info("zh browse page books: %d", len(books))
    out = []
    for book in books:
        title = book["title"]
        if blocked(title):
            continue
        if matches(title, ZH_INCLUDE):
            out.append((book, "zh", "zh_classic", ["chinese_classic", "culture", "emotion"]))
    return out


def collect_en(max_pages: int) -> list[tuple[dict, str, str, list[str]]]:
    out: list[tuple[dict, str, str, list[str]]] = []
    seen: set[int] = set()
    for query in EN_QUERIES:
        for page in range(max_pages):
            params = {"query": query, "sort_order": "downloads"}
            if page:
                params["start_index"] = page * 25 + 1
            books = gutenberg_listing(EN_SEARCH, params)
            if not books:
                break
            for book in books:
                if book["id"] in seen:
                    continue
                title = book["title"]
                if blocked(title) or not matches(title, EN_INCLUDE):
                    continue
                seen.add(book["id"])
                low = title.lower()
                if any(t in low for t in EN_SEX_TERMS):
                    group, topics = "en_sexuality_science", ["sexuality", "psychology", "public_domain", query]
                elif any(t in low for t in EN_BELIEF_TERMS):
                    group, topics = "en_belief_history", ["astrology", "belief", "public_domain", query]
                else:
                    group, topics = "en_etiquette", ["etiquette", "conversation", "courtship", query]
                out.append((book, "en", group, topics))
            time.sleep(1.0)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-books", type=int, default=200)
    ap.add_argument("--max-total-mb", type=float, default=25.0)
    ap.add_argument("--max-pages", type=int, default=3)
    ap.add_argument("--sleep", type=float, default=1.2)
    ap.add_argument("--lang", choices=("all", "zh", "en"), default="all")
    args = ap.parse_args()

    target_bytes = int(args.max_total_mb * 1024 * 1024)

    def total_text_bytes() -> int:
        return sum(p.stat().st_size for p in TEXT_DIR.glob("*.txt"))

    zh_queue = collect_zh() if args.lang in ("all", "zh") else []
    log.info("Chinese whitelist candidates: %d", len(zh_queue))
    en_queue = collect_en(args.max_pages) if args.lang in ("all", "en") else []
    log.info("English whitelist candidates: %d", len(en_queue))

    # Interleave so both language groups are represented early.
    queue: list[tuple[dict, str, str, list[str]]] = []
    for i in range(max(len(zh_queue), len(en_queue))):
        if i < len(zh_queue):
            queue.append(zh_queue[i])
        if i < len(en_queue):
            queue.append(en_queue[i])

    saved = 0
    for book, lang, group, topics in queue:
        if saved >= args.max_books or total_text_bytes() >= target_bytes:
            break
        if save_book(book, lang, group, topics):
            saved += 1
        time.sleep(args.sleep)

    log.info(
        "done: new=%d files=%d text=%.2f MB",
        saved,
        len(list(TEXT_DIR.glob("*.txt"))),
        total_text_bytes() / 1024 / 1024,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
