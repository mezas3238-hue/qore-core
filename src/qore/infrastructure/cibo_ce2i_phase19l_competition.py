"""Phase19L exact-decision-epoch competition identifiability contracts.

T09/T18 can only claim historical competition evidence when multiple eligible
opportunities were available at the same causal decision epoch. Shared entry
time or overlap with an already-open position is capacity occupancy, not
permission to use a future opportunity to reorder a past decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19NormalizedReplayTrade,
)
from qore.infrastructure.cibo_ce2i_phase19_temporal_concordance import (
    phase19k_eligible_traders,
    phase19k_priority_order,
)


@dataclass(frozen=True, slots=True)
class Phase19LCompetitionEpoch:
    decision_at: datetime
    candidates: tuple[Phase19NormalizedReplayTrade, ...]

    def __post_init__(self) -> None:
        if (
            self.decision_at.tzinfo is None
            or self.decision_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "Phase19L competition epoch must be timezone-aware"
            )
        if len(self.candidates) < 2:
            raise CiboCapitalManagementError(
                "Phase19L competition epoch requires at least two candidates"
            )
        if any(
            item.allocation.decision_at != self.decision_at
            for item in self.candidates
        ):
            raise CiboCapitalManagementError(
                "Phase19L candidates must share exact decision epoch"
            )
        eligible = set(phase19k_eligible_traders())
        if any(
            item.opportunity.trader_id not in eligible
            for item in self.candidates
        ):
            raise CiboCapitalManagementError(
                "Phase19L competition candidate is not Phase19K eligible"
            )


def exact_competition_epochs(
    trades: tuple[Phase19NormalizedReplayTrade, ...],
) -> tuple[Phase19LCompetitionEpoch, ...]:
    """Group only exact causal decision-time Phase19K-eligible opportunities."""

    eligible = set(phase19k_eligible_traders())
    grouped: dict[datetime, list[Phase19NormalizedReplayTrade]] = {}
    for item in trades:
        if item.opportunity.trader_id not in eligible:
            continue
        grouped.setdefault(item.allocation.decision_at, []).append(item)
    return tuple(
        Phase19LCompetitionEpoch(
            decision_at=decision_at,
            candidates=tuple(
                sorted(
                    items,
                    key=lambda item: (
                        item.opportunity.trader_id.value,
                        item.opportunity.signal_fingerprint,
                    ),
                )
            ),
        )
        for decision_at, items in sorted(grouped.items())
        if len(items) >= 2
    )


def select_train_priority_candidate(
    epoch: Phase19LCompetitionEpoch,
) -> Phase19NormalizedReplayTrade:
    """Select with the frozen TRAIN capital-velocity priority only."""

    if not isinstance(epoch, Phase19LCompetitionEpoch):
        raise CiboCapitalManagementError(
            "Phase19L epoch must be canonical"
        )
    priority = {
        trader_id: index
        for index, trader_id in enumerate(phase19k_priority_order())
    }
    return min(
        epoch.candidates,
        key=lambda item: (
            priority[item.opportunity.trader_id],
            item.opportunity.signal_fingerprint,
        ),
    )


def select_identity_reference_candidate(
    epoch: Phase19LCompetitionEpoch,
) -> Phase19NormalizedReplayTrade:
    """Deterministic no-edge reference; Trader identity is not a policy claim."""

    if not isinstance(epoch, Phase19LCompetitionEpoch):
        raise CiboCapitalManagementError(
            "Phase19L epoch must be canonical"
        )
    return min(
        epoch.candidates,
        key=lambda item: (
            item.opportunity.trader_id.value,
            item.opportunity.signal_fingerprint,
        ),
    )


def one_slot_delta_ncu(
    selected: tuple[Phase19NormalizedReplayTrade, ...],
    *,
    risk_budget_ncu: Decimal = Decimal("0.25"),
) -> Decimal:
    if (
        not isinstance(risk_budget_ncu, Decimal)
        or not risk_budget_ncu.is_finite()
        or risk_budget_ncu <= 0
    ):
        raise CiboCapitalManagementError(
            "Phase19L risk budget must be finite positive Decimal"
        )
    return sum(
        (
            risk_budget_ncu * item.normalized_outcome_r
            for item in selected
        ),
        Decimal(0),
    )
