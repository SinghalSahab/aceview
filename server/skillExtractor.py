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

# Section headers commonly found in resumes — used to slice the raw text into
# blocks so we can tell "education" text apart from "experience" text instead
# of just dumping every DATE/ORG entity into one bucket.
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


def _split_sections(text: str):
    """
    Very lightweight section splitter: scans line by line, and whenever a
    line matches (case-insensitively, allowing for short lines only — so we
    don't false-positive on a sentence that happens to contain "experience")
    a known header, everything until the next header is bucketed under it.
    """
    lines = text.splitlines()
    sections = {"header": []}
    current = "header"

    header_lookup = {}
    for key, aliases in SECTION_HEADERS.items():
        for alias in aliases:
            header_lookup[alias] = key

    for line in lines:
        stripped = line.strip().lower().strip(":").strip()
        if stripped and len(stripped) < 40 and stripped in header_lookup:
            current = header_lookup[stripped]
            sections.setdefault(current, [])
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


def _extract_years_of_experience(text: str):
    """Look for explicit '5 years of experience' style phrases."""
    match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\s*(?:of)?\s*experience", text, re.I)
    if match:
        return float(match.group(1))
    return None


def parse_resume(text: str) -> dict:
    """
    Main entry point. Given raw resume text (e.g. from PyMuPDF), returns a
    structured dict:

    {
      "name": str,
      "emails": [...],
      "phones": [...],
      "links": {"linkedin": [...], "github": [...], "other": [...]},
      "skills": [str, ...],           # deduped, from the SKILL EntityRuler
      "organizations": [str, ...],    # ORG entities (companies/schools)
      "years_of_experience": float | None,
      "sections": {                   # raw text bucketed by resume section
          "summary": str, "education": str, "experience": str,
          "projects": str, "skills": str, "certifications": str
      },
      "entities": [{"text": str, "label": str}, ...]  # full raw NER dump
    }
    """
    nlp = get_nlp()
    doc = nlp(text)

    skills = sorted({ent.text.strip() for ent in doc.ents if ent.label_ == "SKILL"},
                     key=str.lower)
    organizations = sorted({ent.text.strip() for ent in doc.ents if ent.label_ == "ORG"},
                            key=str.lower)

    result = {
        "name": _guess_name(doc, text),
        "emails": sorted(set(EMAIL_RE.findall(text))),
        "phones": sorted(set(m.strip() for m in PHONE_RE.findall(text) if len(re.sub(r"\D", "", m)) >= 7)),
        "links": {
            "linkedin": sorted(set(LINKEDIN_RE.findall(text))) and _clean_links(LINKEDIN_RE, text),
            "github": _clean_links(GITHUB_RE, text),
            "other": [u for u in sorted(set(URL_RE.findall(text)))
                      if "linkedin.com" not in u and "github.com" not in u],
        },
        "skills": skills,
        "organizations": organizations,
        "years_of_experience": _extract_years_of_experience(text),
        "sections": _split_sections(text),
        "entities": [{"text": ent.text, "label": ent.label_} for ent in doc.ents],
    }
    return result


def _clean_links(pattern: re.Pattern, text: str):
    # re.findall with groups returns tuples; re.finditer keeps the full match.
    return sorted({m.group(0) for m in pattern.finditer(text)})


if __name__ == "__main__":
    sample = """
    Jane Doe
    jane.doe@example.com | +1 (555) 123-4567
    linkedin.com/in/janedoe | github.com/janedoe

    Summary
    Backend engineer with 4 years of experience building distributed systems.

    Skills
    Python, Flask, Docker, Kubernetes, machine learning, PostgreSQL

    Experience
    Backend Engineer, Acme Corp
    Built microservices using Python and Kubernetes.

    Education
    B.S. Computer Science, State University
    """
    import pprint
    pprint.pprint(parse_resume(sample))