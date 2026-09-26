"""Causal temporal-stability measurement for Phase-19 interaction evidence.

This module asks a narrow scientific question: does a cross-Trader temporal-overlap
distribution measured in an earlier window resemble a strictly later validation
window? It never changes expected value, sizing, budgets, QORE Risk, or execution.

Only opportunity identity and observed entry/exit timestamps are used. Strategy
outcomes and heterogeneous Trader R are deliberately outside this contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ChronologicalOpportunity,
)


class Phase19TemporalStabilityStatus(StrEnum):
    MEASURED_OBSERVATIONAL_ONLY = "MEASURED_OBSERVATIONAL_ONLY"
    INSUFFICIENT_SEGMENT_COVERAGE = "INSUFFICIENT_SEGMENT_COVERAGE"
    INSUFFICIENT_INTERACTIONS = "INSUFFICIENT_INTERACTIONS"


@dataclass(frozen=True, slots=True)
class Phase19TemporalPairStability:
    left_trader: TraderLineage
    right_trader: TraderLineage
    training_overlap_pairs: int
    validation_overlap_pairs: int
    training_share: Decimal
    validation_share: Decimal

    def __post_init__(self) -> None:
        if self.left_trader is self.right_trader:
            raise CiboCapitalManagementError(
                "temporal stability pair requires distinct Traders"
            )
        for trader in (self.left_trader, self.right_trader):
            if trader not in PHASE19_REQUIRED_TRADERS:
                raise CiboCapitalManagementError(
                    "temporal stability pair Trader outside CMA portfolio"
                )
        for name in ("training_overlap_pairs", "validation_overlap_pairs"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CiboCapitalManagementError(
                    f"{name} must be non-negative int"
                )
        for name in ("training_share", "validation_share"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite Decimal in [0, 1]"
                )


@dataclass(frozen=True, slots=True)
class Phase19TemporalStabilityEvidence:
    common_window_start: datetime
    split_at: datetime
    common_window_end: datetime
    training_opportunities: int
    validation_opportunities: int
    boundary_crossing_opportunities_excluded: int
    training_cross_trader_overlap_pairs: int
    validation_cross_trader_overlap_pairs: int
    training_population: tuple[TraderLineage, ...]
    validation_population: tuple[TraderLineage, ...]
    pair_stability: tuple[Phase19TemporalPairStability, ...]
    total_variation_distance: Decimal | None
    weighted_jaccard_similarity: Decimal | None
    status: Phase19TemporalStabilityStatus

    def __post_init__(self) -> None:
        for name in ("common_window_start", "split_at", "common_window_end"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"Phase 19 temporal stability {name} must be timezone-aware"
                )
        if not self.common_window_start < self.split_at < self.common_window_end:
            raise CiboCapitalManagementError(
                "Phase 19 temporal stability split must be strictly inside window"
            )
        if len(self.pair_stability) != 21:
            raise CiboCapitalManagementError(
                "Phase 19 temporal stability requires complete 21-pair matrix"
            )
        for name in (
            "training_opportunities",
            "validation_opportunities",
            "boundary_crossing_opportunities_excluded",
            "training_cross_trader_overlap_pairs",
            "validation_cross_trader_overlap_pairs",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CiboCapitalManagementError(
                    f"Phase 19 temporal stability {name} must be non-negative int"
                )
        for value in (
            self.total_variation_distance,
            self.weighted_jaccard_similarity,
        ):
            if value is not None and (
                not value.is_finite() or value < 0 or value > 1
            ):
                raise CiboCapitalManagementError(
                    "Phase 19 temporal stability similarity metric outside [0, 1]"
                )


def _complete_pair_keys() -> tuple[tuple[TraderLineage, TraderLineage], ...]:
    pairs: list[tuple[TraderLineage, TraderLineage]] = []
    for index, left in enumerate(PHASE19_REQUIRED_TRADERS):
        for right in PHASE19_REQUIRED_TRADERS[index + 1 :]:
            first, second = sorted(
                (left, right),
                key=lambda trader: trader.value,
            )
            pairs.append((first, second))
    return tuple(pairs)


def _cross_trader_pair_counts(
    opportunities: tuple[Phase19ChronologicalOpportunity, ...],
) -> dict[tuple[TraderLineage, TraderLineage], int]:
    counts = {key: 0 for key in _complete_pair_keys()}
    ordered = tuple(
        sorted(
            opportunities,
            key=lambda item: (
                item.entry_at,
                item.trader_id.value,
                item.signal_fingerprint,
            ),
        )
    )
    for left_index, left in enumerate(ordered):
        for right in ordered[left_index + 1 :]:
            if right.entry_at >= left.exit_at:
                break
            if left.trader_id is right.trader_id:
                continue
            if left.entry_at < right.exit_at and right.entry_at < left.exit_at:
                first, second = sorted(
                    (left.trader_id, right.trader_id),
                    key=lambda trader: trader.value,
                )
                counts[(first, second)] += 1
    return counts


def measure_phase19_temporal_overlap_stability(
    *,
    opportunities: tuple[Phase19ChronologicalOpportunity, ...],
    common_window_start: datetime,
    split_at: datetime,
    common_window_end: datetime,
) -> Phase19TemporalStabilityEvidence:
    """Measure earlier-window overlap distribution against later-window evidence.

    Positions crossing the split are excluded from both sides so the validation
    window cannot leak position lifetime information into the frozen training
    distribution.
    """

    for name, value in (
        ("common_window_start", common_window_start),
        ("split_at", split_at),
        ("common_window_end", common_window_end),
    ):
        if value.tzinfo is None or value.utcoffset() is None:
            raise CiboCapitalManagementError(
                f"Phase 19 temporal stability {name} must be timezone-aware"
            )
    if not common_window_start < split_at < common_window_end:
        raise CiboCapitalManagementError(
            "Phase 19 temporal stability split must be strictly inside window"
        )
    if not opportunities:
        raise CiboCapitalManagementError(
            "Phase 19 temporal stability requires opportunities"
        )

    fingerprints = tuple(
        (item.trader_id, item.signal_fingerprint) for item in opportunities
    )
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "duplicate opportunity in Phase 19 temporal stability evidence"
        )

    for item in opportunities:
        if (
            item.entry_at < common_window_start
            or item.exit_at > common_window_end
        ):
            raise CiboCapitalManagementError(
                "Phase 19 temporal stability opportunity outside common window"
            )

    training = tuple(
        item
        for item in opportunities
        if item.entry_at >= common_window_start and item.exit_at <= split_at
    )
    validation = tuple(
        item
        for item in opportunities
        if item.entry_at >= split_at and item.exit_at <= common_window_end
    )
    crossing = sum(
        item.entry_at < split_at < item.exit_at for item in opportunities
    )

    training_counts = _cross_trader_pair_counts(training)
    validation_counts = _cross_trader_pair_counts(validation)
    training_total = sum(training_counts.values())
    validation_total = sum(validation_counts.values())

    pair_stability: list[Phase19TemporalPairStability] = []
    for left, right in _complete_pair_keys():
        training_count = training_counts[(left, right)]
        validation_count = validation_counts[(left, right)]
        training_share = (
            Decimal(training_count) / Decimal(training_total)
            if training_total
            else Decimal(0)
        )
        validation_share = (
            Decimal(validation_count) / Decimal(validation_total)
            if validation_total
            else Decimal(0)
        )
        pair_stability.append(
            Phase19TemporalPairStability(
                left_trader=left,
                right_trader=right,
                training_overlap_pairs=training_count,
                validation_overlap_pairs=validation_count,
                training_share=training_share,
                validation_share=validation_share,
            )
        )

    training_population = tuple(
        trader
        for trader in PHASE19_REQUIRED_TRADERS
        if any(item.trader_id is trader for item in training)
    )
    validation_population = tuple(
        trader
        for trader in PHASE19_REQUIRED_TRADERS
        if any(item.trader_id is trader for item in validation)
    )

    if training_total == 0 or validation_total == 0:
        tv_distance = None
        weighted_jaccard = None
        status = Phase19TemporalStabilityStatus.INSUFFICIENT_INTERACTIONS
    else:
        absolute_difference = sum(
            abs(item.training_share - item.validation_share)
            for item in pair_stability
        )
        tv_distance = absolute_difference / Decimal(2)
        min_sum = sum(
            min(item.training_share, item.validation_share)
            for item in pair_stability
        )
        max_sum = sum(
            max(item.training_share, item.validation_share)
            for item in pair_stability
        )
        weighted_jaccard = min_sum / max_sum if max_sum else Decimal(1)
        if (
            set(training_population) == set(PHASE19_REQUIRED_TRADERS)
            and set(validation_population) == set(PHASE19_REQUIRED_TRADERS)
        ):
            status = Phase19TemporalStabilityStatus.MEASURED_OBSERVATIONAL_ONLY
        else:
            status = (
                Phase19TemporalStabilityStatus.INSUFFICIENT_SEGMENT_COVERAGE
            )

    return Phase19TemporalStabilityEvidence(
        common_window_start=common_window_start,
        split_at=split_at,
        common_window_end=common_window_end,
        training_opportunities=len(training),
        validation_opportunities=len(validation),
        boundary_crossing_opportunities_excluded=crossing,
        training_cross_trader_overlap_pairs=training_total,
        validation_cross_trader_overlap_pairs=validation_total,
        training_population=training_population,
        validation_population=validation_population,
        pair_stability=tuple(pair_stability),
        total_variation_distance=tv_distance,
        weighted_jaccard_similarity=weighted_jaccard,
        status=status,
    )
