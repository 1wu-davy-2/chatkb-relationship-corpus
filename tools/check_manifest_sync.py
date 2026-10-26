#!/usr/bin/env python3
"""Check that every record points at files that exist on disk.

Prints the offending doc_ids so a prune that deleted a file but not its record
(or the reverse) is caught before the numbers go into the README.

`missing_files` must be 0. `unlisted_files` is informational: the per-file
components under `01_raw/skills/` are kept as provenance even though one merged
document record points at the whole repo, so a non-zero count there is expected.
A `02_text/` file with no record is not expected (unless a fetch is mid-write).
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(".")
RECORDS = ROOT / "05_manifest" / "records"

missing = []
orphans = []
for path in sorted(RECORDS.glob("*.json")):
    rec = json.loads(path.read_text(encoding="utf-8"))
    for key in ("text_path", "raw_path"):
        rel = rec.get(key)
        if rel and not (ROOT / rel).exists():
            missing.append(f"{rec.get('doc_id')} -> {key}: {rel}")

listed = set()
for path in RECORDS.glob("*.json"):
    rec = json.loads(path.read_text(encoding="utf-8"))
    for key in ("text_path", "raw_path"):
        if rec.get(key):
            listed.add(str((ROOT / rec[key]).resolve()))
for base in ("02_text", "01_raw"):
    for f in (ROOT / base).rglob("*"):
        if f.is_file() and str(f.resolve()) not in listed:
            orphans.append(str(f.relative_to(ROOT)).replace("\\", "/"))

print(f"records={len(list(RECORDS.glob('*.json')))}")
print(f"missing_files={len(missing)}")
for m in missing[:20]:
    print("  ", m)
print(f"unlisted_files={len(orphans)}")
for o in orphans[:20]:
    print("  ", o)
