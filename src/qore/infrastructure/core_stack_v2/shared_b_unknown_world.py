"""Architect-B unknown-world semantics.

Shared must preserve the distinction among observed, missing, stale, degraded,
not-comparable, not-observed and unknown states. None may silently collapse to
neutral, normal or safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SharedBWorldKnowledgeState(StrEnum):
    OBSERVED = "OBSERVED"
    MISSING = "MISSING"
    STALE = "STALE"
    DEGRADED = "DEGRADED"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    NOT_OBSERVED = "NOT_OBSERVED"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class SharedBWorldObservation:
    observation_key: str
    as_of: datetime
    evidence_cutoff_at: datetime
    state: SharedBWorldKnowledgeState
    value_present: bool
    quality_bps: int | None
    uncertainty_bps: int
    reason_codes: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    neutral_assumption_applied: bool = False
    safe_assumption_applied: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.observation_key.strip():
            raise ValueError("observation_key must be non-empty")
        for name in ("as_of", "evidence_cutoff_at"):
            value=getattr(self,name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("future world evidence is forbidden")
        if not isinstance(self.state,SharedBWorldKnowledgeState):
            raise ValueError("state invalid")
        if type(self.value_present) is not bool:
            raise ValueError("value_present must be bool")
        if self.quality_bps is not None and (
            type(self.quality_bps) is not int or not 0 <= self.quality_bps <= 10_000
        ):
            raise ValueError("quality_bps outside 0..10000")
        if (
            type(self.uncertainty_bps) is not int
            or not 0 <= self.uncertainty_bps <= 10_000
        ):
            raise ValueError("uncertainty_bps outside 0..10000")
        if self.state is SharedBWorldKnowledgeState.OBSERVED:
            if not self.value_present:
                raise ValueError("OBSERVED requires value_present")
            if self.quality_bps is None:
                raise ValueError("OBSERVED requires quality")
        elif self.state in {
            SharedBWorldKnowledgeState.MISSING,
            SharedBWorldKnowledgeState.NOT_OBSERVED,
            SharedBWorldKnowledgeState.UNKNOWN,
            SharedBWorldKnowledgeState.INSUFFICIENT,
        } and self.value_present:
            raise ValueError(
                f"{self.state.value} cannot claim an observed value"
            )
        if (
            not self.reason_codes
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise ValueError("reason_codes must be non-empty and canonical")
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError("provenance_refs must be non-empty and canonical")
        if (
            self.neutral_assumption_applied
            or self.safe_assumption_applied
            or self.productive_authority
        ):
            raise ValueError(
                "unknown-world state cannot be silently normalized or authoritative"
            )


def world_observation_can_support_new_claim(
    observation: SharedBWorldObservation,
) -> bool:
    """Only explicit observed evidence may support a new factual market claim."""

    return (
        observation.state is SharedBWorldKnowledgeState.OBSERVED
        and observation.value_present
        and observation.quality_bps is not None
        and observation.quality_bps > 0
    )


def world_observation_requires_abstention(
    observation: SharedBWorldObservation,
) -> bool:
    return not world_observation_can_support_new_claim(observation)
