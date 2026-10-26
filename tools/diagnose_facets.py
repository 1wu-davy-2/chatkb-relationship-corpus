#!/usr/bin/env python3
"""Show why a Europe PMC facet returns zero candidates.

For every raw search hit of the named facets, print the first gate that rejects
it. This keeps query tuning evidence-based instead of guesswork:

    .venv/Scripts/python.exe tools/diagnose_facets.py barnum_forer birth_date_mate
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("tools").resolve()))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests  # noqa: E402

import fetch_europepmc as fz  # noqa: E402
from query_specs import QUERY_SPECS  # noqa: E402

TARGETS = sys.argv[1:] or ["sex_communication_training", "superstition_decision", "birth_date_mate"]


def verdict(result: dict, spec: dict) -> str:
    title = fz.clean_space(result.get("title", ""))
    abstract = fz.clean_space(result.get("abstractText", ""))
    blob = f"{title} {abstract}".lower()
    if not title:
        return "no title"
    if not fz.license_ok(result.get("license")):
        return f"license={result.get('license') or 'none'}"
    if fz.HARD_BLOCK_TITLE_RE.search(title):
        return f"hard_block:{fz.HARD_BLOCK_TITLE_RE.search(title).group(0)}"
    if fz.MINOR_RE.search(blob):
        return f"minor_blob:{fz.MINOR_RE.search(blob).group(0)}"
    if fz.MINOR_TITLE_RE.search(title):
        return f"minor_title:{fz.MINOR_TITLE_RE.search(title).group(0)}"
    if fz.MEDICAL_TITLE_RE.search(title):
        return f"medical_title:{fz.MEDICAL_TITLE_RE.search(title).group(0)}"
    if fz.ANIMAL_TITLE_RE.search(title):
        return f"animal_title:{fz.ANIMAL_TITLE_RE.search(title).group(0)}"
    if any(term in blob for term in fz.OFF_TOPIC_TERMS):
        return "off_topic_term"
    if not any(a.lower() in blob for a in spec["anchors"]):
        return "no anchor"
    if spec.get("require_romantic", True) and not fz.ROMANTIC_RE.search(blob):
        return "no romantic context"
    if not abstract:
        return "no abstract + no strong title"
    if not fz.STRONG_TITLE_RE.search(title):
        return "weak title (abstract lacks romantic anchor)"
    return "PASS"


def main() -> int:
    session = requests.Session()
    session.headers.update({"User-Agent": fz.USER_AGENT})
    for topic in TARGETS:
        spec = next((s for s in QUERY_SPECS if s["topic"] == topic), None)
        if spec is None:
            print(f"!! unknown facet {topic}")
            continue
        results = fz.search_query(session, topic, spec["q"], 40)
        print(f"\n=== {topic} raw={len(results)}")
        tally = {}
        for r in results:
            v = verdict(r, spec)
            tally[v] = tally.get(v, 0) + 1
            if v == "PASS" or tally[v] <= 3:
                print(f"  [{v}] {fz.clean_space(r.get('title', ''))[:110]}")
        print("  tally:", sorted(tally.items(), key=lambda x: -x[1]))
        time.sleep(0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
