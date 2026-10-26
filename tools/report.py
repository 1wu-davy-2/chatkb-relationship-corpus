#!/usr/bin/env python3
"""Summarise the corpus: manifest, source table and size/license/topic report.

Outputs
  05_manifest/manifest.jsonl  one line per document
  05_manifest/sources.csv     flat table for spreadsheets
  05_manifest/report.json     totals used by README section 7
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "05_manifest" / "records"
MANIFEST = ROOT / "05_manifest" / "manifest.jsonl"
SOURCES = ROOT / "05_manifest" / "sources.csv"
REPORT = ROOT / "05_manifest" / "report.json"
BUILD_REPORT = ROOT / "04_chunks" / "build_report.json"

TEXT_DIRS = ("02_text", "03_notes")
RAW_DIRS = ("01_raw",)
CHUNK_DIRS = ("04_chunks",)

# Records store the language as it came from the source ("eng", "zh", "spa"...).
# Aggregate on ISO 639-1 so one language is not split across several keys.
LANG_ALIASES = {"eng": "en", "english": "en", "ger": "de", "deu": "de", "spa": "es",
                "fre": "fr", "fra": "fr", "por": "pt", "ita": "it", "jpn": "ja",
                "kor": "ko", "rus": "ru", "chi": "zh", "zho": "zh"}


def norm_lang(value: str | None) -> str:
    if not value:
        return "unknown"
    low = value.strip().lower()
    return LANG_ALIASES.get(low, low[:2] or "unknown")


FIELDS = (
    "doc_id", "source", "source_type", "title", "url", "language", "license",
    "excerpt_only", "topics", "raw_path", "text_path", "raw_bytes", "text_chars",
    "retrieved_at",
)


def dir_bytes(*names: str) -> int:
    total = 0
    for name in names:
        base = ROOT / name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
    return total


def main() -> int:
    records = []
    for path in sorted(RECORDS.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            print(f"bad record {path.name}: {exc}")

    by_source: Counter[str] = Counter()
    by_license: Counter[str] = Counter()
    by_lang: Counter[str] = Counter()
    by_source_chars: Counter[str] = Counter()
    by_lang_chars: Counter[str] = Counter()
    by_source_bytes: Counter[str] = Counter()
    by_lang_bytes: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()
    excerpt_count = 0
    missing_text = 0

    with MANIFEST.open("w", encoding="utf-8") as manifest, SOURCES.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["doc_id", "source", "source_type", "language", "license",
                         "excerpt_only", "text_chars", "text_bytes", "topics", "title", "url"])
        for rec in sorted(records, key=lambda r: (r.get("source", ""), r.get("doc_id", ""))):
            text_rel = rec.get("text_path") or ""
            text_path = ROOT / text_rel if text_rel else None
            size = 0
            if text_path is None or not text_path.exists():
                missing_text += 1
            else:
                size = text_path.stat().st_size
            source = rec.get("source") or "unknown"
            license_ = rec.get("license") or "unknown"
            lang = norm_lang(rec.get("language"))
            chars = int(rec.get("text_chars") or 0)
            topics = rec.get("topics") or []
            by_source[source] += 1
            by_license[license_] += 1
            by_lang[lang] += 1
            by_source_chars[source] += chars
            by_lang_chars[lang] += chars
            by_source_bytes[source] += size
            by_lang_bytes[lang] += size
            for t in topics:
                topic_counter[t] += 1
            if rec.get("excerpt_only"):
                excerpt_count += 1
            row = {k: rec.get(k) for k in FIELDS}
            row["text_bytes"] = size
            manifest.write(json.dumps(row, ensure_ascii=False) + "\n")
            writer.writerow([rec.get("doc_id", ""), source, rec.get("source_type", ""), lang,
                             license_, "yes" if rec.get("excerpt_only") else "no", chars, size,
                             "|".join(topics), (rec.get("title") or "").replace("\n", " ")[:120],
                             rec.get("url", "")])

    raw_bytes = dir_bytes(*RAW_DIRS)
    text_bytes = dir_bytes(*TEXT_DIRS)
    chunk_bytes = dir_bytes(*CHUNK_DIRS)

    build = {}
    if BUILD_REPORT.exists():
        build = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "documents": len(records),
        "documents_missing_text_file": missing_text,
        "excerpt_only_documents": excerpt_count,
        "bytes": {
            "raw_provenance_01_raw": raw_bytes,
            "cleaned_text_02_text_plus_03_notes": text_bytes,
            "chunks_04_chunks": chunk_bytes,
            # Chunks are the same documents re-serialised as JSONL with overlap
            # and metadata, so counting them next to the text would double-count.
            # The delivery figure is the cleaned text; the export figure is what
            # you actually upload to a knowledge base.
            "effective_content": text_bytes,
            "effective_content_mb": round(text_bytes / 1024 / 1024, 2),
            "export_with_chunks_mb": round((text_bytes + chunk_bytes) / 1024 / 1024, 2),
            "raw_mb": round(raw_bytes / 1024 / 1024, 2),
        },
        "by_source_documents": dict(by_source.most_common()),
        "by_source_text_bytes": dict(by_source_bytes.most_common()),
        "by_source_chars": dict(by_source_chars.most_common()),
        "by_license_documents": dict(by_license.most_common()),
        "by_language_documents": dict(by_lang.most_common()),
        "by_language_text_bytes": dict(by_lang_bytes.most_common()),
        "by_language_chars": dict(by_lang_chars.most_common()),
        "topics": dict(topic_counter.most_common(300)),
        "topic_count": len(topic_counter),
        "chunks": {
            "written": build.get("chunks_written"),
            "documents_chunked": build.get("documents_chunked"),
            "cleaned_chars_total": build.get("cleaned_chars_total"),
            "dropped_duplicate": (build.get("stats") or {}).get("chunk_dropped_duplicate"),
            "dropped_quality": (build.get("stats") or {}).get("chunk_dropped_quality"),
            "target_chars": build.get("chunk_target_chars"),
            "max_chars": build.get("chunk_max_chars"),
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"documents: {len(records)} (missing text: {missing_text}, excerpt-only: {excerpt_count})")
    print(f"raw 01_raw (provenance) : {raw_bytes/1024/1024:8.2f} MB")
    print(f"effective 02_text+03    : {text_bytes/1024/1024:8.2f} MB   <- the delivery figure")
    print(f"export 04_chunks        : {chunk_bytes/1024/1024:8.2f} MB   (same docs as JSONL)")
    print(f"whole repo on disk      : {(raw_bytes+text_bytes+chunk_bytes)/1024/1024:8.2f} MB")
    print("\ndocuments by source (text bytes = files under 02_text/, chars = characters):")
    for k, v in by_source.most_common():
        print(f"  {k:<16} {v:>5} docs  {by_source_bytes[k]/1024/1024:7.2f} MB  {by_source_chars[k]/1024/1024:7.2f} M chars")
    print("\ndocuments by license:")
    for k, v in by_license.most_common():
        print(f"  {v:>5}  {k[:80]}")
    print("\nby language:")
    for k, v in by_lang.most_common():
        print(f"  {k:<6} {v:>5} docs  {by_lang_bytes[k]/1024/1024:7.2f} MB  {by_lang_chars[k]/1024/1024:7.2f} M chars")
    if build:
        print(f"\nchunks: {report['chunks']['written']} written from "
              f"{report['chunks']['documents_chunked']} docs "
              f"({report['chunks']['cleaned_chars_total']/1024/1024:.1f} M chars cleaned); "
              f"dropped {report['chunks']['dropped_duplicate']} duplicate / "
              f"{report['chunks']['dropped_quality']} low-quality")
    print(f"\ntopics tracked: {len(topic_counter)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
