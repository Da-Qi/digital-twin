"""pgvector operations for storing and querying embeddings."""

import json
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.embedder import embedder


async def insert_chunks(
    db: AsyncSession,
    document_id: str,
    chunks: list[dict],
    embeddings: list[list[float]],
):
    """Insert document chunks with embeddings into pgvector."""
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        await db.execute(
            text("""
                INSERT INTO document_chunks (id, document_id, chunk_index, content, token_count, embedding, metadata, created_at)
                VALUES (:id, :document_id, :chunk_index, :content, :token_count, CAST(:embedding AS vector), :metadata, NOW())
            """),
            {
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "chunk_index": i,
                "content": chunk["content"],
                "token_count": len(chunk["content"]) // 4,
                "embedding": str(emb),
                "metadata": json.dumps(chunk.get("metadata", {})),
            },
        )
    await db.flush()


async def search_document_chunks(
    db: AsyncSession, query_embedding: list[float], top_k: int = 8, min_similarity: float = 0.65
) -> list[dict]:
    """Search document chunks by cosine similarity."""
    result = await db.execute(
        text("""
            SELECT content, metadata, 1 - (embedding <=> CAST(:query AS vector)) AS similarity
            FROM document_chunks
            WHERE 1 - (embedding <=> CAST(:query AS vector)) > :min_sim
            ORDER BY embedding <=> CAST(:query AS vector)
            LIMIT :top_k
        """),
        {
            "query": str(query_embedding),
            "top_k": top_k,
            "min_sim": min_similarity,
        },
    )
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def search_memories(db: AsyncSession, query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """Search memory entries by cosine similarity."""
    result = await db.execute(
        text("""
            SELECT id, content, memory_type, importance,
                   1 - (embedding <=> CAST(:query AS vector)) AS similarity
            FROM memory_entries
            WHERE NOT consolidated
            ORDER BY embedding <=> CAST(:query AS vector)
            LIMIT :top_k
        """),
        {
            "query": str(query_embedding),
            "top_k": top_k,
        },
    )
    rows = result.mappings().all()
    return [dict(row) for row in rows]
