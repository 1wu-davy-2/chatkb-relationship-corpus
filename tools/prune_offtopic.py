#!/usr/bin/env python3
"""Remove off-topic Europe PMC records that slipped past the title filters.

Deletes the record JSON, the raw XML and the cleaned text file together so the
manifest stays consistent with what is on disk.

Modes:
  * default  - delete the explicit OFF_TOPIC list below (manual review findings)
  * --scan   - re-check every stored record against the live title filters in
               fetch_europepmc.py; pass --apply to delete what it finds

A dry scan is the cheap way to notice that a facet is pulling in biology or
clinical-cohort papers after the regexes change.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "05_manifest" / "records"

OFF_TOPIC = [
    # animals / behaviour of non-human species
    "PMC13548609", "PMC13596745", "PMC13337320", "PMC11730830", "PMC7265895",
    "PMC13067634", "PMC12633744", "PMC12324880", "PMC5132296", "PMC3492235",
    "PMC9841902", "PMC11435589", "PMC12554810",
    # genomics / materials / chemistry
    "PMC12787533", "PMC13312105", "PMC13117339", "PMC12654262", "PMC7747098",
    # drugs / oncology / clinical outcomes with no relationship content
    "PMC13065010", "PMC13083345", "PMC12992163", "PMC13034523", "PMC12582348",
    "PMC13353123", "PMC12444664", "PMC13288318", "PMC13589677", "PMC12387831",
    # workplace / health-service operations
    "PMC13274821", "PMC13279610", "PMC12109310", "PMC12082926", "PMC12766938",
    "PMC13630100",
    # bioinformatics tooling
    "PMC13174251",
    # 2026-10-26 sexuality/astrology facets: biological "asexuality"/"sexual
    # genes", disease-cohort clinical studies, and literal "fortune telling"/
    # "numerology"/"superstition" in non-human or non-relational senses.
    "PMC13309565", "PMC11515122", "PMC12586296", "PMC13134044",
    "PMC7926711", "PMC5025497", "PMC3473186", "PMC12362938",
    "PMC13625963", "PMC12877804", "PMC13361407", "PMC11849308", "PMC13345366",
    "PMC12380638", "PMC13606613", "PMC12539896", "PMC12897203", "PMC8197378",
    "PMC8924775", "PMC8860008", "PMC7970937", "PMC13451936", "PMC13285199",
    "PMC12560306",
    # 2026-10-26 retuned facets: TITLE:"sexual communication" is also an
    # entomology phrase, and a sexual-assertiveness paper turned out to be an
    # HPV prediction model. Both now blocked in fetch_europepmc.py.
    "PMC12770444", "PMC12630469",
]


def delete(pmcid: str) -> bool:
    rec_path = RECORDS / f"epmc_{pmcid}.json"
    if not rec_path.exists():
        print(f"absent: {pmcid}")
        return False
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    for key in ("raw_path", "text_path"):
        rel = rec.get(key)
        if not rel:
            continue
        path = ROOT / rel
        if path.exists():
            path.unlink()
    rec_path.unlink()
    print(f"deleted: {pmcid} | {rec.get('title', '')[:70]}")
    return True


def scanned_hits() -> list[tuple[str, str, str]]:
    """Return (pmcid, pattern_name, title) for records the live filters reject."""
    sys.path.insert(0, str(ROOT / "tools"))
    from fetch_europepmc import (
        ANIMAL_TITLE_RE, HARD_BLOCK_TITLE_RE, MEDICAL_TITLE_RE, MINOR_TITLE_RE,
    )
    checks = (
        ("hard_block", HARD_BLOCK_TITLE_RE),
        ("medical", MEDICAL_TITLE_RE),
        ("animal", ANIMAL_TITLE_RE),
        ("minor", MINOR_TITLE_RE),
    )
    hits: list[tuple[str, str, str]] = []
    for rec_path in sorted(RECORDS.glob("epmc_*.json")):
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        title = rec.get("title", "")
        for name, pattern in checks:
            if pattern.search(title):
                hits.append((rec_path.stem.removeprefix("epmc_"), name, title))
                break
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true", help="re-check records against the live title filters")
    ap.add_argument("--apply", action="store_true", help="delete what the scan finds (default: list only)")
    args = ap.parse_args()

    removed = 0
    if args.scan:
        hits = scanned_hits()
        for pmcid, name, title in hits:
            print(f"{name:10s} {pmcid} | {title[:80]}")
        print(f"\nscan hits={len(hits)} (use --apply to delete)")
        if args.apply:
            for pmcid, _, _ in hits:
                if delete(pmcid):
                    removed += 1
            print(f"removed={removed}")
    else:
        for pmcid in OFF_TOPIC:
            if delete(pmcid):
                removed += 1
    print(f"remaining_epmc_records={len(list(RECORDS.glob('epmc_*.json')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
