#!/usr/bin/env python3
"""Policy check over the text we control or curate: no manipulation tactics, no
group determinism, no minors, no demeaning generalisations.

Prints context for every hit so matches can be judged — a word inside a warning
is compliant. Public-domain classics are excluded on purpose: 骚/贱 etc. appear
constantly in classical Chinese and produce nothing but noise.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRS = ("03_notes", "02_text/skills", "02_text/zh_official")

MANIP = re.compile(r"(服从性测试|推拉|冷读|打压式|negging|让她上头|操控她|控制她|驯化|洗脑她|欲擒故纵|晾着她)")
DETERM = re.compile(r"(所有(?:的)?女(?:人|生)|女人(?:都|就是|天生)|星座决定|血型决定|MBTI\s*决定|I人(?:都|一定)|E人(?:都|一定)|女人都要)")
MINOR = re.compile(r"(未成年|中学生|初中生|高中生|小学生|1[0-7]\s*岁)")
COERCE = re.compile(r"(灌酒|下药|强迫她|不答应就|威胁她|逼她就范)")
DEROG = re.compile(r"(绿茶|拜金女|捞女|婊|贱|骚|公主病|母狗)")

CHECKS = (
    ("manipulation", MANIP),
    ("determinism", DETERM),
    ("minor", MINOR),
    ("coercion", COERCE),
    ("derogatory", DEROG),
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="*", default=list(DEFAULT_DIRS))
    ap.add_argument("--show", type=int, default=8, help="hits printed per file")
    args = ap.parse_args()

    total = 0
    files_seen = 0
    for rel in args.dirs:
        base = ROOT / rel
        if not base.exists():
            print(f"!! missing directory: {rel}")
            continue
        subtotal = 0
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
                continue
            files_seen += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            hits: list[str] = []
            for name, pattern in CHECKS:
                for m in pattern.finditer(text):
                    start = max(0, m.start() - 45)
                    end = min(len(text), m.end() + 45)
                    context = text[start:end].replace("\n", " ")
                    hits.append(f"[{name}] ...{context}...")
            if hits:
                subtotal += len(hits)
                print(f"== {path.relative_to(ROOT)}: {len(hits)}")
                for h in hits[:args.show]:
                    print("   ", h[:190])
        print(f"-- {rel}: {subtotal} hits")
        total += subtotal
    print(f"\nfiles scanned: {files_seen}")
    print(f"total hits: {total}  (a hit is a review candidate, not a violation)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
