import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.personality import PersonalityProfile, PersonalityTrait, PersonalityChangelog
from app.models.feedback import PersonalityUpdateProposal, FeedbackLog
from app.schemas.personality import PersonalityProfileResponse, AnalyzeResponse, ProfileDiffResponse

router = APIRouter(prefix="/personality", tags=["personality"])


@router.get("/current", response_model=PersonalityProfileResponse)
async def get_current_profile(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PersonalityProfile).options(selectinload(PersonalityProfile.traits)).where(PersonalityProfile.status == "active").order_by(PersonalityProfile.version.desc()).limit(1)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="No active personality profile found")
    return profile


@router.get("/versions", response_model=list[PersonalityProfileResponse])
async def list_versions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PersonalityProfile).options(selectinload(PersonalityProfile.traits)).order_by(PersonalityProfile.version.desc())
    )
    return result.scalars().all()


@router.get("/versions/{profile_id}", response_model=PersonalityProfileResponse)
async def get_version(profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PersonalityProfile).options(selectinload(PersonalityProfile.traits)).where(PersonalityProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_personality_endpoint(db: AsyncSession = Depends(get_db)):
    """Trigger personality analysis pipeline."""
    from app.services.personality.analyzer import analyze_personality as run_analysis

    result = await run_analysis(db)
    return AnalyzeResponse(
        proposal_id=result.get("proposal_id"),
        based_on=result["based_on"],
        changes=(
            ProfileDiffResponse(
                added=result["changes"]["added"],
                modified=result["changes"]["modified"],
                removed=result["changes"]["removed"],
                diff_summary=result["changes"]["diff_summary"],
            )
            if result.get("changes")
            else None
        ),
        auto_approved=result["auto_approved"],
        message=result.get("message"),
    )


@router.get("/proposals/pending")
async def list_pending_proposals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PersonalityUpdateProposal).where(PersonalityUpdateProposal.status == "pending")
    )
    return result.scalars().all()


@router.post("/proposals/{proposal_id}/approve", response_model=PersonalityProfileResponse)
async def approve_proposal(proposal_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PersonalityUpdateProposal).where(PersonalityUpdateProposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get proposed profile
    profile_result = await db.execute(
        select(PersonalityProfile).options(selectinload(PersonalityProfile.traits)).where(PersonalityProfile.id == proposal.proposed_profile_id)
    )
    profile = profile_result.scalar_one_or_none()

    # Archive current active
    await db.execute(
        select(PersonalityProfile)
        .where(PersonalityProfile.status == "active")
        .limit(1)
    )
    active_result = await db.execute(
        select(PersonalityProfile).where(PersonalityProfile.status == "active").limit(1)
    )
    active_profile = active_result.scalar_one_or_none()
    if active_profile:
        active_profile.status = "archived"

    # Activate proposed
    if profile:
        profile.status = "active"

    # Update proposal
    proposal.status = "approved"
    await db.flush()

    if not profile:
        raise HTTPException(status_code=404, detail="Proposed profile not found")
    return profile


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PersonalityUpdateProposal).where(PersonalityUpdateProposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal.status = "rejected"

    # Also mark the proposed profile as rejected
    profile_result = await db.execute(select(PersonalityProfile).where(PersonalityProfile.id == proposal.proposed_profile_id))
    profile = profile_result.scalar_one_or_none()
    if profile:
        profile.status = "rejected"

    await db.flush()
    return {"status": "rejected"}
