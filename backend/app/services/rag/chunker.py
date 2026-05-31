"""Text chunking strategies for different document types."""

import re
from app.config import settings


def estimate_tokens(text: str) -> int:
    """Rough token estimation (~4 chars per token for English)."""
    return len(text) // 4


def chunk_markdown(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[dict]:
    """Split markdown on H2/H3 boundaries, keep headings as context."""
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    # Split on headings
    sections = re.split(r"(^#{1,3}\s.+$)", text, flags=re.MULTILINE)
    chunks: list[dict] = []
    current_section = ""
    current_text = ""
    heading_hierarchy: list[str] = []

    for part in sections:
        if re.match(r"^#{1,3}\s", part):
            # Track heading hierarchy
            level = len(re.match(r"^(#+)", part).group(1))
            heading_text = part.strip()
            heading_hierarchy = [h for h in heading_hierarchy if len(re.match(r"^(#+)", h).group(1)) < level]
            heading_hierarchy.append(heading_text)

            if current_text and estimate_tokens(current_text) > chunk_size * 0.5:
                chunks.append({
                    "content": current_text.strip(),
                    "metadata": {"headings": list(heading_hierarchy)},
                })
                current_text = part + "\n"
            else:
                current_text += part + "\n"
        else:
            current_text += part

    if current_text.strip():
        chunks.append({
            "content": current_text.strip(),
            "metadata": {"headings": list(heading_hierarchy)},
        })

    # Handle oversized chunks by recursive split
    refined_chunks: list[dict] = []
    for chunk in chunks:
        if estimate_tokens(chunk["content"]) > chunk_size:
            refined_chunks.extend(_split_paragraphs(chunk, chunk_size, overlap))
        else:
            refined_chunks.append(chunk)

    return refined_chunks


def chunk_plain_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[dict]:
    """Split plain text on paragraph boundaries."""
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[dict] = []
    current = ""

    for para in paragraphs:
        if estimate_tokens(current + para) > chunk_size and current:
            chunks.append({"content": current.strip(), "metadata": {}})
            # Keep overlap tokens from end of current (rough estimate: ~4 chars per token)
            if overlap:
                overlap_chars = overlap * 4
                current = current[-overlap_chars:] + "\n\n" + para
            else:
                current = para
        else:
            current += "\n\n" + para if current else para

    if current.strip():
        chunks.append({"content": current.strip(), "metadata": {}})

    return chunks


def _split_paragraphs(chunk: dict, chunk_size: int, overlap: int) -> list[dict]:
    """Recursively split a large chunk on paragraphs."""
    paragraphs = re.split(r"\n\s*\n", chunk["content"])
    result: list[dict] = []
    current = ""

    for para in paragraphs:
        if estimate_tokens(current + para) > chunk_size and current:
            result.append({"content": current.strip(), "metadata": chunk["metadata"]})
            if overlap:
                overlap_chars = overlap * 4
                current = current[-overlap_chars:] + "\n\n" + para if current else para
            else:
                current = para
        else:
            current += "\n\n" + para if current else para

    if current.strip():
        result.append({"content": current.strip(), "metadata": chunk["metadata"]})

    return result
