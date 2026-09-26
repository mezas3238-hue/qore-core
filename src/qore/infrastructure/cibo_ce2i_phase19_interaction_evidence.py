"""Phase-19 empirical interaction evidence for the CE2I Opportunity Graph.

This module converts sealed chronology-only portfolio evidence into observational
TEMPORAL_OVERLAP edges for current causal candidates. It does not alter expected
value, sizing, capital budgets, QORE Risk decisions, or execution authority.

The edge weight is the pair's share of all observed cross-Trader overlap pairs
inside one explicitly bounded common evidence window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_opportunity_graph import (
    OpportunityInteractionEvidence,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)


@dataclass(frozen=True, slots=True)
class Phase19TraderPairOverlap:
    left_trader: TraderLineage
    right_trader: TraderLineage
    overlapping_pairs: int

    def __post_init__(self) -> None:
        for trader in (self.left_trader, self.right_trader):
            if type(trader) is not TraderLineage:
                raise CiboCapitalManagementError(
                    "Phase 19 pair trader must be TraderLineage"
                )
            if trader not in PHASE19_REQUIRED_TRADERS:
                raise CiboCapitalManagementError(
                    "Phase 19 pair trader is outside supported CMA portfolio"
                )
        if self.left_trader is self.right_trader:
            raise CiboCapitalManagementError(
                "Phase 19 interaction pair requires distinct Traders"
            )
        if (
            type(self.overlapping_pairs) is not int
            or self.overlapping_pairs < 0
        ):
            raise CiboCapitalManagementError(
                "Phase 19 overlapping_pairs must be non-negative int"
            )

    @property
    def unordered_key(self) -> tuple[TraderLineage, TraderLineage]:
        left, right = sorted(
            (self.left_trader, self.right_trader),
            key=lambda trader: trader.value,
        )
        return left, right


@dataclass(frozen=True, slots=True)
class Phase19TemporalOverlapAtlas:
    source_evidence_id: str
    common_window_start: datetime
    common_window_end: datetime
    total_cross_trader_overlap_pairs: int
    pair_overlaps: tuple[Phase19TraderPairOverlap, ...]

    def __post_init__(self) -> None:
        if not self.source_evidence_id:
            raise CiboCapitalManagementError(
                "Phase 19 atlas source_evidence_id is required"
            )
        for name in ("common_window_start", "common_window_end"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"Phase 19 atlas {name} must be timezone-aware"
                )
        if self.common_window_end <= self.common_window_start:
            raise CiboCapitalManagementError(
                "Phase 19 atlas common window is invalid"
            )
        if (
            type(self.total_cross_trader_overlap_pairs) is not int
            or self.total_cross_trader_overlap_pairs <= 0
        ):
            raise CiboCapitalManagementError(
                "Phase 19 total cross-Trader overlaps must be positive int"
            )

        keys = tuple(item.unordered_key for item in self.pair_overlaps)
        if len(keys) != len(set(keys)):
            raise CiboCapitalManagementError(
                "duplicate Phase 19 Trader interaction pair"
            )

        expected_keys = {
            (left, right)
            for index, left in enumerate(PHASE19_REQUIRED_TRADERS)
            for right in PHASE19_REQUIRED_TRADERS[index + 1 :]
        }
        normalized_expected = {
            tuple(sorted(pair, key=lambda trader: trader.value))
            for pair in expected_keys
        }
        if set(keys) != normalized_expected:
            raise CiboCapitalManagementError(
                "Phase 19 temporal atlas requires complete seven-Trader pair matrix"
            )

        observed_total = sum(
            item.overlapping_pairs for item in self.pair_overlaps
        )
        if observed_total != self.total_cross_trader_overlap_pairs:
            raise CiboCapitalManagementError(
                "Phase 19 temporal atlas overlap total drift"
            )

    def overlap_count(
        self,
        left: TraderLineage,
        right: TraderLineage,
    ) -> int:
        if left is right:
            return 0
        left_key, right_key = sorted(
            (left, right),
            key=lambda trader: trader.value,
        )
        for item in self.pair_overlaps:
            if item.unordered_key == (left_key, right_key):
                return item.overlapping_pairs
        raise CiboCapitalManagementError(
            "Phase 19 temporal atlas missing Trader pair"
        )

    def overlap_share(
        self,
        left: TraderLineage,
        right: TraderLineage,
    ) -> Decimal:
        count = self.overlap_count(left, right)
        return Decimal(count) / Decimal(self.total_cross_trader_overlap_pairs)


def project_phase19_temporal_overlap_evidence(
    *,
    candidates: tuple[CapitalOpportunityCandidate, ...],
    atlas: Phase19TemporalOverlapAtlas,
    decision_as_of: datetime,
) -> tuple[OpportunityInteractionEvidence, ...]:
    """Project past cross-Trader overlap burden onto current candidate pairs.

    This is observational evidence only. A zero historical share creates no
    edge, and no score/risk/margin field on the candidate is changed. The
    historical evidence window must close strictly before the current decision.
    """

    if not isinstance(atlas, Phase19TemporalOverlapAtlas):
        raise CiboCapitalManagementError(
            "Phase 19 temporal atlas must be Phase19TemporalOverlapAtlas"
        )
    if decision_as_of.tzinfo is None or decision_as_of.utcoffset() is None:
        raise CiboCapitalManagementError(
            "Phase 19 temporal projection decision_as_of must be timezone-aware"
        )
    if atlas.common_window_end >= decision_as_of:
        raise CiboCapitalManagementError(
            "Phase 19 temporal atlas must predate current decision"
        )

    fingerprints = tuple(item.signal_fingerprint for item in candidates)
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "duplicate candidate fingerprint in Phase 19 temporal projection"
        )
    for candidate in candidates:
        if candidate.trader_id not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "Phase 19 temporal projection candidate outside CMA portfolio"
            )

    projected: list[OpportunityInteractionEvidence] = []
    ordered = sorted(candidates, key=lambda item: item.signal_fingerprint)
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if left.trader_id is right.trader_id:
                continue
            share = atlas.overlap_share(left.trader_id, right.trader_id)
            if share <= 0:
                continue
            projected.append(
                OpportunityInteractionEvidence(
                    left_signal_fingerprint=left.signal_fingerprint,
                    right_signal_fingerprint=right.signal_fingerprint,
                    temporal_overlap=share,
                )
            )

    return tuple(projected)
