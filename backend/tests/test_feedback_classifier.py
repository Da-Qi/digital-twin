"""Tests for feedback classification service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.feedback.classifier import _mark_applied, classify_and_route_feedback


class TestMarkApplied:
    def test_adds_target_to_empty_list(self):
        feedback = MagicMock(applied_to=None)
        _mark_applied(feedback, "memory")
        assert feedback.applied_to == ["memory"]

    def test_adds_target_to_existing_list(self):
        feedback = MagicMock(applied_to=["personality_analysis"])
        _mark_applied(feedback, "memory")
        assert feedback.applied_to == ["personality_analysis", "memory"]

    def test_does_not_duplicate(self):
        feedback = MagicMock(applied_to=["memory"])
        _mark_applied(feedback, "memory")
        assert feedback.applied_to == ["memory"]

    def test_preserves_other_targets(self):
        feedback = MagicMock(applied_to=["memory", "personality_analysis"])
        _mark_applied(feedback, "knowledge_graph")
        assert feedback.applied_to == ["memory", "personality_analysis", "knowledge_graph"]


class FakeAsyncSession:
    """A minimal fake for AsyncSession that makes await db.execute() work."""
    def __init__(self):
        self.execute_result = MagicMock()

    async def execute(self, *args, **kwargs):
        return self.execute_result

    async def flush(self):
        pass

    def add(self, obj):
        pass


class TestClassifyAndRoute:
    @pytest.mark.asyncio
    async def test_other_classification_no_routing(self):
        """'other' classification should not set applied_to."""
        mock_feedback = MagicMock(
            user_input="Just saying thanks!",
            target_message_id=None,
            classification=None,
            applied_to=None,
        )
        db = FakeAsyncSession()
        with patch("app.services.feedback.classifier.llm_service") as mock_llm:
            mock_llm.chat = AsyncMock(
                return_value='{"classification": "other", "reason": "just thanks", "extracted_fact": null}'
            )
            result = await classify_and_route_feedback(db, mock_feedback)

        assert result == "other"
        assert mock_feedback.classification == "other"

    @pytest.mark.asyncio
    async def test_knowledge_gap_creates_memory(self):
        """knowledge_gap classification should create a memory entry and mark applied_to."""
        mock_feedback = MagicMock(
            user_input="I actually work at Google, not Facebook.",
            target_message_id="00000000-0000-0000-0000-000000000001",
            classification=None,
            applied_to=None,
        )
        db = FakeAsyncSession()
        with (
            patch("app.services.feedback.classifier.llm_service") as mock_llm,
            patch("app.services.feedback.classifier.create_memory_entry") as mock_create,
        ):
            mock_llm.chat = AsyncMock(
                return_value=(
                    '{"classification": "knowledge_gap", "reason": "user corrected workplace", '
                    '"extracted_fact": "User works at Google"}'
                )
            )
            result = await classify_and_route_feedback(db, mock_feedback)

        assert result == "knowledge_gap"
        assert mock_feedback.classification == "knowledge_gap"
        mock_create.assert_called_once()
        assert mock_feedback.applied_to == ["memory"]

    @pytest.mark.asyncio
    async def test_tone_preference_marks_personality(self):
        mock_feedback = MagicMock(
            user_input="Please be more concise in your responses.",
            target_message_id="00000000-0000-0000-0000-000000000001",
            classification=None,
            applied_to=None,
        )
        db = FakeAsyncSession()
        with patch("app.services.feedback.classifier.llm_service") as mock_llm:
            mock_llm.chat = AsyncMock(
                return_value=(
                    '{"classification": "tone_preference", "reason": "user prefers concise responses", '
                    '"extracted_fact": null}'
                )
            )
            result = await classify_and_route_feedback(db, mock_feedback)

        assert result == "tone_preference"
        assert mock_feedback.classification == "tone_preference"
        assert mock_feedback.applied_to == ["personality_analysis"]

    @pytest.mark.asyncio
    async def test_boundary_marks_personality(self):
        mock_feedback = MagicMock(
            user_input="I don't want to discuss politics.",
            target_message_id="00000000-0000-0000-0000-000000000001",
            classification=None,
            applied_to=None,
        )
        db = FakeAsyncSession()
        with patch("app.services.feedback.classifier.llm_service") as mock_llm:
            mock_llm.chat = AsyncMock(
                return_value=(
                    '{"classification": "boundary", "reason": "user set political boundary", '
                    '"extracted_fact": null}'
                )
            )
            result = await classify_and_route_feedback(db, mock_feedback)

        assert result == "boundary"
        assert mock_feedback.classification == "boundary"
        assert mock_feedback.applied_to == ["personality_analysis"]

    @pytest.mark.asyncio
    async def test_factual_correction_marks_knowledge_graph(self):
        mock_feedback = MagicMock(
            user_input="Actually Python was released in 1991, not 1995.",
            target_message_id="00000000-0000-0000-0000-000000000001",
            classification=None,
            applied_to=None,
        )
        db = FakeAsyncSession()
        with patch("app.services.feedback.classifier.llm_service") as mock_llm:
            mock_llm.chat = AsyncMock(
                return_value=(
                    '{"classification": "factual_correction", "reason": "user corrected date", '
                    '"extracted_fact": "Python was released in 1991"}'
                )
            )
            result = await classify_and_route_feedback(db, mock_feedback)

        assert result == "factual_correction"
        assert mock_feedback.classification == "factual_correction"
        assert mock_feedback.applied_to == ["knowledge_graph"]

    @pytest.mark.asyncio
    async def test_empty_user_input_returns_other(self):
        """Empty or whitespace-only input should return 'other' without calling LLM."""
        mock_feedback = MagicMock(user_input="  ", target_message_id=None)
        db = FakeAsyncSession()
        with patch("app.services.feedback.classifier.llm_service") as mock_llm:
            result = await classify_and_route_feedback(db, mock_feedback)

        assert result == "other"
        mock_llm.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_error_falls_back_to_other(self):
        """LLM failure should not crash — fall back to 'other'."""
        mock_feedback = MagicMock(
            user_input="Something wrong here.",
            target_message_id="00000000-0000-0000-0000-000000000001",
            classification=None,
            applied_to=None,
        )
        db = FakeAsyncSession()
        with patch("app.services.feedback.classifier.llm_service") as mock_llm:
            mock_llm.chat = AsyncMock(side_effect=Exception("API error"))
            result = await classify_and_route_feedback(db, mock_feedback)

        assert result == "other"
        assert mock_feedback.classification == "other"
