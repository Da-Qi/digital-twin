import uuid
from datetime import datetime

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    summary: str | None
    message_count: int
    token_count: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str
    stream: bool = True


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    token_count: int
    correction_flag: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MessageSendRequest(BaseModel):
    content: str
    stream: bool = True
