"""
Step 4.1 — Chunking strategy

Produces chunks (with metadata) from three source types:
  - resume sections (from Step 2's section splitter output)
  - GitHub README markdown
  - per-repo code-analysis summaries (from Step 3)

Each chunk is a dict matching:
  {candidate_id, source_type, section, chunk_id, text}

source_type is one of: "resume" | "readme" | "code_summary"
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Literal

SourceType = Literal["resume", "readme", "code_summary"]

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
    source_type: SourceType
    section: str  # section name, repo name, etc.
    text: str
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "source_type": self.source_type,
            "section": self.section,
            "chunk_id": self.chunk_id,
            "text": self.text,
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

    windows = []
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


def chunk_resume(candidate_id: str, sections: dict[str, str]) -> list[Chunk]:
    """
    sections: output of Step 2's section splitter, e.g.
      {"Summary": "...", "Experience": "...", "Education": "...", ...}

    Each section becomes 1+ chunks, ~150-300 tokens each, with a 20-token
    overlap only when a section exceeds the max.
    """
    chunks: list[Chunk] = []
    for section_name, section_text in sections.items():
        if not section_text or not section_text.strip():
            continue
        windows = _split_into_token_windows(
            section_text, max_tokens=RESUME_MAX_TOKENS, overlap_tokens=RESUME_OVERLAP_TOKENS
        )
        for window in windows:
            chunks.append(
                Chunk(candidate_id=candidate_id, source_type="resume", section=section_name, text=window)
            )
    return chunks


def chunk_readme(candidate_id: str, repo_name: str, readme_text: str) -> list[Chunk]:
    """
    Chunk a GitHub README by markdown heading blocks (## / ### sections),
    ~200-400 tokens each. If a heading block itself exceeds the max, it is
    further split (no overlap specified for README chunks).
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
            chunks.append(
                Chunk(
                    candidate_id=candidate_id,
                    source_type="readme",
                    section=f"{repo_name}:{section_label}",
                    text=window,
                )
            )
    return chunks


def chunk_code_summary(candidate_id: str, repo_name: str, metrics: dict) -> Chunk:
    """
    One chunk per repo: a natural-language summary of that repo's metrics.
    `metrics` is the sub-score dict produced in Step 3.3/3.4, e.g.:
      {architecture_score, testing_score, complexity_score,
       documentation_score, commit_score, overall_code_score,
       languages: {...}}
    """
    languages = metrics.get("languages") or {}
    lang_str = "/".join(languages.keys()) if languages else "unspecified language(s)"

    summary_text = (
        f"{repo_name}: overall code score {metrics.get('overall_code_score', 'N/A')}/100. "
        f"architecture {metrics.get('architecture_score', 'N/A')}/100, "
        f"testing {metrics.get('testing_score', 'N/A')}/100, "
        f"complexity {metrics.get('complexity_score', 'N/A')}/100, "
        f"documentation {metrics.get('documentation_score', 'N/A')}/100, "
        f"commit history {metrics.get('commit_score', 'N/A')}/100. "
        f"Uses {lang_str}."
    )

    return Chunk(candidate_id=candidate_id, source_type="code_summary", section=repo_name, text=summary_text)


def build_all_chunks(
    candidate_id: str,
    resume_sections: dict[str, str],
    github_repos: list[dict],
) -> list[dict]:
    """
    Convenience entry point: builds every chunk for a candidate from resume
    sections + a list of repo dicts (each with 'name', 'readme_text', and
    the Step 3 metric fields). Returns plain dicts ready for embedding (4.2).
    """
    all_chunks: list[Chunk] = []
    all_chunks.extend(chunk_resume(candidate_id, resume_sections))

    for repo in github_repos:
        repo_name = repo.get("name", "unnamed_repo")
        all_chunks.extend(chunk_readme(candidate_id, repo_name, repo.get("readme_text", "")))
        all_chunks.append(chunk_code_summary(candidate_id, repo_name, repo))

    return [c.to_dict() for c in all_chunks]