import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.db.session import Base


class PersonalityProfile(Base):
    __tablename__ = "personality_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("personality_profiles.id"), nullable=True)
    based_on_stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    traits = relationship("PersonalityTrait", back_populates="profile", cascade="all, delete-orphan")
    parent = relationship("PersonalityProfile", remote_side=[id], uselist=False)

    __table_args__ = (UniqueConstraint("version", "status", name="uq_profile_version_status"),)


class PersonalityTrait(Base):
    __tablename__ = "personality_traits"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("personality_profiles.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(32))
    trait_name: Mapped[str] = mapped_column(String(64))
    value: Mapped[dict] = mapped_column(JSONB)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_refs: Mapped[list | None] = mapped_column(ARRAY(UUID), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    profile = relationship("PersonalityProfile", back_populates="traits")

    __table_args__ = (UniqueConstraint("profile_id", "category", "trait_name", name="uq_trait_profile_cat_name"),)


class PersonalityChangelog(Base):
    __tablename__ = "personality_changelog"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("personality_profiles.id", ondelete="CASCADE"))
    change_type: Mapped[str] = mapped_column(String(16))
    previous_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_traits: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
