"""Global Shared attention budget driven by explicit value-of-information priority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SharedAttentionCategory(StrEnum):
    OPEN_POSITION = "OPEN_POSITION"
    RELATIONSHIP_BREAK = "RELATIONSHIP_BREAK"
    ACTIVE_OPPORTUNITY = "ACTIVE_OPPORTUNITY"
    GLOBAL_ANOMALY = "GLOBAL_ANOMALY"
    TRADER_WATCHLIST = "TRADER_WATCHLIST"
    BACKGROUND_WORLD = "BACKGROUND_WORLD"


_CATEGORY_RANK = {
    SharedAttentionCategory.OPEN_POSITION: 0,
    SharedAttentionCategory.RELATIONSHIP_BREAK: 1,
    SharedAttentionCategory.ACTIVE_OPPORTUNITY: 2,
    SharedAttentionCategory.GLOBAL_ANOMALY: 3,
    SharedAttentionCategory.TRADER_WATCHLIST: 4,
    SharedAttentionCategory.BACKGROUND_WORLD: 5,
}


@dataclass(frozen=True, slots=True)
class SharedAttentionCandidate:
    candidate_id: str
    category: SharedAttentionCategory
    as_of: datetime
    evidence_cutoff_at: datetime
    information_value_bps: int
    uncertainty_bps: int
    urgency_bps: int
    compute_units: int
    data_health_passed: bool
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("attention candidate_id must be non-empty")
        for name in ("as_of", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("attention candidate cannot use future evidence")
        for name in ("information_value_bps", "uncertainty_bps", "urgency_bps"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        if type(self.compute_units) is not int or self.compute_units < 1:
            raise ValueError("compute_units must be positive int")
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError("attention provenance_refs must be canonical")


@dataclass(frozen=True, slots=True)
class SharedAttentionDecision:
    candidate_id: str
    category: SharedAttentionCategory
    selected: bool
    rank: int
    information_value_bps: int
    compute_units: int
    reason_code: str


@dataclass(frozen=True, slots=True)
class SharedAttentionPlan:
    as_of: datetime
    budget_units: int
    used_units: int
    decisions: tuple[SharedAttentionDecision, ...]
    unresolved_candidate_ids: tuple[str, ...]
    methodology_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("attention plan as_of must be timezone-aware")
        if type(self.budget_units) is not int or self.budget_units < 1:
            raise ValueError("attention budget_units must be positive int")
        if not 0 <= self.used_units <= self.budget_units:
            raise ValueError("attention used_units outside budget")
        if self.unresolved_candidate_ids != tuple(
            sorted(set(self.unresolved_candidate_ids))
        ):
            raise ValueError("unresolved candidate ids must be canonical")
        if (
            self.methodology_authority
            or self.capital_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise ValueError("attention plan carries no downstream authority")


def _sort_key(candidate: SharedAttentionCandidate) -> tuple[int, int, int, int, int, str]:
    """Owner-priority first, then pure information-value ordering."""

    return (
        _CATEGORY_RANK[candidate.category],
        -candidate.information_value_bps,
        -candidate.uncertainty_bps,
        -candidate.urgency_bps,
        candidate.compute_units,
        candidate.candidate_id,
    )


def allocate_shared_attention(
    candidates: tuple[SharedAttentionCandidate, ...],
    *,
    as_of: datetime,
    budget_units: int,
) -> SharedAttentionPlan:
    """Allocate scarce cognition without touching capital or trading authority."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("attention as_of must be timezone-aware")
    if type(budget_units) is not int or budget_units < 1:
        raise ValueError("attention budget_units must be positive int")
    ids = tuple(item.candidate_id for item in candidates)
    if ids != tuple(sorted(set(ids))):
        raise ValueError("attention candidates must be unique and canonical")
    if any(item.as_of != as_of for item in candidates):
        raise ValueError("attention candidates must share one causal as_of")
    if any(item.evidence_cutoff_at > as_of for item in candidates):
        raise ValueError("attention cannot consume future evidence")

    ranked = tuple(sorted(candidates, key=_sort_key))
    used = 0
    decisions: list[SharedAttentionDecision] = []
    unresolved: list[str] = []

    for rank, item in enumerate(ranked, start=1):
        if not item.data_health_passed:
            decisions.append(
                SharedAttentionDecision(
                    candidate_id=item.candidate_id,
                    category=item.category,
                    selected=False,
                    rank=rank,
                    information_value_bps=item.information_value_bps,
                    compute_units=item.compute_units,
                    reason_code="DATA_HEALTH_BLOCK",
                )
            )
            unresolved.append(item.candidate_id)
            continue
        if item.information_value_bps <= 0:
            decisions.append(
                SharedAttentionDecision(
                    candidate_id=item.candidate_id,
                    category=item.category,
                    selected=False,
                    rank=rank,
                    information_value_bps=item.information_value_bps,
                    compute_units=item.compute_units,
                    reason_code="ZERO_INFORMATION_VALUE",
                )
            )
            continue
        if used + item.compute_units > budget_units:
            decisions.append(
                SharedAttentionDecision(
                    candidate_id=item.candidate_id,
                    category=item.category,
                    selected=False,
                    rank=rank,
                    information_value_bps=item.information_value_bps,
                    compute_units=item.compute_units,
                    reason_code="ATTENTION_BUDGET_EXHAUSTED",
                )
            )
            unresolved.append(item.candidate_id)
            continue

        used += item.compute_units
        decisions.append(
            SharedAttentionDecision(
                candidate_id=item.candidate_id,
                category=item.category,
                selected=True,
                rank=rank,
                information_value_bps=item.information_value_bps,
                compute_units=item.compute_units,
                reason_code="SELECTED_FOR_COGNITIVE_ATTENTION",
            )
        )

    return SharedAttentionPlan(
        as_of=as_of,
        budget_units=budget_units,
        used_units=used,
        decisions=tuple(decisions),
        unresolved_candidate_ids=tuple(sorted(unresolved)),
    )
