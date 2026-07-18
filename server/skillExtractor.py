"""
skillExtractor.py

spaCy-based structured parsing for resume text extracted via PyMuPDF.

Uses:
- en_core_web_sm for base NLP (tokenization, POS, base NER for PERSON/ORG/GPE/DATE)
- An EntityRuler loaded from skills.jsonl for domain-specific SKILL matching
  (skills.jsonl is a list of {"label": "SKILL", "pattern": [...]} spaCy pattern objects)
- Regex for structured fields spaCy's NER isn't reliable for (email, phone, links)
- Light heuristics for resume sections (education / experience) and candidate name

This module is import-and-reuse: load the spaCy pipeline ONCE at process start
(model loading is slow), then call `parse_resume(text)` per request.
"""

import re
import json
import os
from datetime import datetime
from functools import lru_cache

import spacy
from spacy.pipeline import EntityRuler  # noqa: F401 (kept for clarity / IDEs)

SKILLS_PATTERN_PATH = os.path.join(os.path.dirname(__file__), "skills.jsonl")

# ---------------------------------------------------------------------------
# Regex helpers — spaCy's statistical NER is not reliable for these, so they
# are pulled out separately and merged into the final result.
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?){2,4}\d{3,4})"
)
LINKEDIN_RE = re.compile(r"(https?://)?(www\.)?linkedin\.com/in/[A-Za-z0-9\-_/]+", re.I)
GITHUB_RE = re.compile(r"(https?://)?(www\.)?github\.com/[A-Za-z0-9\-_/]+", re.I)
URL_RE = re.compile(r"https?://[^\s)]+")

# Explicit "5 years of experience" style phrase — checked first, before the
# DATE-entity fallback, since an explicit claim is more reliable than summing
# inferred date ranges.
YEARS_PHRASE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\s*(?:of)?\s*experience", re.I
)

MONTH_RE = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
YEAR_RE = r"(?:19|20)\d{2}"
PRESENT_RE = r"present|current|now|ongoing"

# ---------------------------------------------------------------------------
# Section headers commonly found in resumes — used to slice the raw text into
# blocks so we can tell "education" text apart from "experience" text instead
# of just dumping every DATE/ORG entity into one bucket. This also lets
# downstream GitHub-project matching (Step 5) reason about "projects section"
# vs. "work experience" separately.
# ---------------------------------------------------------------------------
SECTION_HEADERS = {
    "education": ["education", "academic background", "academics"],
    "experience": ["experience", "work experience", "employment history", "professional experience"],
    "projects": ["projects", "personal projects", "academic projects"],
    "skills": ["skills", "technical skills", "core competencies"],
    "certifications": ["certifications", "certificates", "licenses"],
    "summary": ["summary", "objective", "profile"],
}


def _load_skill_patterns(path: str):
    patterns = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            patterns.append(json.loads(line))
    return patterns


@lru_cache(maxsize=1)
def get_nlp():
    """
    Build (once, cached) the spaCy pipeline:
    base en_core_web_sm + EntityRuler seeded with skills.jsonl patterns.

    EntityRuler is inserted BEFORE the statistical `ner` component so exact
    skill patterns (e.g. ".NET", "machine learning") win over/are protected
    from the statistical model on overlapping spans.
    """
    nlp = spacy.load("en_core_web_sm")

    ruler = nlp.add_pipe("entity_ruler", before="ner", config={"overwrite_ents": True})
    ruler.add_patterns(_load_skill_patterns(SKILLS_PATTERN_PATH))

    return nlp


# ---------------------------------------------------------------------------
# Skill normalization — builds a canonical "display casing" map straight from
# skills.jsonl, keyed by a punctuation/space-insensitive lowercase form, so
# skills extracted here can later be cross-referenced 1:1 against
# GitHub-detected languages/skills (ATS scoring + question generation both
# need this to be the same key space).
# ---------------------------------------------------------------------------
def _normalize_key(text: str) -> str:
    """Punctuation/space-insensitive comparison key, e.g. '.NET' and 'net' -> 'net'."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _pattern_tokens_to_text(pattern):
    """
    Reconstruct a display string from a spaCy EntityRuler token pattern.
    Returns (text, has_explicit_casing) — has_explicit_casing is True only
    when the pattern uses a TEXT token (exact string, e.g. {"TEXT": ".NET"}),
    which is the only case where skills.jsonl encodes a real casing/format
    decision. Patterns built only from LOWER tokens (the overwhelming
    majority in skills.jsonl) carry no casing information at all.
    """
    if isinstance(pattern, str):
        return pattern.strip(), True
    parts = []
    has_text_token = False
    for tok in pattern:
        if not isinstance(tok, dict):
            continue
        if "TEXT" in tok:
            parts.append(str(tok["TEXT"]))
            has_text_token = True
        elif "LOWER" in tok:
            parts.append(str(tok["LOWER"]))
    return " ".join(p for p in parts if p).strip(), has_text_token


@lru_cache(maxsize=1)
def get_skill_canonical_map() -> dict:
    """
    key (normalized, e.g. 'net') -> canonical display text (e.g. '.NET')

    Only populated from patterns that explicitly encode casing via a TEXT
    token (e.g. ".NET", "3D", acronym-style entries). skills.jsonl patterns
    built purely from LOWER tokens (the majority — "python", "docker", ...)
    are intentionally left OUT of this map: they carry no real casing intent,
    so for those, normalize_skill() below keeps whatever casing the resume
    itself used rather than forcing everything to lowercase.
    """
    canonical = {}
    for entry in _load_skill_patterns(SKILLS_PATTERN_PATH):
        text, has_explicit_casing = _pattern_tokens_to_text(entry.get("pattern", []))
        if not text or not has_explicit_casing:
            continue
        key = _normalize_key(text)
        if not key:
            continue
        existing = canonical.get(key)
        if existing is None or len(text) > len(existing):
            canonical[key] = text
    return canonical


def normalize_skill(skill_text: str) -> str:
    """
    Public helper — normalize a single skill string (from resume OR GitHub
    language/topic detection) to a canonical display form:
    - If skills.jsonl explicitly encodes casing for this skill (a TEXT-token
      pattern, e.g. ".NET"), use that.
    - Otherwise, keep the casing as it was actually written (in the resume,
      or whatever the caller passed in) rather than flattening to lowercase.
    The normalized KEY (used for dedupe/cross-referencing) is always
    punctuation/space/case-insensitive regardless of which casing is shown.
    """
    key = _normalize_key(skill_text)
    return get_skill_canonical_map().get(key, skill_text.strip())


def _normalize_and_dedupe_skills(raw_skills) -> list:
    """Dedupe by normalized key, keep the canonical casing per key."""
    deduped = {}
    for s in raw_skills:
        s = s.strip()
        if not s:
            continue
        key = _normalize_key(s)
        if not key:
            continue
        deduped[key] = normalize_skill(s)
    return sorted(deduped.values(), key=str.lower)


# ---------------------------------------------------------------------------
# Section splitting
# ---------------------------------------------------------------------------
def _split_sections(text: str):
    """
    Line-by-line section splitter: whenever a line IS a known header (allowing
    for bullet prefixes, ALL CAPS, trailing colon, or a header immediately
    followed by inline content after a colon, e.g. "Skills: Python, SQL"),
    everything from that point is bucketed under that section until the next
    header. Short-line-only matching avoids false-positiving on a sentence
    that happens to contain the word "experience".
    """
    lines = text.splitlines()
    sections = {"header": []}
    current = "header"

    header_lookup = {}
    for key, aliases in SECTION_HEADERS.items():
        for alias in aliases:
            header_lookup[alias] = key

    for line in lines:
        raw = line.strip()
        # strip common bullet/marker prefixes before checking for a header match
        candidate_line = re.sub(r"^[\-\*\u2022\u25CF\u25AA\s]+", "", raw)

        matched_key = None
        inline_rest = ""

        # Case A: the whole (stripped) line is just the header
        plain = candidate_line.lower().rstrip(":").strip()
        if plain and len(plain) < 40 and plain in header_lookup:
            matched_key = header_lookup[plain]

        # Case B: "Header: inline content on the same line"
        elif ":" in candidate_line:
            head_part, rest_part = candidate_line.split(":", 1)
            head_key = head_part.strip().lower()
            if head_key and len(head_key) < 40 and head_key in header_lookup:
                matched_key = header_lookup[head_key]
                inline_rest = rest_part.strip()

        if matched_key:
            current = matched_key
            sections.setdefault(current, [])
            if inline_rest:
                sections[current].append(inline_rest)
            continue

        sections.setdefault(current, []).append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _guess_name(doc, text: str) -> str:
    """
    Heuristic: the candidate's name is almost always the first PERSON entity
    spaCy finds near the top of the document (resume headers put the name
    first). Fall back to the first non-empty line if NER finds nothing.
    """
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()

    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:60]
    return ""


# ---------------------------------------------------------------------------
# Years of experience: explicit phrase first, DATE-entity range summation
# as a fallback (scoped to the Experience section only).
# ---------------------------------------------------------------------------
def _year_from_date_text(text: str, allow_present=False):
    if allow_present and re.search(PRESENT_RE, text, re.I):
        return datetime.now().year + datetime.now().month / 12.0
    m = re.search(YEAR_RE, text)
    if not m:
        return None
    year = int(m.group(0))
    month_m = re.search(MONTH_RE, text, re.I)
    month_offset = 0.0
    if month_m:
        months = ["jan", "feb", "mar", "apr", "may", "jun",
                  "jul", "aug", "sep", "oct", "nov", "dec"]
        mon_str = month_m.group(0)[:3].lower()
        if mon_str in months:
            month_offset = months.index(mon_str) / 12.0
    return year + month_offset


DATE_RANGE_RE = re.compile(
    rf"({MONTH_RE}\.?\s+{YEAR_RE}|{YEAR_RE})\s*(?:-|–|—|to)\s*"
    rf"({MONTH_RE}\.?\s+{YEAR_RE}|{YEAR_RE}|{PRESENT_RE})",
    re.I,
)


def _years_from_regex_ranges(experience_text: str):
    """
    Primary fallback: scan the Experience section text directly for
    "<start> - <end>" style date ranges (the overwhelming majority of resume
    date ranges follow this exact shape) and sum the spans. This is checked
    BEFORE the spaCy DATE-entity pairing fallback below because, in testing,
    en_core_web_sm's statistical NER frequently mis-tags compact bulleted
    date ranges as ORG/PERSON instead of DATE on real resume formatting —
    a direct regex pass over the text is materially more reliable here.
    """
    total_years = 0.0
    ranges_found = 0
    for m in DATE_RANGE_RE.finditer(experience_text):
        start = _year_from_date_text(m.group(1))
        end = _year_from_date_text(m.group(2), allow_present=True)
        if start is None or end is None:
            continue
        span = end - start
        if span < 0:
            continue
        total_years += span if span > 0 else 0.5
        ranges_found += 1
    return round(total_years, 1) if ranges_found else None


def _years_from_date_entities(nlp, experience_text: str):
    """
    Secondary fallback: run spaCy over the Experience section text and pull
    out DATE entities, pairing them sequentially as (start, end) ranges. Only
    used when the regex pass above finds nothing, since DATE-entity tagging
    on short bulleted resume text is noticeably less reliable than a direct
    pattern match. Assumes dates appear in reading order as start/end pairs,
    which holds for the large majority of standard resumes; overlapping
    roles will be over-counted — this is a best-effort estimate, not an
    exact figure.
    """
    if not experience_text.strip():
        return None

    doc = nlp(experience_text)
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    if len(dates) < 2:
        return None

    total_years = 0.0
    ranges_found = 0
    i = 0
    while i < len(dates) - 1:
        start = _year_from_date_text(dates[i])
        end = _year_from_date_text(dates[i + 1], allow_present=True)
        i += 2
        if start is None or end is None:
            continue
        span = end - start
        if span < 0:
            continue
        total_years += span if span > 0 else 0.5
        ranges_found += 1

    return round(total_years, 1) if ranges_found else None


def _extract_years_of_experience(nlp, text: str, experience_section_text: str):
    match = YEARS_PHRASE_RE.search(text)
    if match:
        return float(match.group(1))

    regex_result = _years_from_regex_ranges(experience_section_text)
    if regex_result is not None:
        return regex_result

    return _years_from_date_entities(nlp, experience_section_text)


# ---------------------------------------------------------------------------
# Validation against the Candidate Profile schema (resume sub-object).
# A resume that produces neither a name nor any skills is very likely a
# parsing failure (bad PDF extraction, scanned/image-only resume, etc.) and
# should be flagged/rejected rather than silently treated as a thin profile.
# ---------------------------------------------------------------------------
def validate_parsed_resume(result: dict) -> dict:
    """
    Returns:
      {
        "status": "ok" | "flagged" | "failed",
        "issues": [str, ...]
      }

    - "failed": no name AND no skills detected — almost certainly a parsing
      failure, not a genuinely empty resume. Caller (API layer) should reject
      this rather than passing it downstream.
    - "flagged": one of name/skills/raw text is missing or unusually thin —
      still usable, but worth a manual look.
    - "ok": passes baseline checks.
    """
    issues = []

    has_name = bool(result.get("name"))
    has_skills = bool(result.get("skills"))
    raw_text = result.get("raw_text", "") or ""

    if not has_name:
        issues.append("no name detected")
    if not has_skills:
        issues.append("no skills detected")
    if len(raw_text.strip()) < 50:
        issues.append("extracted text is unusually short (possible scanned/image-only PDF)")
    if not result.get("emails"):
        issues.append("no email address detected")

    if not has_name and not has_skills:
        status = "failed"
    elif issues:
        status = "flagged"
    else:
        status = "ok"

    return {"status": status, "issues": issues}


def parse_resume(text: str) -> dict:
    """
    Main entry point. Given raw resume text (e.g. from PyMuPDF), returns a
    structured dict:

    {
      "name": str,
      "raw_text": str,
      "emails": [...],
      "phones": [...],
      "links": {"linkedin": [...], "github": [...], "other": [...]},
      "skills": [str, ...],           # deduped + normalized to skills.jsonl canonical casing
      "organizations": [str, ...],    # ORG entities (companies/schools)
      "years_of_experience": float | None,
      "sections": {                   # raw text bucketed by resume section
          "summary": str, "education": str, "experience": str,
          "projects": str, "skills": str, "certifications": str
      },
      "entities": [{"text": str, "label": str}, ...],  # full raw NER dump
      "validation": {"status": "ok"|"flagged"|"failed", "issues": [...]}
    }
    """
    nlp = get_nlp()
    doc = nlp(text)

    sections = _split_sections(text)

    raw_skills = {ent.text.strip() for ent in doc.ents if ent.label_ == "SKILL"}
    skills = _normalize_and_dedupe_skills(raw_skills)

    organizations = sorted({ent.text.strip() for ent in doc.ents if ent.label_ == "ORG"},
                            key=str.lower)

    result = {
        "name": _guess_name(doc, text),
        "raw_text": text,
        "emails": sorted(set(EMAIL_RE.findall(text))),
        "phones": sorted(set(m.strip() for m in PHONE_RE.findall(text) if len(re.sub(r"\D", "", m)) >= 7)),
        "links": {
            "linkedin": _clean_links(LINKEDIN_RE, text),
            "github": _clean_links(GITHUB_RE, text),
            "other": [u for u in sorted(set(URL_RE.findall(text)))
                      if "linkedin.com" not in u and "github.com" not in u],
        },
        "skills": skills,
        "organizations": organizations,
        "years_of_experience": _extract_years_of_experience(nlp, text, sections.get("experience", "")),
        "sections": sections,
        "entities": [{"text": ent.text, "label": ent.label_} for ent in doc.ents],
    }
    result["validation"] = validate_parsed_resume(result)
    return result


def _clean_links(pattern: re.Pattern, text: str):
    return sorted({m.group(0) for m in pattern.finditer(text)})


if __name__ == "__main__":
    sample = """
    Jane Doe
    jane.doe@example.com | +1 (555) 123-4567
    linkedin.com/in/janedoe | github.com/janedoe

    Summary
    Backend engineer with distributed systems experience.

    Skills: Python, Flask, Docker, Kubernetes, machine learning, PostgreSQL

    Experience
    Backend Engineer, Acme Corp
    Jan 2021 - Present
    Built microservices using Python and Kubernetes.

    Software Engineer Intern, StartCo
    Jun 2019 - Aug 2020
    Worked on internal tooling.

    Education
    B.S. Computer Science, State University
    """
    import pprint
    pprint.pprint(parse_resume(sample))