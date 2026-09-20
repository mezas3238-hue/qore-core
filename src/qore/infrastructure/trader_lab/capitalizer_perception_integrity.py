"""Decision-time data/perception integrity for QORE Capitalizer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CapitalizerPerceptionStatus(StrEnum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    BAD = "BAD"


@dataclass(frozen=True, slots=True)
class CapitalizerPerceptionFacts:
    quote_fresh: bool
    bars_complete: bool
    timestamps_ordered: bool
    session_clock_valid: bool
    provenance_valid: bool
    microstructure_complete: bool


@dataclass(frozen=True, slots=True)
class CapitalizerPerceptionAssessment:
    status: CapitalizerPerceptionStatus
    reasons: tuple[str, ...]
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.grants_capital_authority:
            raise ValueError("perception integrity cannot grant capital authority")


def assess_perception_integrity(
    facts: CapitalizerPerceptionFacts,
) -> CapitalizerPerceptionAssessment:
    """Fail closed on corrupted evidence without inventing numeric thresholds."""

    hard_failures: list[str] = []
    if not facts.bars_complete:
        hard_failures.append("BARS_INCOMPLETE")
    if not facts.timestamps_ordered:
        hard_failures.append("TIMESTAMPS_NOT_ORDERED")
    if not facts.session_clock_valid:
        hard_failures.append("SESSION_CLOCK_INVALID")
    if not facts.provenance_valid:
        hard_failures.append("PROVENANCE_INVALID")
    if hard_failures:
        return CapitalizerPerceptionAssessment(
            status=CapitalizerPerceptionStatus.BAD,
            reasons=tuple(hard_failures),
        )

    degraded: list[str] = []
    if not facts.quote_fresh:
        degraded.append("QUOTE_NOT_FRESH")
    if not facts.microstructure_complete:
        degraded.append("MICROSTRUCTURE_INCOMPLETE")
    if degraded:
        return CapitalizerPerceptionAssessment(
            status=CapitalizerPerceptionStatus.DEGRADED,
            reasons=tuple(degraded),
        )

    return CapitalizerPerceptionAssessment(
        status=CapitalizerPerceptionStatus.GOOD,
        reasons=("PERCEPTION_INTEGRITY_PASSED",),
    )
