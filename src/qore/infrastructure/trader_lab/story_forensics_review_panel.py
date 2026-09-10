"""Independent multi-reviewer analysis contract for Trader Story Forensics.

Every retained episode and selected streak is a frozen research subject. Harness,
Expert, Work, Architect and the Human Owner contribute bounded assessments without
changing the Trader methodology. Machine first-pass packets intentionally omit
other reviews to reduce anchoring and groupthink. Policy synthesis remains research
only and always requires fresh falsification before any methodology change.
"""

from __future__ import annotations

import json
from copy import deepcopy
from enum import StrEnum
from hashlib import sha256
from typing import cast

from qore.infrastructure.trader_lab.first_cohort_story_forensics import (
    FirstCohortStoryForensicsError,
)

_STORY_SCHEMA = "qore.trader_lab.first_cohort_story_forensics.v1"
_PANEL_SCHEMA = "qore.trader_lab.story_forensics_review_panel.v1"
_POLICY_SCHEMA = "qore.trader_lab.story_forensics_policy_candidate.v1"
_NO_SAFE_IMPROVEMENT = "NO_SAFE_IMPROVEMENT_FOUND"
_NO_MATERIAL_DEGRADATION = "NO_MATERIAL_DEGRADATION_RISK_FOUND"


class StoryForensicsReviewError(FirstCohortStoryForensicsError):
    """Raised when reviewer evidence or sequencing weakens the review contract."""

    __slots__ = ()


class ReviewRole(StrEnum):
    """Required independent perspectives for every frozen story subject."""

    HARNESS = "harness"
    EXPERT = "expert"
    WORK = "work"
    ARCHITECT = "architect"
    HUMAN_OWNER = "human_owner"


class ReviewScope(StrEnum):
    """Bounded areas where a research hypothesis may apply."""

    ENTRY = "entry"
    FILTER = "filter"
    MARKET = "market"
    DIRECTION = "direction"
    REGIME = "regime"
    TIMING = "timing"
    LIFECYCLE = "lifecycle"
    RISK_GEOMETRY = "risk_geometry"
    ABSTENTION = "abstention"
    PRESERVATION = "preservation"
    OTHER = "other"


_MACHINE_ROLES = (
    ReviewRole.HARNESS,
    ReviewRole.EXPERT,
    ReviewRole.WORK,
    ReviewRole.ARCHITECT,
)
_REQUIRED_ROLES = (*_MACHINE_ROLES, ReviewRole.HUMAN_OWNER)


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise StoryForensicsReviewError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise StoryForensicsReviewError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise StoryForensicsReviewError(f"{field_name} must be a non-empty string")
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise StoryForensicsReviewError(f"{field_name} must be bool")
    return value


def _string_list(value: object, *, field_name: str) -> list[str]:
    rows = _array(value, field_name=field_name)
    if not rows:
        raise StoryForensicsReviewError(f"{field_name} cannot be empty")
    result: list[str] = []
    for item in rows:
        result.append(_text(item, field_name=field_name))
    if len(set(result)) != len(result):
        raise StoryForensicsReviewError(f"{field_name} cannot contain duplicates")
    return result


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise StoryForensicsReviewError("review payload must be canonical JSON") from error


def _digest(value: object) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _story_contract(story: dict[str, object]) -> None:
    if _text(story.get("schema"), field_name="story schema") != _STORY_SCHEMA:
        raise StoryForensicsReviewError("review panel requires Story Forensics v1")
    if not _strict_bool(story.get("research_only"), field_name="research_only"):
        raise StoryForensicsReviewError("review panel requires research-only evidence")
    if _strict_bool(story.get("execution_authority"), field_name="execution_authority"):
        raise StoryForensicsReviewError("review panel refuses execution-authoritative evidence")


def _episode_subjects(story: dict[str, object]) -> list[dict[str, object]]:
    subjects: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in _array(story.get("episodes"), field_name="episodes"):
        episode = _object(item, field_name="episode")
        episode_id = _text(episode.get("episode_id"), field_name="episode id")
        if episode_id in seen:
            raise StoryForensicsReviewError("duplicate episode id")
        seen.add(episode_id)
        subjects.append(
            {
                "subject_id": episode_id,
                "subject_type": "episode",
                "subject_digest": _digest(episode),
                "trader_code": _text(
                    episode.get("trader_code"),
                    field_name="episode trader code",
                ),
                "symbol": _text(episode.get("symbol"), field_name="episode symbol"),
                "classification": _text(
                    episode.get("classification"),
                    field_name="episode classification",
                ),
            }
        )
    return subjects


def _streak_subjects(story: dict[str, object]) -> list[dict[str, object]]:
    families = _object(story.get("story_families"), field_name="story families")
    subjects: list[dict[str, object]] = []
    seen: set[str] = set()
    for family_name in ("winning_streaks", "losing_streaks"):
        for item in _array(families.get(family_name), field_name=family_name):
            streak = _object(item, field_name="streak")
            streak_id = _text(streak.get("streak_id"), field_name="streak id")
            if streak_id in seen:
                continue
            seen.add(streak_id)
            episode_ids = _string_list(
                streak.get("episode_ids"),
                field_name="streak episode ids",
            )
            subjects.append(
                {
                    "subject_id": streak_id,
                    "subject_type": "streak",
                    "subject_digest": _digest(streak),
                    "family": family_name,
                    "episode_ids": episode_ids,
                }
            )
    return subjects


def _empty_lanes() -> dict[str, object]:
    return {
        role.value: {
            "status": "PENDING",
            "assessment": None,
            "assessment_digest": None,
        }
        for role in _REQUIRED_ROLES
    }


def build_review_panel(story: dict[str, object]) -> dict[str, object]:
    """Create one immutable-subject review ledger for every episode and streak."""
    _story_contract(story)
    subjects = [*_episode_subjects(story), *_streak_subjects(story)]
    if not subjects:
        raise StoryForensicsReviewError("review panel requires at least one subject")
    for subject in subjects:
        subject["review_lanes"] = _empty_lanes()
        subject["synthesis_status"] = "BLOCKED_PENDING_REVIEWS"
    return {
        "schema": _PANEL_SCHEMA,
        "research_only": True,
        "execution_authority": False,
        "source_story_digest": _digest(story),
        "source_forensics_fingerprint": _text(
            story.get("forensics_fingerprint"),
            field_name="forensics fingerprint",
        ),
        "review_protocol": {
            "required_roles": [role.value for role in _REQUIRED_ROLES],
            "machine_first_pass_independent": True,
            "human_reviews_after_machine_first_pass": True,
            "consensus_required": False,
            "disagreement_retained": True,
            "direct_methodology_mutation_allowed": False,
            "fresh_holdout_required_after_methodology_change": True,
            "favorable_candidate_sentinel": _NO_SAFE_IMPROVEMENT,
            "degradation_risk_sentinel": _NO_MATERIAL_DEGRADATION,
        },
        "subjects": subjects,
    }


def _panel_subject(
    panel: dict[str, object],
    *,
    subject_id: str,
) -> dict[str, object]:
    if _text(panel.get("schema"), field_name="panel schema") != _PANEL_SCHEMA:
        raise StoryForensicsReviewError("unexpected review panel schema")
    matches = [
        _object(item, field_name="review subject")
        for item in _array(panel.get("subjects"), field_name="review subjects")
        if _text(
            _object(item, field_name="review subject").get("subject_id"),
            field_name="subject id",
        )
        == subject_id
    ]
    if len(matches) != 1:
        raise StoryForensicsReviewError("subject_id must identify exactly one review subject")
    return matches[0]


def _parse_role(value: object) -> ReviewRole:
    raw = _text(value, field_name="review role")
    try:
        return ReviewRole(raw)
    except ValueError as error:
        raise StoryForensicsReviewError("unknown review role") from error


def _parse_scope(value: object) -> ReviewScope:
    raw = _text(value, field_name="review scope")
    try:
        return ReviewScope(raw)
    except ValueError as error:
        raise StoryForensicsReviewError("unknown review scope") from error


def reviewer_packet(
    panel: dict[str, object],
    *,
    subject_id: str,
    role: ReviewRole,
) -> dict[str, object]:
    """Return the bounded packet a reviewer may see for one first-pass assessment."""
    subject = _panel_subject(panel, subject_id=subject_id)
    lanes = _object(subject.get("review_lanes"), field_name="review lanes")
    if role is ReviewRole.HUMAN_OWNER:
        sealed_machine: dict[str, object] = {}
        for machine_role in _MACHINE_ROLES:
            lane = _object(lanes.get(machine_role.value), field_name="machine review lane")
            if lane.get("status") != "SEALED":
                raise StoryForensicsReviewError(
                    "human review is blocked until machine first-pass reviews are sealed"
                )
            sealed_machine[machine_role.value] = deepcopy(lane.get("assessment"))
        return {
            "subject": {
                key: deepcopy(value)
                for key, value in subject.items()
                if key not in {"review_lanes", "synthesis_status"}
            },
            "role": role.value,
            "mode": "human_synthesis",
            "sealed_machine_reviews": sealed_machine,
            "required_output": _required_output_contract(),
        }
    return {
        "subject": {
            key: deepcopy(value)
            for key, value in subject.items()
            if key not in {"review_lanes", "synthesis_status"}
        },
        "role": role.value,
        "mode": "independent_first_pass",
        "required_output": _required_output_contract(),
    }


def _required_output_contract() -> dict[str, object]:
    return {
        "favorable_candidate": (
            "evidence-backed improvement/preservation idea or "
            f"{_NO_SAFE_IMPROVEMENT}"
        ),
        "degradation_risks": (
            "one or more risks, or " f"{_NO_MATERIAL_DEGRADATION}"
        ),
        "preserve": "one or more invariants/edge characteristics to protect",
        "evidence": "one or more exact observations from the frozen subject",
        "counterexample_or_falsifier": "what would disprove the candidate",
        "scope": [scope.value for scope in ReviewScope],
        "confidence": ["low", "medium", "high"],
        "fresh_holdout_required": True,
    }


def _validate_assessment(
    assessment: dict[str, object],
    *,
    subject_digest: str,
) -> ReviewRole:
    if _text(assessment.get("subject_digest"), field_name="subject digest") != subject_digest:
        raise StoryForensicsReviewError("assessment subject digest mismatch")
    role = _parse_role(assessment.get("role"))
    favorable = _text(
        assessment.get("favorable_candidate"),
        field_name="favorable candidate",
    )
    degradation_risks = _string_list(
        assessment.get("degradation_risks"),
        field_name="degradation risks",
    )
    _string_list(assessment.get("preserve"), field_name="preserve")
    _string_list(assessment.get("evidence"), field_name="evidence")
    _text(
        assessment.get("counterexample_or_falsifier"),
        field_name="counterexample or falsifier",
    )
    _parse_scope(assessment.get("scope"))
    confidence = _text(assessment.get("confidence"), field_name="confidence")
    if confidence not in {"low", "medium", "high"}:
        raise StoryForensicsReviewError("confidence must be low, medium or high")
    if not _strict_bool(
        assessment.get("fresh_holdout_required"),
        field_name="fresh_holdout_required",
    ):
        raise StoryForensicsReviewError("review hypotheses require fresh holdout governance")
    if favorable == _NO_SAFE_IMPROVEMENT and assessment.get("scope") != "preservation":
        raise StoryForensicsReviewError(
            "NO_SAFE_IMPROVEMENT_FOUND must use preservation scope"
        )
    if _NO_MATERIAL_DEGRADATION in degradation_risks and len(degradation_risks) != 1:
        raise StoryForensicsReviewError(
            "degradation sentinel cannot be mixed with material risks"
        )
    return role


def seal_assessment(
    panel: dict[str, object],
    *,
    subject_id: str,
    assessment: dict[str, object],
) -> dict[str, object]:
    """Return a new panel with one exact role assessment sealed once."""
    result = deepcopy(panel)
    subject = _panel_subject(result, subject_id=subject_id)
    subject_digest = _text(subject.get("subject_digest"), field_name="subject digest")
    role = _validate_assessment(assessment, subject_digest=subject_digest)
    lanes = _object(subject.get("review_lanes"), field_name="review lanes")
    lane = _object(lanes.get(role.value), field_name="review lane")
    if lane.get("status") != "PENDING":
        raise StoryForensicsReviewError("review lane is already sealed")
    if role is ReviewRole.HUMAN_OWNER:
        for machine_role in _MACHINE_ROLES:
            machine_lane = _object(
                lanes.get(machine_role.value),
                field_name="machine review lane",
            )
            if machine_lane.get("status") != "SEALED":
                raise StoryForensicsReviewError(
                    "human review cannot seal before all machine first passes"
                )
    else:
        human_lane = _object(
            lanes.get(ReviewRole.HUMAN_OWNER.value),
            field_name="human review lane",
        )
        if human_lane.get("status") == "SEALED":
            raise StoryForensicsReviewError("machine first pass cannot follow human synthesis")
    lane["status"] = "SEALED"
    lane["assessment"] = deepcopy(assessment)
    lane["assessment_digest"] = _digest(assessment)
    all_sealed = all(
        _object(lanes.get(role_item.value), field_name="review lane").get("status")
        == "SEALED"
        for role_item in _REQUIRED_ROLES
    )
    subject["synthesis_status"] = (
        "READY_FOR_ARCHITECT_ADJUDICATION"
        if all_sealed
        else "BLOCKED_PENDING_REVIEWS"
    )
    return result


def synthesize_subject(
    panel: dict[str, object],
    *,
    subject_id: str,
) -> dict[str, object]:
    """Expose all sealed perspectives without treating agreement as certification."""
    subject = _panel_subject(panel, subject_id=subject_id)
    lanes = _object(subject.get("review_lanes"), field_name="review lanes")
    if subject.get("synthesis_status") != "READY_FOR_ARCHITECT_ADJUDICATION":
        raise StoryForensicsReviewError("subject synthesis requires all five sealed reviews")
    assessments: dict[str, object] = {}
    favorable_candidates: list[str] = []
    degradation_risks: list[str] = []
    preserve: list[str] = []
    scopes: list[str] = []
    for role in _REQUIRED_ROLES:
        lane = _object(lanes.get(role.value), field_name="review lane")
        assessment = _object(lane.get("assessment"), field_name="sealed assessment")
        assessments[role.value] = deepcopy(assessment)
        favorable_candidates.append(
            _text(
                assessment.get("favorable_candidate"),
                field_name="favorable candidate",
            )
        )
        degradation_risks.extend(
            _string_list(
                assessment.get("degradation_risks"),
                field_name="degradation risks",
            )
        )
        preserve.extend(_string_list(assessment.get("preserve"), field_name="preserve"))
        scopes.append(_parse_scope(assessment.get("scope")).value)
    return {
        "schema": _POLICY_SCHEMA,
        "subject_id": subject_id,
        "subject_digest": _text(subject.get("subject_digest"), field_name="subject digest"),
        "state": "RESEARCH_CANDIDATE_ONLY",
        "activation_authority": False,
        "consensus_required": False,
        "disagreement_retained": True,
        "fresh_holdout_required": True,
        "favorable_candidates": favorable_candidates,
        "degradation_risks": sorted(set(degradation_risks)),
        "preserve": sorted(set(preserve)),
        "scopes": scopes,
        "reviews": assessments,
    }


def build_trader_policy_candidate(panel: dict[str, object]) -> dict[str, object]:
    """Aggregate reviewed subjects into a non-authoritative per-Trader policy ledger."""
    subjects = _array(panel.get("subjects"), field_name="review subjects")
    syntheses: list[dict[str, object]] = []
    pending: list[str] = []
    for item in subjects:
        subject = _object(item, field_name="review subject")
        subject_id = _text(subject.get("subject_id"), field_name="subject id")
        if subject.get("synthesis_status") != "READY_FOR_ARCHITECT_ADJUDICATION":
            pending.append(subject_id)
            continue
        syntheses.append(synthesize_subject(panel, subject_id=subject_id))
    return {
        "schema": _POLICY_SCHEMA,
        "state": "BLOCKED_PENDING_REVIEWS" if pending else "READY_FOR_ADJUDICATION",
        "activation_authority": False,
        "fresh_holdout_required": True,
        "reviewed_subject_count": len(syntheses),
        "pending_subject_ids": pending,
        "subject_policy_candidates": syntheses,
        "policy_rule": (
            "repeated cross-subject support and counterexamples must be adjudicated; "
            "reviewer consensus alone is insufficient"
        ),
    }
