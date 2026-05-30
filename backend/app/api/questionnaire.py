"""Onboarding questionnaire API."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.personality import PersonalityProfile, PersonalityTrait
from app.schemas.questionnaire import QuestionnaireSubmit, QuestionnaireResponse
from app.services.personality.seed import seed_from_questionnaire

router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])


@router.post("/submit", response_model=QuestionnaireResponse, status_code=201)
async def submit_questionnaire(data: QuestionnaireSubmit, db: AsyncSession = Depends(get_db)):
    """Submit the onboarding personality questionnaire and create initial profile."""

    # Check if profile already exists
    result = await db.execute(
        select(PersonalityProfile).where(PersonalityProfile.status == "active").limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return QuestionnaireResponse(
            profile_id=str(existing.id),
            version=existing.version,
            trait_count=0,
            has_writing_sample=False,
        )

    profile = await seed_from_questionnaire(db, data.model_dump())

    # Query trait count directly to avoid lazy loading issues
    trait_count_result = await db.execute(
        select(PersonalityTrait).where(PersonalityTrait.profile_id == profile.id)
    )
    trait_count = len(trait_count_result.scalars().all())

    return QuestionnaireResponse(
        profile_id=str(profile.id),
        version=profile.version,
        trait_count=trait_count,
        has_writing_sample=bool(data.voice.get("sample", "").strip()),
    )


@router.get("/status")
async def questionnaire_status(db: AsyncSession = Depends(get_db)):
    """Check if the user has completed the onboarding questionnaire."""
    result = await db.execute(
        select(PersonalityProfile).where(PersonalityProfile.status == "active").limit(1)
    )
    profile = result.scalar_one_or_none()
    return {"completed": profile is not None}
