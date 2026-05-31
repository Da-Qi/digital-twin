"""Feedback classification and routing service."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Message
from app.models.feedback import FeedbackLog
from app.services.llm import llm_service
from app.services.memory.extractor import create_memory_entry

CLASSIFICATION_SYSTEM_PROMPT = """You are a feedback classifier for a personal digital twin system. Your role is to understand why the user gave feedback on the assistant's response and classify it.

Classification categories:
- "factual_correction": The user corrected a factual error in the assistant's response
- "tone_preference": The user expressed how they prefer things to be said (tone, formality, verbosity, level of detail, style)
- "knowledge_gap": The user provided new information the system didn't know about the user or the world
- "boundary": The user set a limit on what topics to discuss, how to handle uncertainty, or what stance to take
- "other": None of the above

Analyze the feedback and respond with a JSON object:
{
  "classification": "<category>",
  "reason": "<one-sentence explanation>",
  "extracted_fact": "<if knowledge_gap or factual_correction, the corrected fact; otherwise null>"
}"""


async def classify_and_route_feedback(db: AsyncSession, feedback_entry: FeedbackLog) -> str:
    """Classify a feedback entry using DeepSeek and route to appropriate subsystem."""
    # Fetch original assistant message for context
    assistant_message = None
    if feedback_entry.target_message_id:
        result = await db.execute(select(Message).where(Message.id == feedback_entry.target_message_id))
        msg = result.scalar_one_or_none()
        if msg:
            assistant_message = msg.content

    user_input = feedback_entry.user_input or ""

    if not user_input.strip():
        return "other"

    messages = [
        {
            "role": "system",
            "content": CLASSIFICATION_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": f"Original assistant response:\n{assistant_message or '(unknown)'}\n\nUser feedback:\n{user_input}",
        },
    ]

    try:
        result = await llm_service.chat(messages, temperature=0.1, max_tokens=256)
        data = json.loads(result)
        classification = data.get("classification", "other")
        extracted_fact = data.get("extracted_fact")
    except (json.JSONDecodeError, Exception):
        classification = "other"
        extracted_fact = None

    valid = {"factual_correction", "tone_preference", "knowledge_gap", "boundary", "other"}
    if classification not in valid:
        classification = "other"

    feedback_entry.classification = classification
    if extracted_fact and classification in ("knowledge_gap", "factual_correction"):
        feedback_entry.extracted_correction = {"fact": extracted_fact}

    # Route to appropriate subsystem
    if classification == "knowledge_gap" and extracted_fact:
        await create_memory_entry(
            db=db,
            content=extracted_fact,
            memory_type="fact",
            importance=0.5,
            source_message_ids=(
                [feedback_entry.target_message_id] if feedback_entry.target_message_id else None
            ),
        )
        _mark_applied(feedback_entry, "memory")

    elif classification in ("tone_preference", "boundary"):
        _mark_applied(feedback_entry, "personality_analysis")

    elif classification == "factual_correction":
        _mark_applied(feedback_entry, "knowledge_graph")

    await db.flush()
    return classification


def _mark_applied(feedback_entry: FeedbackLog, target: str) -> None:
    current = feedback_entry.applied_to or []
    if target not in current:
        current.append(target)
    feedback_entry.applied_to = current
