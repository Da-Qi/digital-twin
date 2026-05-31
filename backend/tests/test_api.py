"""API integration tests.

Requires a separate PostgreSQL test database with pgvector.
Set TEST_DATABASE_URL env var (default: .../digitaltwin_test).
Run with: RUN_API_TESTS=1 pytest tests/test_api.py -v

SAFETY: These tests DROP ALL TABLES. They will refuse to run against a
database named "digitaltwin" (the default dev DB name).
"""

import os

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


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient):
    resp = await client.post("/api/v1/conversations", json={"title": "Test chat"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test chat"
    assert "id" in data
    assert data["message_count"] == 0


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient):
    await client.post("/api/v1/conversations", json={"title": "C1"})
    resp = await client.get("/api/v1/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(c["title"] == "C1" for c in data)


@pytest.mark.asyncio
async def test_get_conversation(client: AsyncClient):
    r = await client.post("/api/v1/conversations", json={"title": "Get me"})
    conv_id = r.json()["id"]
    resp = await client.get(f"/api/v1/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Get me"


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient):
    r = await client.post("/api/v1/conversations", json={"title": "Delete me"})
    conv_id = r.json()["id"]
    resp = await client.delete(f"/api/v1/conversations/{conv_id}")
    assert resp.status_code == 204
    get = await client.get(f"/api/v1/conversations/{conv_id}")
    assert get.status_code == 200
    assert get.json()["is_archived"] is True


@pytest.mark.asyncio
async def test_questionnaire_status_no_profile(client: AsyncClient):
    resp = await client.get("/api/v1/questionnaire/status")
    assert resp.status_code == 200
    assert resp.json() == {"completed": False}


@pytest.mark.asyncio
async def test_feedback_create(client: AsyncClient):
    resp = await client.post(
        "/api/v1/feedback",
        json={
            "target_message_id": "00000000-0000-0000-0000-000000000001",
            "feedback_type": "rating",
            "user_input": "Good!",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["feedback_type"] == "rating"
