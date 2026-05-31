import uuid

from pydantic import BaseModel


class KnowledgeNodeResponse(BaseModel):
    id: uuid.UUID
    label: str
    node_type: str
    description: str | None
    confidence: float

    model_config = {"from_attributes": True}


class KnowledgeEdgeResponse(BaseModel):
    id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    relation_type: str
    weight: float
    evidence: str | None

    model_config = {"from_attributes": True}


class KnowledgeGraphResponse(BaseModel):
    nodes: list[KnowledgeNodeResponse]
    edges: list[KnowledgeEdgeResponse]


class KnowledgeNodeDetailResponse(BaseModel):
    node: KnowledgeNodeResponse
    edges: list[KnowledgeEdgeResponse]
