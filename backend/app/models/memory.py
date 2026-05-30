import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime
from pgvector.sqlalchemy import Vector

from app.db.session import Base


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    memory_type: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    importance: Mapped[float] = mapped_column(Float, default=0.3)
    source_conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("conversations.id"), nullable=True)
    source_message_ids: Mapped[list | None] = mapped_column(ARRAY(UUID), default=list)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    consolidated: Mapped[bool] = mapped_column(Boolean, default=False)
    consolidated_into: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("memory_entries.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    access_count: Mapped[int] = mapped_column(Integer, default=0)
