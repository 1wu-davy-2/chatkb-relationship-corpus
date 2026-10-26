#!/usr/bin/env python3
"""Clean every fetched document and emit AI-ready chunks.

Input:  05_manifest/records/*.json  (each points at a file under 02_text/)
Output: 04_chunks/chunks.jsonl      one JSON object per chunk
        04_chunks/build_report.json statistics for the run

Cleaning steps: drop the provenance header (kept in the record), cut reference
lists, collapse whitespace, drop boilerplate lines, then split into
sentence-aware chunks with a small overlap. Exact-duplicate chunks are removed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "05_manifest" / "records"
CHUNK_DIR = ROOT / "04_chunks"
CHUNKS = CHUNK_DIR / "chunks.jsonl"
REPORT = CHUNK_DIR / "build_report.json"
LOG_PATH = ROOT / "05_manifest" / "build_corpus.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("build")

ROLE_BY_SOURCE = {
    "europepmc": "evidence_paper",
    "zh_wikipedia": "encyclopedia",
    "zh_official": "official_or_excerpt",
    "gutenberg": "public_domain_book",
    "github_skill": "ai_skill",
    "open_textbook": "open_textbook",
    "original_note": "original_note",
}

REFERENCE_RE = re.compile(
    r"^\s*(references?|bibliography|works cited|literature cited|"
    r"参考文献|参考文獻|參考資料|引用文献)\s*[:：]?\s*$",
    re.IGNORECASE,
)
BOILERPLATE_RE = re.compile(
    r"(downloaded from|this article is distributed|copyright ©|all rights reserved|"
    r"^\s*https?://\S+\s*$|^\s*doi:\s*\S+\s*$|^\s*pmcid:|^\s*©\s*\d{4})",
    re.IGNORECASE,
)
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff]")
SENTENCE_EN_RE = re.compile(r"(?<=[.!?;:])\s+(?=[A-Z0-9\"'(])")
SENTENCE_ZH_RE = re.compile(r"(?<=[。！？；：\n])")


def strip_header(text: str) -> str:
    """Drop the provenance header block written by the fetchers."""
    parts = text.split("\n---\n", 1)
    return parts[1].lstrip("\n") if len(parts) == 2 else text


def cut_references(text: str) -> str:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if REFERENCE_RE.match(line) and i > 20:
            return "\n".join(lines[:i])
    return text


def clean_body(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = cut_references(text)
    out = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t\u3000]+", " ", line).strip()
        if not line:
            continue
        if BOILERPLATE_RE.search(line):
            continue
        if len(line) == 1 and not CJK_RE.search(line):
            continue
        out.append(line)
    return "\n".join(out)


def split_sentences(text: str, lang: str) -> list[str]:
    pieces = SENTENCE_ZH_RE.split(text) if lang == "zh" else SENTENCE_EN_RE.split(text)
    return [p.strip() for p in pieces if p and p.strip()]


def make_chunks(text: str, lang: str, target: int, max_size: int, overlap_sentences: int) -> list[str]:
    sentences = split_sentences(text, lang)
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for sent in sentences:
        if len(sent) > max_size:
            if buf:
                chunks.append(" ".join(buf) if lang != "zh" else "".join(buf))
                buf, size = [], 0
            for i in range(0, len(sent), max_size):
                chunks.append(sent[i:i + max_size])
            continue
        buf.append(sent)
        size += len(sent) + 1
        if size >= target:
            chunks.append(" ".join(buf) if lang != "zh" else "".join(buf))
            buf = buf[-overlap_sentences:] if overlap_sentences else []
            size = sum(len(s) + 1 for s in buf)
    if buf and sum(len(s) for s in buf) >= 120:
        chunks.append(" ".join(buf) if lang != "zh" else "".join(buf))
    return chunks


def keep_chunk(text: str, lang: str, min_chars: int) -> bool:
    if len(text) < min_chars:
        return False
    letters = sum(1 for c in text if c.isalpha() or CJK_RE.match(c))
    if letters < min_chars * 0.6:
        return False
    digits = sum(1 for c in text if c.isdigit())
    if digits > len(text) * 0.35:
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-chars", type=int, default=900)
    ap.add_argument("--max-chars", type=int, default=1400)
    ap.add_argument("--overlap-sentences", type=int, default=1)
    ap.add_argument("--min-chars", type=int, default=200)
    ap.add_argument("--limit-docs", type=int, default=0)
    args = ap.parse_args()

    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    records = sorted(RECORDS.glob("*.json"))
    if args.limit_docs:
        records = records[:args.limit_docs]
    log.info("records: %d", len(records))

    seen_hashes: set[str] = set()
    seen_prefixes: set[str] = set()
    stats = Counter()
    per_source_chars: Counter[str] = Counter()
    per_license_chars: Counter[str] = Counter()
    per_lang_chars: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()
    written = 0
    doc_count = 0

    with CHUNKS.open("w", encoding="utf-8") as out:
        for idx, path in enumerate(records, 1):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                stats["record_read_error"] += 1
                log.warning("bad record %s: %s", path.name, exc)
                continue
            text_rel = rec.get("text_path")
            if not text_rel:
                stats["no_text_path"] += 1
                continue
            text_path = ROOT / text_rel
            if not text_path.exists():
                stats["missing_text"] += 1
                continue
            try:
                raw = text_path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                stats["text_read_error"] += 1
                log.warning("cannot read %s: %s", text_path, exc)
                continue
            lang = (rec.get("language") or "en").lower()[:2]
            if lang not in {"zh", "en"}:
                lang = "zh" if CJK_RE.search(raw[:2000]) else "en"
            body = clean_body(strip_header(raw))
            if len(body) < args.min_chars:
                stats["body_too_short"] += 1
                continue
            source = rec.get("source") or "unknown"
            role = rec.get("content_role") or ROLE_BY_SOURCE.get(source, "other")
            if role == "original_note":
                body = clean_body(raw)
            doc_count += 1
            per_source_chars[source] += len(body)
            per_license_chars[(rec.get("license") or "unknown").lower()] += len(body)
            per_lang_chars[lang] += len(body)
            for t in rec.get("topics") or []:
                topic_counter[t] += 1
            chunks = make_chunks(body, lang, args.target_chars, args.max_chars, args.overlap_sentences)
            kept = 0
            for ci, chunk in enumerate(chunks):
                if not keep_chunk(chunk, lang, args.min_chars):
                    stats["chunk_dropped_quality"] += 1
                    continue
                norm = re.sub(r"\s+", "", chunk)
                digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()
                prefix = norm[:160]
                if digest in seen_hashes or prefix in seen_prefixes:
                    stats["chunk_dropped_duplicate"] += 1
                    continue
                seen_hashes.add(digest)
                seen_prefixes.add(prefix)
                out.write(json.dumps({
                    "chunk_id": f"{rec.get('doc_id')}_c{ci:04d}",
                    "doc_id": rec.get("doc_id"),
                    "source": source,
                    "role": role,
                    "lang": lang,
                    "title": rec.get("title") or "",
                    "url": rec.get("url") or "",
                    "license": rec.get("license") or "",
                    "license_url": rec.get("license_url") or "",
                    "topics": rec.get("topics") or [],
                    "excerpt_only": bool(rec.get("excerpt_only")),
                    "chunk_index": ci,
                    "chars": len(chunk),
                    "sha256": digest,
                    "text": chunk,
                }, ensure_ascii=False) + "\n")
                kept += 1
                written += 1
            stats["chunks_written"] += kept
            if idx % 100 == 0:
                log.info("[%d/%d] docs=%d chunks=%d", idx, len(records), doc_count, written)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_seen": len(records),
        "documents_chunked": doc_count,
        "chunks_written": written,
        "stats": dict(stats),
        "cleaned_chars_by_source": dict(per_source_chars.most_common()),
        "cleaned_chars_by_license": dict(per_license_chars.most_common(40)),
        "cleaned_chars_by_language": dict(per_lang_chars),
        "cleaned_chars_total": sum(per_source_chars.values()),
        "topics": dict(topic_counter.most_common(200)),
        "chunk_target_chars": args.target_chars,
        "chunk_max_chars": args.max_chars,
        "min_chunk_chars": args.min_chars,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("done: docs=%d chunks=%d cleaned_chars=%d (%.1f MB)",
             doc_count, written, report["cleaned_chars_total"], report["cleaned_chars_total"] / 1024 / 1024)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
