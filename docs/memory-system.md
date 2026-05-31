# Memory System

## Overview

The memory system extracts, stores, retrieves, and consolidates information about the user from conversations. Memories are typed, scored by importance, stored as vector embeddings, and retrievable via semantic search.

## Memory Types

| Type | What to Store | Importance Range | Decay |
|------|--------------|------------------|-------|
| **fact** | Objective facts (job, location, skills, experiences) | 0.3-0.9 | 180 days |
| **preference** | Likes, dislikes, habits, communication preferences | 0.2-0.8 | 365 days |
| **event** | Past or planned events | 0.3-0.8 | 30 days |
| **relationship** | People or relationships mentioned | 0.2-0.7 | 90 days |
| **opinion** | Strong opinions, beliefs, values | 0.4-1.0 | 365 days |

## Extraction

### `extract_memories_from_conversation()`

Called after every chat exchange (synchronously for non-streaming, background task for streaming).

1. **Skip check**: If user message < 10 characters, skip (greetings, short replies)
2. **LLM analysis**: Sends `(user_message, assistant_message)` to DeepSeek with extraction prompt
3. **Parse**: Expects JSON array of `{content, memory_type, importance}`
4. **Filter**: Skips entries with empty content or invalid memory type
5. **Clamp**: Importance clamped to [0.0, 1.0]
6. **Store**: Creates `MemoryEntry` with embedding (via BGE model)

### `create_memory_entry()` (utility)

Creates a single memory entry with:
- Generated embedding from content text
- Optional source conversation and message IDs
- Default importance 0.3

## Retrieval

Memory retrieval is triggered when the user sends a chat message:

1. User message is embedded using BGE
2. `search_memories()` queries pgvector for the top-5 most similar unconsolidated entries
3. Results are injected into the system prompt as "Relevant context about the user"
4. Both memory search and document chunk search run in parallel

## Consolidation

### `consolidate_memories()`

Runs on-demand via `POST /api/v1/memories/consolidate`. Prevents table bloat from low-value entries.

1. Finds candidates: importance < 0.3, unconsolidated, created > 24 hours ago
2. Groups by memory_type
3. Within each group, computes pairwise cosine similarity (threshold: 0.75)
4. Merges consecutive similar entries into one consolidated entry with:
   - Combined content (pipe-separated)
   - Average importance + 0.1 boost (capped at 0.5)
   - Summary: "Consolidated from N memories"
5. Original entries marked `consolidated = True`, linked to the merged entry

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/memories/search?q=&top_k=` | Semantic search |
| GET | `/api/v1/memories?memory_type=&consolidated=&limit=&offset=` | List with filters |
| DELETE | `/api/v1/memories/{id}` | Delete single entry |
| POST | `/api/v1/memories/consolidate` | Trigger consolidation |

## Key Files

- `services/memory/extractor.py` — Extraction + create_memory_entry utility
- `services/memory/consolidator.py` — Memory consolidation
- `models/memory.py` — MemoryEntry model
- `api/memories.py` — Route handlers
- `services/rag/vector_store.py` — pgvector queries
