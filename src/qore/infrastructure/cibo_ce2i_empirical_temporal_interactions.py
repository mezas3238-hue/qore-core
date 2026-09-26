"""Historical temporal-competition priors for the CE2I opportunity graph.

The priors are descriptive evidence derived only from consumed historical
chronology. They may annotate CURRENT simultaneous opportunity pairs when the
historical evidence window is strictly before the current decision timestamp.

They do not create capital, size positions, authorize Risk, or select trades.
No PnL/outcome is accepted by this module.
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


@dataclass(frozen=True, slots=True)
class HistoricalTemporalCompetitionPrior:
    left_trader: TraderLineage
    right_trader: TraderLineage
    overlap_pairs: int
    total_cross_trader_overlap_pairs: int
    observed_window_start: datetime
    observed_window_end: datetime
    evidence_id: str

    def __post_init__(self) -> None:
        if type(self.left_trader) is not TraderLineage or type(
            self.right_trader
        ) is not TraderLineage:
            raise CiboCapitalManagementError(
                "temporal prior Traders must be TraderLineage"
            )
        if self.left_trader is self.right_trader:
            raise CiboCapitalManagementError(
                "temporal prior requires distinct Traders"
            )
        if self.left_trader.value >= self.right_trader.value:
            raise CiboCapitalManagementError(
                "temporal prior Trader pair must use canonical lexical order"
            )
        if type(self.overlap_pairs) is not int or self.overlap_pairs <= 0:
            raise CiboCapitalManagementError(
                "temporal prior overlap_pairs must be positive int"
            )
        if (
            type(self.total_cross_trader_overlap_pairs) is not int
            or self.total_cross_trader_overlap_pairs <= 0
            or self.overlap_pairs > self.total_cross_trader_overlap_pairs
        ):
            raise CiboCapitalManagementError(
                "temporal prior total overlap count is invalid"
            )
        for name in ("observed_window_start", "observed_window_end"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"temporal prior {name} must be timezone-aware"
                )
        if self.observed_window_end <= self.observed_window_start:
            raise CiboCapitalManagementError(
                "temporal prior evidence window must be positive"
            )
        if not self.evidence_id:
            raise CiboCapitalManagementError(
                "temporal prior evidence_id required"
            )

    @property
    def trader_pair(self) -> tuple[TraderLineage, TraderLineage]:
        return (self.left_trader, self.right_trader)

    @property
    def competition_share(self) -> Decimal:
        return Decimal(self.overlap_pairs) / Decimal(
            self.total_cross_trader_overlap_pairs
        )


def build_historical_temporal_interactions(
    *,
    candidates: tuple[CapitalOpportunityCandidate, ...],
    priors: tuple[HistoricalTemporalCompetitionPrior, ...],
    decision_as_of: datetime,
) -> tuple[OpportunityInteractionEvidence, ...]:
    """Map frozen historical Trader-pair priors onto current candidates.

    Only a pair's historical temporal-overlap share is transferred. Current
    opportunity identity/geometry remain untouched. Missing historical pairs
    produce no inferred edge.
    """

    if decision_as_of.tzinfo is None or decision_as_of.utcoffset() is None:
        raise CiboCapitalManagementError(
            "temporal interaction decision_as_of must be timezone-aware"
        )

    fingerprints = tuple(item.signal_fingerprint for item in candidates)
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "duplicate candidate fingerprint in temporal interaction mapping"
        )

    prior_by_pair: dict[
        tuple[TraderLineage, TraderLineage],
        HistoricalTemporalCompetitionPrior,
    ] = {}
    for prior in priors:
        if prior.trader_pair in prior_by_pair:
            raise CiboCapitalManagementError(
                "duplicate historical temporal prior Trader pair"
            )
        if prior.observed_window_end >= decision_as_of:
            raise CiboCapitalManagementError(
                "historical temporal prior must predate current decision"
            )
        prior_by_pair[prior.trader_pair] = prior

    interactions: list[OpportunityInteractionEvidence] = []
    ordered = sorted(candidates, key=lambda item: item.signal_fingerprint)
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if left.trader_id is right.trader_id:
                continue
            trader_pair = tuple(
                sorted(
                    (left.trader_id, right.trader_id),
                    key=lambda trader: trader.value,
                )
            )
            prior = prior_by_pair.get(trader_pair)  # type: ignore[arg-type]
            if prior is None:
                continue
            interactions.append(
                OpportunityInteractionEvidence(
                    left_signal_fingerprint=left.signal_fingerprint,
                    right_signal_fingerprint=right.signal_fingerprint,
                    temporal_overlap=prior.competition_share,
                )
            )

    return tuple(interactions)
