"""Seed initial personality profile from onboarding questionnaire."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personality import PersonalityProfile, PersonalityTrait, PersonalityChangelog
from app.models.document import Document, DocumentChunk
from app.services.rag.embedder import embedder
from app.services.rag.chunker import estimate_tokens


def _score_to_label(slider_val: int, low_label: str, high_label: str, mid_label: str | None = None) -> str:
    if slider_val < 35:
        return low_label
    elif slider_val > 65:
        return high_label
    return mid_label or f"适中"


async def seed_from_questionnaire(db: AsyncSession, data: dict) -> PersonalityProfile:
    """Create initial personality profile from questionnaire data."""

    p = data.get("personality", {})
    v = data.get("voice", {})
    d = data.get("values", {})
    k = data.get("knowledge", {})
    l = data.get("limits", {})

    # --- Build profile ---
    profile = PersonalityProfile(
        version=1,
        status="active",
        summary="Initial personality profile from onboarding questionnaire",
        based_on_stats={"source": "questionnaire", "version": 1},
        activated_at=datetime.now(timezone.utc),
    )
    db.add(profile)
    await db.flush()

    traits: list[PersonalityTrait] = []

    # === 性格基调 ===
    chips = p.get("traits", [])
    if chips:
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="personality", trait_name="core_traits",
            value={"items": chips}, confidence=0.7,
        ))

    introvert = p.get("introvert0")
    if introvert:
        label = "独处充电型" if introvert == "a" else "社交充电型"
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="personality", trait_name="social_energy",
            value={"type": introvert, "label": label}, confidence=0.6,
        ))

    thinking = p.get("introvert1")
    if thinking:
        label = "大局思考" if thinking == "a" else "细节导向"
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="personality", trait_name="thinking_style",
            value={"type": thinking, "label": label}, confidence=0.6,
        ))

    # === 表达风格 ===
    formal = v.get("formal", 50)
    traits.append(PersonalityTrait(
        profile_id=profile.id, category="communication", trait_name="formality",
        value={"score": formal, "label": _score_to_label(formal, "偏口语随意", "偏正式严谨")},
        confidence=0.5,
    ))

    verbose = v.get("verbose", 50)
    traits.append(PersonalityTrait(
        profile_id=profile.id, category="communication", trait_name="verbosity",
        value={"score": verbose, "label": _score_to_label(verbose, "简洁精炼", "喜欢详细展开")},
        confidence=0.5,
    ))

    habits = v.get("voice_habits", [])
    if habits:
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="communication", trait_name="speech_habits",
            value={"items": habits}, confidence=0.6,
        ))

    # === 价值观与决策 ===
    dec_mapping = {
        "decisions0": ("快速行动", "深思熟虑"),
        "decisions1": ("数据优先", "直觉优先"),
        "decisions2": ("坚守原则", "灵活变通"),
    }
    for key, (label_a, label_b) in dec_mapping.items():
        val = d.get(key)
        if val:
            label = label_a if val == "a" else label_b
            traits.append(PersonalityTrait(
                profile_id=profile.id, category="reasoning", trait_name=key,
                value={"type": val, "label": label}, confidence=0.5,
            ))

    values_chips = d.get("values", [])
    if values_chips:
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="values", trait_name="core_values",
            value={"items": values_chips}, confidence=0.6,
        ))

    regret = d.get("regret", "").strip()
    if regret:
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="values", trait_name="meaningful_decision",
            value={"text": regret}, confidence=0.4,
        ))

    # === 知识与专长 ===
    expertise = k.get("expertise", "").strip()
    if expertise:
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="knowledge", trait_name="expertise",
            value={"text": expertise}, confidence=0.7,
        ))

    interests = k.get("interests", [])
    if interests:
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="knowledge", trait_name="interests",
            value={"items": interests}, confidence=0.6,
        ))

    opinions = k.get("opinions", "").strip()
    if opinions:
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="knowledge", trait_name="strong_opinions",
            value={"text": opinions}, confidence=0.5,
        ))

    # === 边界与禁区 ===
    avoid = l.get("avoid_topics", [])
    if avoid:
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="boundaries", trait_name="avoid_topics",
            value={"items": avoid}, confidence=0.7,
        ))

    limits0 = l.get("limits0")
    if limits0:
        label = "遇到不确定就说不知道" if limits0 == "a" else "尽力推断给出答案"
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="boundaries", trait_name="uncertainty_handling",
            value={"type": limits0, "label": label}, confidence=0.5,
        ))

    limits1 = l.get("limits1")
    if limits1:
        label = "保持中立" if limits1 == "a" else "表达真实立场"
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="boundaries", trait_name="stance",
            value={"type": limits1, "label": label}, confidence=0.5,
        ))

    extra = l.get("extra", "").strip()
    if extra:
        traits.append(PersonalityTrait(
            profile_id=profile.id, category="boundaries", trait_name="extra_notes",
            value={"text": extra}, confidence=0.4,
        ))

    # Save all traits
    for trait in traits:
        db.add(trait)
    await db.flush()

    # --- Log the creation ---
    changelog = PersonalityChangelog(
        profile_id=profile.id,
        change_type="created",
        reason="Initial profile from onboarding questionnaire",
    )
    db.add(changelog)
    await db.flush()

    # --- Process writing sample as a document ---
    sample = v.get("sample", "").strip()
    if sample:
        from app.services.rag.chunker import chunk_plain_text
        from app.services.rag.vector_store import insert_chunks

        doc = Document(
            filename="voice_sample.md",
            content_type="text/markdown",
            source_type="writing_sample",
            authorship="user",
            title="语气样本 — 问卷采集",
            raw_text=sample,
            char_count=len(sample),
            processing_status="processing",
        )
        db.add(doc)
        await db.flush()

        chunks = chunk_plain_text(sample)
        if chunks:
            texts = [c["content"] for c in chunks]
            embeddings = embedder.encode(texts)
            await insert_chunks(db, str(doc.id), chunks, embeddings.tolist())

        doc.processing_status = "ready"
        doc.chunk_count = len(chunks)
        await db.flush()

    return profile
