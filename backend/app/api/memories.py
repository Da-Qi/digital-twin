import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.memory import MemoryEntry
from app.schemas.memory import MemoryEntryResponse, MemorySearchResponse
from app.services.rag.embedder import embedder
from app.services.rag.vector_store import search_memories

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("/search", response_model=MemorySearchResponse)
async def search_memories_endpoint(
    q: str = Query(...),
    top_k: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    if not q.strip():
        return MemorySearchResponse(results=[], total=0)

    query_emb = embedder.encode_query(q).tolist()
    results = await search_memories(db, query_emb, top_k)
    return MemorySearchResponse(results=results, total=len(results))


@router.get("", response_model=list[MemoryEntryResponse])
async def list_memories(
    memory_type: str | None = None,
    consolidated: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(MemoryEntry).order_by(MemoryEntry.created_at.desc())
    if memory_type:
        query = query.where(MemoryEntry.memory_type == memory_type)
    if consolidated is not None:
        query = query.where(MemoryEntry.consolidated == consolidated)
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MemoryEntry).where(MemoryEntry.id == memory_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Memory not found")
    await db.delete(entry)
    await db.flush()


@router.post("/consolidate")
async def run_consolidation(db: AsyncSession = Depends(get_db)):
    from app.services.memory.consolidator import consolidate_memories

    count = await consolidate_memories(db)
    return {"consolidated": count}
