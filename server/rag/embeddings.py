"""
Step 4.2 — Embeddings & storage

Embeds chunks from chunking.py (Step 4.1) with sentence-transformers and
upserts them into the `rag_documents` table (pgvector, 384-dim, HNSW index)
from your existing schema.

Note on the original plan doc: it suggested Chroma with one collection per
candidate_id. Since your schema already has rag_documents with a pgvector
column + a unique (user_id, chunk_id) constraint + HNSW index, we store
directly there instead — one fewer moving part, and per-candidate isolation
is handled by filtering on user_id (== candidate_id) at query time (4.3),
which is exactly what unique_profile_chunk and idx_rag_documents_user_source
are built for.

Model: sentence-transformers/all-MiniLM-L6-v2 (384-dim, local, no API cost —
matches VECTOR(384) in your schema exactly).
"""

from __future__ import annotations

import uuid
from functools import lru_cache

from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from db.models import RagDocument

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHARS_PER_TOKEN = 4  # matches chunking.py


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Loaded once per process (model load is the expensive part — cache it,
    don't reconstruct per request). FastAPI: call this once at app startup
    to warm the cache rather than paying the load cost on the first request.
    """
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embed a list of strings. Returns one 384-dim vector per input."""
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
    return vectors.tolist()


def store_chunks(session: Session, chunks: list[dict]) -> int:
    """
    Embeds and upserts a list of chunk dicts (as produced by
    chunking.build_all_chunks) into rag_documents.

    Upsert key: (user_id, chunk_id) — matches the unique_profile_chunk
    constraint, so re-running the pipeline for a candidate (e.g. after a
    resume re-upload) overwrites stale chunks instead of duplicating them.

    Returns the number of rows written.
    """
    if not chunks:
        return 0

    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    rows = []
    for chunk, embedding in zip(chunks, embeddings):
        token_count = max(1, len(chunk["text"]) // CHARS_PER_TOKEN)
        rows.append(
            {
                "id": uuid.uuid4(),
                "user_id": chunk["candidate_id"],
                "source_type": chunk["source_type"],
                "chunk_id": chunk["chunk_id"],
                "content": chunk["text"],
                "metadata": {"section": chunk["section"]},
                "embedding": embedding,
                "source_ref": chunk["section"],
                "repo_id": chunk.get("repo_id"),
                "token_count": token_count,
            }
        )

    stmt = pg_insert(RagDocument).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="unique_profile_chunk",
        set_={
            "content": stmt.excluded.content,
            "metadata": stmt.excluded.metadata,
            "embedding": stmt.excluded.embedding,
            "source_ref": stmt.excluded.source_ref,
            "repo_id": stmt.excluded.repo_id,
            "token_count": stmt.excluded.token_count,
        },
    )
    session.execute(stmt)
    session.commit()
    return len(rows)


def clear_candidate_index(session: Session, candidate_id: str) -> int:
    """
    Deletes all rag_documents rows for a candidate. Useful before a full
    re-index (e.g. resume replaced, GitHub re-scraped) so stale chunks
    don't linger under different chunk_ids than what build_all_chunks
    would now generate.
    """
    result = session.execute(
        select(RagDocument.id).where(RagDocument.user_id == candidate_id)
    )
    ids = [row[0] for row in result]
    if ids:
        session.query(RagDocument).filter(RagDocument.id.in_(ids)).delete(synchronize_session=False)
        session.commit()
    return len(ids)