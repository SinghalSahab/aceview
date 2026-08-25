"""
Step 4.3 — Retrieval function

retrieve(query, candidate_id, k=4, source_type_filter=None, repo_id_filter=None):
  - embeds the query using all-MiniLM-L6-v2
  - runs cosine similarity search scoped to that candidate's rows (user_id = candidate_id)
  - optionally filtered by source_type (e.g. "skills", "project", "code_summary", "readme", "resume")
  - optionally filtered by repo_id
  - applies the 0.35 similarity floor
  - returns rich RetrievedChunk objects including structured JSONB metadata

Uses pgvector HNSW index for high performance.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

try:
    from rag.embeddings import embed_texts
except ImportError:
    from embeddings import embed_texts

from db.models import RagDocument

SIMILARITY_FLOOR = 0.35


@dataclass
class RetrievedChunk:
    chunk_id: str
    source_type: str
    section: str  # source_ref
    text: str  # content
    similarity: float
    repo_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def retrieve(
    session: Session,
    query: str,
    candidate_id: str | uuid.UUID,
    k: int = 4,
    source_type_filter: str | Sequence[str] | None = None,
    repo_id_filter: str | uuid.UUID | None = None,
    min_similarity: float = SIMILARITY_FLOOR,
) -> list[RetrievedChunk]:
    """
    Returns up to `k` chunks for this candidate, ranked by cosine
    similarity, filtered to similarity >= min_similarity.
    Returns an empty list if nothing clears the floor.
    """
    query_vec = embed_texts([query])[0]
    c_uuid = uuid.UUID(str(candidate_id)) if not isinstance(candidate_id, uuid.UUID) else candidate_id

    # embeddings.py stores normalize_embeddings=True vectors, so
    # cosine_distance = 1 - cosine_similarity.
    distance_expr = RagDocument.embedding.cosine_distance(query_vec)
    similarity_expr = (1 - distance_expr).label("similarity")

    stmt = (
        select(RagDocument, similarity_expr)
        .where(RagDocument.user_id == c_uuid)
        .where(distance_expr <= (1 - min_similarity))  # push the floor into the index scan
        .order_by(distance_expr)
        .limit(k)
    )

    if source_type_filter is not None:
        if isinstance(source_type_filter, str):
            stmt = stmt.where(RagDocument.source_type == source_type_filter)
        elif isinstance(source_type_filter, (list, tuple, set)):
            stmt = stmt.where(RagDocument.source_type.in_(list(source_type_filter)))

    if repo_id_filter is not None:
        r_uuid = uuid.UUID(str(repo_id_filter)) if not isinstance(repo_id_filter, uuid.UUID) else repo_id_filter
        stmt = stmt.where(RagDocument.repo_id == r_uuid)

    rows = session.execute(stmt).all()

    return [
        RetrievedChunk(
            chunk_id=doc.chunk_id,
            source_type=doc.source_type,
            section=doc.source_ref or "",
            text=doc.content,
            similarity=float(similarity),
            repo_id=str(doc.repo_id) if doc.repo_id else None,
            metadata=doc.metadata_ if isinstance(doc.metadata_, dict) else {},
        )
        for doc, similarity in rows
    ]


# --- Convenience wrappers for the agent's typical query patterns (Step 5) ---


def retrieve_skills(session: Session, candidate_id: str | uuid.UUID, query: str = "candidate technical skills") -> list[RetrievedChunk]:
    """Retrieves dedicated skills chunks and resume skill sections."""
    return retrieve(session, query, candidate_id, k=4, source_type_filter=["skills", "resume"])


def retrieve_projects(session: Session, candidate_id: str | uuid.UUID, query: str = "candidate projects and portfolio") -> list[RetrievedChunk]:
    """Retrieves dedicated project chunks and portfolio link context."""
    return retrieve(session, query, candidate_id, k=4, source_type_filter=["project", "readme"])


def retrieve_most_complex_project(session: Session, candidate_id: str | uuid.UUID) -> list[RetrievedChunk]:
    return retrieve(
        session, "candidate's most complex project", candidate_id, k=4, source_type_filter="code_summary"
    )


def retrieve_testing_practices(session: Session, candidate_id: str | uuid.UUID) -> list[RetrievedChunk]:
    return retrieve(session, "testing practices used", candidate_id, k=4, source_type_filter=["code_summary", "readme"])


def retrieve_skills_claimed_vs_demonstrated(session: Session, candidate_id: str | uuid.UUID) -> list[RetrievedChunk]:
    # Deliberately no source_type_filter: needs both resume claims and code-derived evidence
    return retrieve(session, "skills claimed vs. skills demonstrated in code", candidate_id, k=6)


def retrieve_prior_answer_about(session: Session, candidate_id: str | uuid.UUID, topic: str) -> list[RetrievedChunk]:
    return retrieve(session, f"prior answer about {topic}", candidate_id, k=2, source_type_filter="transcript")