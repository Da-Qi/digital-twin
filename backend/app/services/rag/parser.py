"""Document parsing for PDF and Markdown."""

from pathlib import Path


def parse_markdown(content: str | bytes) -> str:
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return content


def parse_pdf(file_path: str | Path) -> str:
    import pdfplumber

    text_parts: list[str] = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(f"[Page {page.page_number}]\n{text}")
    return "\n\n".join(text_parts)


def parse_pdf_bytes(content: bytes) -> str:
    import pdfplumber
    import io

    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(f"[Page {page.page_number}]\n{text}")
    return "\n\n".join(text_parts)
