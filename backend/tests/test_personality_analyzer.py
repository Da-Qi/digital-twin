"""Tests for personality analysis engine — pure functions and pipeline logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.personality.analyzer import (
    _empty_result,
    _format_feedback_for_prompt,
    _format_conversations_for_prompt,
)


class TestEmptyResult:
    def test_returns_expected_structure(self):
        result = _empty_result("Not enough data")
        assert result["proposal_id"] is None
        assert result["changes"] is None
        assert result["auto_approved"] is False
        assert result["message"] == "Not enough data"
        assert result["based_on"] == {"new_conversations": 0, "new_documents": 0, "new_corrections": 0}

    def test_includes_reason(self):
        result = _empty_result("No active profile")
        assert result["message"] == "No active profile"


class TestFormatFeedbackForPrompt:
    def test_empty(self):
        assert _format_feedback_for_prompt([]) == "(no recent feedback)"

    def test_single_entry(self):
        entry = MagicMock(classification="tone_preference", user_input="Be more concise")
        result = _format_feedback_for_prompt([entry])
        assert "[tone_preference]" in result
        assert "Be more concise" in result

    def test_includes_classification_prefix(self):
        entries = [
            MagicMock(classification="factual_correction", user_input="Wrong date"),
            MagicMock(classification="knowledge_gap", user_input="I work at Acme"),
        ]
        result = _format_feedback_for_prompt(entries)
        assert "[factual_correction] Wrong date" in result
        assert "[knowledge_gap] I work at Acme" in result

    def test_none_user_input(self):
        entry = MagicMock(classification="other", user_input=None)
        result = _format_feedback_for_prompt([entry])
        assert "[other] (no text)" in result

    def test_limit_to_10_entries(self):
        entries = [MagicMock(classification="other", user_input=f"Item {i}") for i in range(15)]
        result = _format_feedback_for_prompt(entries)
        lines = result.split("\n")
        assert len(lines) == 10

    def test_first_10_are_most_recent(self):
        entries = [MagicMock(classification="other", user_input=f"Item {i}") for i in range(15)]
        result = _format_feedback_for_prompt(entries)
        assert "Item 0" in result
        assert "Item 14" not in result


class TestFormatConversationsForPrompt:
    def test_empty(self):
        assert _format_conversations_for_prompt([]) == "(no recent conversations)"

    def test_single_conversation(self):
        conv = MagicMock(title="Hello World", message_count=3)
        result = _format_conversations_for_prompt([conv])
        assert "Hello World" in result
        assert "(3 messages)" in result

    def test_none_title(self):
        conv = MagicMock(title=None, message_count=5)
        result = _format_conversations_for_prompt([conv])
        assert "Untitled" in result
        assert "(5 messages)" in result

    def test_limit_to_10_with_overflow_message(self):
        convs = [MagicMock(title=f"Chat {i}", message_count=1) for i in range(15)]
        result = _format_conversations_for_prompt(convs)
        lines = result.split("\n")
        assert len(lines) == 11  # 10 convs + 1 overflow line
        assert "and 5 more" in result

    def test_under_10_no_overflow_message(self):
        convs = [MagicMock(title=f"Chat {i}", message_count=1) for i in range(3)]
        result = _format_conversations_for_prompt(convs)
        assert "more" not in result


class FakeAsyncSession:
    """A minimal fake for AsyncSession that makes await db.execute() work."""
    def __init__(self):
        self.execute_result = MagicMock()

    async def execute(self, *args, **kwargs):
        return self.execute_result

    async def flush(self):
        pass

    async def commit(self):
        pass

    def add(self, obj):
        pass

    async def delete(self, obj):
        pass


class TestAnalyzePersonality:
    @pytest.mark.asyncio
    async def test_no_active_profile_returns_early(self):
        """If no active profile, should return empty result without LLM call."""
        db = FakeAsyncSession()
        db.execute_result.scalar_one_or_none.return_value = None

        with patch("app.services.personality.analyzer.llm_service") as mock_llm:
            from app.services.personality.analyzer import analyze_personality

            res = await analyze_personality(db)
            assert res["proposal_id"] is None
            assert res["message"] == "No active personality profile found"
            mock_llm.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_pending_proposal_aborts(self):
        """If a pending proposal exists, should return early without LLM call."""
        db = FakeAsyncSession()

        # First call to scalar_one_or_none: return a profile (for get active profile)
        # Second call: return a proposal (for pending check)
        db.execute_result.scalar_one_or_none.side_effect = [
            MagicMock(),  # active profile exists
            MagicMock(),  # pending proposal exists
        ]

        with patch("app.services.personality.analyzer.llm_service") as mock_llm:
            from app.services.personality.analyzer import analyze_personality

            res = await analyze_personality(db)
            assert "pending proposal" in (res["message"] or "").lower()
            mock_llm.chat.assert_not_called()


class TestCopyTraitsAndApplyChanges:
    @pytest.mark.asyncio
    async def test_copies_all_traits(self):
        """Verify that _copy_traits_and_apply_changes creates traits for the target profile."""
        db = AsyncMock()
        source_trait_1 = MagicMock(
            category="personality", trait_name="openness",
            value={"score": 80}, confidence=0.8, evidence_refs=None,
        )
        source_trait_2 = MagicMock(
            category="communication", trait_name="formality",
            value={"score": 30}, confidence=0.6, evidence_refs=None,
        )
        source_profile = MagicMock(traits=[source_trait_1, source_trait_2])
        target_profile = MagicMock(id=MagicMock())

        with patch("app.services.personality.analyzer.PersonalityTrait") as mock_trait_cls:
            mock_trait_cls.return_value = MagicMock()
            from app.services.personality.analyzer import _copy_traits_and_apply_changes

            result = await _copy_traits_and_apply_changes(db, target_profile, source_profile, {})
            assert len(result) == 2
            assert "personality:openness" in result
            assert "communication:formality" in result
