"""
Step 4.2 — Embeddings & storage

Embeds chunks from chunking.py with sentence-transformers and
upserts them into the `rag_documents` table (pgvector, 384-dim, HNSW index)
from your database schema.

Stores rich JSONB metadata, candidate UUID, repo UUID, source_ref, token count,
and handles idempotent upserting on the `unique_profile_chunk` constraint.

Model: sentence-transformers/all-MiniLM-L6-v2 (384-dim, local, no API cost —
matches VECTOR(384) in your schema exactly).
"""

import os
import uuid
from functools import lru_cache
from typing import Any
from dotenv import load_dotenv

load_dotenv()

from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from db.models import RagDocument
try:
    from rag.chunking import count_tokens
except ImportError:
    from chunking import count_tokens

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def get_embedding_model():
    """
    Loaded once per process (model load is cached, not reconstructed per request).
    FastAPI: call this once at app startup to warm the cache.
    Automatically authenticates with Hugging Face Hub using your token.
    """
    from sentence_transformers import SentenceTransformer
    hf_token = os.environ.get("HUGGING_FACE_TOKEN", "").strip()

    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
        try:
            return SentenceTransformer(EMBEDDING_MODEL_NAME, token=hf_token)
        except TypeError:
            pass

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embed a list of strings. Returns one 384-dim vector per input."""
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
    return vectors.tolist()


def store_chunks(session: Session, chunks: list[dict[str, Any]] | list[Any]) -> int:
    """
    Embeds and upserts a list of chunk dicts or Chunk dataclass instances
    (as produced by chunking.build_all_chunks or chunk_transcript) into rag_documents.

    Upsert key: (user_id, chunk_id) — matches the unique_profile_chunk
    constraint, so re-running the pipeline for a candidate overwrites
    stale chunks cleanly instead of duplicating them.

    Tombstoning (Task 8):
    For each (candidate_id, source_type) present in the incoming batch,
    diffs the new batch's chunk_ids against what's currently stored with
    deleted_at IS NULL. Any stored chunk_id not present in the new batch is
    soft-deleted (deleted_at = func.now()). Re-ingested chunks have deleted_at
    reset to NULL.

    Stores rich JSONB metadata (skills, repo URLs, metric scores, project details).
    Returns the number of rows written.
    """
    if not chunks:
        return 0

    norm_chunks: list[dict[str, Any]] = [
        c.to_dict() if hasattr(c, "to_dict") else c for c in chunks
    ]

    # 1. Diff and tombstone stale chunks for each (candidate_id, source_type) pair
    from collections import defaultdict
    incoming_by_pair: dict[tuple[uuid.UUID, str], set[str]] = defaultdict(set)
    for chunk in norm_chunks:
        user_id_raw = chunk["candidate_id"]
        u_uuid = uuid.UUID(str(user_id_raw)) if not isinstance(user_id_raw, uuid.UUID) else user_id_raw
        st = chunk["source_type"]
        cid = chunk["chunk_id"]
        incoming_by_pair[(u_uuid, st)].add(cid)

    for (cand_uuid, st), new_ids in incoming_by_pair.items():
        existing_stmt = select(RagDocument.chunk_id).where(
            RagDocument.user_id == cand_uuid,
            RagDocument.source_type == st,
            RagDocument.deleted_at.is_(None),
        )
        stored_ids = set(session.scalars(existing_stmt).all())
        stale_ids = stored_ids - new_ids
        if stale_ids:
            tombstone_stmt = (
                update(RagDocument)
                .where(
                    RagDocument.user_id == cand_uuid,
                    RagDocument.source_type == st,
                    RagDocument.chunk_id.in_(list(stale_ids)),
                )
                .values(deleted_at=func.now())
            )
            session.execute(tombstone_stmt)

    # 2. Embed and upsert incoming batch
    texts = [c["text"] for c in norm_chunks]
    embeddings = embed_texts(texts)

    rows = []
    for chunk, embedding in zip(norm_chunks, embeddings):
        token_count = max(1, count_tokens(chunk["text"]))
        raw_meta = chunk.get("metadata")
        metadata: dict[str, Any] = dict(raw_meta) if isinstance(raw_meta, dict) else {}
        metadata.setdefault("section", chunk.get("section", ""))

        repo_id_raw = chunk.get("repo_id")
        repo_id_uuid = uuid.UUID(str(repo_id_raw)) if repo_id_raw else None

        user_id_raw = chunk["candidate_id"]
        user_id_uuid = uuid.UUID(str(user_id_raw)) if not isinstance(user_id_raw, uuid.UUID) else user_id_raw

        rows.append(
            {
                "id": uuid.uuid4(),
                "user_id": user_id_uuid,
                "source_type": chunk["source_type"],
                "chunk_id": chunk["chunk_id"],
                "content": chunk["text"],
                "metadata_": metadata,
                "embedding": embedding,
                "source_ref": chunk.get("section", ""),
                "repo_id": repo_id_uuid,
                "token_count": token_count,
                "deleted_at": None,
            }
        )

    stmt = pg_insert(RagDocument.__table__).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="unique_profile_chunk",
        set_={
            "content": stmt.excluded.content,
            "metadata_": stmt.excluded.metadata_,
            "embedding": stmt.excluded.embedding,
            "source_ref": stmt.excluded.source_ref,
            "repo_id": stmt.excluded.repo_id,
            "token_count": stmt.excluded.token_count,
            "deleted_at": None,
        },
    )
    session.execute(stmt)
    session.commit()
    return len(rows)


def clear_candidate_index(session: Session, candidate_id: str | uuid.UUID) -> int:
    """
    Deletes all rag_documents rows for a candidate. Useful before a full
    re-index (e.g. resume replaced, GitHub re-scraped) so stale chunks
    don't linger under different chunk_ids.
    """
    c_uuid = uuid.UUID(str(candidate_id)) if not isinstance(candidate_id, uuid.UUID) else candidate_id
    result = session.execute(
        delete(RagDocument).where(RagDocument.user_id == c_uuid)
    )
    session.commit()
    return result.rowcount or 0