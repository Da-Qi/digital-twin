import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    source_type: str
    authorship: str
    char_count: int
    chunk_count: int
    processing_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentChunkResponse(BaseModel):
    id: uuid.UUID
    chunk_index: int
    content: str
    token_count: int
    metadata: dict | None

    model_config = {"from_attributes": True}
