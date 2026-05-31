import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.db.session import get_db, async_session_factory
from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
    MessageSendRequest,
)
import asyncio

from app.services.llm import llm_service
from app.services.personality.prompt_builder import build_personality_prompt
from app.services.rag.embedder import embedder
from app.services.rag import vector_store
from app.services.rag.retriever import retrieve_context
from app.services.memory.extractor import extract_memories_from_conversation

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).where(Conversation.is_archived == False).order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(body: ConversationCreate, db: AsyncSession = Depends(get_db)):
    conv = Conversation(title=body.title)
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv


@router.get("/{conv_id}", response_model=ConversationResponse)
async def get_conversation(conv_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conv_id}", status_code=204)
async def delete_conversation(conv_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.is_archived = True
    await db.flush()


@router.get("/{conv_id}/messages", response_model=list[MessageResponse])
async def list_messages(conv_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
    )
    return result.scalars().all()


@router.post("/{conv_id}/messages")
async def send_message(conv_id: uuid.UUID, body: MessageSendRequest, db: AsyncSession = Depends(get_db)):
    # Verify conversation exists
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Store user message
    user_msg = Message(conversation_id=conv_id, role="user", content=body.content, token_count=len(body.content) // 4)
    db.add(user_msg)
    conv.message_count += 1
    conv.token_count += user_msg.token_count
    await db.commit()

    # Gather conversation history
    history_result = await db.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at).limit(50)
    )
    history = history_result.scalars().all()

    # Build personality-aware system prompt
    personality_prompt = await build_personality_prompt(db)

    # Retrieve relevant context from memories + documents
    context = await retrieve_context(body.content, db)

    # Combine system prompt with context
    system_parts = []
    if personality_prompt:
        system_parts.append(personality_prompt)
    if context["context"]:
        system_parts.append(f"Relevant context about the user:\n{context['context']}")

    system_content = "\n\n---\n\n".join(system_parts) if system_parts else "You are a helpful assistant."

    # Build messages array for LLM
    llm_messages = [{"role": "system", "content": system_content}]
    for msg in history:
        llm_messages.append({"role": msg.role, "content": msg.content})

    if body.stream:
        return EventSourceResponse(_stream_response(conv_id, body.content, llm_messages))

    # Non-streaming fallback
    response_text = await llm_service.chat(llm_messages)
    assistant_msg = Message(
        conversation_id=conv_id, role="assistant", content=response_text, token_count=len(response_text) // 4
    )
    db.add(assistant_msg)
    conv.message_count += 1
    conv.token_count += assistant_msg.token_count
    await db.commit()

    # Extract memories from this exchange
    try:
        await extract_memories_from_conversation(
            db=db,
            user_message=body.content,
            assistant_message=response_text,
            conversation_id=conv_id,
            user_message_id=user_msg.id,
            assistant_message_id=assistant_msg.id,
        )
        await db.commit()
    except Exception:
        pass

    return {"id": str(assistant_msg.id), "role": "assistant", "content": response_text}


async def _stream_response(conv_id: uuid.UUID, user_message_content: str, llm_messages: list[dict]):
    """Stream the LLM response token by token via SSE."""
    full_content = ""
    try:
        async for event in llm_service.chat_stream(llm_messages):
            if event["type"] == "token":
                full_content += event["token"]
                yield {"event": "token", "data": event["token"]}
            elif event["type"] == "done":
                break

        # Store the complete assistant message
        async with async_session_factory() as session:
            msg = Message(
                conversation_id=conv_id, role="assistant", content=full_content, token_count=len(full_content) // 4
            )
            session.add(msg)
            await session.flush()
            # Update conversation
            result = await session.execute(select(Conversation).where(Conversation.id == conv_id))
            conv = result.scalar_one()
            conv.message_count += 1
            conv.token_count += msg.token_count
            await session.commit()

        # Extract memories in the background
        asyncio.create_task(
            _extract_memories_background(
                conv_id=conv_id,
                user_content=user_message_content,
                assistant_content=full_content,
                assistant_msg_id=msg.id,
            )
        )

        yield {"event": "metadata", "data": {"message_id": str(msg.id), "token_count": msg.token_count}}
        yield {"event": "done", "data": ""}
    except Exception as e:
        yield {"event": "error", "data": str(e)}


async def _extract_memories_background(
    conv_id: uuid.UUID, user_content: str, assistant_content: str, assistant_msg_id: uuid.UUID
):
    """Background task for memory extraction to not block the SSE response."""
    try:
        async with async_session_factory() as session:
            # Find the user message for this turn (most recent user msg in this conv)
            result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conv_id, Message.role == "user")
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            user_msg = result.scalar_one_or_none()
            if user_msg:
                await extract_memories_from_conversation(
                    db=session,
                    user_message=user_content,
                    assistant_message=assistant_content,
                    conversation_id=conv_id,
                    user_message_id=user_msg.id,
                    assistant_message_id=assistant_msg_id,
                )
                await session.commit()
    except Exception:
        pass
