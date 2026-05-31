"""API integration tests.

Requires a running PostgreSQL with pgvector at a separate test database.
Set TEST_DATABASE_URL env var, or defaults to localhost.
Run with: pytest tests/test_api.py -v --run-api-tests

These tests create/drop tables and are destructive — do NOT run against your dev DB.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.session import Base

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://dtadmin:dtpassword@localhost:5432/digitaltwin_test",
)

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_API_TESTS") != "1",
    reason="Set RUN_API_TESTS=1 to run (requires separate test DB)",
)


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


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
    create_resp = await client.post("/api/v1/conversations", json={"title": "Get me"})
    conv_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Get me"


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient):
    create_resp = await client.post("/api/v1/conversations", json={"title": "Delete me"})
    conv_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/conversations/{conv_id}")
    assert resp.status_code == 204
    get_resp = await client.get(f"/api/v1/conversations/{conv_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["is_archived"] is True


@pytest.mark.asyncio
async def test_questionnaire_status_no_profile(client: AsyncClient):
    resp = await client.get("/api/v1/questionnaire/status")
    assert resp.status_code == 200
    assert resp.json() == {"completed": False}


@pytest.mark.asyncio
async def test_feedback_create(client: AsyncClient):
    # Use a placeholder message ID
    resp = await client.post(
        "/api/v1/feedback",
        json={
            "target_message_id": "00000000-0000-0000-0000-000000000001",
            "feedback_type": "rating",
            "user_input": "Good!",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["feedback_type"] == "rating"
