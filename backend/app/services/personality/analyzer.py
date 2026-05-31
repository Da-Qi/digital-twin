"""Personality analysis engine: collect data, analyze with DeepSeek, generate proposals."""

import json
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personality import PersonalityProfile, PersonalityTrait, PersonalityChangelog
from app.models.feedback import FeedbackLog, PersonalityUpdateProposal
from app.models.conversation import Conversation
from app.services.llm import llm_service
from app.services.personality.prompt_builder import CATEGORY_HEADINGS

AUTO_APPROVE_CONFIDENCE_THRESHOLD = 0.7
MIN_FEEDBACK_FOR_ANALYSIS = 3
MIN_CONVERSATIONS_FOR_ANALYSIS = 5

ANALYSIS_SYSTEM_PROMPT = """You are a personality analysis engine for a personal digital twin system. Your task is to analyze the user's recent feedback and conversation patterns to determine if their personality profile needs updating.

Current personality traits grouped by category:
{current_traits}

Recent user feedback and corrections:
{feedback_summary}

Recent conversation topics:
{conversation_summary}

Analyze whether the profile needs updating. Consider:
1. Has the user repeatedly corrected the twin's behavior in a specific category?
2. Have new preferences, boundaries, or values emerged?
3. Have old traits been contradicted by recent feedback?
4. Are these isolated incidents or recurring patterns?

Respond with a JSON object:
{{
  "needs_update": true/false,
  "confidence": 0.0-1.0,
  "changes": {{
    "modified": [
      {{
        "category": "<trait category>",
        "trait_name": "<existing trait name>",
        "new_value": {{}},
        "reason": "<why this change is needed>"
      }}
    ],
    "added": [
      {{
        "category": "<trait category>",
        "trait_name": "<new trait name>",
        "value": {{}},
        "reason": "<why this was added>"
      }}
    ],
    "removed": [
      {{
        "category": "<trait category>",
        "trait_name": "<trait name to remove>",
        "reason": "<why removed>"
      }}
    ]
  }},
  "summary": "<one-paragraph summary of what changed and why>"
}}

If no update is needed, set needs_update to false and leave changes as null."""


async def analyze_personality(db: AsyncSession) -> dict:
    """Run the full personality analysis pipeline."""
    # 1. Get current active profile
    result = await db.execute(
        select(PersonalityProfile)
        .options(selectinload(PersonalityProfile.traits))
        .where(PersonalityProfile.status == "active")
        .order_by(PersonalityProfile.version.desc())
        .limit(1)
    )
    current_profile = result.scalar_one_or_none()
    if not current_profile:
        return _empty_result("No active personality profile found")

    # 2. Check for pending proposals
    pending = await db.execute(
        select(PersonalityUpdateProposal).where(PersonalityUpdateProposal.status == "pending").limit(1)
    )
    if pending.scalar_one_or_none():
        return _empty_result("There is already a pending proposal. Respond to it first.")

    # 3. Get last analysis time
    last_analysis = await _get_last_analysis_time(db)

    # 4. Gather feedback marked for personality analysis
    feedback_result = await db.execute(
        select(FeedbackLog).where(
            FeedbackLog.created_at > last_analysis,
            FeedbackLog.applied_to.contains(["personality_analysis"]),
        ).order_by(FeedbackLog.created_at.desc()).limit(20)
    )
    feedback_entries = feedback_result.scalars().all()

    # 5. Count new conversations since last analysis
    count_result = await db.execute(
        select(Conversation).where(Conversation.created_at > last_analysis)
    )
    new_convs = count_result.scalars().all()
    new_conv_count = len(new_convs)

    # 6. Check minimum thresholds
    if len(feedback_entries) < MIN_FEEDBACK_FOR_ANALYSIS and new_conv_count < MIN_CONVERSATIONS_FOR_ANALYSIS:
        return _empty_result(
            f"Insufficient data: {len(feedback_entries)} feedback, {new_conv_count} conversations "
            f"(need {MIN_FEEDBACK_FOR_ANALYSIS}+ feedback or {MIN_CONVERSATIONS_FOR_ANALYSIS}+ conversations)"
        )

    # 7. Build analysis prompt
    current_traits_str = _format_traits_for_prompt(current_profile.traits)
    feedback_str = _format_feedback_for_prompt(feedback_entries)
    conv_str = _format_conversations_for_prompt(new_convs)

    prompt_content = ANALYSIS_SYSTEM_PROMPT.format(
        current_traits=current_traits_str,
        feedback_summary=feedback_str,
        conversation_summary=conv_str,
    )

    messages = [
        {"role": "system", "content": prompt_content},
    ]

    # 8. Call DeepSeek
    try:
        result_text = await llm_service.chat(messages, temperature=0.2, max_tokens=2048)
        analysis = json.loads(result_text)
    except (json.JSONDecodeError, Exception) as e:
        return _empty_result(f"Analysis failed: {e}")

    if not analysis.get("needs_update"):
        return {
            "proposal_id": None,
            "based_on": {"new_conversations": new_conv_count, "new_corrections": len(feedback_entries)},
            "changes": None,
            "auto_approved": False,
            "message": analysis.get("summary", "No update needed"),
        }

    # 9. Apply changes or create proposal
    changes = analysis.get("changes", {})
    confidence = analysis.get("confidence", 0.5)
    summary = analysis.get("summary", "")

    diff = {
        "added": changes.get("added", []),
        "modified": changes.get("modified", []),
        "removed": changes.get("removed", []),
        "diff_summary": summary,
    }

    total_changes = len(diff["added"]) + len(diff["modified"]) + len(diff["removed"])

    if confidence >= AUTO_APPROVE_CONFIDENCE_THRESHOLD and total_changes <= 2:
        new_profile = await _apply_changes(db, current_profile, changes, summary)
        return {
            "proposal_id": None,
            "based_on": {"new_conversations": new_conv_count, "new_corrections": len(feedback_entries)},
            "changes": diff,
            "auto_approved": True,
            "message": "Changes auto-approved and applied",
        }
    else:
        proposal = await _create_proposal(
            db, current_profile, changes, summary, [f.id for f in feedback_entries]
        )
        return {
            "proposal_id": str(proposal.id),
            "based_on": {"new_conversations": new_conv_count, "new_corrections": len(feedback_entries)},
            "changes": diff,
            "auto_approved": False,
            "message": "Proposal created pending approval",
        }


async def _get_last_analysis_time(db: AsyncSession) -> datetime:
    """Get the timestamp of the last analysis."""
    result = await db.execute(
        select(PersonalityChangelog)
        .where(PersonalityChangelog.change_type.in_(["created", "evolved"]))
        .order_by(PersonalityChangelog.created_at.desc())
        .limit(1)
    )
    changelog = result.scalar_one_or_none()
    if changelog:
        return changelog.created_at
    return datetime.now(timezone.utc) - timedelta(days=7)


def _format_traits_for_prompt(traits: list[PersonalityTrait]) -> str:
    grouped: dict[str, list[PersonalityTrait]] = {}
    for t in traits:
        grouped.setdefault(t.category, []).append(t)
    lines = []
    for cat, tlist in grouped.items():
        heading = CATEGORY_HEADINGS.get(cat, cat)
        lines.append(f"\n{heading}:")
        for t in tlist:
            lines.append(f"  - {t.trait_name}: {json.dumps(t.value, ensure_ascii=False)} (confidence: {t.confidence})")
    return "\n".join(lines)


def _format_feedback_for_prompt(entries: list[FeedbackLog]) -> str:
    if not entries:
        return "(no recent feedback)"
    lines = []
    for f in entries[:10]:
        lines.append(f"- [{f.classification}] {f.user_input or '(no text)'}")
    return "\n".join(lines)


def _format_conversations_for_prompt(convs: list[Conversation]) -> str:
    if not convs:
        return "(no recent conversations)"
    lines = []
    for c in convs[:10]:
        lines.append(f"- {c.title or 'Untitled'} ({c.message_count} messages)")
    if len(convs) > 10:
        lines.append(f"- ... and {len(convs) - 10} more")
    return "\n".join(lines)


def _empty_result(reason: str) -> dict:
    return {
        "proposal_id": None,
        "based_on": {"new_conversations": 0, "new_documents": 0, "new_corrections": 0},
        "changes": None,
        "auto_approved": False,
        "message": reason,
    }


async def _copy_traits_and_apply_changes(
    db: AsyncSession,
    target_profile: PersonalityProfile,
    source_profile: PersonalityProfile,
    changes: dict,
) -> dict[str, PersonalityTrait]:
    """Copy traits from source to target profile, then apply modifications/additions/removals."""
    trait_map: dict[str, PersonalityTrait] = {}
    for old_trait in source_profile.traits:
        new_trait = PersonalityTrait(
            profile_id=target_profile.id,
            category=old_trait.category,
            trait_name=old_trait.trait_name,
            value=old_trait.value,
            confidence=old_trait.confidence,
            evidence_refs=old_trait.evidence_refs,
        )
        db.add(new_trait)
        trait_map[f"{old_trait.category}:{old_trait.trait_name}"] = new_trait
    await db.flush()

    for mod in changes.get("modified", []):
        key = f"{mod['category']}:{mod['trait_name']}"
        if key in trait_map:
            trait_map[key].value = mod["new_value"]
            trait_map[key].confidence = min(1.0, trait_map[key].confidence + 0.05)

    for add in changes.get("added", []):
        db.add(PersonalityTrait(
            profile_id=target_profile.id,
            category=add["category"],
            trait_name=add["trait_name"],
            value=add["value"],
            confidence=0.4,
        ))

    for rem in changes.get("removed", []):
        key = f"{rem['category']}:{rem['trait_name']}"
        if key in trait_map:
            await db.delete(trait_map[key])

    await db.flush()
    return trait_map


async def _apply_changes(
    db: AsyncSession,
    current_profile: PersonalityProfile,
    changes: dict,
    summary: str,
) -> PersonalityProfile:
    """Create a new active profile version with changes applied."""
    new_profile = PersonalityProfile(
        version=current_profile.version + 1,
        status="active",
        summary=summary,
        parent_id=current_profile.id,
        based_on_stats={"source": "analysis", "version": current_profile.version + 1},
        activated_at=datetime.now(timezone.utc),
    )
    db.add(new_profile)
    await db.flush()

    await _copy_traits_and_apply_changes(db, new_profile, current_profile, changes)

    # Archive old profile
    current_profile.status = "archived"
    current_profile.superseded_at = datetime.now(timezone.utc)

    # Changelog
    db.add(PersonalityChangelog(
        profile_id=current_profile.id,
        change_type="evolved",
        previous_version=current_profile.version,
        reason=summary,
        changed_traits={
            "modified": [m["trait_name"] for m in changes.get("modified", [])],
            "added": [a["trait_name"] for a in changes.get("added", [])],
            "removed": [r["trait_name"] for r in changes.get("removed", [])],
        },
    ))
    await db.flush()
    return new_profile


async def _create_proposal(
    db: AsyncSession,
    current_profile: PersonalityProfile,
    changes: dict,
    summary: str,
    feedback_ids: list[uuid.UUID],
) -> PersonalityUpdateProposal:
    """Create a proposed profile version and a pending proposal for user approval."""
    proposed_profile = PersonalityProfile(
        version=current_profile.version + 1,
        status="proposed",
        summary=summary,
        parent_id=current_profile.id,
        based_on_stats={"source": "analysis", "version": current_profile.version + 1},
    )
    db.add(proposed_profile)
    await db.flush()

    await _copy_traits_and_apply_changes(db, proposed_profile, current_profile, changes)

    proposal = PersonalityUpdateProposal(
        proposed_profile_id=proposed_profile.id,
        feedback_ids=feedback_ids,
        summary=summary,
        status="pending",
        notified_at=datetime.now(timezone.utc),
    )
    db.add(proposal)
    await db.flush()
    return proposal
