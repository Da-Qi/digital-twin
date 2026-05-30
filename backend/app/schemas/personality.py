import uuid
from datetime import datetime

from pydantic import BaseModel


class PersonalityTraitResponse(BaseModel):
    id: uuid.UUID
    category: str
    trait_name: str
    value: dict
    confidence: float
    evidence_refs: list | None

    class Config:
        from_attributes = True


class PersonalityProfileResponse(BaseModel):
    id: uuid.UUID
    version: int
    status: str
    summary: str | None
    based_on_stats: dict
    traits: list[PersonalityTraitResponse]
    created_at: datetime
    activated_at: datetime | None

    class Config:
        from_attributes = True


class ProfileDiffResponse(BaseModel):
    added: list[dict]
    modified: list[dict]
    removed: list[dict]
    diff_summary: str


class AnalyzeResponse(BaseModel):
    proposal_id: uuid.UUID | None
    based_on: dict
    changes: ProfileDiffResponse | None
    auto_approved: bool
