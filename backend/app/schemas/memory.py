import uuid
from datetime import datetime

from pydantic import BaseModel


class MemoryCreate(BaseModel):
    content: str
    memory_type: str
    importance: float | None = None
    source_conversation_id: uuid.UUID | None = None
    source_message_ids: list[uuid.UUID] | None = None


class MemoryEntryResponse(BaseModel):
    id: uuid.UUID
    memory_type: str
    content: str
    summary: str | None
    importance: float
    source_conversation_id: uuid.UUID | None
    source_message_ids: list | None
    consolidated: bool
    consolidated_into: uuid.UUID | None
    created_at: datetime
    accessed_at: datetime
    access_count: int

    model_config = {"from_attributes": True}


class MemorySearchResult(BaseModel):
    id: uuid.UUID
    content: str
    memory_type: str
    importance: float
    similarity: float


class MemorySearchResponse(BaseModel):
    results: list[MemorySearchResult]
    total: int
