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
from app.services.llm import llm_service
from app.services.rag.embedder import embedder
from app.services.rag import vector_store

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

    # Build messages array for LLM
    llm_messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for msg in history:
        llm_messages.append({"role": msg.role, "content": msg.content})

    if body.stream:
        return EventSourceResponse(_stream_response(conv_id, db, llm_messages))

    # Non-streaming fallback
    response_text = await llm_service.chat(llm_messages)
    assistant_msg = Message(
        conversation_id=conv_id, role="assistant", content=response_text, token_count=len(response_text) // 4
    )
    db.add(assistant_msg)
    conv.message_count += 1
    conv.token_count += assistant_msg.token_count
    await db.commit()

    return {"id": str(assistant_msg.id), "role": "assistant", "content": response_text}


async def _stream_response(conv_id: uuid.UUID, db: AsyncSession, llm_messages: list[dict]):
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

        yield {"event": "metadata", "data": {"message_id": str(msg.id), "token_count": msg.token_count}}
        yield {"event": "done", "data": ""}
    except Exception as e:
        yield {"event": "error", "data": str(e)}
