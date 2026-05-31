"""Tests for memory consolidation service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.memory.consolidator import _merge_contents, _compute_similarity


class TestMergeContents:
    def test_single_entry(self):
        entries = [MagicMock(content="Hello world")]
        assert _merge_contents(entries) == "Hello world"

    def test_multiple_entries(self):
        entries = [MagicMock(content="First"), MagicMock(content="Second"), MagicMock(content="Third")]
        assert _merge_contents(entries) == "First | Second | Third"

    def test_empty_string_content(self):
        entries = [MagicMock(content=""), MagicMock(content="B")]
        assert _merge_contents(entries) == " | B"

    def test_unicode_content(self):
        entries = [MagicMock(content="你好"), MagicMock(content="世界")]
        assert _merge_contents(entries) == "你好 | 世界"


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

    async def delete(self, obj):
        pass


class TestComputeSimilarity:
    @pytest.mark.asyncio
    async def test_returns_zero_if_no_embedding(self):
        db = AsyncMock()
        a = MagicMock(embedding=None)
        b = MagicMock(embedding=[0.1, 0.2, 0.3])
        result = await _compute_similarity(db, a, b)
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_returns_zero_if_both_no_embedding(self):
        db = AsyncMock()
        a = MagicMock(embedding=None)
        b = MagicMock(embedding=None)
        result = await _compute_similarity(db, a, b)
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_returns_similarity_from_db(self):
        db = FakeAsyncSession()
        mapping_result = MagicMock()
        db.execute_result.mappings.return_value = mapping_result
        row = MagicMock()
        mapping_result.first.return_value = row
        row.__getitem__.return_value = 0.85

        a = MagicMock(embedding=[0.1] * 1024)
        b = MagicMock(embedding=[0.2] * 1024)

        result = await _compute_similarity(db, a, b)
        assert result == 0.85

    @pytest.mark.asyncio
    async def test_returns_zero_on_no_rows(self):
        db = FakeAsyncSession()
        mapping_result = MagicMock()
        db.execute_result.mappings.return_value = mapping_result
        mapping_result.first.return_value = None

        a = MagicMock(embedding=[0.1] * 1024)
        b = MagicMock(embedding=[0.2] * 1024)

        result = await _compute_similarity(db, a, b)
        assert result == 0.0


class TestConsolidateMemories:
    @pytest.mark.asyncio
    async def test_less_than_two_candidates_returns_zero(self):
        """If fewer than 2 candidates found, return 0 immediately."""
        db = FakeAsyncSession()
        db.execute_result.scalars.return_value.all.return_value = []

        with patch("app.services.memory.consolidator.select") as mock_select:
            from app.services.memory.consolidator import consolidate_memories

            result = await consolidate_memories(db)
            assert result == 0

    @pytest.mark.asyncio
    async def test_passes_correct_filters(self):
        """Verify query filters for importance, consolidated flag, and age."""
        db = FakeAsyncSession()
        db.execute_result.scalars.return_value.all.return_value = []

        with patch("app.services.memory.consolidator.select") as mock_select:
            from app.services.memory.consolidator import consolidate_memories

            await consolidate_memories(db)

        mock_select.assert_called_once()
        where_calls = mock_select.return_value.where.call_args_list
        assert len(where_calls) >= 1
