import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.feedback import FeedbackLog
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(body: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    feedback = FeedbackLog(
        target_message_id=body.target_message_id,
        feedback_type=body.feedback_type,
        classification=body.classification,
        user_input=body.user_input,
        extracted_correction=body.extracted_correction,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)
    return feedback


@router.get("", response_model=list[FeedbackResponse])
async def list_feedback(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FeedbackLog).order_by(FeedbackLog.created_at.desc()))
    return result.scalars().all()


@router.get("/stats")
async def feedback_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FeedbackLog))
    all_feedback = result.scalars().all()

    stats = {
        "total": len(all_feedback),
        "by_type": {},
        "by_classification": {},
    }
    for fb in all_feedback:
        stats["by_type"][fb.feedback_type] = stats["by_type"].get(fb.feedback_type, 0) + 1
        if fb.classification:
            stats["by_classification"][fb.classification] = stats["by_classification"].get(fb.classification, 0) + 1
    return stats
