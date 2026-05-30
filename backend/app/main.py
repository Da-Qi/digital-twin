from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db.session import engine, Base
from app.api import conversations, documents, personality, feedback, knowledge, questionnaire


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: enable pgvector extension and create tables
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(title="Digital Twin API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(personality.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(questionnaire.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
