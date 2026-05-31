"""Tests for personality prompt builder."""

from unittest.mock import MagicMock

import pytest

from app.services.personality.prompt_builder import build_personality_prompt


def _make_trait(category: str, name: str, value: dict, confidence: float = 0.5):
    return MagicMock(
        category=category,
        trait_name=name,
        value=value,
        confidence=confidence,
    )


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


class TestBuildPersonalityPrompt:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_profile(self):
        """No active profile should return None."""
        db = FakeAsyncSession()
        db.execute_result.scalar_one_or_none.return_value = None
        prompt = await build_personality_prompt(db)
        assert prompt is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_traits(self):
        """Profile exists but has no traits should return None."""
        db = FakeAsyncSession()
        profile = MagicMock(traits=[])
        db.execute_result.scalar_one_or_none.return_value = profile
        prompt = await build_personality_prompt(db)
        assert prompt is None

    @pytest.mark.asyncio
    async def test_includes_personality_section(self):
        """Personality traits should produce a '## Personality' heading."""
        db = FakeAsyncSession()
        traits = [_make_trait("personality", "openness", {"score": 80, "label": "high", "description": "Embraces new ideas"})]
        profile = MagicMock(traits=traits)
        db.execute_result.scalar_one_or_none.return_value = profile

        prompt = await build_personality_prompt(db)
        assert prompt is not None
        assert "## Personality" in prompt
        assert "Openness" in prompt
        assert "Embraces new ideas" in prompt

    @pytest.mark.asyncio
    async def test_includes_communication_section(self):
        db = FakeAsyncSession()
        traits = [_make_trait("communication", "formality", {"score": 30, "label": "informal", "description": "Casual tone"})]
        profile = MagicMock(traits=traits)
        db.execute_result.scalar_one_or_none.return_value = profile

        prompt = await build_personality_prompt(db)
        assert "## Communication Style" in prompt
        assert "Formality" in prompt
        assert "Casual tone" in prompt

    @pytest.mark.asyncio
    async def test_items_value_format(self):
        """Knowledge traits with 'items' value should render as comma-separated list."""
        db = FakeAsyncSession()
        traits = [_make_trait("knowledge", "programming", {"items": ["Python", "Rust", "TypeScript"]})]
        profile = MagicMock(traits=traits)
        db.execute_result.scalar_one_or_none.return_value = profile

        prompt = await build_personality_prompt(db)
        assert "Programming" in prompt
        assert "Python, Rust, TypeScript" in prompt

    @pytest.mark.asyncio
    async def test_text_value_format(self):
        """Traits with 'text' value should render as text."""
        db = FakeAsyncSession()
        traits = [_make_trait("values", "privacy", {"text": "Prioritizes data ownership"})]
        profile = MagicMock(traits=traits)
        db.execute_result.scalar_one_or_none.return_value = profile

        prompt = await build_personality_prompt(db)
        assert "Privacy" in prompt
        assert "Prioritizes data ownership" in prompt

    @pytest.mark.asyncio
    async def test_type_value_format(self):
        """Traits with 'type' value should render type + label."""
        db = FakeAsyncSession()
        traits = [_make_trait("reasoning", "style", {"type": "analytical", "label": "Data-driven"})]
        profile = MagicMock(traits=traits)
        db.execute_result.scalar_one_or_none.return_value = profile

        prompt = await build_personality_prompt(db)
        assert "Style" in prompt
        assert "Data-driven" in prompt

    @pytest.mark.asyncio
    async def test_all_six_categories(self):
        """All six standard categories should produce proper headings."""
        db = FakeAsyncSession()
        traits = [
            _make_trait("personality", "t1", {"label": "A"}),
            _make_trait("communication", "t2", {"label": "B"}),
            _make_trait("reasoning", "t3", {"label": "C"}),
            _make_trait("values", "t4", {"label": "D"}),
            _make_trait("knowledge", "t5", {"items": ["E"]}),
            _make_trait("boundaries", "t6", {"label": "F"}),
        ]
        profile = MagicMock(traits=traits)
        db.execute_result.scalar_one_or_none.return_value = profile

        prompt = await build_personality_prompt(db)
        assert "## Personality" in prompt
        assert "## Communication Style" in prompt
        assert "## Reasoning & Decision Making" in prompt
        assert "## Values & Beliefs" in prompt
        assert "## Knowledge & Expertise" in prompt
        assert "## Boundaries & Preferences" in prompt
        assert "digital twin" in prompt.lower()

    @pytest.mark.asyncio
    async def test_trait_name_case_conversion(self):
        """trait_name with underscores should be converted to Title Case."""
        db = FakeAsyncSession()
        traits = [_make_trait("personality", "openness_to_experience", {"label": "high"})]
        profile = MagicMock(traits=traits)
        db.execute_result.scalar_one_or_none.return_value = profile

        prompt = await build_personality_prompt(db)
        assert "Openness To Experience" in prompt
