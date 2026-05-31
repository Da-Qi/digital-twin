"""Query-time retrieval combining document chunks, memories, and knowledge."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.embedder import embedder
from app.services.rag.vector_store import search_document_chunks, search_memories, search_knowledge_nodes

logger = logging.getLogger(__name__)


def _log_error(source: str, exc: Exception) -> None:
    """Log a per-source retrieval failure."""
    logger.warning("RAG search failed for %s: %s", source, exc)


async def retrieve_context(query: str, db: AsyncSession) -> dict:
    """Retrieve relevant context from all sources for a given query."""
    query_embedding = embedder.encode_query(query).tolist()

    # Parallel searches with error isolation
    chunks_task = search_document_chunks(db, query_embedding, top_k=8)
    memories_task = search_memories(db, query_embedding, top_k=5)
    nodes_task = search_knowledge_nodes(db, query_embedding, top_k=5)

    results = await asyncio.gather(chunks_task, memories_task, nodes_task, return_exceptions=True)
    chunks = results[0] if not isinstance(results[0], Exception) else _log_error("document_chunks", results[0]) or []
    memories = results[1] if not isinstance(results[1], Exception) else _log_error("memories", results[1]) or []
    nodes = results[2] if not isinstance(results[2], Exception) else _log_error("knowledge_nodes", results[2]) or []

    logger.info(
        "RAG context for %r: %d chunks, %d memories, %d knowledge nodes",
        query[:50], len(chunks), len(memories), len(nodes),
    )
    if nodes:
        labels = [n["label"] for n in nodes]
        logger.info("Knowledge nodes matched: %s", labels)

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

    if nodes:
        context_parts.append("=== KNOWLEDGE GRAPH ===")
        for node in nodes:
            context_parts.append(
                f"[{node['node_type']}] {node['label']} "
                f"(similarity: {node['similarity']:.2f}): {node['description']}"
            )

    return {
        "context": "\n\n".join(context_parts) if context_parts else "",
        "memory_count": len(memories),
        "chunk_count": len(chunks),
        "node_count": len(nodes),
    }
