"""Build personality-aware system prompt from active profile."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personality import PersonalityProfile

CATEGORY_HEADINGS = {
    "personality": "Personality",
    "communication": "Communication Style",
    "reasoning": "Reasoning & Decision Making",
    "values": "Values & Beliefs",
    "knowledge": "Knowledge & Expertise",
    "boundaries": "Boundaries & Preferences",
}


async def build_personality_prompt(db: AsyncSession) -> str | None:
    """Build a system prompt describing the user's digital twin personality.

    Returns None if no active personality profile exists.
    """
    result = await db.execute(
        select(PersonalityProfile)
        .where(PersonalityProfile.status == "active")
        .options(selectinload(PersonalityProfile.traits))
        .order_by(PersonalityProfile.created_at.desc())
        .limit(1)
    )
    profile = result.scalar_one_or_none()
    if not profile or not profile.traits:
        return None

    # Group traits by category
    grouped: dict[str, list] = {cat: [] for cat in CATEGORY_HEADINGS}
    for trait in profile.traits:
        if trait.category in grouped:
            grouped[trait.category].append(trait)

    lines = [
        "You are the digital twin of the user. Respond as if you ARE the user, "
        "not a generic assistant. Answer questions, make decisions, and express "
        "opinions the way the user would based on their personality profile below."
    ]

    for cat_key, heading in CATEGORY_HEADINGS.items():
        traits = grouped[cat_key]
        if not traits:
            continue
        lines.append(f"\n## {heading}")
        for t in traits:
            name = t.trait_name.replace("_", " ").title()
            v = t.value
            if "label" in v:
                desc = v.get("description", v["label"])
                lines.append(f"- {name}: {desc}")
            elif "items" in v and v["items"]:
                items = ", ".join(v["items"])
                lines.append(f"- {name}: {items}")
            elif "text" in v:
                lines.append(f"- {name}: {v['text']}")
            elif "type" in v:
                lines.append(f"- {name}: {v.get('label', v['type'])}")
            else:
                lines.append(f"- {name}: {v}")

    lines.append(
        "\nIMPORTANT: Always respond in the same language the user is speaking. "
        "Mirror their terminology and communication habits."
    )

    return "\n".join(lines)
