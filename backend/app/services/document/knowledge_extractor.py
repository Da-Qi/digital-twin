"""Knowledge extraction from document chunks via DeepSeek."""

import json
import logging
import uuid
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import llm_service
from app.services.rag.embedder import embedder

logger = logging.getLogger(__name__)

MAX_CHUNKS_FOR_LLM = 30
CHUNK_SAMPLE_FRONT = 10
CHUNK_SAMPLE_BACK = 5


def _sample_chunks(chunks: list[dict]) -> list[dict]:
    """Sample at most MAX_CHUNKS_FOR_LLM chunks for LLM processing.

    For documents with many chunks, include the first N, last M, and random
    samples from the middle to ensure representative coverage.
    """
    total = len(chunks)
    if total <= MAX_CHUNKS_FOR_LLM:
        return chunks

    front = chunks[:CHUNK_SAMPLE_FRONT]
    back = chunks[-CHUNK_SAMPLE_BACK:]
    middle_count = MAX_CHUNKS_FOR_LLM - CHUNK_SAMPLE_FRONT - CHUNK_SAMPLE_BACK
    middle_start = CHUNK_SAMPLE_FRONT
    middle_end = total - CHUNK_SAMPLE_BACK

    import random
    random.seed(hash(str(chunks[0].get("content", ""))) & 0xFFFFFFFF)
    middle_indices = sorted(random.sample(range(middle_start, middle_end), min(middle_count, middle_end - middle_start)))
    middle = [chunks[i] for i in middle_indices]
    return front + middle + back


def _build_prompt(title: str, content_type: str, sampled_chunks: list[dict]) -> list[dict]:
    """Build the DeepSeek messages for knowledge extraction."""
    chunks_text = "\n\n---\n\n".join(
        f"[Chunk {i}] {c['content']}" for i, c in enumerate(sampled_chunks)
    )

    system_msg = {
        "role": "system",
        "content": (
            "You are a knowledge graph extractor. Given document content, identify "
            "key concepts, skills, tools, domains, and technologies mentioned. Also "
            "identify relationships between them (e.g., 'uses', 'part_of', "
            "'related_to', 'implements', 'is_a'). Return ONLY valid JSON without "
            "markdown formatting."
        ),
    }

    user_msg = {
        "role": "user",
        "content": (
            f"Document title: {title}\n"
            f"Content type: {content_type}\n\n"
            f"Content chunks:\n{chunks_text}\n\n"
            "Extract knowledge nodes and relationships. Return JSON in this format:\n"
            '{\n'
            '  "nodes": [{"label": "...", "type": "skill|tool|domain|concept|technology", '
            '"description": "...", "confidence": 0.0-1.0}],\n'
            '  "edges": [{"source": "...", "target": "...", "relation": "...", '
            '"weight": 0.0-1.0, "evidence": "..."}]\n'
            "}"
        ),
    }

    return [system_msg, user_msg]


def _parse_response(raw: str) -> tuple[list[dict], list[dict]]:
    """Parse LLM JSON response into nodes and edges lists."""
    cleaned = raw.strip()

    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if "```" in cleaned:
            cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    # Extract JSON object by finding outermost braces with fallback for truncated JSON
    brace_start = cleaned.find("{")
    if brace_start >= 0:
        depth = 0
        last_valid_end = -1
        for i in range(brace_start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    last_valid_end = i + 1
        if last_valid_end > 0:
            cleaned = cleaned[brace_start:last_valid_end]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(
            "Failed to parse LLM response (len=%d, cleaned_len=%d, pos=%d, msg=%s)",
            len(raw), len(cleaned), e.pos, e.msg,
        )
        # Fallback: try to recover truncated JSON by finding last valid closing brace
        recovered = False
        for i in range(min(e.pos, len(cleaned) - 1), -1, -1):
            if cleaned[i] == "}":
                try:
                    data = json.loads(cleaned[: i + 1])
                    logger.info("Recovered truncated JSON at pos %d", i)
                    recovered = True
                    break
                except (json.JSONDecodeError, ValueError):
                    continue
        if not recovered:
            return [], []

    nodes = data.get("nodes", []) if isinstance(data, dict) else []
    edges = data.get("edges", []) if isinstance(data, dict) else []

    valid_nodes = []
    for n in nodes:
        label = n.get("label", "").strip()
        if not label:
            continue
        valid_nodes.append({
            "label": label,
            "type": n.get("type", "concept"),
            "description": n.get("description") or "",
            "confidence": max(0.0, min(1.0, float(n.get("confidence", 0.5)))),
        })

    valid_edges = []
    for e in edges:
        source = e.get("source", "").strip()
        target = e.get("target", "").strip()
        relation = e.get("relation", "").strip()
        if not source or not target or not relation:
            continue
        valid_edges.append({
            "source": source,
            "target": target,
            "relation": relation,
            "weight": max(0.0, min(1.0, float(e.get("weight", 1.0)))),
            "evidence": e.get("evidence") or "",
        })

    return valid_nodes, valid_edges


async def extract_knowledge_from_document(
    db: AsyncSession,
    document_id: str,
    title: str,
    content_type: str,
    chunks: list[dict],
) -> int:
    """Extract knowledge nodes and edges from document chunks via DeepSeek.

    Returns the number of nodes extracted (0 if no data or on error).
    """
    if not chunks:
        logger.info("No chunks to extract knowledge from for document %s", document_id)
        return 0

    sampled = _sample_chunks(chunks)
    messages = _build_prompt(title, content_type, sampled)

    try:
        raw = await llm_service.chat(messages, temperature=0.3, max_tokens=8192)
    except Exception:
        logger.exception("LLM call failed during knowledge extraction for document %s", document_id)
        return 0

    nodes, edges = _parse_response(raw)
    if not nodes:
        logger.info("No knowledge nodes extracted from document %s", document_id)
        return 0

    # Compute embeddings in batches to avoid OOM on large extractions
    texts_to_embed = [f"{n['label']}: {n['description']}" for n in nodes]
    batch_size = 32
    node_embeddings = np.vstack([
        embedder.encode(texts_to_embed[i:i + batch_size])
        for i in range(0, len(texts_to_embed), batch_size)
    ])

    now = datetime.now(timezone.utc)

    # Upsert nodes
    node_id_map: dict[str, str] = {}
    for i, node in enumerate(nodes):
        label = node["label"]
        node_type = node["type"]
        description = node["description"]
        confidence = node["confidence"]

        # Check if node already exists
        result = await db.execute(
            text("SELECT id, confidence, source_ids FROM knowledge_nodes WHERE label = :label"),
            {"label": label},
        )
        existing = result.first()

        if existing:
            node_id = str(existing[0])
            old_conf = float(existing[1])
            old_ids = existing[2] or []
            new_ids = list(set(old_ids + [document_id]))

            # Weighted average confidence
            count = len(new_ids)
            merged_conf = (old_conf * (count - 1) + confidence) / count

            await db.execute(
                text("""
                    UPDATE knowledge_nodes
                    SET description = :description,
                        confidence = :confidence,
                        source_ids = :source_ids,
                        embedding = CAST(:embedding AS vector),
                        updated_at = :now
                    WHERE id = :id
                """),
                {
                    "id": node_id,
                    "description": description,
                    "confidence": merged_conf,
                    "source_ids": new_ids,
                    "embedding": str(node_embeddings[i].tolist()),
                    "now": now,
                },
            )
        else:
            node_id = str(uuid.uuid4())
            await db.execute(
                text("""
                    INSERT INTO knowledge_nodes (id, label, node_type, description, confidence, source_ids, embedding, created_at, updated_at)
                    VALUES (:id, :label, :type, :description, :confidence, :source_ids, CAST(:embedding AS vector), :now, :now)
                """),
                {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "description": description,
                    "confidence": confidence,
                    "source_ids": [document_id],
                    "embedding": str(node_embeddings[i].tolist()),
                    "now": now,
                },
            )

        node_id_map[label] = node_id

    # Upsert edges
    for edge in edges:
        source_id = node_id_map.get(edge["source"])
        target_id = node_id_map.get(edge["target"])
        if not source_id or not target_id:
            continue

        # Check if edge already exists
        result = await db.execute(
            text("""
                SELECT id, weight FROM knowledge_edges
                WHERE source_node_id = :source AND target_node_id = :target AND relation_type = :relation
            """),
            {"source": source_id, "target": target_id, "relation": edge["relation"]},
        )
        existing_edge = result.first()

        if existing_edge:
            old_weight = float(existing_edge[1])
            merged_weight = (old_weight + edge["weight"]) / 2
            await db.execute(
                text("""
                    UPDATE knowledge_edges
                    SET weight = :weight, evidence = :evidence
                    WHERE id = :id
                """),
                {"id": str(existing_edge[0]), "weight": merged_weight, "evidence": edge["evidence"]},
            )
        else:
            await db.execute(
                text("""
                    INSERT INTO knowledge_edges (id, source_node_id, target_node_id, relation_type, weight, evidence, created_at)
                    VALUES (:id, :source, :target, :relation, :weight, :evidence, :now)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "source": source_id,
                    "target": target_id,
                    "relation": edge["relation"],
                    "weight": edge["weight"],
                    "evidence": edge["evidence"],
                    "now": now,
                },
            )

    # Mark document as knowledge-extracted
    await db.execute(
        text("""
            UPDATE documents
            SET metadata = jsonb_set(
                jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{knowledge_extracted}',
                    :val
                ),
                '{knowledge_status}',
                '"completed"'
            )
            WHERE id = :id
        """),
        {
            "id": document_id,
            "val": json.dumps({"extracted": True, "node_count": len(nodes), "edge_count": len(edges), "extracted_at": now.isoformat()}),
        },
    )

    logger.info(
        "Extracted %d nodes and %d edges from document %s",
        len(nodes), len(edges), document_id,
    )
    return len(nodes)
