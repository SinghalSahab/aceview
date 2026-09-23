"""
Step 4.1 — Chunking strategy

Produces rich chunks (with structured metadata) from candidate data sources:
  - resume sections (Experience, Summary, Education, etc.)
  - dedicated skills chunks (from resumes.skills JSONB array)
  - dedicated project chunks (from resumes.projects JSONB / project link annotations)
  - GitHub README markdown (split by heading sections)
  - per-repo code-analysis summaries & metrics (from Step 3 & github_repositories table)

Each chunk is a dict matching:
  {
    "candidate_id": str,
    "source_type": str,  # "resume" | "skills" | "project" | "readme" | "code_summary"
    "section": str,
    "chunk_id": str,
    "text": str,
    "repo_id": str | None,
    "metadata": dict
  }
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from functools import lru_cache
from transformers import AutoTokenizer

try:
    from skills.skillExtractor import get_nlp
except ImportError:
    from skillExtractor import get_nlp

SourceType = Literal["resume", "skills", "project", "readme", "code_summary", "github_profile_summary", "transcript", "claim"]

TOKENIZER_MODEL_NAME = "BAAI/bge-small-en-v1.5"

@lru_cache(maxsize=1)
def get_tokenizer() -> AutoTokenizer:
    return AutoTokenizer.from_pretrained(TOKENIZER_MODEL_NAME)

TOKENIZER = get_tokenizer()

RESUME_MIN_TOKENS = 150
RESUME_MAX_TOKENS = 300
RESUME_OVERLAP_TOKENS = 20

README_MIN_TOKENS = 200
README_MAX_TOKENS = 400


def count_tokens(text: str) -> int:
    """Returns exact token count using BAAI/bge-small-en-v1.5 tokenizer."""
    if not text:
        return 0
    return len(TOKENIZER.encode(text, add_special_tokens=False))


def extract_tech_entities(text: str) -> list[str]:
    """
    Extracts normalized (lowercased, deduped, sorted) technology and skill terms
    from arbitrary chunk text using the spaCy EntityRuler pipeline.
    """
    if not text or not text.strip():
        return []
    try:
        nlp = get_nlp()
        doc = nlp(text)
        entities = {
            ent.text.strip().lower()
            for ent in doc.ents
            if ent.label_ == "SKILL" and ent.text.strip()
        }
        return sorted(entities)
    except Exception:
        return []


def normalize_project_key(name: str) -> str:
    """
    Normalized, deterministic slug derived from project or repository name:
    lowercased, punctuation/symbols stripped or converted to '-',
    collapsed to single hyphens, stripped at edges.
    """
    if not name:
        return ""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower())
    return slug.strip("-")


def assert_within_model_limit(chunk_text: str, chunk_id: str, hard_max: int = 480) -> None:
    """
    Fails loud if any chunk exceeds the embedding model limit (512 minus ~32 safety margin).
    """
    tokens = count_tokens(chunk_text)
    if tokens > hard_max:
        raise ValueError(
            f"Chunk '{chunk_id}' exceeds maximum model token limit: "
            f"{tokens} tokens > {hard_max} hard limit."
        )


@dataclass
class Chunk:
    candidate_id: str
    source_type: str
    section: str  # section name, repo name, etc.
    text: str
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    repo_id: str | None = None  # UUID string, FK to github_repositories.id (readme/code_summary only)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_type": self.source_type,
            "section": self.section,
            "chunk_id": self.chunk_id,
            "text": self.text,
            "repo_id": self.repo_id,
            "metadata": self.metadata,
        }


def _split_into_token_windows(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """
    Split text into token windows of at most max_tokens, operating on real token IDs.
    Applies sentence-snap backwards to sentence boundaries past the ~50% mark,
    re-measuring actual consumed tokens to maintain correct overlap step-back.
    """
    if not text or not text.strip():
        return []

    token_ids = TOKENIZER.encode(text, add_special_tokens=False)
    if len(token_ids) <= max_tokens:
        return [text.strip()]

    windows: list[str] = []
    start = 0
    n_tokens = len(token_ids)

    while start < n_tokens:
        end = min(start + max_tokens, n_tokens)
        window_ids = token_ids[start:end]
        window_text = TOKENIZER.decode(window_ids, skip_special_tokens=True).strip()

        # If not the final window, try to snap backward to a clean sentence/paragraph boundary
        if end < n_tokens:
            boundary_idx = -1
            half_mark = len(window_text) // 2
            for punct in [". ", ".\n", "\n", "? ", "! "]:
                pos = window_text.rfind(punct)
                if pos > half_mark and pos > boundary_idx:
                    boundary_idx = pos + len(punct)

            if boundary_idx != -1:
                snapped_text = window_text[:boundary_idx].strip()
                consumed_tokens = count_tokens(snapped_text)
                if consumed_tokens > 0:
                    windows.append(snapped_text)
                    start = start + max(1, consumed_tokens - overlap_tokens)
                    continue

        windows.append(window_text)
        if end >= n_tokens:
            break
        start = max(start + 1, end - overlap_tokens)

    return [w for w in windows if w]


def chunk_skills(
    candidate_id: str,
    skills: list[str] | list[dict[str, Any]] | set[str] | None = None,
) -> list[Chunk]:
    """
    Creates dedicated, structured skill chunks from candidate's skills array (resumes.skills).
    Groups skills into readable clusters so they can be easily retrieved
    by semantic questions (e.g. 'what backend skills does the candidate have?').
    """
    if not skills:
        return []

    cleaned_skills: list[str] = []
    for s in skills:
        if isinstance(s, str) and s.strip():
            cleaned_skills.append(s.strip())
        elif isinstance(s, dict) and "name" in s and s["name"]:
            cleaned_skills.append(str(s["name"]).strip())

    if not cleaned_skills:
        return []

    # Deduplicate while preserving original order
    deduped = list(dict.fromkeys(cleaned_skills))

    chunks: list[Chunk] = []
    chunk_size = 20  # group ~20 skills per chunk for dense semantic coverage
    for i in range(0, len(deduped), chunk_size):
        batch = deduped[i : i + chunk_size]
        skills_text = (
            f"Candidate Technical Skills ({i + 1}-{i + len(batch)} of {len(deduped)}): "
            + ", ".join(batch)
        )
        chunks.append(
            Chunk(
                candidate_id=candidate_id,
                source_type="skills",
                section="skills",
                text=skills_text,
                metadata={
                    "section": "skills",
                    "skills": batch,
                    "all_skills_count": len(deduped),
                },
            )
        )
    for c in chunks:
        c.metadata["detected_tech"] = extract_tech_entities(c.text)
        assert_within_model_limit(c.text, c.chunk_id)
    return chunks


def chunk_projects(
    candidate_id: str,
    projects: list[dict[str, Any]] | list[str] | None = None,
    project_links: list[dict[str, Any]] | None = None,
) -> list[Chunk]:
    """
    Creates dedicated project chunks from structured projects list (resumes.projects)
    and project link annotations.
    """
    chunks: list[Chunk] = []

    if projects:
        for idx, proj in enumerate(projects):
            if isinstance(proj, dict):
                title = proj.get("title") or proj.get("name") or f"Project {idx + 1}"
                desc = proj.get("description") or proj.get("summary") or ""
                tech = proj.get("technologies") or proj.get("skills") or []
                url = proj.get("url") or proj.get("link") or ""

                tech_str = ", ".join(tech) if isinstance(tech, list) else str(tech)
                text_parts = [f"Project: {title}"]
                if desc:
                    text_parts.append(f"Description: {desc}")
                if tech_str:
                    text_parts.append(f"Technologies: {tech_str}")
                if url:
                    text_parts.append(f"Link: {url}")

                full_text = "\n".join(text_parts)
                proj_key = normalize_project_key(title)
                chunks.append(
                    Chunk(
                        candidate_id=candidate_id,
                        source_type="project",
                        section=f"project:{title}",
                        text=full_text,
                        metadata={
                            "section": f"project:{title}",
                            "project_name": title,
                            "project_key": proj_key,
                            "description": desc,
                            "technologies": tech if isinstance(tech, list) else ([tech_str] if tech_str else []),
                            "url": url,
                        },
                    )
                )
            elif isinstance(proj, str) and proj.strip():
                proj_key = normalize_project_key(proj.strip()[:40]) or f"project-{idx + 1}"
                chunks.append(
                    Chunk(
                        candidate_id=candidate_id,
                        source_type="project",
                        section=f"project:{idx + 1}",
                        text=proj.strip(),
                        metadata={
                            "section": f"project:{idx + 1}",
                            "project_key": proj_key,
                        },
                    )
                )

    if project_links:
        for p_link in project_links:
            if isinstance(p_link, dict):
                uri = p_link.get("uri") or p_link.get("url") or ""
                context = p_link.get("context") or p_link.get("anchor") or ""
                proj_name = p_link.get("project_name") or p_link.get("repo_name") or "Project Link"
                proj_key = normalize_project_key(proj_name)
                if uri:
                    chunks.append(
                        Chunk(
                            candidate_id=candidate_id,
                            source_type="project",
                            section=f"project_link:{proj_name}",
                            text=f"Project Link: {proj_name}\nURL: {uri}\nContext: {context}",
                            metadata={
                                "section": f"project_link:{proj_name}",
                                "project_name": proj_name,
                                "project_key": proj_key,
                                "url": uri,
                                "context": context,
                            },
                        )
                    )
    for c in chunks:
        c.metadata["detected_tech"] = extract_tech_entities(c.text)
        assert_within_model_limit(c.text, c.chunk_id)
    return chunks


def chunk_resume(
    candidate_id: str,
    sections: dict[str, str],
    skills: list[str] | list[dict[str, Any]] | None = None,
    projects: list[dict[str, Any]] | list[str] | None = None,
    project_links: list[dict[str, Any]] | None = None,
    years_of_experience: float | int | None = None,
) -> list[Chunk]:
    """
    sections: output of Step 2's section splitter, e.g.
      {"Summary": "...", "Experience": "...", "Education": "...", ...}

    Each section becomes 1+ chunks, ~150-300 tokens each, with a 20-token
    overlap only when a section exceeds the max.
    Also produces dedicated chunks for skills and projects if provided.
    """
    chunks: list[Chunk] = []

    # 1. Dedicated structured skills chunks
    if skills:
        chunks.extend(chunk_skills(candidate_id, skills))

    # 2. Dedicated structured project chunks
    if projects or project_links:
        chunks.extend(chunk_projects(candidate_id, projects=projects, project_links=project_links))

    # 3. Standard text section chunks (Experience, Education, Summary, etc.)
    if sections:
        for section_name, section_text in sections.items():
            if not section_text or not section_text.strip():
                continue

            # Skip duplicate raw skills text if we already created dedicated structured skills chunks
            if section_name.lower() in ("skills", "technical skills") and skills:
                continue

            windows = _split_into_token_windows(
                section_text, max_tokens=RESUME_MAX_TOKENS, overlap_tokens=RESUME_OVERLAP_TOKENS
            )
            for window in windows:
                meta: dict[str, Any] = {"section": section_name}
                if years_of_experience is not None:
                    meta["years_of_experience"] = float(years_of_experience)

                chunks.append(
                    Chunk(
                        candidate_id=candidate_id,
                        source_type="resume",
                        section=section_name,
                        text=window,
                        metadata=meta,
                    )
                )
    for c in chunks:
        if "detected_tech" not in c.metadata:
            c.metadata["detected_tech"] = extract_tech_entities(c.text)
        assert_within_model_limit(c.text, c.chunk_id)
    return chunks


def chunk_readme(
    candidate_id: str,
    repo_name: str,
    readme_text: str,
    repo_id: str | None = None,
    repo_metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    """
    Chunk a GitHub README by markdown heading blocks (## / ### sections),
    ~200-400 tokens each. If a heading block itself exceeds the max, it is
    further split. Attaches enriched repo metadata (URL, description, languages).
    """
    if not readme_text or not readme_text.strip():
        return []

    # Split on lines starting with ## or ### (keep the heading with its block)
    heading_pattern = re.compile(r"(?=^#{2,3}\s.+$)", re.MULTILINE)
    blocks = [b for b in heading_pattern.split(readme_text) if b.strip()]

    if not blocks:
        blocks = [readme_text]

    chunks: list[Chunk] = []
    for block in blocks:
        heading_match = re.match(r"^#{2,3}\s+(.+)$", block.strip(), re.MULTILINE)
        section_label = heading_match.group(1).strip() if heading_match else "intro"

        windows = _split_into_token_windows(block, max_tokens=README_MAX_TOKENS, overlap_tokens=0)
        for window in windows:
            meta: dict[str, Any] = {
                "section": f"{repo_name}:{section_label}",
                "repo_name": repo_name,
                "project_key": normalize_project_key(repo_name),
            }
            if repo_metadata:
                if "url" in repo_metadata and repo_metadata["url"]:
                    meta["url"] = repo_metadata["url"]
                if "description" in repo_metadata and repo_metadata["description"]:
                    meta["description"] = repo_metadata["description"]
                if "languages" in repo_metadata and repo_metadata["languages"]:
                    meta["languages"] = repo_metadata["languages"]
                if "is_fork" in repo_metadata:
                    meta["is_fork"] = repo_metadata["is_fork"]

            chunks.append(
                Chunk(
                    candidate_id=candidate_id,
                    source_type="readme",
                    section=f"{repo_name}:{section_label}",
                    text=window,
                    repo_id=repo_id,
                    metadata=meta,
                )
            )
    for c in chunks:
        c.metadata["detected_tech"] = extract_tech_entities(c.text)
        assert_within_model_limit(c.text, c.chunk_id)
    return chunks


def chunk_code_summary(
    candidate_id: str,
    repo_name: str,
    metrics: dict[str, Any],
    repo_id: str | None = None,
    repo_metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    """
    Replaces single-chunk-per-repo with 3 distinct sub-chunks per repo:
      - Architecture & Stack (summary_kind = "architecture")
      - Testing & Quality (summary_kind = "testing")
      - Commit Habits & Consistency (summary_kind = "commits")
    Each carries identical repo_id, project_key, and detected_tech.
    """
    proj_key = normalize_project_key(repo_name)
    base_id = repo_id or proj_key or "repo"

    languages = (
        metrics.get("languages")
        or (repo_metadata.get("languages") if repo_metadata else {})
        or {}
    )
    if isinstance(languages, dict):
        lang_str = "/".join(languages.keys()) if languages else "unspecified language(s)"
    elif isinstance(languages, list):
        lang_str = ", ".join(languages) if languages else "unspecified language(s)"
    else:
        lang_str = str(languages)

    desc = (
        metrics.get("description")
        or (repo_metadata.get("description") if repo_metadata else "")
        or ""
    )
    url = (
        metrics.get("url")
        or (repo_metadata.get("url") if repo_metadata else "")
        or ""
    )

    # 1. Architecture & Stack
    arch_lines = [f"Repository Architecture & Stack: {repo_name}"]
    if desc:
        arch_lines.append(f"Description: {desc}")
    if url:
        arch_lines.append(f"URL: {url}")
    arch_lines.append(
        f"Architecture score: {metrics.get('architecture_score', 'N/A')}/100. "
        f"Overall code score: {metrics.get('overall_code_score', 'N/A')}/100. "
        f"Primary languages: {lang_str}."
    )
    arch_text = "\n".join(arch_lines)

    arch_meta: dict[str, Any] = {
        "section": f"{repo_name}:architecture",
        "repo_name": repo_name,
        "project_key": proj_key,
        "summary_kind": "architecture",
        "url": url,
        "description": desc,
        "languages": languages,
        "detected_tech": extract_tech_entities(arch_text),
    }
    for k in ("architecture_score", "overall_code_score"):
        if metrics.get(k) is not None:
            try:
                arch_meta[k] = float(metrics[k])
            except (ValueError, TypeError):
                arch_meta[k] = str(metrics[k])

    arch_chunk = Chunk(
        candidate_id=candidate_id,
        source_type="code_summary",
        section=f"{repo_name}:architecture",
        chunk_id=f"{base_id}-architecture",
        text=arch_text,
        repo_id=repo_id,
        metadata=arch_meta,
    )

    # 2. Testing & Quality
    doc_score = metrics.get("documentation_score") or metrics.get("doc_score", "N/A")
    test_lines = [
        f"Repository Testing & Quality: {repo_name}",
        f"Testing score: {metrics.get('testing_score', 'N/A')}/100. "
        f"Code complexity score: {metrics.get('complexity_score', 'N/A')}/100. "
        f"Documentation score: {doc_score}/100."
    ]
    test_text = "\n".join(test_lines)

    test_meta: dict[str, Any] = {
        "section": f"{repo_name}:testing",
        "repo_name": repo_name,
        "project_key": proj_key,
        "summary_kind": "testing",
        "detected_tech": extract_tech_entities(test_text),
    }
    for k in ("testing_score", "complexity_score", "documentation_score", "doc_score"):
        if metrics.get(k) is not None:
            try:
                test_meta[k] = float(metrics[k])
            except (ValueError, TypeError):
                test_meta[k] = str(metrics[k])

    test_chunk = Chunk(
        candidate_id=candidate_id,
        source_type="code_summary",
        section=f"{repo_name}:testing",
        chunk_id=f"{base_id}-testing",
        text=test_text,
        repo_id=repo_id,
        metadata=test_meta,
    )

    # 3. Commit Habits & Consistency
    commit_lines = [
        f"Repository Commit Habits & Consistency: {repo_name}",
        f"Commit history score: {metrics.get('commit_score', 'N/A')}/100."
    ]
    if metrics.get("commit_count"):
        commit_lines.append(f"Total commits analyzed: {metrics.get('commit_count')}.")
    if metrics.get("streak_days") or metrics.get("active_days_ratio"):
        commit_lines.append(
            f"Commit streak: {metrics.get('streak_days', 'N/A')} days, "
            f"active days ratio: {metrics.get('active_days_ratio', 'N/A')}."
        )
    commit_text = "\n".join(commit_lines)

    commit_meta: dict[str, Any] = {
        "section": f"{repo_name}:commits",
        "repo_name": repo_name,
        "project_key": proj_key,
        "summary_kind": "commits",
        "detected_tech": extract_tech_entities(commit_text),
    }
    for k in ("commit_score", "commit_count", "streak_days", "active_days_ratio"):
        if metrics.get(k) is not None:
            try:
                commit_meta[k] = float(metrics[k])
            except (ValueError, TypeError):
                commit_meta[k] = str(metrics[k])

    commit_chunk = Chunk(
        candidate_id=candidate_id,
        source_type="code_summary",
        section=f"{repo_name}:commits",
        chunk_id=f"{base_id}-commits",
        text=commit_text,
        repo_id=repo_id,
        metadata=commit_meta,
    )

    sub_chunks = [arch_chunk, test_chunk, commit_chunk]
    for sc in sub_chunks:
        assert_within_model_limit(sc.text, sc.chunk_id)
    return sub_chunks


def chunk_github_profile_summary(
    candidate_id: str,
    username: str,
    summary_text: str,
    score_data: dict[str, Any] | None = None,
) -> Chunk:
    """
    Creates a dedicated RAG chunk for the candidate's overall GitHub profile analytics & habits.
    """
    meta: dict[str, Any] = {
        "username": username,
        "source_type": "github_profile_summary",
    }
    if score_data:
        meta["overall_score"] = score_data.get("overall_score")
        meta["sub_scores"] = score_data.get("sub_scores", {})
        meta["signals"] = score_data.get("signals", {})

    chunk = Chunk(
        candidate_id=candidate_id,
        source_type="github_profile_summary",
        section="github_profile_summary",
        text=summary_text,
        metadata=meta,
    )
    assert_within_model_limit(chunk.text, chunk.chunk_id)
    return chunk


def _classify_claim(text: str) -> str:
    """Classifies a claim into 'metric', 'architecture', 'leadership', or 'other'."""
    text_lower = text.lower()

    # 1. Metric: quantifiable assertions
    has_percentage = bool(re.search(r"\b\d+(?:\.\d+)?%", text_lower))
    has_multiplier = bool(re.search(r"\b\d+(?:\.\d+)?x\b", text_lower))
    has_metric_verb_num = bool(re.search(
        r"\b(reduced|cut|decreased|improved|increased|scaled|saved|boosted|grew|dropped|halved|doubled|tripled)\b.*\b\d+",
        text_lower
    ))

    # 2. Architecture patterns
    is_arch_keyword = bool(re.search(
        r"\b(microservices|microservice|architecture|distributed systems|distributed system|scalable|pipeline|event-driven|serverless|fault-tolerant|caching layer|message queue|load balancing|restful api|graphql api)\b",
        text_lower
    ))
    is_arch_verb = bool(re.search(
        r"\b(built|architected|designed|implemented|structured|migrated|engineered|developed|deployed)\b",
        text_lower
    ))

    # 3. Leadership patterns
    is_leadership = bool(re.search(
        r"\b(led|lead|managed|mentored|spearheaded|directed|supervised|coordinated|hired|coached|guided)\b.*\b(team|engineers|developers|interns|cross-functional|initiatives|project)\b",
        text_lower
    ))
    if is_leadership and not has_percentage:
        return "leadership"

    # If it has strong architecture signals ("built a scalable microservices architecture...")
    if is_arch_keyword and is_arch_verb:
        if has_percentage or has_multiplier or (has_metric_verb_num and ("reduced" in text_lower or "improved" in text_lower)):
            if any(w in text_lower for w in ["reduced", "cutting", "improved", "increased", "decreased", "saved"]):
                return "metric"
        return "architecture"

    if has_percentage or has_multiplier or has_metric_verb_num:
        return "metric"

    if is_arch_keyword:
        return "architecture"

    if is_leadership:
        return "leadership"

    return "other"


def chunk_claim(
    resume_text: str,
    project_chunks: list[Chunk] | list[dict[str, Any]],
    candidate_id: str,
) -> list[Chunk]:
    """
    Extracts discrete, verifiable assertions from resume and project text into their own retrievable unit.
    Each claim chunk has:
      source_type: 'claim'
      text: normalized claim sentence
      metadata:
        claim_type: 'metric' | 'architecture' | 'leadership' | 'other'
        project_key: str | None
        verified: False (default)
        detected_tech: list[str]
    """
    claims: list[Chunk] = []
    seen_texts: set[str] = set()

    # Known project keys and titles for attribution
    project_map: dict[str, str] = {}
    for pc in project_chunks:
        meta = pc.metadata if isinstance(pc, Chunk) else pc.get("metadata", {})
        pkey = meta.get("project_key")
        pname = meta.get("project_name")
        if pkey:
            project_map[pkey.lower()] = pkey
        if pname and pkey:
            project_map[pname.lower()] = pkey

    # 1. Extract from project chunks
    for pc in project_chunks:
        text = pc.text if isinstance(pc, Chunk) else pc.get("text", "")
        meta = pc.metadata if isinstance(pc, Chunk) else pc.get("metadata", {})
        pkey = meta.get("project_key")

        lines = [line.strip().lstrip("-•* ").strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            if line.lower().startswith(("project:", "technologies:", "link:", "description:")):
                if line.lower().startswith("description:"):
                    line = line[len("description:"):].strip()
                else:
                    continue

            sentences = re.split(r"(?<=[.!?])\s+", line)
            for s in sentences:
                s_clean = s.strip()
                if not s_clean or len(s_clean) < 15:
                    continue
                if not re.search(r"\b(built|architected|designed|implemented|reduced|improved|increased|cut|saved|developed|led|created|scaled|migrated)\b", s_clean, re.I):
                    continue

                key_text = s_clean.lower()
                if key_text in seen_texts:
                    continue
                seen_texts.add(key_text)

                claim_type = _classify_claim(s_clean)
                claim_hash = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{candidate_id}:{s_clean}"))[:12]
                chunk_id = f"{candidate_id}-claim-{claim_hash}"

                c_meta = {
                    "claim_type": claim_type,
                    "project_key": pkey,
                    "verified": False,
                    "detected_tech": extract_tech_entities(s_clean),
                }
                claim_chunk = Chunk(
                    candidate_id=candidate_id,
                    source_type="claim",
                    section=f"claim:{claim_type}",
                    chunk_id=chunk_id,
                    text=s_clean,
                    metadata=c_meta,
                )
                assert_within_model_limit(claim_chunk.text, claim_chunk.chunk_id)
                claims.append(claim_chunk)

    # 2. Extract from resume text
    if resume_text:
        lines = [line.strip().lstrip("-•* ").strip() for line in resume_text.split("\n") if line.strip()]
        current_project_key = None

        for line in lines:
            for pname_lower, pkey in project_map.items():
                if pname_lower in line.lower():
                    current_project_key = pkey
                    break

            sentences = re.split(r"(?<=[.!?])\s+", line)
            for s in sentences:
                s_clean = s.strip()
                if not s_clean or len(s_clean) < 15:
                    continue
                if not re.search(r"\b(built|architected|designed|implemented|reduced|improved|increased|cut|saved|developed|led|created|scaled|migrated|spearheaded|engineered)\b", s_clean, re.I):
                    continue

                key_text = s_clean.lower()
                if key_text in seen_texts:
                    continue
                seen_texts.add(key_text)

                attr_pkey = current_project_key
                for pname_lower, pkey in project_map.items():
                    if pname_lower in s_clean.lower():
                        attr_pkey = pkey
                        break

                claim_type = _classify_claim(s_clean)
                claim_hash = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{candidate_id}:{s_clean}"))[:12]
                chunk_id = f"{candidate_id}-claim-{claim_hash}"

                c_meta = {
                    "claim_type": claim_type,
                    "project_key": attr_pkey,
                    "verified": False,
                    "detected_tech": extract_tech_entities(s_clean),
                }
                claim_chunk = Chunk(
                    candidate_id=candidate_id,
                    source_type="claim",
                    section=f"claim:{claim_type}",
                    chunk_id=chunk_id,
                    text=s_clean,
                    metadata=c_meta,
                )
                assert_within_model_limit(claim_chunk.text, claim_chunk.chunk_id)
                claims.append(claim_chunk)

    return claims


def chunk_transcript(
    question: str,
    answer: str,
    candidate_id: str,
    turn_number: int,
    question_topic: str,
    evaluation_score: int | float | None = None,
) -> Chunk:
    """
    Creates a RAG chunk for a live interview conversation turn.
    Called live per-turn during an active interview session.
    chunk_id scheme: {candidate_id}-turn-{turn_number}
    """
    text = f"Question: {question.strip()}\nAnswer: {answer.strip()}"
    chunk_id = f"{candidate_id}-turn-{turn_number}"

    meta = {
        "question_topic": question_topic,
        "turn_number": turn_number,
        "evaluation_score": evaluation_score,
        "detected_tech": extract_tech_entities(answer),
    }

    chunk = Chunk(
        candidate_id=candidate_id,
        source_type="transcript",
        section=f"turn-{turn_number}",
        chunk_id=chunk_id,
        text=text,
        metadata=meta,
    )
    assert_within_model_limit(chunk.text, chunk.chunk_id)
    return chunk


def build_all_chunks(
    candidate_id: str,
    resume_sections: dict[str, str] | None = None,
    github_repos: list[dict[str, Any]] | None = None,
    resume_skills: list[str] | list[dict[str, Any]] | None = None,
    resume_projects: list[dict[str, Any]] | list[str] | None = None,
    resume_links: dict[str, Any] | list[dict[str, Any]] | None = None,
    years_of_experience: float | int | None = None,
    github_profile_summary: dict[str, Any] | str | None = None,
    resume_text: str | None = None,
) -> list[dict[str, Any]]:
    """
    Convenience entry point: builds every chunk for a candidate from:
      - resume sections + structured skills + structured projects + links
      - list of repo dicts (with 'id', 'name', 'readme_text', and metric fields)
      - overall GitHub profile analytics summary (github_profile_summary)
      - verifiable claims extracted from resume and project text
    Returns plain dicts ready for embedding & storage in rag_documents.
    """
    all_chunks: list[Chunk] = []

    # Extract project links if passed in resume_links dictionary
    project_links: list[dict[str, Any]] | None = None
    if isinstance(resume_links, dict):
        project_links = resume_links.get("projects")
    elif isinstance(resume_links, list):
        project_links = resume_links

    # 1. Resume chunking
    if resume_sections or resume_skills or resume_projects or project_links:
        all_chunks.extend(
            chunk_resume(
                candidate_id=candidate_id,
                sections=resume_sections or {},
                skills=resume_skills,
                projects=resume_projects,
                project_links=project_links,
                years_of_experience=years_of_experience,
            )
        )

    # 2. GitHub Repositories chunking
    if github_repos:
        for repo in github_repos:
            repo_name = repo.get("name") or repo.get("repo_name") or "unnamed_repo"
            repo_id = str(repo["id"]) if repo.get("id") else None

            # Repo metadata bundle
            repo_metadata = {
                "url": repo.get("url"),
                "description": repo.get("description"),
                "languages": repo.get("languages", {}),
                "is_fork": repo.get("is_fork", False),
            }

            all_chunks.extend(
                chunk_readme(
                    candidate_id=candidate_id,
                    repo_name=repo_name,
                    readme_text=repo.get("readme_text", ""),
                    repo_id=repo_id,
                    repo_metadata=repo_metadata,
                )
            )
            all_chunks.extend(
                chunk_code_summary(
                    candidate_id=candidate_id,
                    repo_name=repo_name,
                    metrics=repo,
                    repo_id=repo_id,
                    repo_metadata=repo_metadata,
                )
            )

    # 3. Overall GitHub Profile Summary chunking
    if github_profile_summary:
        if isinstance(github_profile_summary, dict):
            summary_text = github_profile_summary.get("rag_summary") or github_profile_summary.get("rag_summary_text") or ""
            username = github_profile_summary.get("username", "candidate")
            score_data = github_profile_summary.get("score_data")
        else:
            summary_text = str(github_profile_summary)
            username = "candidate"
            score_data = None

        if summary_text.strip():
            all_chunks.append(
                chunk_github_profile_summary(
                    candidate_id=candidate_id,
                    username=username,
                    summary_text=summary_text,
                    score_data=score_data,
                )
            )

    # 4. Discrete Claims chunking (Task 5)
    full_resume_text = resume_text or (
        "\n\n".join(resume_sections.values()) if resume_sections else ""
    )
    project_chunks = [c for c in all_chunks if c.source_type == "project"]
    if full_resume_text or project_chunks:
        all_chunks.extend(
            chunk_claim(
                resume_text=full_resume_text,
                project_chunks=project_chunks,
                candidate_id=candidate_id,
            )
        )

    return [c.to_dict() for c in all_chunks]