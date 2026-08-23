"""
Step 4.3 — Retrieval function

retrieve(query, candidate_id, k=4, source_type_filter=None):
  - embeds the query
  - runs cosine similarity search scoped to that candidate's rows only
    (user_id = candidate_id — this is what replaces "one Chroma collection
    per candidate": row-level scoping via an indexed column)
  - optionally filtered by source_type
  - applies the 0.35 similarity floor from the plan; anything that doesn't
    clear it is dropped, so the caller (Step 5's agent) can fall back to
    the seed/fallback question bank instead of grounding on noise.

Uses the `pgvector` package's Vector comparator (cosine_distance), which is
what your HNSW index (vector_cosine_ops) is built to accelerate.
"""

from __future__ import annotations

from dataclasses import dataclass

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


def retrieve(
    session: Session,
    query: str,
    candidate_id: str,
    k: int = 4,
    source_type_filter: str | None = None,
) -> list[RetrievedChunk]:
    """
    Returns up to `k` chunks for this candidate, ranked by cosine
    similarity, filtered to similarity >= SIMILARITY_FLOOR (0.35).
    Returns an empty list if nothing clears the floor — callers must
    handle that by falling back to the seed/fallback question bank
    rather than treating an empty list as an error.
    """
    query_vec = embed_texts([query])[0]

    # embeddings.py stores normalize_embeddings=True vectors, so
    # cosine_distance = 1 - cosine_similarity here.
    distance_expr = RagDocument.embedding.cosine_distance(query_vec)
    similarity_expr = (1 - distance_expr).label("similarity")

    stmt = (
        select(RagDocument, similarity_expr)
        .where(RagDocument.user_id == candidate_id)
        .where(distance_expr <= (1 - SIMILARITY_FLOOR))  # push the floor into the index scan
        .order_by(distance_expr)
        .limit(k)
    )

    if source_type_filter is not None:
        stmt = stmt.where(RagDocument.source_type == source_type_filter)

    rows = session.execute(stmt).all()

    return [
        RetrievedChunk(
            chunk_id=doc.chunk_id,
            source_type=doc.source_type,
            section=doc.source_ref or "",
            text=doc.content,
            similarity=float(similarity),
            repo_id=str(doc.repo_id) if doc.repo_id else None,
        )
        for doc, similarity in rows
    ]


# --- Convenience wrappers for the agent's typical query patterns (Step 5) ---


def retrieve_most_complex_project(session: Session, candidate_id: str) -> list[RetrievedChunk]:
    return retrieve(
        session, "candidate's most complex project", candidate_id, k=4, source_type_filter="code_summary"
    )


def retrieve_testing_practices(session: Session, candidate_id: str) -> list[RetrievedChunk]:
    return retrieve(session, "testing practices used", candidate_id, k=4, source_type_filter="code_summary")


def retrieve_skills_claimed_vs_demonstrated(session: Session, candidate_id: str) -> list[RetrievedChunk]:
    # Deliberately no source_type_filter: this needs both resume claims
    # and code-derived evidence in the same result set.
    return retrieve(session, "skills claimed vs. skills demonstrated in code", candidate_id, k=4)


def retrieve_prior_answer_about(session: Session, candidate_id: str, topic: str) -> list[RetrievedChunk]:
    # Only makes sense once transcript turns are also being written into
    # rag_documents as source_type="transcript" (not part of Step 4's
    # scope — that lands when Step 5's session loop persists turns).
    return retrieve(session, f"prior answer about {topic}", candidate_id, k=2, source_type_filter="transcript")