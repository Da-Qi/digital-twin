import uuid
from datetime import datetime

from pydantic import BaseModel


class FeedbackCreate(BaseModel):
    target_message_id: uuid.UUID
    feedback_type: str = "explicit"
    classification: str | None = None
    user_input: str | None = None
    extracted_correction: dict | None = None


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    feedback_type: str
    classification: str | None
    applied_to: list | None
    handled_in_message: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
