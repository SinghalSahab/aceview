"""
skillExtractor.py

spaCy-based structured parsing for resume text extracted via PyMuPDF.

Uses:
- en_core_web_sm for base NLP (tokenization, POS, base NER for PERSON/ORG/GPE/DATE)
- An EntityRuler loaded from skills.jsonl + a supplementary in-code tech-term
  pattern list for domain-specific SKILL matching
- Regex for structured fields spaCy's NER isn't reliable for (email, phone)
- Position/hyperlink-aware link extraction (see LINKS section) — PDF resumes
  almost always embed URLs as invisible link annotations behind short anchor
  text ("GitHub", "Live"), not as literal visible URL text, so plain text
  extraction alone can never find them; this module optionally accepts a
  `layout` argument (word bboxes + link annotations, built in app.py from
  fitz) to resolve those links and attribute each one to a section/project.
- Light heuristics for resume sections (education / experience / achievements
  / etc.) and candidate name

This module is import-and-reuse: load the spaCy pipeline ONCE at process start
(model loading is slow), then call `parse_resume(text, layout=...)` per request.
"""

import re
import json
import os
from collections import defaultdict
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

YEARS_PHRASE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\s*(?:of)?\s*experience", re.I
)

MONTH_RE = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
YEAR_RE = r"(?:19|20)\d{2}"
PRESENT_RE = r"present|current|now|ongoing"

DATE_RANGE_RE = re.compile(
    rf"({MONTH_RE}\.?\s+{YEAR_RE}|{YEAR_RE})\s*(?:-|–|—|to)\s*"
    rf"({MONTH_RE}\.?\s+{YEAR_RE}|{YEAR_RE}|{PRESENT_RE})",
    re.I,
)

# ---------------------------------------------------------------------------
# Section headers. Extended with achievement/award/publication/etc. aliases
# (a common gap: without these, that content silently got merged into
# whatever section happened to precede it — e.g. "Achievements" bullets
# ending up inside "skills").
# ---------------------------------------------------------------------------
SECTION_HEADERS = {
    "education": ["education", "academic background", "academics"],
    "experience": ["experience", "work experience", "employment history", "professional experience"],
    "projects": ["projects", "personal projects", "academic projects"],
    "skills": ["skills", "technical skills", "core competencies"],
    "certifications": ["certifications", "certificates", "licenses"],
    "summary": ["summary", "objective", "profile"],
    "achievements": ["achievements", "accomplishments", "awards", "honors", "honours"],
    "publications": ["publications"],
    "leadership": ["leadership", "leadership experience"],
    "volunteer": ["volunteer", "volunteering", "volunteer experience", "community involvement"],
    "extracurricular": ["extracurricular", "extra-curricular", "activities", "extracurricular activities"],
    "languages_spoken": ["languages spoken", "spoken languages"],
    "interests": ["interests", "hobbies"],
    "references": ["references"],
}

# Sections where sub-entry titles (job titles, school names, project names)
# commonly look header-like (short, Title Case) but must NOT be treated as
# new top-level sections — only known headers can end these sections.
_NO_GENERIC_SPLIT_SECTIONS = {"header", "experience", "education", "projects"}

# Marker lines inside a Projects block that are never a project title
# themselves (link-anchor lines like "Live", "GitHub", or combined "Live
# GitHub" on one physical line, plus the "Technologies:" summary line).
_PROJECT_LINK_MARKER_WORDS = {"live", "github", "demo", "code", "view", "source", "repo", "link", "url"}


def _is_project_marker_line(plain: str) -> bool:
    """True if every word on the line is a link-anchor marker word (e.g.
    'live', 'github', or both together as 'live github') rather than an
    actual project title — checked word-by-word since PyMuPDF groups
    multiple adjacent short words (like "Live" and "GitHub") onto a single
    line, so an exact whole-string match against a single marker word would
    miss the combined case entirely."""
    if not plain:
        return False
    if plain.startswith("technologies"):
        return True
    words = plain.split()
    return bool(words) and all(w in _PROJECT_LINK_MARKER_WORDS for w in words)


# ---------------------------------------------------------------------------
# Supplementary SKILL patterns.
#
# skills.jsonl is the primary, user-owned source of truth for SKILL patterns
# and is never modified here. But any term not covered by it falls through
# to spaCy's generic statistical NER, which frequently mis-tags common tech
# acronyms/tools as ORG, PERSON, GPE, or NORP (e.g. "JWT" -> ORG, "RAG" ->
# PERSON, "Monaco" -> NORP, "LangChain" -> ORG). Because the EntityRuler
# below is inserted BEFORE the statistical `ner` component, any span it
# claims is left alone by `ner` entirely — so adding a term here is what
# actually fixes both problems at once: the term stops polluting
# organizations/other labels, AND it starts showing up correctly in the
# `skills` array. Extend this list over time as new gaps show up.
# ---------------------------------------------------------------------------
def _text_pattern(*tokens):
    return [{"TEXT": t} for t in tokens]


def _lower_pattern(*tokens):
    return [{"LOWER": t.lower()} for t in tokens]


SUPPLEMENTARY_SKILL_PATTERNS = [
    {"label": "SKILL", "pattern": _text_pattern("JWT")},
    {"label": "SKILL", "pattern": _text_pattern("RDS")},
    {"label": "SKILL", "pattern": _text_pattern("S3")},
    {"label": "SKILL", "pattern": _text_pattern("EC2")},
    {"label": "SKILL", "pattern": _text_pattern("IAM")},
    {"label": "SKILL", "pattern": _text_pattern("Amplify")},
    {"label": "SKILL", "pattern": _text_pattern("Cognito")},
    {"label": "SKILL", "pattern": _text_pattern("PM2")},
    {"label": "SKILL", "pattern": _text_pattern("AWS")},
    {"label": "SKILL", "pattern": _text_pattern("WebContainers")},
    {"label": "SKILL", "pattern": _text_pattern("WebSockets")},
    {"label": "SKILL", "pattern": _lower_pattern("websocket")},
    {"label": "SKILL", "pattern": _text_pattern("LangChain")},
    {"label": "SKILL", "pattern": _text_pattern("LangGraph")},
    {"label": "SKILL", "pattern": _text_pattern("Monaco", "Editor")},
    {"label": "SKILL", "pattern": _text_pattern("Monaco")},
    {"label": "SKILL", "pattern": _text_pattern("Pinecone")},
    {"label": "SKILL", "pattern": _text_pattern("RAG")},
    {"label": "SKILL", "pattern": _lower_pattern("retrieval-augmented", "generation")},
    {"label": "SKILL", "pattern": _lower_pattern("ai", "agents")},
    {"label": "SKILL", "pattern": _lower_pattern("vector", "databases")},
    {"label": "SKILL", "pattern": _lower_pattern("vector", "database")},
    {"label": "SKILL", "pattern": _text_pattern("OpenAI")},
    {"label": "SKILL", "pattern": _lower_pattern("gemini")},
    {"label": "SKILL", "pattern": _text_pattern("OAuth")},
    {"label": "SKILL", "pattern": _text_pattern("CI/CD")},
    {"label": "SKILL", "pattern": _text_pattern("CI")},
    {"label": "SKILL", "pattern": _text_pattern("DSA")},
    {"label": "SKILL", "pattern": _text_pattern("Golang")},
    {"label": "SKILL", "pattern": _text_pattern("MERN")},
    {"label": "SKILL", "pattern": _text_pattern("Express.js")},
    {"label": "SKILL", "pattern": _lower_pattern("express", "js")},
    {"label": "SKILL", "pattern": _text_pattern("GitHub", "Actions")},
    {"label": "SKILL", "pattern": _text_pattern("Zoom")},
    {"label": "SKILL", "pattern": _lower_pattern("restful", "apis")},
    {"label": "SKILL", "pattern": _lower_pattern("restful", "api")},
]


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
    base en_core_web_sm + EntityRuler seeded with skills.jsonl patterns +
    SUPPLEMENTARY_SKILL_PATTERNS.

    EntityRuler is inserted BEFORE the statistical `ner` component. spaCy's
    ner treats tokens already covered by an existing entity span as resolved
    and skips them — it will not attempt to relabel them — so any term
    matched here is protected from ORG/PERSON/GPE/NORP mis-tagging.
    """
    nlp = spacy.load("en_core_web_sm")

    ruler = nlp.add_pipe("entity_ruler", before="ner", config={"overwrite_ents": True})
    ruler.add_patterns(_load_skill_patterns(SKILLS_PATTERN_PATH))
    ruler.add_patterns(SUPPLEMENTARY_SKILL_PATTERNS)

    return nlp


# ---------------------------------------------------------------------------
# Skill normalization
# ---------------------------------------------------------------------------
def _normalize_key(text: str) -> str:
    """Punctuation/space-insensitive comparison key, e.g. '.NET' and 'net' -> 'net'."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _pattern_tokens_to_text(pattern):
    """
    Reconstruct a display string from a spaCy EntityRuler token pattern.
    Returns (text, has_explicit_casing) — has_explicit_casing is True only
    when the pattern uses a TEXT token (exact string), the only case where a
    pattern actually encodes a real casing/format decision. Patterns built
    purely from LOWER tokens carry no casing information.
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
    key (normalized) -> canonical display text, built ONLY from patterns that
    explicitly encode casing via a TEXT token (from skills.jsonl AND
    SUPPLEMENTARY_SKILL_PATTERNS). Patterns built purely from LOWER tokens
    are left out so normalize_skill() keeps the resume's own casing for
    those instead of flattening everything to lowercase.
    """
    canonical = {}
    all_patterns = _load_skill_patterns(SKILLS_PATTERN_PATH) + SUPPLEMENTARY_SKILL_PATTERNS
    for entry in all_patterns:
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
    Normalize a single skill string (from resume NER, the deterministic
    skills-section parse, or GitHub language/topic detection later) to a
    canonical display form where one is known; otherwise keep the casing as
    written. The normalized KEY (used for dedupe/cross-referencing) is
    always punctuation/space/case-insensitive regardless of display casing.
    """
    key = _normalize_key(skill_text)
    return get_skill_canonical_map().get(key, skill_text.strip())


_HEADER_ALIAS_KEYS = {
    _normalize_key(alias) for aliases in SECTION_HEADERS.values() for alias in aliases
}


def _normalize_and_dedupe_skills(raw_skills) -> list:
    deduped = {}
    for s in raw_skills:
        s = s.strip()
        if not s or len(s) > 60:
            continue
        key = _normalize_key(s)
        if not key or key in _SKILL_LABEL_STOPWORDS:
            # structural category-label words (e.g. "Technical Skills",
            # "Languages") sometimes get matched as if they were themselves
            # a skill — these are section/category labels, not real skills.
            continue
        deduped[key] = normalize_skill(s)
    return sorted(deduped.values(), key=str.lower)


def _extract_skills_from_skills_section(skills_section_text: str) -> list:
    """
    Deterministic extraction directly from the Skills section text: resumes
    almost always list skills as "<Category>: term, term, term" per
    line/bullet, sometimes with a parenthetical sub-list like
    "AWS (EC2, RDS, S3, Amplify, Cognito)". NER (even with the supplementary
    patterns above) can still miss terms neither list anticipated, so this
    pass acts as a comprehensive floor — it's what actually closes the
    "skills section lists everything, but the skills array is missing half
    of it" gap, rather than relying purely on catching every possible term
    via patterns.
    """
    if not skills_section_text.strip():
        return []
    terms = []
    for line in skills_section_text.splitlines():
        line = re.sub(r"^[\-\*\u2022\u25CF\u25AA\s]+", "", line).strip()
        if not line:
            continue
        if ":" in line:
            _, line = line.split(":", 1)

        # Harvest parenthetical sub-lists as their own terms BEFORE the main
        # comma split, so "AWS (EC2, RDS, S3)" yields "AWS", "EC2", "RDS",
        # "S3" rather than a naive split producing a mangled "AWS (EC2"
        # chunk (the comma inside the parens would otherwise be treated as
        # a top-level separator).
        def _harvest_parens(m):
            for sub in m.group(1).split(","):
                sub = sub.strip()
                if sub:
                    terms.append(sub)
            return " "

        line = re.sub(r"\(([^)]*)\)", _harvest_parens, line)

        for chunk in line.split(","):
            chunk = chunk.strip().strip(".")
            if chunk and len(chunk) <= 40:
                terms.append(chunk)
    return terms


# ---------------------------------------------------------------------------
# Organization cleanup — drops NER false positives (bullet-prefixed
# fragments like "• Owned", roman-numeral class levels like "XII") that are
# neither real organizations nor skills, and trims trailing month tokens
# that sometimes get swept into an ORG span (e.g. "... Technology Jul").
# ---------------------------------------------------------------------------
_ORG_NOISE_PREFIXES = ("•", "-", "*", "◦")
_ROMAN_NUMERAL_RE = re.compile(r"^(?:I{1,3}|IV|VI{0,3}|IX|XI{0,3}|XIV|XV)$")
_TRAILING_MONTH_RE = re.compile(rf"\s+{MONTH_RE}\.?$", re.I)


def _clean_organizations(raw_orgs):
    cleaned = set()
    for org in raw_orgs:
        stripped = org.strip()
        if not stripped:
            continue
        # NER spans occasionally cross line boundaries and sweep up
        # unrelated following lines (e.g. "Acme Corp\nJan 2021 - Present\n
        # Projects") — the real org name is reliably the first line only.
        stripped = stripped.split("\n")[0].strip()
        if not stripped:
            continue
        if stripped.startswith(_ORG_NOISE_PREFIXES):
            continue  # bullet-fragment NER false positive, not a real entity
        if _ROMAN_NUMERAL_RE.match(stripped):
            continue  # e.g. "XII" from "Class XII" — not an organization
        stripped = _TRAILING_MONTH_RE.sub("", stripped).strip()
        if not stripped:
            continue
        cleaned.add(stripped)
    return sorted(cleaned, key=str.lower)


# ---------------------------------------------------------------------------
# Section splitting (string-only fallback, used when no PDF layout/position
# data is available — e.g. plain-text input).
# ---------------------------------------------------------------------------
def _header_lookup():
    lookup = {}
    for key, aliases in SECTION_HEADERS.items():
        for alias in aliases:
            lookup[alias] = key
    return lookup


def _looks_like_header_line(clean_line: str) -> bool:
    """
    Generic section-header heuristic for headings not in SECTION_HEADERS.

    Deliberately requires ALL CAPS rather than "Title Case, few words" — an
    earlier version accepted Title Case too, but that false-positived on
    short plain entries that merely happen to look header-like (e.g. a
    degree/grade line like "Class XII CBSE", or a short company name).
    ALL CAPS is a much less ambiguous signal for an actual section header in
    plain resume text. The trade-off: a genuinely novel Title-Case heading
    not already in SECTION_HEADERS won't be auto-detected — extend
    SECTION_HEADERS with new aliases as real gaps are found instead of
    loosening this check back up.
    """
    if not clean_line or len(clean_line) > 40:
        return False
    if clean_line.startswith(("-", "*", "\u2022", "\u25CF", "\u25AA")):
        return False
    if clean_line.endswith((".", ",", ";")):
        return False
    if ":" in clean_line:
        return False
    words = clean_line.split()
    if not (1 <= len(words) <= 4):
        return False
    letters_only = re.sub(r"[^A-Za-z]", "", clean_line)
    if len(letters_only) < 3:
        return False
    return clean_line.isupper()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _looks_like_project_title(clean_line: str) -> bool:
    """
    Lenient title heuristic used ONLY inside the Projects section (a much
    narrower, safer context than general header detection — we already know
    we're inside "projects", so a short non-bullet, non-marker line is
    almost always a project name). Unlike _looks_like_header_line, this
    allows Title Case, since project titles are conventionally Title Case
    rather than ALL CAPS.
    """
    if not clean_line or len(clean_line) > 60:
        return False
    if clean_line.startswith(("-", "*", "\u2022", "\u25CF", "\u25AA")):
        return False
    if ":" in clean_line:
        return False
    words = clean_line.split()
    if not (1 <= len(words) <= 8):
        return False
    return True


# Category-LABEL words that sometimes get matched as if they were a skill in
# their own right (e.g. the literal word "Languages" heading a programming-
# languages sub-list, or "Technical Skills" itself). Kept separate from
# _HEADER_ALIAS_KEYS (which controls section *splitting* further below)
# because a word can need different treatment for splitting vs. for being
# filtered out of the skills array.
_SKILL_LABEL_STOPWORDS = {
    _normalize_key(w) for w in [
        "languages", "language", "skills", "technical skills", "technologies",
        "tools", "frameworks", "databases", "database", "cloud", "frontend",
        "backend", "devops", "generative ai", "core competencies",
    ]
}


def _split_sections(text: str):
    """
    String-only section splitter (no position data). Known headers always
    start a new section. Elsewhere — except inside header/experience/
    education/projects, where sub-entry titles look header-like but aren't —
    a generic header-looking line starts a new, dynamically-named section,
    so an unanticipated heading (anything not in SECTION_HEADERS) still gets
    its own bucket instead of being silently absorbed into whatever came
    before it.
    """
    lookup = _header_lookup()
    lines = text.splitlines()
    sections = {"header": []}
    current = "header"

    for line in lines:
        raw = line.strip()
        candidate = re.sub(r"^[\-\*\u2022\u25CF\u25AA\s]+", "", raw)
        plain = candidate.lower().rstrip(":").strip()

        if plain and len(plain) < 40 and plain in lookup:
            current = lookup[plain]
            sections.setdefault(current, [])
            continue

        if ":" in candidate:
            head_part, rest_part = candidate.split(":", 1)
            head_key = head_part.strip().lower()
            if head_key and len(head_key) < 40 and head_key in lookup:
                current = lookup[head_key]
                sections.setdefault(current, [])
                rest_part = rest_part.strip()
                if rest_part:
                    sections[current].append(rest_part)
                continue

        if current not in _NO_GENERIC_SPLIT_SECTIONS and _looks_like_header_line(candidate):
            key = _slugify(candidate)
            if key:
                current = key
                sections.setdefault(current, [])
                continue

        sections.setdefault(current, []).append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


# ---------------------------------------------------------------------------
# Position-aware section + project assignment (used when PDF layout data
# IS available). Mirrors the logic of _split_sections above but operates on
# word-grouped lines carrying (x, y) bounding boxes, which is what lets link
# annotations be attributed to the right section/project by position.
# ---------------------------------------------------------------------------
def _words_to_lines(words):
    grouped = defaultdict(list)
    for w in words:
        grouped[(w["page"], w["block"], w["line"])].append(w)
    lines = []
    for key, ws in grouped.items():
        ws_sorted = sorted(ws, key=lambda w: w["word_no"])
        text = " ".join(w["text"] for w in ws_sorted)
        lines.append({
            "text": text,
            "x0": min(w["x0"] for w in ws_sorted),
            "x1": max(w["x1"] for w in ws_sorted),
            "y0": min(w["y0"] for w in ws_sorted),
            "y1": max(w["y1"] for w in ws_sorted),
            "words": ws_sorted,
        })
    lines.sort(key=lambda l: (l["y0"], l["x0"]))
    return lines


def _assign_sections_positioned(lines):
    """
    Position-aware counterpart of _split_sections: same header-matching
    rules, but each line also gets tagged with the y-position it starts at
    (needed to later map a hyperlink's position to a section) and, while
    inside "projects", with the currently-active project title so each
    project's links can be grouped separately. A header line itself is
    still tagged (so a link that happens to sit on that same line still
    resolves to the right section) but marked is_header=True so
    _sections_dict_from_tagged excludes its own text from the section body.
    """
    lookup = _header_lookup()
    tagged = []
    current = "header"
    current_project = None

    for line in lines:
        raw = line["text"].strip()
        candidate = re.sub(r"^[\-\*\u2022\u25CF\u25AA\s]+", "", raw)
        plain = candidate.lower().rstrip(":").strip()

        if plain and len(plain) < 40 and plain in lookup:
            current = lookup[plain]
            current_project = None
            tagged.append({**line, "section": current, "project": None, "is_header": True})
            continue

        if ":" in candidate:
            head_part, rest_part = candidate.split(":", 1)
            head_key = head_part.strip().lower()
            if head_key and len(head_key) < 40 and head_key in lookup:
                current = lookup[head_key]
                current_project = None
                rest_part = rest_part.strip()
                tagged.append({**line, "text": rest_part, "section": current,
                                "project": None, "is_header": not rest_part})
                continue

        if current == "projects":
            is_marker = _is_project_marker_line(plain)
            if not is_marker and not candidate.startswith(("•", "-", "*")) and _looks_like_project_title(candidate):
                current_project = candidate
            tagged.append({**line, "section": "projects", "project": current_project, "is_header": False})
            continue

        if current not in _NO_GENERIC_SPLIT_SECTIONS and _looks_like_header_line(candidate):
            key = _slugify(candidate)
            if key:
                current = key
                current_project = None
                tagged.append({**line, "section": current, "project": None, "is_header": True})
                continue

        tagged.append({**line, "section": current, "project": current_project, "is_header": False})

    return tagged


def _sections_dict_from_tagged(tagged_lines):
    buckets = {}
    for tl in tagged_lines:
        if tl.get("is_header"):
            buckets.setdefault(tl["section"], [])
            continue
        buckets.setdefault(tl["section"], []).append(tl["text"])
    return {k: "\n".join(v).strip() for k, v in buckets.items()}


# ---------------------------------------------------------------------------
# Link resolution
# ---------------------------------------------------------------------------
def _classify_link(uri: str) -> str:
    low = uri.lower()
    if "linkedin.com" in low:
        return "linkedin"
    if "github.com" in low:
        return "github"
    return "other"


def _nearest_word(words, link):
    """Anchor-text lookup: the word whose bbox overlaps the link rect most; falls back to nearest by center distance."""
    best, best_overlap = None, 0.0
    for w in words:
        ox = max(0.0, min(w["x1"], link["x1"]) - max(w["x0"], link["x0"]))
        oy = max(0.0, min(w["y1"], link["y1"]) - max(w["y0"], link["y0"]))
        overlap = ox * oy
        if overlap > best_overlap:
            best_overlap, best = overlap, w
    if best is not None:
        return best["text"]
    if not words:
        return ""
    lcx, lcy = (link["x0"] + link["x1"]) / 2, (link["y0"] + link["y1"]) / 2
    return min(words, key=lambda w: ((w["x0"] + w["x1"]) / 2 - lcx) ** 2 + ((w["y0"] + w["y1"]) / 2 - lcy) ** 2)["text"]


def _resolve_positioned_links(layout, tagged_lines):
    all_words = [w for page in layout for w in page["words"]]
    all_links = [l for page in layout for l in page["links"]]
    sorted_lines = sorted(tagged_lines, key=lambda l: l["y0"])

    resolved = []
    for link in all_links:
        anchor = _nearest_word(all_words, link)
        link_cy = (link["y0"] + link["y1"]) / 2

        owning_line = None
        for tl in sorted_lines:
            if tl["y0"] <= link_cy + 2:
                owning_line = tl
            else:
                break

        resolved.append({
            "url": link["uri"],
            "anchor": anchor,
            "type": _classify_link(link["uri"]),
            "section": owning_line["section"] if owning_line else "header",
            "project": owning_line["project"] if owning_line else None,
        })
    return resolved


def _build_links_output(text, layout, tagged_lines):
    """
    Returns:
      {
        "linkedin": [...], "github": [...], "other": [...],
        "by_section": {section_key: [{url, anchor, type}, ...]},
        "projects": [{"project": name, "github": url|None, "live": url|None, "other": [...]}]
      }

    When `layout` (word bboxes + hyperlink annotations from the PDF) is
    available, links are resolved by position — this is the ONLY reliable
    path, since resume URLs are almost always PDF link annotations behind
    plain anchor words ("GitHub", "Live") rather than literal visible URL
    text. Without layout (plain-text-only input), falls back to regex
    matching literal URLs in the text, which will find nothing for
    annotation-based links — this is a known, unavoidable limitation of
    text-only input, not a bug in the regex.
    """
    if layout:
        resolved = _resolve_positioned_links(layout, tagged_lines)
    else:
        resolved = []
        for pattern, ltype in ((LINKEDIN_RE, "linkedin"), (GITHUB_RE, "github")):
            for url in _clean_links(pattern, text):
                resolved.append({"url": url, "anchor": "", "type": ltype, "section": None, "project": None})
        for url in sorted(set(URL_RE.findall(text))):
            if "linkedin.com" not in url and "github.com" not in url:
                resolved.append({"url": url, "anchor": "", "type": "other", "section": None, "project": None})

    linkedin = sorted({r["url"] for r in resolved if r["type"] == "linkedin"})
    github = sorted({r["url"] for r in resolved if r["type"] == "github"})
    other = sorted({r["url"] for r in resolved if r["type"] == "other"})

    by_section = {}
    for r in resolved:
        sec = r["section"] or "unknown"
        by_section.setdefault(sec, []).append({"url": r["url"], "anchor": r["anchor"], "type": r["type"]})

    projects_out = {}
    for r in resolved:
        if r["section"] == "projects" and r["project"]:
            proj = projects_out.setdefault(
                r["project"], {"project": r["project"], "github": None, "live": None, "other": []}
            )
            anchor_lower = (r["anchor"] or "").lower()
            if r["type"] == "github":
                proj["github"] = r["url"]
            elif "live" in anchor_lower or "demo" in anchor_lower:
                proj["live"] = r["url"]
            else:
                proj["other"].append(r["url"])

    return {
        "linkedin": linkedin,
        "github": github,
        "other": other,
        "by_section": by_section,
        "projects": list(projects_out.values()),
    }


def _clean_links(pattern: re.Pattern, text: str):
    return sorted({m.group(0) for m in pattern.finditer(text)})


# ---------------------------------------------------------------------------
# Name / years-of-experience (unchanged logic from the previous version)
# ---------------------------------------------------------------------------
def _guess_name(doc, text: str) -> str:
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:60]
    return ""


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
        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        mon_str = month_m.group(0)[:3].lower()
        if mon_str in months:
            month_offset = months.index(mon_str) / 12.0
    return year + month_offset


def _years_from_regex_ranges(experience_text: str):
    total_years, ranges_found = 0.0, 0
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
    if not experience_text.strip():
        return None
    doc = nlp(experience_text)
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    if len(dates) < 2:
        return None
    total_years, ranges_found = 0.0, 0
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
# Validation (unchanged from the previous version)
# ---------------------------------------------------------------------------
def validate_parsed_resume(result: dict) -> dict:
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


def _extract_summary(sections: dict, text: str) -> str:
    for key in ("summary", "objective", "profile", "about", "professional_summary", "executive_summary"):
        if key in sections and sections[key].strip():
            return sections[key].strip()
    return ""


def _extract_structured_projects(sections: dict, links: dict, all_skills: list[str]) -> list[dict]:
    projects_text = (
        sections.get("projects")
        or sections.get("personal_projects")
        or sections.get("academic_projects")
        or ""
    ).strip()

    link_projects = {p.get("project"): p for p in links.get("projects", []) if p.get("project")}

    if not projects_text and not link_projects:
        return []

    blocks = [b.strip() for b in re.split(r"\n\s*\n", projects_text) if b.strip()]
    if not blocks and projects_text:
        blocks = [projects_text]

    extracted_projects = []
    seen_titles = set()

    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        first_line = lines[0]
        title_candidate = re.sub(r"^[\-\*\u2022\u25CF\u25AA\s]+", "", first_line)
        title_candidate = re.sub(r"\s*\(?\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{4}).*$", "", title_candidate, flags=re.I).strip()
        title = title_candidate if len(title_candidate) < 60 else lines[0][:60]

        block_lower = block.lower()
        proj_techs = [s for s in all_skills if re.search(rf"\b{re.escape(s.lower())}\b", block_lower)]

        matched_link = link_projects.get(title) or link_projects.get(first_line)
        github_url = matched_link.get("github") if matched_link else None
        live_url = matched_link.get("live") if matched_link else None

        desc_lines = lines[1:] if len(lines) > 1 else lines
        desc = "\n".join(desc_lines).strip()

        extracted_projects.append({
            "title": title,
            "description": desc,
            "skills": proj_techs[:8],
            "technologies": proj_techs[:8],
            "github": github_url,
            "live": live_url,
            "url": live_url or github_url or None,
        })
        seen_titles.add(title.lower())

    for p_name, p_data in link_projects.items():
        if p_name and p_name.lower() not in seen_titles:
            extracted_projects.append({
                "title": p_name,
                "description": "",
                "skills": [],
                "technologies": [],
                "github": p_data.get("github"),
                "live": p_data.get("live"),
                "url": p_data.get("live") or p_data.get("github"),
            })

    return extracted_projects


def _extract_structured_experience(sections: dict, organizations: list[str]) -> list[dict]:
    exp_text = (
        sections.get("experience")
        or sections.get("work_experience")
        or sections.get("professional_experience")
        or sections.get("employment_history")
        or ""
    ).strip()

    if not exp_text:
        return []

    blocks = [b.strip() for b in re.split(r"\n\s*\n", exp_text) if b.strip()]
    if not blocks:
        blocks = [exp_text]

    experiences = []
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue

        company = None
        for org in organizations:
            if org.lower() in block.lower():
                company = org
                break

        title = lines[0]
        desc = "\n".join(lines[1:]).strip() if len(lines) > 1 else lines[0]

        experiences.append({
            "role": title,
            "company": company or title,
            "description": desc,
            "raw_text": block,
        })

    return experiences


def _extract_structured_education(sections: dict) -> list[dict]:
    edu_text = (
        sections.get("education")
        or sections.get("academic_background")
        or sections.get("academics")
        or ""
    ).strip()

    if not edu_text:
        return []

    blocks = [b.strip() for b in re.split(r"\n\s*\n", edu_text) if b.strip()]
    if not blocks:
        blocks = [edu_text]

    education_entries = []
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        education_entries.append({
            "degree": lines[0],
            "institution": lines[1] if len(lines) > 1 else lines[0],
            "details": "\n".join(lines).strip(),
            "raw_text": block,
        })
    return education_entries


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def parse_resume(text: str, layout=None) -> dict:
    nlp = get_nlp()
    doc = nlp(text)

    if layout:
        all_words = [w for page in layout for w in page["words"]]
        lines = _words_to_lines(all_words)
        tagged_lines = _assign_sections_positioned(lines)
        sections = _sections_dict_from_tagged(tagged_lines)
    else:
        tagged_lines = []
        sections = _split_sections(text)

    ner_skills = {ent.text.strip() for ent in doc.ents if ent.label_ == "SKILL"}
    section_skills = set(_extract_skills_from_skills_section(sections.get("skills", "")))
    skills = _normalize_and_dedupe_skills(ner_skills | section_skills)

    organizations = _clean_organizations({ent.text.strip() for ent in doc.ents if ent.label_ == "ORG"})
    links = _build_links_output(text, layout, tagged_lines)

    summary = _extract_summary(sections, text)
    structured_projects = _extract_structured_projects(sections, links, skills)
    structured_experience = _extract_structured_experience(sections, organizations)
    structured_education = _extract_structured_education(sections)

    result = {
        "name": _guess_name(doc, text),
        "raw_text": text,
        "summary": summary,
        "experience": structured_experience,
        "education": structured_education,
        "projects": structured_projects,
        "emails": sorted(set(EMAIL_RE.findall(text))),
        "phones": sorted(set(m.strip() for m in PHONE_RE.findall(text) if len(re.sub(r"\D", "", m)) >= 7)),
        "links": links,
        "skills": skills,
        "organizations": organizations,
        "years_of_experience": _extract_years_of_experience(nlp, text, sections.get("experience", "")),
        "sections": sections,
        "entities": [{"text": ent.text, "label": ent.label_} for ent in doc.ents],
    }
    result["validation"] = validate_parsed_resume(result)
    return result


if __name__ == "__main__":
    sample = """
    Jane Doe
    jane.doe@example.com | +1 (555) 123-4567

    Summary
    Backend engineer with distributed systems experience.

    Skills: Python, Flask, Docker, Kubernetes, RAG, LangChain, JWT

    Experience
    Backend Engineer, Acme Corp
    Jan 2021 - Present
    Built microservices using Python and Kubernetes.

    Education
    B.S. Computer Science, State University

    Achievements
    1st place at HackWinter 2025
    """
    import pprint
    pprint.pprint(parse_resume(sample))