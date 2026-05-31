# Architecture

## Four-Layer Design

```
┌──────────────────────────────────────────────────────────────┐
│                     Input Layer                              │
│  Chat ←→ Documents ←→ Feedback (implicit / explicit)         │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                   Processing Layer                           │
│                                                              │
│  ┌─────────────────┐  ┌──────────────────┐                   │
│  │ Memory           │  │ Feedback Classif.│                   │
│  │ Extraction (LLM) │  │ Classification   │                   │
│  │ → pgvector store │  │ → Route to       │                   │
│  │ → Consolidation  │  │   subsystem      │                   │
│  └─────────────────┘  └──────────────────┘                   │
│                                                              │
│  ┌─────────────────┐  ┌──────────────────┐                   │
│  │ RAG (Retrieval)  │  │ Knowledge Graph  │                   │
│  │ → Docs + Memories│  │ → Nodes & Edges  │                   │
│  │ → Context inject │  │ → Entity store   │                   │
│  └─────────────────┘  └──────────────────┘                   │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                  Personality Core Layer                       │
│                                                              │
│  ┌──────────────────────────────────────────────────┐        │
│  │  Profile (versioned, 6 trait categories)         │        │
│  │  active ←→ proposed → approved / rejected        │        │
│  │                                                  │        │
│  │  Analysis Engine:                                │        │
│  │  Collect data → LLM analysis → Diff → Apply      │        │
│  │                                  ↓                │        │
│  │                    Auto-approve (small changes)    │        │
│  │                    Proposal (significant changes)  │        │
│  └──────────────────────────────────────────────────┘        │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                     Output Layer                             │
│  Chat Response (personality-aware) ←→ Knowledge API          │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

### Conversation Flow
1. User sends message in chat
2. System builds personality-aware system prompt from active profile
3. Retrieves relevant context (memories + document chunks) via pgvector similarity search
4. Sends to DeepSeek with history
5. Returns response (streaming or non-streaming)
6. Background: extracts memories from the exchange via DeepSeek

### Feedback Flow
1. User provides feedback (correction, rating, or implicit signal)
2. If unclassified → DeepSeek classifies (factual_correction, tone_preference, knowledge_gap, boundary, other)
3. Routes to subsystem: memory store / personality analysis queue / knowledge graph
4. Accumulated feedback triggers personality analysis

### Personality Analysis Flow
1. Triggered on-demand via `POST /personality/analyze`
2. Checks for pending proposals (aborts if one exists)
3. Gathers recent feedback (tagged `personality_analysis`) + new conversations
4. If insufficient data → returns early
5. Sends current traits + feedback + conversation summary to DeepSeek
6. DeepSeek returns diff (modified/added/removed traits)
7. If confidence ≥ 0.7 and ≤ 2 changes → auto-apply new profile version
8. Otherwise → create proposed profile + pending proposal for user approval

## Database

### Key Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `personality_profiles` | Versioned profile snapshots | version, status, parent_id |
| `personality_traits` | Individual traits per profile | category, trait_name, value (JSONB), confidence |
| `personality_changelog` | Audit trail | change_type, previous_version, changed_traits |
| `memory_entries` | Long-term memories | memory_type, content, importance, embedding (vector) |
| `document_chunks` | Document text chunks | chunk_index, content, embedding (vector) |
| `feedback_log` | All feedback events | feedback_type, classification, applied_to |
| `personality_update_proposals` | Pending profile changes | proposed_profile_id, status, feedback_ids |

### pgvector

- Embedding dimension: 1024 (BGE-large-en-v1.5)
- Cosine similarity for all vector searches
- Memory consolidation uses `<=>` operator to find similar entries

## Key Design Decisions

- **Streaming responses**: SSE (Server-Sent Events) for chat; memory extraction runs in `asyncio.create_task` to not block the stream
- **Isolation**: Extract/classify/analyze failures are caught silently — never blocks the main flow
- **Concurrency safety**: Analysis aborts if a pending proposal exists; no locking needed
- **Memory consolidation**: Batch process for entries with importance < 0.3, age > 24h, similarity > 0.75 — prevents table bloat
- **Auto-approval guard**: Only auto-applies personality changes when confidence ≥ 0.7 and ≤ 2 changes — major changes always require approval
