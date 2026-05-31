"""Integration tests for document API endpoints.

Requires a separate PostgreSQL test database with pgvector.
Set TEST_DATABASE_URL env var (default: .../digitaltwin_test).
Run with: RUN_API_TESTS=1 pytest tests/test_documents_api.py -v

SAFETY: These tests DROP ALL TABLES. They will refuse to run against a
database named "digitaltwin" (the default dev DB name).
"""

import os
import io

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app
from app.db.session import Base

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://dtadmin:dtpassword@localhost:5432/digitaltwin_test",
)

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_API_TESTS") != "1",
    reason="Set RUN_API_TESTS=1 to run (requires separate test DB)",
)


def _check_not_dev_db(url: str) -> None:
    """Refuse to run against the default dev database."""
    if "/digitaltwin" in url and "digitaltwin_test" not in url:
        raise RuntimeError(
            f"Refusing to run destructive tests against {url}. "
            "Point TEST_DATABASE_URL at a test-specific database."
        )


@pytest.fixture(scope="module")
async def setup_db():
    """Create tables once per module, drop after all tests complete."""
    _check_not_dev_db(TEST_DB_URL)
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_markdown_file(filename="test.md") -> dict:
    content = b"# Test Document\n\nThis is a test markdown document for unit testing."
    return {"file": (io.BytesIO(content), filename)}


def _make_pdf_file(filename="test.pdf") -> dict:
    """Create a minimal valid PDF."""
    # Minimal PDF: %PDF-1.4 header + a simple page
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
    )
    return {"file": (io.BytesIO(pdf_content), filename)}


class TestDocumentUpload:
    @pytest.mark.asyncio
    async def test_upload_markdown(self, client: AsyncClient):
        resp = await client.post("/api/v1/documents/upload", files=_make_markdown_file())
        assert resp.status_code == 201
        data = resp.json()
        assert data["processing_status"] == "ready"
        assert data["content_type"] == "text/markdown"
        assert data["filename"] == "test.md"

    @pytest.mark.asyncio
    async def test_upload_pdf(self, client: AsyncClient):
        resp = await client.post("/api/v1/documents/upload", files=_make_pdf_file())
        assert resp.status_code == 201
        data = resp.json()
        assert data["processing_status"] in ("ready", "processing")
        assert "pdf" in data["content_type"]

    @pytest.mark.asyncio
    async def test_upload_invalid_type(self, client: AsyncClient):
        content = b"plain text file"
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": (io.BytesIO(content), "test.txt")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_overly_large(self, client: AsyncClient):
        # Create a file larger than limit (but in-memory to avoid disk I/O)
        large_content = b"X" * (51 * 1024 * 1024)
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": (io.BytesIO(large_content), "large.md")},
        )
        assert resp.status_code == 400


class TestDocumentList:
    @pytest.mark.asyncio
    async def test_list_documents_pagination(self, client: AsyncClient):
        # Upload 3 documents
        for i in range(3):
            await client.post(
                "/api/v1/documents/upload",
                files=_make_markdown_file(f"test_{i}.md"),
            )

        resp = await client.get("/api/v1/documents?page=1&size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["items"]) <= 2
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_list_documents_default_pagination(self, client: AsyncClient):
        resp = await client.get("/api/v1/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["size"] == 20


class TestDocumentChunks:
    @pytest.mark.asyncio
    async def test_get_document_chunks(self, client: AsyncClient):
        # Upload a document
        resp = await client.post("/api/v1/documents/upload", files=_make_markdown_file())
        assert resp.status_code == 201
        doc_id = resp.json()["id"]

        # Get its chunks
        resp = await client.get(f"/api/v1/documents/{doc_id}/chunks")
        assert resp.status_code == 200
        chunks = resp.json()
        assert isinstance(chunks, list)
        assert len(chunks) >= 1
        assert chunks[0].get("content") is not None
        assert chunks[0].get("chunk_index") is not None

    @pytest.mark.asyncio
    async def test_get_chunks_nonexistent_document(self, client: AsyncClient):
        import uuid
        resp = await client.get(f"/api/v1/documents/{uuid.uuid4()}/chunks")
        assert resp.status_code == 404


class TestDocumentKnowledge:
    @pytest.mark.asyncio
    async def test_get_document_knowledge_empty(self, client: AsyncClient):
        # Upload a document and check knowledge (should be empty for new docs)
        resp = await client.post("/api/v1/documents/upload", files=_make_markdown_file())
        assert resp.status_code == 201
        doc_id = resp.json()["id"]

        resp = await client.get(f"/api/v1/documents/{doc_id}/knowledge")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data


class TestDocumentDelete:
    @pytest.mark.asyncio
    async def test_delete_document(self, client: AsyncClient):
        resp = await client.post("/api/v1/documents/upload", files=_make_markdown_file())
        assert resp.status_code == 201
        doc_id = resp.json()["id"]

        resp = await client.delete(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp = await client.get(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client: AsyncClient):
        import uuid
        resp = await client.delete(f"/api/v1/documents/{uuid.uuid4()}")
        assert resp.status_code == 404
