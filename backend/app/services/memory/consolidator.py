"""Memory consolidation service — merge related low-importance memories."""

from datetime import datetime, timezone, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryEntry
from app.services.memory.extractor import create_memory_entry

CONSOLIDATION_WINDOW_HOURS = 24
CONSOLIDATION_SIMILARITY_THRESHOLD = 0.75


async def consolidate_memories(db: AsyncSession) -> int:
    """Consolidate old, low-importance memories into merged entries."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=CONSOLIDATION_WINDOW_HOURS)

    result = await db.execute(
        select(MemoryEntry).where(
            MemoryEntry.importance < 0.3,
            MemoryEntry.consolidated == False,
            MemoryEntry.created_at < cutoff,
        ).order_by(MemoryEntry.memory_type, MemoryEntry.created_at).limit(50)
    )
    candidates = result.scalars().all()

    if len(candidates) < 2:
        return 0

    grouped: dict[str, list[MemoryEntry]] = {}
    for c in candidates:
        grouped.setdefault(c.memory_type, []).append(c)

    consolidations = 0
    for mem_type, entries in grouped.items():
        if len(entries) < 2:
            continue

        i = 0
        while i < len(entries):
            j = i + 1
            while j < len(entries):
                sim = await _compute_similarity(db, entries[i], entries[j])
                if sim >= CONSOLIDATION_SIMILARITY_THRESHOLD:
                    j += 1
                else:
                    break

            if j - i >= 2:
                cluster = entries[i:j]
                merged_content = _merge_contents(cluster)
                avg_importance = sum(e.importance for e in cluster) / len(cluster)

                consolidated_entry = await create_memory_entry(
                    db=db,
                    content=merged_content,
                    memory_type=mem_type,
                    importance=min(0.5, avg_importance + 0.1),
                    summary=f"Consolidated from {len(cluster)} memories",
                )

                for entry in cluster:
                    entry.consolidated = True
                    entry.consolidated_into = consolidated_entry.id

                consolidations += 1

            i = j

    await db.flush()
    return consolidations


def _merge_contents(entries: list[MemoryEntry]) -> str:
    return " | ".join(e.content for e in entries)


async def _compute_similarity(db: AsyncSession, a: MemoryEntry, b: MemoryEntry) -> float:
    if a.embedding is None or b.embedding is None:
        return 0.0
    result = await db.execute(
        text("SELECT 1 - (CAST(:emb_a AS vector) <=> CAST(:emb_b AS vector)) AS similarity"),
        {"emb_a": str(a.embedding), "emb_b": str(b.embedding)},
    )
    row = result.mappings().first()
    return row["similarity"] if row else 0.0
