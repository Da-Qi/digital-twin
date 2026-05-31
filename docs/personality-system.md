# Personality System

## Overview

The personality system manages a versioned, evolving profile of the user across six trait categories. It extracts personality signals from feedback and conversation patterns, analyzes them with DeepSeek, and applies changes through a controlled workflow.

## Trait Categories

| Category | Description | Example |
|----------|-------------|---------|
| **personality** | Big Five / core traits | openness: high, conscientiousness: moderate |
| **communication** | How the twin should communicate | formality: informal, directness: moderate |
| **reasoning** | Decision-making patterns | analytical: high, intuitive: moderate |
| **values** | Core beliefs & values | independence: moderate, privacy: high |
| **knowledge** | Expertise areas | software engineering, system design |
| **boundaries** | Topic & behavior limits | avoids unsolicited advice, privacy-conscious |

## Profile Versioning

```
version 1 (active)
    │
    ├── analysis detects changes, low confidence
    │   └── version 2 (proposed)
    │       ├── user approves → version 2 (active), version 1 (archived)
    │       └── user rejects → version 2 (rejected)
    │
    └── analysis detects changes, high confidence, small diff
        └── version 2 (active), version 1 (archived)
```

## Analysis Pipeline

Triggered by `POST /api/v1/personality/analyze`:

1. **Fetch active profile** — current traits from DB
2. **Check for existing proposals** — abort if pending proposal exists
3. **Collect data since last analysis**:
   - Feedback marked for `personality_analysis` (tone_preference, boundary)
   - New conversations
4. **Check minimum thresholds** — needs ≥ 3 feedback entries or ≥ 5 conversations
5. **LLM analysis** — DeepSeek receives current traits + feedback + conversation summary, returns diff
6. **Route result**:
   - No update needed → return early
   - Auto-approve (confidence ≥ 0.7, ≤ 2 changes) → create new active profile
   - Needs approval → create proposed profile + pending proposal

## Traits Value Format

Traits store their value as JSONB. Common formats:

```json
// Label-based (personality, communication)
{"score": 80, "label": "high", "description": "Embraces new ideas"}

// List-based (knowledge)
{"items": ["Python", "Rust", "System Design"]}

// Text-based (values)
{"text": "Prioritizes privacy and data ownership"}
```

## Building the System Prompt

The `build_personality_prompt()` function in `services/personality/prompt_builder.py`:
1. Loads active profile with all traits
2. Groups by category using `CATEGORY_HEADINGS`
3. Formats each trait based on its value structure (label, items, text)
4. Returns a multi-section prompt describing how the twin should behave

Used in `POST /conversations/{id}/messages` before every LLM call. Falls back to `"You are a helpful assistant."` if no profile exists.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/personality/current` | Current active profile with traits |
| GET | `/api/v1/personality/versions` | All profile versions |
| GET | `/api/v1/personality/versions/{id}` | Specific version |
| POST | `/api/v1/personality/analyze` | Run analysis pipeline |
| GET | `/api/v1/personality/proposals/pending` | List pending proposals |
| POST | `/api/v1/personality/proposals/{id}/approve` | Approve proposal |
| POST | `/api/v1/personality/proposals/{id}/reject` | Reject proposal |

## Key Files

- `services/personality/analyzer.py` — Analysis engine (data collection, LLM, apply/propose)
- `services/personality/prompt_builder.py` — System prompt generator
- `services/personality/seed.py` — Initial profile seed data
- `models/personality.py` — Profile, Trait, Changelog models
- `api/personality.py` — Route handlers
