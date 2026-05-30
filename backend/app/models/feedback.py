import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from app.db.session import Base


class FeedbackLog(Base):
    __tablename__ = "feedback_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    feedback_type: Mapped[str] = mapped_column(String(16))
    classification: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("messages.id"), nullable=True)
    target_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("messages.id"), nullable=True)
    user_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_correction: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    applied_to: Mapped[list | None] = mapped_column(ARRAY(Text), default=list)
    handled_in_message: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("messages.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PersonalityUpdateProposal(Base):
    __tablename__ = "personality_update_proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    proposed_profile_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("personality_profiles.id", ondelete="CASCADE"))
    feedback_ids: Mapped[list] = mapped_column(ARRAY(UUID), default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
