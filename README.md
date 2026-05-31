# Digital Twin

A **personal digital twin** system that learns from conversations, feedback, and documents to construct an evolving personality profile that mirrors the user. Built with FastAPI, Next.js, PostgreSQL + pgvector, and DeepSeek.

## Architecture

```
Input Layer          Processing Layer        Personality Core       Output Layer
┌──────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────┐
│ Chat     │    │ Memory Extraction│    │ Personality      │    │ Chat     │
│ Feedback │───→│ Feedback Classify │───→│ Profile (static) │───→│ Response │
│ Documents│    │ Knowledge Build  │    │ Evolution (loop) │    │ Knowledge│
└──────────┘    └──────────────────┘    └──────────────────┘    └──────────┘
                       │                       ▲
                       └────── Feedback ───────┘
                       Loop (corrections → analysis → proposal → approve)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TailwindCSS, Zustand |
| Backend | Python FastAPI, SQLAlchemy async, Alembic |
| Database | PostgreSQL 16 + pgvector |
| LLM | DeepSeek API (deepseek-chat) |
| Embeddings | BAAI/bge-large-en-v1.5 (local, 1024d) |
| Container | Docker Compose |

## Quick Start

```bash
# Set your DeepSeek API key
export DEEPSEEK_API_KEY=sk-...

# Start all services
docker compose up -d

# Run database migrations
make migrate

# Open http://localhost:3000
# Complete the onboarding questionnaire → start chatting
```

## Project Structure

```
├── backend/               # Python FastAPI
│   ├── app/
│   │   ├── api/           # Route handlers
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic
│   │       ├── feedback/  # Classification & routing
│   │       ├── memory/    # Extraction & consolidation
│   │       ├── personality/# Profile & analysis
│   │       └── rag/       # Embeddings & vector search
│   └── tests/             # pytest suite
├── frontend/              # Next.js
│   └── src/
│       ├── app/           # Routes
│       ├── components/    # UI components
│       └── lib/           # API client, store, types
└── docs/                  # Module documentation
```

## Core Systems

| System | Description | Entry Points |
|--------|------------|--------------|
| **Memory** | Extract facts/preferences/events from conversations, store as vector embeddings, consolidate low-importance entries | `docs/memory-system.md`, `app/services/memory/` |
| **Personality** | Versioned profile with 6 trait categories, analysis engine that proposes updates based on feedback | `docs/personality-system.md`, `app/services/personality/` |
| **Feedback Loop** | Three-mode feedback (implicit/like-dislike/explicit), classification and routing to subsystems | `docs/feedback-loop.md`, `app/services/feedback/` |
| **RAG** | Local embedding (BGE), pgvector similarity search across document chunks and memories | `app/services/rag/` |

## Key Principles

- **Personality evolves**: The twin isn't static — feedback and conversation patterns drive periodic analysis that proposes profile updates
- **Feedback closes the loop**: Every correction is classified and routed to the relevant subsystem (memory, personality, knowledge graph)
- **Memory is typed**: Five memory types (fact, preference, event, relationship, opinion) with importance scoring and consolidation
- **Safe analysis**: Personality changes go through a proposal → approval workflow unless confidence is high and changes are minimal
