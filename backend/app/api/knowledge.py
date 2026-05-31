import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.knowledge import KnowledgeNode, KnowledgeEdge
from app.schemas.knowledge import (
    KnowledgeGraphResponse,
    KnowledgeNodeResponse,
    KnowledgeEdgeResponse,
    KnowledgeNodeDetailResponse,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    node_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(KnowledgeNode)
    if node_type:
        query = query.where(KnowledgeNode.node_type == node_type)
    nodes_result = await db.execute(query.order_by(KnowledgeNode.label))
    nodes = nodes_result.scalars().all()

    node_ids = [n.id for n in nodes]
    if not node_ids:
        return KnowledgeGraphResponse(nodes=[], edges=[])

    edges_result = await db.execute(
        select(KnowledgeEdge).where(
            KnowledgeEdge.source_node_id.in_(node_ids),
            KnowledgeEdge.target_node_id.in_(node_ids),
        )
    )
    edges = edges_result.scalars().all()

    return KnowledgeGraphResponse(
        nodes=[KnowledgeNodeResponse.model_validate(n) for n in nodes],
        edges=[e for e in edges],
    )


@router.get("/nodes/{node_id}", response_model=KnowledgeNodeDetailResponse)
async def get_knowledge_node(node_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeNode).where(KnowledgeNode.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Knowledge node not found")

    # Find all edges where this node is source or target
    edge_result = await db.execute(
        select(KnowledgeEdge).where(
            (KnowledgeEdge.source_node_id == node_id) | (KnowledgeEdge.target_node_id == node_id)
        )
    )
    edges = edge_result.scalars().all()

    return KnowledgeNodeDetailResponse(
        node=KnowledgeNodeResponse.model_validate(node),
        edges=[KnowledgeEdgeResponse.model_validate(e) for e in edges],
    )


@router.get("/search")
async def search_knowledge(q: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(KnowledgeNode).where(KnowledgeNode.label.ilike(f"%{q}%")).limit(20)
    )
    return result.scalars().all()
