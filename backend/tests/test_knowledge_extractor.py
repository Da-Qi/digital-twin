"""Tests for knowledge extraction from documents."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.document.knowledge_extractor import (
    _sample_chunks,
    _build_prompt,
    _parse_response,
    extract_knowledge_from_document,
)


class TestSampleChunks:
    def test_returns_all_when_under_limit(self):
        chunks = [{"content": f"chunk {i}", "chunk_index": i} for i in range(5)]
        result = _sample_chunks(chunks)
        assert len(result) == 5

    def test_samples_when_over_limit(self):
        chunks = [{"content": f"chunk {i}", "chunk_index": i} for i in range(50)]
        result = _sample_chunks(chunks)
        assert len(result) <= 30
        # First and last chunks should be included
        assert result[0]["chunk_index"] == 0
        assert result[-1]["chunk_index"] == 49

    def test_empty_chunks(self):
        assert _sample_chunks([]) == []


class TestBuildPrompt:
    def test_includes_chunks_in_prompt(self):
        chunks = [
            {"content": "Python is a programming language", "chunk_index": 0},
            {"content": "FastAPI is a web framework", "chunk_index": 1},
        ]
        messages = _build_prompt("Test Doc", "text/markdown", chunks)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Test Doc" in messages[1]["content"]
        assert "Python is a programming language" in messages[1]["content"]
        assert "FastAPI" in messages[1]["content"]

    def test_empty_chunks_no_error(self):
        messages = _build_prompt("Test", "text/plain", [])
        assert len(messages) == 2


class TestParseResponse:
    def test_valid_nodes_and_edges(self):
        raw = json.dumps({
            "nodes": [
                {"label": "Python", "type": "skill", "description": "Language", "confidence": 0.9},
            ],
            "edges": [
                {"source": "Python", "target": "FastAPI", "relation": "used_by", "weight": 0.8, "evidence": "used in web dev"},
            ],
        })
        nodes, edges = _parse_response(raw)
        assert len(nodes) == 1
        assert nodes[0]["label"] == "Python"
        assert len(edges) == 1
        assert edges[0]["relation"] == "used_by"

    def test_skips_missing_label(self):
        raw = json.dumps({
            "nodes": [
                {"type": "skill", "description": "No label"},
                {"label": "Valid", "type": "skill", "description": "Has label", "confidence": 0.5},
            ],
            "edges": [],
        })
        nodes, edges = _parse_response(raw)
        assert len(nodes) == 1
        assert nodes[0]["label"] == "Valid"

    def test_skips_edge_without_source(self):
        raw = json.dumps({
            "nodes": [{"label": "A", "type": "concept", "description": "", "confidence": 0.5}],
            "edges": [
                {"target": "B", "relation": "related", "weight": 0.5, "evidence": ""},
            ],
        })
        nodes, edges = _parse_response(raw)
        assert len(nodes) == 1
        assert len(edges) == 0

    def test_invalid_json(self):
        nodes, edges = _parse_response("not json at all")
        assert nodes == []
        assert edges == []

    def test_empty_json(self):
        nodes, edges = _parse_response('{"nodes":[],"edges":[]}')
        assert nodes == []
        assert edges == []

    def test_clamps_confidence(self):
        raw = json.dumps({
            "nodes": [
                {"label": "Low", "type": "concept", "description": "", "confidence": -0.5},
                {"label": "High", "type": "concept", "description": "", "confidence": 1.5},
            ],
            "edges": [],
        })
        nodes, edges = _parse_response(raw)
        assert nodes[0]["confidence"] == 0.0
        assert nodes[1]["confidence"] == 1.0

    def test_strips_markdown_code_fence(self):
        raw = "```json\n{\"nodes\": [{\"label\": \"Python\", \"type\": \"skill\", \"description\": \"\", \"confidence\": 0.5}], \"edges\": []}\n```"
        nodes, edges = _parse_response(raw)
        assert len(nodes) == 1
        assert nodes[0]["label"] == "Python"


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


class TestExtractKnowledge:
    @pytest.mark.asyncio
    async def test_empty_chunks_returns_zero(self):
        """Empty chunks should not call LLM and return 0."""
        db = FakeAsyncSession()
        with patch("app.services.document.knowledge_extractor.llm_service") as mock_llm:
            result = await extract_knowledge_from_document(
                db=db,
                document_id="doc-1",
                title="Test",
                content_type="text/markdown",
                chunks=[],
            )
        assert result == 0
        mock_llm.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_extracts_nodes_and_edges(self):
        """Normal flow: LLM returns valid JSON, nodes and edges are extracted."""
        db = FakeAsyncSession()
        # No existing nodes found
        db.execute_result.first.return_value = None

        with patch("app.services.document.knowledge_extractor.llm_service") as mock_llm:
            mock_llm.chat = AsyncMock(return_value=json.dumps({
                "nodes": [
                    {"label": "Python", "type": "skill", "description": "Programming language", "confidence": 0.9},
                ],
                "edges": [],
            }))
            result = await extract_knowledge_from_document(
                db=db,
                document_id="doc-1",
                title="Python Guide",
                content_type="text/markdown",
                chunks=[{"content": "Python is great", "chunk_index": 0}],
            )

        assert result == 1
        mock_llm.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_deduplicates_nodes_by_label(self):
        """When a node with the same label exists, confidence is merged."""
        db = FakeAsyncSession()

        class FakeRow:
            """Simulate a DB row with __getitem__ support."""
            def __getitem__(self, idx):
                return ["existing-uuid", 0.5, ["prev-doc"]][idx]

        existing_row = FakeRow()
        db.execute_result.first.side_effect = [None, existing_row, None, None, None]

        with patch("app.services.document.knowledge_extractor.llm_service") as mock_llm:
            mock_llm.chat = AsyncMock(return_value=json.dumps({
                "nodes": [
                    {"label": "Python", "type": "skill", "description": "Language", "confidence": 0.9},
                    {"label": "Python", "type": "skill", "description": "Language", "confidence": 0.7},
                ],
                "edges": [],
            }))
            result = await extract_knowledge_from_document(
                db=db,
                document_id="doc-2",
                title="Python Again",
                content_type="text/markdown",
                chunks=[{"content": "More Python", "chunk_index": 0}],
            )

        assert result == 2

    @pytest.mark.asyncio
    async def test_invalid_json_response_returns_zero(self):
        """LLM returning invalid JSON should not crash and return 0."""
        db = FakeAsyncSession()

        with patch("app.services.document.knowledge_extractor.llm_service") as mock_llm:
            mock_llm.chat = AsyncMock(return_value="not valid json at all")
            result = await extract_knowledge_from_document(
                db=db,
                document_id="doc-1",
                title="Test",
                content_type="text/plain",
                chunks=[{"content": "Some content", "chunk_index": 0}],
            )

        assert result == 0

    @pytest.mark.asyncio
    async def test_empty_response_from_llm(self):
        """LLM returning empty nodes/edges should return 0."""
        db = FakeAsyncSession()

        with patch("app.services.document.knowledge_extractor.llm_service") as mock_llm:
            mock_llm.chat = AsyncMock(return_value='{"nodes":[],"edges":[]}')
            result = await extract_knowledge_from_document(
                db=db,
                document_id="doc-1",
                title="Test",
                content_type="text/plain",
                chunks=[{"content": "Some content", "chunk_index": 0}],
            )

        assert result == 0

    @pytest.mark.asyncio
    async def test_skips_malformed_nodes(self):
        """Nodes missing required fields should be filtered."""
        db = FakeAsyncSession()
        db.execute_result.first.return_value = None

        with patch("app.services.document.knowledge_extractor.llm_service") as mock_llm:
            mock_llm.chat = AsyncMock(return_value=json.dumps({
                "nodes": [
                    {"type": "skill", "description": "Missing label"},  # invalid
                    {"label": "", "type": "skill", "description": "Empty label"},  # invalid
                    {"label": "Valid", "type": "skill", "description": "OK", "confidence": 0.5},  # valid
                ],
                "edges": [],
            }))
            result = await extract_knowledge_from_document(
                db=db,
                document_id="doc-1",
                title="Test",
                content_type="text/plain",
                chunks=[{"content": "Some content", "chunk_index": 0}],
            )

        assert result == 1

    @pytest.mark.asyncio
    async def test_handles_llm_error(self):
        """LLM exception should be caught and return 0."""
        db = FakeAsyncSession()

        with patch("app.services.document.knowledge_extractor.llm_service") as mock_llm:
            mock_llm.chat = AsyncMock(side_effect=Exception("API error"))
            result = await extract_knowledge_from_document(
                db=db,
                document_id="doc-1",
                title="Test",
                content_type="text/plain",
                chunks=[{"content": "Some content", "chunk_index": 0}],
            )

        assert result == 0
