#!/usr/bin/env python3
"""Verify 04_chunks/chunks.jsonl is loadable and provenance-complete."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "04_chunks" / "chunks.jsonl"
REQUIRED = ("chunk_id", "doc_id", "source", "role", "lang", "title", "url",
            "license", "topics", "chunk_index", "chars", "sha256", "text")

bad_lines = 0
missing_fields = Counter()
roles = Counter()
langs = Counter()
sizes = Counter()
total = 0
examples: dict[str, str] = {}

with CHUNKS.open(encoding="utf-8") as fh:
    for lineno, line in enumerate(fh, 1):
        line = line.strip()
        if not line:
            continue
        total += 1
        try:
            obj = json.loads(line)
        except Exception:
            bad_lines += 1
            continue
        for key in REQUIRED:
            if key not in obj:
                missing_fields[key] += 1
        roles[obj.get("role", "?")] += 1
        langs[obj.get("lang", "?")] += 1
        n = obj.get("chars", 0)
        sizes["<200" if n < 200 else "200-900" if n <= 900 else "900-1400" if n <= 1400 else ">1400"] += 1
        role = obj.get("role", "?")
        if role not in examples:
            examples[role] = (obj.get("title", "")[:40], obj.get("text", "")[:110].replace("\n", " "))

print(f"lines={total} unparseable={bad_lines} missing_fields={dict(missing_fields)}")
print(f"roles={dict(roles)}")
print(f"langs={dict(langs)}")
print(f"chunk size buckets={dict(sizes)}")
print()
for role, (title, text) in examples.items():
    print(f"[{role}] {title}")
    print(f"    {text}")
