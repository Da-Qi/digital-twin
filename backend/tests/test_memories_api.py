"""Integration tests for memory API endpoints.

Requires a separate PostgreSQL test database with pgvector.
Set TEST_DATABASE_URL env var (default: .../digitaltwin_test).
Run with: RUN_API_TESTS=1 pytest tests/test_memories_api.py -v

SAFETY: These tests DROP ALL TABLES. They will refuse to run against a
database named "digitaltwin" (the default dev DB name).
"""

import os
import uuid

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app
from app.db.session import Base
from app.services.rag.embedder import embedder

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


@pytest.fixture
async def sample_memories(client: AsyncClient):
    """Insert sample memory entries via raw SQL for testing."""
    from app.db.session import async_session_factory

    async with async_session_factory() as session:
        emb = embedder.encode(["test memory content"])[0].tolist()
        emb_str = str(emb)

        memories = [
            ("User knows Python", "fact", 0.6),
            ("User prefers VS Code", "preference", 0.4),
            ("User attended KubeCon", "event", 0.5),
        ]
        ids = []
        for content, mem_type, importance in memories:
            mem_id = str(uuid.uuid4())
            ids.append(mem_id)
            await session.execute(
                text("""
                    INSERT INTO memory_entries (id, memory_type, content, importance, embedding, created_at, accessed_at)
                    VALUES (:id, :type, :content, :importance, CAST(:emb AS vector), NOW(), NOW())
                """),
                {"id": mem_id, "type": mem_type, "content": content, "importance": importance, "emb": emb_str},
            )
        await session.commit()
        return ids


@pytest.mark.asyncio
async def test_search_memories(client: AsyncClient, sample_memories):
    resp = await client.get("/api/v1/memories/search?q=python&top_k=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_search_empty_query(client: AsyncClient):
    resp = await client.get("/api/v1/memories/search?q=&top_k=5")
    assert resp.status_code == 200
    assert resp.json() == {"results": [], "total": 0}


@pytest.mark.asyncio
async def test_list_memories(client: AsyncClient, sample_memories):
    resp = await client.get("/api/v1/memories")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_list_memories_filter_by_type(client: AsyncClient, sample_memories):
    resp = await client.get("/api/v1/memories?memory_type=fact")
    assert resp.status_code == 200
    data = resp.json()
    assert all(m["memory_type"] == "fact" for m in data)


@pytest.mark.asyncio
async def test_list_memories_pagination(client: AsyncClient, sample_memories):
    resp = await client.get("/api/v1/memories?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) <= 2


@pytest.mark.asyncio
async def test_delete_memory(client: AsyncClient, sample_memories):
    mem_id = sample_memories[0]
    resp = await client.delete(f"/api/v1/memories/{mem_id}")
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(f"/api/v1/memories?limit=200")
    data = resp.json()
    ids = [m["id"] for m in data]
    assert mem_id not in ids


@pytest.mark.asyncio
async def test_delete_nonexistent_memory(client: AsyncClient):
    resp = await client.delete(f"/api/v1/memories/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_consolidate_empty(client: AsyncClient):
    """Consolidation with minimal data should not error."""
    resp = await client.post("/api/v1/memories/consolidate")
    assert resp.status_code == 200
    data = resp.json()
    assert "consolidated" in data
