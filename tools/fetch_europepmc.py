#!/usr/bin/env python3
"""Fetch open-access relationship/communication papers from Europe PMC.

Only CC-licensed, full-text, adult-focused papers are kept. Metadata and raw
JATS XML are stored for provenance; clean body text goes to 02_text.
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
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "01_raw" / "europepmc_xml"
TEXT_DIR = ROOT / "02_text" / "europepmc"
RECORD_DIR = ROOT / "05_manifest" / "records"
SEARCH_DIR = ROOT / "05_manifest" / "search"
LOG_PATH = ROOT / "05_manifest" / "fetch_epmc.log"
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
XML_API = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
USER_AGENT = "ChatKBResearch/1.0 (personal study corpus; local use)"

# Each query targets one facet. Anchors are required in title/abstract to stop
# biomedical "relationship" papers (e.g. caregiver studies) leaking into dating.
from query_specs import QUERY_SPECS

MINOR_RE = re.compile(
    r"\b(adolescen\w*|teen\w*|high school|underage|pediatric\w*|middle school|elementary school)\b",
    re.IGNORECASE,
)
MINOR_TITLE_RE = re.compile(
    r"\b(children|child|childhood|infant\w*|toddler\w*|maternal|postpartum|pregnan\w*|parenting)\b",
    re.IGNORECASE,
)
ROMANTIC_RE = re.compile(
    r"\b(romantic\w*|dating|date|couple\w*|marriage|marital|spouse\w*|"
    r"intima\w*|attraction|attractive|courtship|divorce\w*|breakup|break-up|"
    r"flirt\w*|online dating|dating app|mate attraction)\b",
    re.IGNORECASE,
)
STRONG_TITLE_RE = re.compile(
    r"\b(romantic\w*|romance|dating|date|dates|couple|couples|marriage|marital|"
    r"spouse\w*|partner\w*|intimacy|intimate|attraction|attractive|courtship|"
    r"flirt\w*|love|loving|divorce\w*|breakup|break-up|"
    r"relationship satisfaction|relationship quality|relationship well-being|"
    r"relationship maintenance|relationship education|relationship skills|"
    r"relationship anxiety|relationship addiction|relationship sabotage|"
    r"relationship confidence|close relationship|"
    r"singlehood|singles|hookup\w*|casual sex|friends with benefits|"
    r"consensual|sexual consent|sexual communication|sexual satisfaction|"
    r"sexual desire|sexual abuse|sexual violence|sexual assault|sexual harm|"
    r"domestic violence|mate choice|mate preference|mating|cohabit\w*|"
    r"remarri\w*|infidelity|affair|jealousy|ghost\w*|phub\w*|catfish\w*|"
    r"romance scam|romance fraud|pickup artist|seduction community|"
    r"gaslight\w*|coercive control|dating violence|intimate partner violence|"
    r"love bombing|stalking|sexual harassment|attachment style|attachment anxiety|"
    r"attachment avoidance|adult attachment|loneliness|social anxiety|"
    r"self-esteem|body image|emotional intelligence|emotion regulation|"
    r"alexithymia|assertiveness|personal boundaries|boundary setting|"
    r"people-pleasing|codependency|emotional labor|gratitude|forgiveness|"
    r"apology|trust in relationships|commitment|self-disclosure|"
    r"validation|listening|rejection|incel|sugar relationship|"
    r"transactional sex|situationship|marriage squeeze|bride price|dowry|"
    r"matchmaking|blind date|arranged marriage|long-distance relationship|"
    r"intercultural relationship|interracial relationship|online dating|"
    r"dating app|texting|sexting|AI companion|virtual companion|"
    r"first impression|compliment\w*|flattery|praise|gift giving|gift-giving|"
    r"gift exchange|sugar relationship|sugar dating|astrology|zodiac|"
    r"myers-briggs|mbti|self-compassion|shyness|social inhibition|childfree|"
    r"child-free|benevolent sexism|chivalry|conflict\w*|commitment|trust|"
    r"empathy|emotional validation|validation|active listening|"
    r"empathic listening|listening|social skills|interpersonal competence|"
    r"communication competence|conversational skills|capitalization|"
    r"demand-withdraw|repair attempt|communication training|mindfulness|"
    r"widowhood|bereavement|widowed|foodie call|catfishing|"
    # sexuality research (adult, peer-reviewed, communication/health framing)
    r"sexual pleasure|sexual intimacy|sexual scripts?|sexual self-disclosure|"
    r"sexual self-schema|sexual frequency|sexual boredom|sexual regret|"
    r"sexual dissatisfaction|sexual incompatibility|sexual communication|"
    r"safer sex|sex-positive|sex positivity|pornography|porn use|"
    r"asexual\w*|orgasm\w*|sexual dysfunction|hypoactive|"
    r"desire discrepancy|sensate focus|sexless|celibacy|chastity|"
    r"sexual autonomy|sexual agency|affirmative consent|enthusiastic consent|"
    r"sexual gatekeeping|sexual decision-making|sexual assertiveness|"
    # astrology / paranormal belief (studied as belief, not as fact).
    # superstit\w* and astrological\w* because the plain stems missed
    # "superstitious beliefs" and "astrological signs" in otherwise good titles.
    r"horoscope|barnum|forer|numerology|paranormal|superstit\w*|"
    r"divination|fortune-telling|fortune telling|psychic belief|"
    r"chinese zodiac|zodiac sign|astrological\w*|star sign|birth season|"
    r"magical thinking|birth date)\b",
    re.IGNORECASE,
)
MEDICAL_TITLE_RE = re.compile(
    r"\b(alzheimer\w*|dementia|cancer|palliative|caregiver\w*|nursing home|"
    r"parkinson\w*|stroke|hiv|patients?|nurse\w*|nursing|clinician\w*|"
    r"physician\w*|medical student\w*|oncolog\w*)\b",
    re.IGNORECASE,
)
ANIMAL_TITLE_RE = re.compile(
    r"\b(bee|bees|hymenopter\w*|drosophila|chameleon\w*|bird\w*|fish|"
    r"stickleback\w*|insect\w*|moth\w*|butterfl\w*|fungus|fungi|"
    r"nonhuman|non-human|animal\w*|mice|mouse|rats?|zebrafish|spider\w*|"
    r"catfish|beetle\w*|frog\w*|turtle\w*|duck\w*|pigeon\w*|budgerigar\w*|"
    r"warbler\w*|scorpion\w*|primate\w*|monkey\w*|rodent\w*|"
    r"stink bug|aphid\w*|weevil\w*|cockroach\w*|termite\w*|beetle\w*)\b",
    re.IGNORECASE,
)
HARD_BLOCK_TITLE_RE = re.compile(
    r"\b(genom\w*|phylogen\w*|mitogenom\w*|transcriptom\w*|proteom\w*|"
    r"fossil\w*|geolog\w*|zircon\w*|nanoslit\w*|flotation|semaglutide|"
    r"dulaglutide|biologic|jak inhibitor|carcinoma|lymphoma|leukemia|"
    r"melanoma|dementia|alzheimer\w*|parkinson\w*|stroke|copd|asthma|"
    r"epilep\w*|multiple sclerosis|muscular dystrophy|methadone|tuberculosis|"
    r"hepatitis|cardiomyopathy|pharmacist|pharmacy|burnout|"
    r"employee productivity|recommendation network|poultry|cattle|sheep|"
    # non-human senses of "asexual", "sexual", "fortune telling", "numerology".
    # Deliberately narrow: "algae" not "alg\w*" (blocks "algorithms", which
    # appear in dating-app and divorce-prediction papers), and no blanket
    # "bacterial" or "domestication" (STI/dating and couple-imagination studies
    # matched those).
    r"asexual reproduction|sexual-asexual|life cycle trade-offs|fissiparous|"
    r"recombination|lichen\w*|plant|mating type|reproductive mode|dN/dS|"
    r"gene|genes|genetic\w*|"
    r"protein\w*|chromosome\w*|rotifer\w*|plasmodium|conidi\w*|fruiting body|"
    r"directed evolution|allele\w*|mutant\w*|transcription|"
    r"chloroplast|algae|algal|spore\w*|symbiosis|bdelloid|diploid|polyploid|"
    r"offspring|gametocyte\w*|parasite\w*|knockout|virulence|proliferation|"
    # occupational / field populations rather than relational samples
    r"fishers?|fishermen|fishing|"
    # clinical/disease-cohort studies: sexuality is a secondary outcome here
    r"arthroplasty|transplant|bariatric|penectomy|perinatal|endometriosis|"
    r"genital warts|thyroid|overactive bladder|inflammatory bowel|bowel|"
    r"telemonitoring|diabetes|hypertension|cardiovascular|vulnerable plaque|"
    r"trimethylamine|adenocarcinoma|surgical residents?|surgery residents?|"
    r"human papillomavirus|papillomavirus|"
    # engineering senses of "numerology"
    r"5g|wireless|antenna|orthogonal frequency)\b",
    re.IGNORECASE,
)
OFF_TOPIC_TERMS = (
    "hearing loss", "audiology", "tinnitus", "cochlear", "mice", "mouse",
    "rats", "rat ", "zebrafish", "neural correlate", "fmri", "eeg",
    "music training", "language learning", "medication adherence",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("epmc")


def clean_space(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def first_by_localname(root, name: str):
    for el in root.iter():
        if localname(el.tag) == name:
            return el
    return None


def first_text(root, name: str) -> str:
    el = first_by_localname(root, name)
    if el is None:
        return ""
    return clean_space("".join(el.itertext()))


def jats_to_text(xml_bytes: bytes) -> tuple[str, str]:
    parser = etree.XMLParser(recover=True, huge_tree=True, resolve_entities=False)
    root = etree.fromstring(xml_bytes, parser)
    if root is None:
        return "", ""
    title = first_text(root, "article-title")
    abstract = first_text(root, "abstract")
    paragraphs: list[str] = []
    seen: set[str] = set()
    body = first_by_localname(root, "body")
    if body is not None:
        for el in body.iter():
            if localname(el.tag) not in {"p", "title", "list-item", "caption", "disp-quote"}:
                continue
            t = clean_space("".join(el.itertext()))
            if len(t) < 2 or t in seen:
                continue
            seen.add(t)
            paragraphs.append(t)
    parts = []
    if abstract:
        parts.append("ABSTRACT\n" + abstract)
    if paragraphs:
        parts.append("BODY\n" + "\n\n".join(paragraphs))
    return title, "\n\n".join(parts)


def normalize_license(value: str | None) -> str:
    return (value or "").lower().replace("_", " ").replace("-", " ").strip()


def license_ok(value: str | None) -> bool:
    if not value:
        return False
    v = normalize_license(value)
    return v in {"cc by", "cc by sa", "cc by nc", "cc by nc sa", "cc by nc nd", "cc0", "public domain"}


def license_url(value: str | None) -> str:
    v = normalize_license(value)
    mapping = {
        "cc by nc nd": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "cc by nc sa": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "cc by nc": "https://creativecommons.org/licenses/by-nc/4.0/",
        "cc by sa": "https://creativecommons.org/licenses/by-sa/4.0/",
        "cc by": "https://creativecommons.org/licenses/by/4.0/",
        "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
        "public domain": "https://creativecommons.org/publicdomain/mark/1.0/",
    }
    return mapping.get(v, "")


def relevant(result: dict, spec: dict) -> bool:
    title = clean_space(result.get("title", ""))
    abstract = clean_space(result.get("abstractText", ""))
    blob = f"{title} {abstract}".lower()
    if not title:
        return False
    blob = f"{title} {abstract}".lower()
    if not abstract:
        # Many relevant social-science records have no abstract in the search
        # index but do have full text; accept only precise, strong-title hits.
        if not STRONG_TITLE_RE.search(title):
            return False
        if not any(anchor.lower() in blob for anchor in spec["anchors"]):
            return False
    if HARD_BLOCK_TITLE_RE.search(title):
        return False
    if MINOR_RE.search(blob) or MINOR_TITLE_RE.search(title):
        return False
    if MEDICAL_TITLE_RE.search(title) or ANIMAL_TITLE_RE.search(title):
        return False
    if any(term in blob for term in OFF_TOPIC_TERMS):
        return False
    if not any(anchor.lower() in blob for anchor in spec["anchors"]):
        return False
    if spec.get("require_romantic", True) and not ROMANTIC_RE.search(blob):
        return False
    if not STRONG_TITLE_RE.search(title):
        # Generic "relationship between X and Y" papers only pass when the
        # abstract itself carries a clear romantic/dating context.
        if not (re.search(r"\brelationships?\b", title, re.IGNORECASE) and STRONG_TITLE_RE.search(blob)):
            return False
    pub_types = " ".join(
        str(x.get("name", "")) if isinstance(x, dict) else str(x)
        for x in ((result.get("pubTypeList") or {}).get("pubType", []) or [])
    ).lower()
    if any(x in pub_types for x in ("editorial", "comment", "letter", "erratum", "retraction")):
        return False
    return True


def search_query(session: requests.Session, topic: str, query: str, page_size: int) -> list[dict]:
    params = {
        "query": f"({query}) AND OPEN_ACCESS:y",
        "format": "json",
        "resultType": "core",
        "pageSize": page_size,
    }
    for attempt in range(3):
        try:
            resp = session.get(API, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            SEARCH_DIR.mkdir(parents=True, exist_ok=True)
            (SEARCH_DIR / f"{topic}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return data.get("resultList", {}).get("result", []) or []
        except Exception as exc:
            log.warning("search %s failed (%s/3): %s", topic, attempt + 1, exc)
            time.sleep(2 + attempt * 2)
    return []


def existing_record(pmcid: str) -> dict | None:
    path = RECORD_DIR / f"epmc_{pmcid}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def write_record(record: dict) -> None:
    RECORD_DIR.mkdir(parents=True, exist_ok=True)
    path = RECORD_DIR / f"epmc_{record['pmcid']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_one(session: requests.Session, result: dict, topic: str, spec: dict) -> dict | None:
    pmcid = (result.get("pmcid") or "").strip()
    if not pmcid:
        return None
    title = clean_space(result.get("title", ""))
    abstract = clean_space(result.get("abstractText", ""))
    lic = (result.get("license") or "").strip()
    if not (result.get("isOpenAccess") == "Y" and result.get("inEPMC") == "Y"):
        return None
    if not license_ok(lic):
        return None
    if not relevant(result, spec):
        return None

    old = existing_record(pmcid)
    if old:
        topics = sorted(set(old.get("topics", [])) | {topic})
        if topics != old.get("topics"):
            old["topics"] = topics
            write_record(old)
        # A record we already hold is not a new download; returning None keeps
        # --max-papers from being eaten by candidates we previously fetched.
        return None

    xml_url = XML_API.format(pmcid=pmcid)
    try:
        resp = session.get(xml_url, timeout=90)
        if resp.status_code != 200 or len(resp.content) < 1000:
            log.info("skip %s: XML status=%s bytes=%s", pmcid, resp.status_code, len(resp.content))
            return None
        xml_bytes = resp.content
    except Exception as exc:
        log.warning("xml %s failed: %s", pmcid, exc)
        return None

    title_xml, body_text = jats_to_text(xml_bytes)
    if len(body_text) < 3000:
        log.info("skip %s: text too short (%s chars)", pmcid, len(body_text))
        return None
    if title_xml and len(title_xml) > len(title):
        title = title_xml

    year = str(result.get("pubYear") or "").strip()
    journal = clean_space(result.get("journalTitle") or (result.get("bookOrReportDetails") or {}).get("publisher", ""))
    authors = clean_space(result.get("authorString", ""))
    doi = (result.get("doi") or "").strip()
    header = "\n".join(
        [
            f"TITLE: {title}",
            f"AUTHORS: {authors}",
            f"YEAR: {year}",
            f"JOURNAL: {journal}",
            f"DOI: {doi}",
            f"PMCID: {pmcid}",
            f"LICENSE: {lic}",
            f"LICENSE_URL: {license_url(lic)}",
            f"SOURCE: https://europepmc.org/article/PMC/{pmcid}",
            f"TOPICS: {topic}",
            "",
            "---",
            "",
            body_text,
        ]
    )
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"{pmcid}.xml"
    text_path = TEXT_DIR / f"{pmcid}.txt"
    raw_path.write_bytes(xml_bytes)
    text_path.write_text(header, encoding="utf-8")

    record = {
        "doc_id": f"epmc_{pmcid}",
        "source": "europepmc",
        "source_type": "open_access_paper",
        "title": title,
        "authors": authors,
        "year": year,
        "journal": journal,
        "doi": doi,
        "pmcid": pmcid,
        "url": f"https://europepmc.org/article/PMC/{pmcid}",
        "xml_url": xml_url,
        "license": lic,
        "license_url": license_url(lic),
        "language": result.get("language", "en") or "en",
        "topics": [topic],
        "abstract": abstract,
        "raw_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
        "text_path": str(text_path.relative_to(ROOT)).replace("\\", "/"),
        "raw_bytes": len(xml_bytes),
        "text_chars": len(header),
        "raw_sha256": hashlib.sha256(xml_bytes).hexdigest(),
        "text_sha256": hashlib.sha256(header.encode("utf-8")).hexdigest(),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    write_record(record)
    log.info("saved %s | %s chars | %s | %s", pmcid, len(header), lic, title[:80])
    return record


def total_bytes() -> int:
    if not RAW_DIR.exists():
        return 0
    return sum(p.stat().st_size for p in RAW_DIR.glob("*.xml"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-raw-mb", type=float, default=55.0)
    ap.add_argument("--max-papers", type=int, default=420)
    ap.add_argument("--per-query", type=int, default=30)
    ap.add_argument(
        "--only-topics",
        default="",
        help="comma-separated facet names (exact or prefix) to restrict the run",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    specs = QUERY_SPECS
    if args.only_topics:
        wanted = [t.strip() for t in args.only_topics.split(",") if t.strip()]
        specs = [s for s in QUERY_SPECS if any(s["topic"] == w or s["topic"].startswith(w) for w in wanted)]
        missing = sorted({w for w in wanted if not any(s["topic"].startswith(w) for s in QUERY_SPECS)})
        if missing:
            log.warning("unknown topics ignored: %s", ", ".join(missing))
        if not specs:
            log.error("no facets matched --only-topics")
            return 1

    RECORD_DIR.mkdir(parents=True, exist_ok=True)
    SEARCH_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json, application/xml, text/xml, */*"})

    log.info("searching %s queries", len(specs))
    by_query: list[tuple[dict, list[dict]]] = []
    seen_candidates: set[str] = set()
    for idx, spec in enumerate(specs, 1):
        topic = spec["topic"]
        results = search_query(session, topic, spec["q"], args.per_query)
        filtered = []
        for r in results:
            pmcid = (r.get("pmcid") or "").strip()
            if not pmcid or pmcid in seen_candidates:
                continue
            if not (license_ok(r.get("license")) and relevant(r, spec)):
                continue
            seen_candidates.add(pmcid)
            filtered.append(r)
        by_query.append((spec, filtered))
        log.info("[%02d/%02d] %-22s raw=%-3d filtered=%-3d", idx, len(specs), topic, len(results), len(filtered))
        time.sleep(0.3)

    if args.dry_run:
        log.info("dry run: candidates=%d", sum(len(rs) for _, rs in by_query))
        return 0

    # Interleave queries by rank so every facet gets early coverage.
    ordered: list[tuple[dict, dict]] = []
    max_len = max((len(rs) for _, rs in by_query), default=0)
    for rank in range(max_len):
        for spec, results in by_query:
            if rank < len(results):
                ordered.append((spec, results[rank]))

    target = args.target_raw_mb * 1024 * 1024
    downloaded = 0
    for spec, result in ordered:
        if total_bytes() >= target or downloaded >= args.max_papers:
            break
        record = fetch_one(session, result, spec["topic"], spec)
        if record:
            downloaded += 1
        time.sleep(0.25)

    raw_mb = total_bytes() / 1024 / 1024
    text_bytes = sum(p.stat().st_size for p in TEXT_DIR.glob("*.txt")) if TEXT_DIR.exists() else 0
    log.info(
        "done: new=%d records=%d raw=%.1f MB text=%.1f MB",
        downloaded,
        len(list(RECORD_DIR.glob("epmc_*.json"))),
        raw_mb,
        text_bytes / 1024 / 1024,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
