import uuid

from pydantic import BaseModel


class KnowledgeNodeResponse(BaseModel):
    id: uuid.UUID
    label: str
    node_type: str
    description: str | None
    confidence: float

    class Config:
        from_attributes = True


class KnowledgeEdgeResponse(BaseModel):
    id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    relation_type: str
    weight: float

    class Config:
        from_attributes = True


class KnowledgeGraphResponse(BaseModel):
    nodes: list[KnowledgeNodeResponse]
    edges: list[KnowledgeEdgeResponse]
