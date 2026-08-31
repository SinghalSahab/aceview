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

SourceType = Literal["resume", "skills", "project", "readme", "code_summary", "github_profile_summary", "transcript"]

# Rough token estimate: ~4 chars/token (good enough for chunk sizing, no
# tokenizer dependency needed at this stage).
CHARS_PER_TOKEN = 4

RESUME_MIN_TOKENS = 150
RESUME_MAX_TOKENS = 300
RESUME_OVERLAP_TOKENS = 20

README_MIN_TOKENS = 200
README_MAX_TOKENS = 400


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


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _split_into_token_windows(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """
    Split text into ~max_tokens windows, only applying overlap when the
    text actually exceeds the max (per spec: overlap only when a section
    exceeds the max size).
    """
    max_chars = max_tokens * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN

    if len(text) <= max_chars:
        return [text.strip()] if text.strip() else []

    windows: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # try not to cut mid-sentence: back off to the last sentence boundary
        # within this window if one exists past the halfway point
        window = text[start:end]
        boundary = max(window.rfind(". "), window.rfind("\n"))
        if boundary > max_chars // 2 and end < len(text):
            end = start + boundary + 1
            window = text[start:end]

        windows.append(window.strip())
        if end >= len(text):
            break
        start = end - overlap_chars  # only meaningful because we're in the >max branch
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
                chunks.append(
                    Chunk(
                        candidate_id=candidate_id,
                        source_type="project",
                        section=f"project:{title}",
                        text=full_text,
                        metadata={
                            "section": f"project:{title}",
                            "project_name": title,
                            "description": desc,
                            "technologies": tech if isinstance(tech, list) else ([tech_str] if tech_str else []),
                            "url": url,
                        },
                    )
                )
            elif isinstance(proj, str) and proj.strip():
                chunks.append(
                    Chunk(
                        candidate_id=candidate_id,
                        source_type="project",
                        section=f"project:{idx + 1}",
                        text=proj.strip(),
                        metadata={"section": f"project:{idx + 1}"},
                    )
                )

    if project_links:
        for p_link in project_links:
            if isinstance(p_link, dict):
                uri = p_link.get("uri") or p_link.get("url") or ""
                context = p_link.get("context") or p_link.get("anchor") or ""
                proj_name = p_link.get("project_name") or p_link.get("repo_name") or "Project Link"
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
                                "url": uri,
                                "context": context,
                            },
                        )
                    )
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
    return chunks


def chunk_code_summary(
    candidate_id: str,
    repo_name: str,
    metrics: dict[str, Any],
    repo_id: str | None = None,
    repo_metadata: dict[str, Any] | None = None,
) -> Chunk:
    """
    One chunk per repo: a natural-language summary of that repo's code metrics
    with full enriched metadata attached in JSONB.
    """
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

    text_lines = [f"Repository: {repo_name}"]
    if desc:
        text_lines.append(f"Description: {desc}")
    if url:
        text_lines.append(f"URL: {url}")

    text_lines.append(
        f"Metrics: overall code score {metrics.get('overall_code_score', 'N/A')}/100, "
        f"architecture {metrics.get('architecture_score', 'N/A')}/100, "
        f"testing {metrics.get('testing_score', 'N/A')}/100, "
        f"complexity {metrics.get('complexity_score', 'N/A')}/100, "
        f"documentation {metrics.get('documentation_score', 'N/A')}/100, "
        f"commit history {metrics.get('commit_score', 'N/A')}/100. "
        f"Primary languages: {lang_str}."
    )
    summary_text = "\n".join(text_lines)

    meta: dict[str, Any] = {
        "section": repo_name,
        "repo_name": repo_name,
        "url": url,
        "description": desc,
        "languages": languages,
    }
    # Attach numeric scores if present
    for score_key in (
        "overall_code_score",
        "architecture_score",
        "testing_score",
        "complexity_score",
        "documentation_score",
        "commit_score",
    ):
        val = metrics.get(score_key)
        if val is not None:
            try:
                meta[score_key] = float(val)
            except (ValueError, TypeError):
                meta[score_key] = str(val)

    return Chunk(
        candidate_id=candidate_id,
        source_type="code_summary",
        section=repo_name,
        text=summary_text,
        repo_id=repo_id,
        metadata=meta,
    )


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

    return Chunk(
        candidate_id=candidate_id,
        source_type="github_profile_summary",
        section="github_profile_summary",
        text=summary_text,
        metadata=meta,
    )


def build_all_chunks(
    candidate_id: str,
    resume_sections: dict[str, str] | None = None,
    github_repos: list[dict[str, Any]] | None = None,
    resume_skills: list[str] | list[dict[str, Any]] | None = None,
    resume_projects: list[dict[str, Any]] | list[str] | None = None,
    resume_links: dict[str, Any] | list[dict[str, Any]] | None = None,
    years_of_experience: float | int | None = None,
    github_profile_summary: dict[str, Any] | str | None = None,
) -> list[dict[str, Any]]:
    """
    Convenience entry point: builds every chunk for a candidate from:
      - resume sections + structured skills + structured projects + links
      - list of repo dicts (with 'id', 'name', 'readme_text', and metric fields)
      - overall GitHub profile analytics summary (github_profile_summary)
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
            all_chunks.append(
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

    return [c.to_dict() for c in all_chunks]