"""Tests for memory extraction service."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.services.memory.extractor import (
    VALID_MEMORY_TYPES,
    extract_memories_from_conversation,
)


class TestConstants:
    def test_valid_memory_types(self):
        assert VALID_MEMORY_TYPES == {"fact", "preference", "event", "relationship", "opinion"}


class TestExtractMemories:
    @pytest.mark.asyncio
    async def test_skip_short_message(self):
        """Messages shorter than 10 characters should be skipped without calling LLM."""
        db = AsyncMock()
        result = await extract_memories_from_conversation(
            db=db,
            user_message="hi",
            assistant_message="Hello!",
            conversation_id=uuid.uuid4(),
            user_message_id=uuid.uuid4(),
            assistant_message_id=uuid.uuid4(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_skip_whitespace_only(self):
        db = AsyncMock()
        result = await extract_memories_from_conversation(
            db=db,
            user_message="   \n  ",
            assistant_message="Hello!",
            conversation_id=uuid.uuid4(),
            user_message_id=uuid.uuid4(),
            assistant_message_id=uuid.uuid4(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_llm_called_with_user_and_assistant_messages(self):
        """Verify LLM receives both user and assistant messages in prompt."""
        db = AsyncMock()
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])

        with (
            patch("app.services.memory.extractor.llm_service") as mock_llm,
            patch("app.services.memory.extractor.embedder", mock_embed),
        ):
            mock_llm.chat = AsyncMock(return_value="[]")
            await extract_memories_from_conversation(
                db=db,
                user_message="I just got promoted to senior engineer.",
                assistant_message="Congratulations! That's great news.",
                conversation_id=uuid.uuid4(),
                user_message_id=uuid.uuid4(),
                assistant_message_id=uuid.uuid4(),
            )

        mock_llm.chat.assert_called_once()
        args, _ = mock_llm.chat.call_args
        user_content = args[0][1]["content"]  # messages[1]["content"]
        assert "I just got promoted" in user_content
        assert "Congratulations" in user_content

    @pytest.mark.asyncio
    async def test_parses_valid_json_response(self):
        db = AsyncMock()
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])

        with (
            patch("app.services.memory.extractor.llm_service") as mock_llm,
            patch("app.services.memory.extractor.embedder", mock_embed),
        ):
            mock_llm.chat = AsyncMock(
                return_value=json.dumps([
                    {"content": "User was promoted to senior engineer", "memory_type": "fact", "importance": 0.7},
                ])
            )
            result = await extract_memories_from_conversation(
                db=db,
                user_message="I got promoted!",
                assistant_message="Congrats!",
                conversation_id=uuid.uuid4(),
                user_message_id=uuid.uuid4(),
                assistant_message_id=uuid.uuid4(),
            )

        assert len(result) == 1
        assert result[0].content == "User was promoted to senior engineer"
        assert result[0].memory_type == "fact"
        assert result[0].importance == 0.7

    @pytest.mark.asyncio
    async def test_filters_empty_content(self):
        db = AsyncMock()
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])

        with (
            patch("app.services.memory.extractor.llm_service") as mock_llm,
            patch("app.services.memory.extractor.embedder", mock_embed),
        ):
            mock_llm.chat = AsyncMock(
                return_value=json.dumps([
                    {"content": "", "memory_type": "fact", "importance": 0.5},
                    {"content": "  ", "memory_type": "fact", "importance": 0.5},
                    {"content": "Valid memory", "memory_type": "fact", "importance": 0.5},
                ])
            )
            result = await extract_memories_from_conversation(
                db=db,
                user_message="Some message with enough length here",
                assistant_message="Response",
                conversation_id=uuid.uuid4(),
                user_message_id=uuid.uuid4(),
                assistant_message_id=uuid.uuid4(),
            )

        assert len(result) == 1
        assert result[0].content == "Valid memory"

    @pytest.mark.asyncio
    async def test_filters_invalid_memory_types(self):
        db = AsyncMock()
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])

        with (
            patch("app.services.memory.extractor.llm_service") as mock_llm,
            patch("app.services.memory.extractor.embedder", mock_embed),
        ):
            mock_llm.chat = AsyncMock(
                return_value=json.dumps([
                    {"content": "Valid fact", "memory_type": "fact", "importance": 0.5},
                    {"content": "Invalid type", "memory_type": "gossip", "importance": 0.5},
                    {"content": "Also valid", "memory_type": "preference", "importance": 0.4},
                ])
            )
            result = await extract_memories_from_conversation(
                db=db,
                user_message="Some message with enough length here",
                assistant_message="Response",
                conversation_id=uuid.uuid4(),
                user_message_id=uuid.uuid4(),
                assistant_message_id=uuid.uuid4(),
            )

        assert len(result) == 2
        types = {e.memory_type for e in result}
        assert types == {"fact", "preference"}

    @pytest.mark.asyncio
    async def test_clamps_importance(self):
        db = AsyncMock()
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])

        with (
            patch("app.services.memory.extractor.llm_service") as mock_llm,
            patch("app.services.memory.extractor.embedder", mock_embed),
        ):
            mock_llm.chat = AsyncMock(
                return_value=json.dumps([
                    {"content": "Too low", "memory_type": "fact", "importance": -0.5},
                    {"content": "Too high", "memory_type": "fact", "importance": 1.5},
                    {"content": "Just right", "memory_type": "fact", "importance": 0.5},
                ])
            )
            result = await extract_memories_from_conversation(
                db=db,
                user_message="Some message with enough length here",
                assistant_message="Response",
                conversation_id=uuid.uuid4(),
                user_message_id=uuid.uuid4(),
                assistant_message_id=uuid.uuid4(),
            )

        assert len(result) == 3
        importances = [e.importance for e in result]
        assert importances == [0.0, 1.0, 0.5]

    @pytest.mark.asyncio
    async def test_non_array_response_returns_empty(self):
        """LLM returning a non-array JSON should be treated as empty."""
        db = AsyncMock()
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])

        with (
            patch("app.services.memory.extractor.llm_service") as mock_llm,
            patch("app.services.memory.extractor.embedder", mock_embed),
        ):
            mock_llm.chat = AsyncMock(return_value='{"content": "not an array"}')
            result = await extract_memories_from_conversation(
                db=db,
                user_message="Some message with enough length here",
                assistant_message="Response",
                conversation_id=uuid.uuid4(),
                user_message_id=uuid.uuid4(),
                assistant_message_id=uuid.uuid4(),
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_json_returns_empty(self):
        db = AsyncMock()
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])

        with (
            patch("app.services.memory.extractor.llm_service") as mock_llm,
            patch("app.services.memory.extractor.embedder", mock_embed),
        ):
            mock_llm.chat = AsyncMock(return_value="not even json")
            result = await extract_memories_from_conversation(
                db=db,
                user_message="Some message with enough length here",
                assistant_message="Response",
                conversation_id=uuid.uuid4(),
                user_message_id=uuid.uuid4(),
                assistant_message_id=uuid.uuid4(),
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_array_is_valid(self):
        db = AsyncMock()
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])

        with (
            patch("app.services.memory.extractor.llm_service") as mock_llm,
            patch("app.services.memory.extractor.embedder", mock_embed),
        ):
            mock_llm.chat = AsyncMock(return_value="[]")
            result = await extract_memories_from_conversation(
                db=db,
                user_message="Some message with enough length here",
                assistant_message="Response",
                conversation_id=uuid.uuid4(),
                user_message_id=uuid.uuid4(),
                assistant_message_id=uuid.uuid4(),
            )
        assert result == []
