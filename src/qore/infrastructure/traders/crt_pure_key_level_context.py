"""Source-bound key-level context for VT08 CRT PURE.

Primary RomeoTPT material closes the causal ROLE of key levels and explicitly
names old CRTH/CRL reactions plus the MOB (make-or-break) level.  The reviewed
source does not close a universal OB/FVG/PDH/PDL taxonomy, proximity threshold,
or NO_KEY_LEVEL => ABSTAIN rule.

This module therefore enriches cognition without granting entry/capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CrtPureKeyLevelFamily(StrEnum):
    OLD_CRTH = "OLD_CRTH"
    OLD_CRTL = "OLD_CRTL"
    MOB = "MOB"
    OTHER_SOURCE_AUTHORIZED = "OTHER_SOURCE_AUTHORIZED"


class CrtPureKeyLevelInteraction(StrEnum):
    UNKNOWN = "UNKNOWN"
    JOURNEY_TO = "JOURNEY_TO"
    REACTION_FROM = "REACTION_FROM"
    MAKE_OR_BREAK = "MAKE_OR_BREAK"


class CrtPureKeyLevelReadiness(StrEnum):
    ROLE_SOURCE_CLOSED = "ROLE_SOURCE_CLOSED"
    FAMILY_SOURCE_CLOSED = "FAMILY_SOURCE_CLOSED"
    TAXONOMY_UNRESOLVED = "TAXONOMY_UNRESOLVED"
    GEOMETRY_UNRESOLVED = "GEOMETRY_UNRESOLVED"


_SOURCE_NATIVE_FAMILIES: tuple[CrtPureKeyLevelFamily, ...] = (
    CrtPureKeyLevelFamily.OLD_CRTH,
    CrtPureKeyLevelFamily.OLD_CRTL,
    CrtPureKeyLevelFamily.MOB,
)


@dataclass(frozen=True, slots=True)
class CrtPureKeyLevelEvidence:
    evidence_id: str
    level_token: str
    observed_at: datetime
    interaction: CrtPureKeyLevelInteraction
    family: CrtPureKeyLevelFamily
    level_timeframe_seconds: int | None = None

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.level_token:
            raise ValueError("key-level evidence identifiers must be non-empty")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("key-level evidence timestamp must be timezone-aware")
        if (
            self.level_timeframe_seconds is not None
            and self.level_timeframe_seconds <= 0
        ):
            raise ValueError("key-level timeframe must be positive when known")


@dataclass(frozen=True, slots=True)
class CrtPureKeyLevelAssessment:
    interaction: CrtPureKeyLevelInteraction
    families: tuple[CrtPureKeyLevelFamily, ...]
    evidence_ids: tuple[str, ...]
    readiness: tuple[CrtPureKeyLevelReadiness, ...]
    higher_timeframe_context_present: bool
    hard_veto_if_absent: bool = False
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.hard_veto_if_absent:
            raise ValueError("source does not close universal NO_KEY_LEVEL => ABSTAIN")
        if self.grants_entry_authority:
            raise ValueError("key-level context cannot independently grant entry")
        if self.grants_capital_authority:
            raise ValueError("key-level context cannot grant capital authority")


def source_native_key_level_families() -> tuple[CrtPureKeyLevelFamily, ...]:
    """Return only key-level families directly named in accepted primary evidence."""

    return _SOURCE_NATIVE_FAMILIES


def assess_key_level_context(
    evidence: tuple[CrtPureKeyLevelEvidence, ...],
    *,
    execution_timeframe_seconds: int,
) -> CrtPureKeyLevelAssessment:
    """Describe causal key-level context without inventing universal geometry."""

    if execution_timeframe_seconds <= 0:
        raise ValueError("execution timeframe must be positive")

    if not evidence:
        return CrtPureKeyLevelAssessment(
            interaction=CrtPureKeyLevelInteraction.UNKNOWN,
            families=(),
            evidence_ids=(),
            readiness=(
                CrtPureKeyLevelReadiness.ROLE_SOURCE_CLOSED,
                CrtPureKeyLevelReadiness.FAMILY_SOURCE_CLOSED,
                CrtPureKeyLevelReadiness.TAXONOMY_UNRESOLVED,
                CrtPureKeyLevelReadiness.GEOMETRY_UNRESOLVED,
            ),
            higher_timeframe_context_present=False,
        )

    interactions = {item.interaction for item in evidence}
    resolved = interactions - {CrtPureKeyLevelInteraction.UNKNOWN}
    interaction = (
        next(iter(resolved))
        if len(resolved) == 1
        else CrtPureKeyLevelInteraction.UNKNOWN
    )
    htf_present = any(
        item.level_timeframe_seconds is not None
        and item.level_timeframe_seconds > execution_timeframe_seconds
        for item in evidence
    )
    families = tuple(dict.fromkeys(item.family for item in evidence))
    return CrtPureKeyLevelAssessment(
        interaction=interaction,
        families=families,
        evidence_ids=tuple(item.evidence_id for item in evidence),
        readiness=(
            CrtPureKeyLevelReadiness.ROLE_SOURCE_CLOSED,
            CrtPureKeyLevelReadiness.FAMILY_SOURCE_CLOSED,
            CrtPureKeyLevelReadiness.TAXONOMY_UNRESOLVED,
            CrtPureKeyLevelReadiness.GEOMETRY_UNRESOLVED,
        ),
        higher_timeframe_context_present=htf_present,
    )


def key_level_absence_is_universal_veto() -> bool:
    """Explicitly preserve the source boundary discovered in audit."""

    return False
