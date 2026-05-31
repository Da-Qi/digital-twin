"""Memory extraction from conversation turns and utility for creating memory entries."""

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryEntry
from app.services.rag.embedder import embedder
from app.services.llm import llm_service

VALID_MEMORY_TYPES = {"fact", "preference", "event", "relationship", "opinion"}

EXTRACTION_SYSTEM_PROMPT = """You are a memory extraction engine for a personal digital twin. Your task is to extract noteworthy information about the user from a conversation turn.

Extract memories of these types:
- "fact": Objective facts about the user (job, location, experiences, skills, history)
- "preference": User preferences (likes, dislikes, communication preferences, habits)
- "event": Past or planned events involving the user
- "relationship": People or relationships the user mentioned
- "opinion": Strong opinions, beliefs, or values expressed

For each memory, provide:
- content (string): A concise, self-contained statement of what to remember
- memory_type (string): One of the five types above
- importance (float 0.0-1.0): How important is this to remember? Base this on:
  * 0.1-0.3: Minor details, casual mentions
  * 0.4-0.6: Moderately important preferences or facts
  * 0.7-0.8: Important values, recurring patterns, significant life events
  * 0.9-1.0: Core identity traits, fundamental beliefs, critical boundaries

Only extract genuinely noteworthy information. Skip greetings, pleasantries, and trivial exchanges. If nothing is worth remembering, respond with an empty array [].

Respond ONLY with a valid JSON array. No other text."""


async def create_memory_entry(
    db: AsyncSession,
    content: str,
    memory_type: str,
    importance: float = 0.3,
    source_conversation_id: uuid.UUID | None = None,
    source_message_ids: list[uuid.UUID] | None = None,
    summary: str | None = None,
) -> MemoryEntry:
    """Create a memory entry with embedding."""
    embedding = embedder.encode([content])[0].tolist()
    entry = MemoryEntry(
        memory_type=memory_type,
        content=content,
        summary=summary or content[:500],
        importance=importance,
        source_conversation_id=source_conversation_id,
        source_message_ids=source_message_ids or [],
        embedding=embedding,
    )
    db.add(entry)
    await db.flush()
    return entry


async def extract_memories_from_conversation(
    db: AsyncSession,
    user_message: str,
    assistant_message: str,
    conversation_id: uuid.UUID,
    user_message_id: uuid.UUID,
    assistant_message_id: uuid.UUID,
) -> list[MemoryEntry]:
    """Analyze a conversation turn and extract memory entries using DeepSeek."""
    if len(user_message.strip()) < 10:
        return []

    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": f"User: {user_message}\nAssistant: {assistant_message}"},
    ]

    try:
        result = await llm_service.chat(messages, temperature=0.1, max_tokens=1024)
        memories_data = json.loads(result)
    except (json.JSONDecodeError, Exception):
        return []

    if not isinstance(memories_data, list):
        return []

    entries: list[MemoryEntry] = []
    for mem in memories_data:
        content = (mem.get("content") or "").strip()
        memory_type = mem.get("memory_type", "fact")
        importance = float(mem.get("importance", 0.3))

        if not content or memory_type not in VALID_MEMORY_TYPES:
            continue
        importance = max(0.0, min(1.0, importance))

        entry = await create_memory_entry(
            db=db,
            content=content,
            memory_type=memory_type,
            importance=importance,
            source_conversation_id=conversation_id,
            source_message_ids=[user_message_id, assistant_message_id],
        )
        entries.append(entry)

    return entries
