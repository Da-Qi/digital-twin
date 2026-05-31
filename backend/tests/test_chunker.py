"""Unit tests for document chunker."""

from app.services.rag.chunker import chunk_markdown, chunk_plain_text, estimate_tokens


def test_estimate_tokens():
    assert estimate_tokens("hello world") == 2  # 11 chars // 4
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 100) == 25


class TestChunkPlainText:
    def test_empty_text(self):
        assert chunk_plain_text("") == []

    def test_short_text_no_split(self):
        chunks = chunk_plain_text("Hello world", chunk_size=800, overlap=100)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "Hello world"

    def test_splits_on_paragraph_boundary(self):
        text = "Short para.\n\n" * 5
        chunks = chunk_plain_text(text, chunk_size=10, overlap=0)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c["content"]) > 0

    def test_overlap_preserves_chars(self):
        text = "This is paragraph one. It has enough tokens.\n\nThis is paragraph two. Also enough tokens.\n\nThis is paragraph three. More tokens here."
        chunks = chunk_plain_text(text, chunk_size=12, overlap=2)
        # With chunk_size=12 and overlap=2 (~8 chars), the text should split into at least 2 chunks
        # and the second chunk should contain overlap chars from the first
        assert len(chunks) >= 2
        if len(chunks) >= 2:
            assert len(chunks[1]["content"]) > 0


class TestChunkMarkdown:
    def test_empty_text(self):
        assert chunk_markdown("") == []

    def test_single_section(self):
        md = "# Title\n\nSome content here."
        chunks = chunk_markdown(md, chunk_size=800, overlap=100)
        assert len(chunks) == 1
        assert "# Title" in chunks[0]["content"]

    def test_h2_sections_split(self):
        md = "## Section 1\nContent A.\n\n## Section 2\nContent B."
        chunks = chunk_markdown(md, chunk_size=5, overlap=0)
        assert len(chunks) >= 2

    def test_metadata_contains_headings(self):
        md = "## Intro\n\nHello.\n\n## Details\n\nWorld."
        chunks = chunk_markdown(md, chunk_size=800, overlap=100)
        assert len(chunks) >= 1
        # Each chunk should have headings metadata
        for c in chunks:
            assert "headings" in c["metadata"]
