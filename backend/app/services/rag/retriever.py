"""Query-time retrieval combining document chunks, memories, and knowledge."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.embedder import embedder
from app.services.rag.vector_store import search_document_chunks, search_memories


async def retrieve_context(query: str, db: AsyncSession) -> dict:
    """Retrieve relevant context from all sources for a given query."""
    query_embedding = embedder.encode_query(query).tolist()

    # Parallel searches
    import asyncio

    chunks_task = search_document_chunks(db, query_embedding, top_k=8)
    memories_task = search_memories(db, query_embedding, top_k=5)

    chunks, memories = await asyncio.gather(chunks_task, memories_task)

    context_parts = []

    if memories:
        context_parts.append("=== RELEVANT MEMORIES ===")
        for mem in memories:
            context_parts.append(mem["content"])

    if chunks:
        context_parts.append("=== REFERENCED KNOWLEDGE ===")
        for chunk in chunks:
            source = chunk.get("metadata", {}).get("headings", [])
            header = f"[{', '.join(source)}]" if source else ""
            context_parts.append(f"{header}\n{chunk['content']}")

    return {
        "context": "\n\n".join(context_parts) if context_parts else "",
        "memory_count": len(memories),
        "chunk_count": len(chunks),
    }
