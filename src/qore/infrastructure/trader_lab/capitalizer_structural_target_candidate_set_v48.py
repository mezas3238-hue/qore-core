"""V48 structural target candidate-set semantics.

V46/V47 collapsed target availability into an exactly-one resolver. V48 separates:
1. source-supported target availability: one or more causal untouched HTF objectives exist;
2. target-selection policy: which objective an execution route actually chooses.

Only (1) is closed here. No nearest/farthest/R:R/outcome target is selected.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_STRUCTURAL_TARGET_CANDIDATE_SET"


class V48TargetDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class V48StructuralTargetCandidate:
    target_id: str
    kind: str
    price: Decimal
    known_at_iso: str
    untouched: bool
    higher_timeframe: bool

    def __post_init__(self) -> None:
        if not self.target_id or not self.kind or not self.known_at_iso:
            raise ValueError("target candidate requires identity/provenance")
        if not self.price.is_finite() or self.price <= 0:
            raise ValueError("target price must be finite positive")


@dataclass(frozen=True, slots=True)
class V48StructuralTargetCandidateSet:
    identity: str
    direction: V48TargetDirection
    entry_reference: Decimal
    eligible: tuple[V48StructuralTargetCandidate, ...]
    rejected: tuple[V48StructuralTargetCandidate, ...]
    exact_target_selected: bool = False
    outcome_used: bool = False
    reward_r_used: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 target set identity is frozen")
        if not self.entry_reference.is_finite() or self.entry_reference <= 0:
            raise ValueError("entry reference must be finite positive")
        if self.exact_target_selected:
            raise ValueError("candidate-set stage cannot select final target")
        if self.outcome_used or self.reward_r_used:
            raise ValueError("target availability cannot use outcome/R ranking")
        ids = tuple(item.target_id for item in self.eligible + self.rejected)
        if len(ids) != len(set(ids)):
            raise ValueError("target candidates must be unique")

    @property
    def structural_target_available(self) -> bool:
        return bool(self.eligible)

    @property
    def ambiguous_multiple_targets(self) -> bool:
        return len(self.eligible) > 1


def build_target_candidate_set(
    candidates: tuple[V48StructuralTargetCandidate, ...],
    *,
    direction: V48TargetDirection,
    entry_reference: Decimal,
) -> V48StructuralTargetCandidateSet:
    """Keep every causal source-valid target without choosing between them."""

    eligible: list[V48StructuralTargetCandidate] = []
    rejected: list[V48StructuralTargetCandidate] = []
    for candidate in candidates:
        ahead = (
            candidate.price > entry_reference
            if direction is V48TargetDirection.LONG
            else candidate.price < entry_reference
        )
        if candidate.untouched and candidate.higher_timeframe and ahead:
            eligible.append(candidate)
        else:
            rejected.append(candidate)

    return V48StructuralTargetCandidateSet(
        identity=IDENTITY,
        direction=direction,
        entry_reference=entry_reference,
        eligible=tuple(eligible),
        rejected=tuple(rejected),
    )
