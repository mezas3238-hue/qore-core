"""Phase 19 integrated-portfolio replay readiness contract.

Phase 19 may combine Traders only when every required Phase-18 lineage is bound
and its provider economics are comparable in USD.  R-denominated Trader results
remain valid evidence, but their heterogeneous R units must never be summed into
one portfolio capital pool.

Research-only.  This module does not reserve capital, call QORE Risk, or mutate
broker state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import CiboCapitalManagementError
from qore.infrastructure.cibo_ce2i_chronological_replay import ReplayEconomicsStatus


PHASE19_REQUIRED_TRADERS = (
    TraderLineage.VT08_FOREX,
    TraderLineage.R34_XAUUSD,
    TraderLineage.R38_EURUSD,
    TraderLineage.R43_GBPUSD,
    TraderLineage.R38_GBPJPY,
    TraderLineage.R42_AUDJPY,
    TraderLineage.VT31_NAS100,
)


class Phase19ReadinessStatus(StrEnum):
    BLOCKED_PHASE18_COVERAGE = "BLOCKED_PHASE18_COVERAGE"
    BLOCKED_PROVIDER_ECONOMICS = "BLOCKED_PROVIDER_ECONOMICS"
    READY_FOR_USD_PORTFOLIO_REPLAY = "READY_FOR_USD_PORTFOLIO_REPLAY"


@dataclass(frozen=True, slots=True)
class Phase19TraderEvidence:
    trader_id: TraderLineage
    evidence_id: str
    row_count: int
    economics_status: ReplayEconomicsStatus

    def __post_init__(self) -> None:
        if self.trader_id not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "Phase 19 evidence trader is outside supported CMA portfolio"
            )
        if not self.evidence_id:
            raise CiboCapitalManagementError(
                "Phase 19 evidence_id must be non-empty"
            )
        if type(self.row_count) is not int or self.row_count <= 0:
            raise CiboCapitalManagementError(
                "Phase 19 evidence row_count must be positive int"
            )
        if type(self.economics_status) is not ReplayEconomicsStatus:
            raise CiboCapitalManagementError(
                "Phase 19 economics_status must be ReplayEconomicsStatus"
            )


@dataclass(frozen=True, slots=True)
class Phase19Readiness:
    status: Phase19ReadinessStatus
    phase18_population_complete: bool
    usd_portfolio_replay_authorized: bool
    cross_trader_r_aggregation_authorized: bool
    bound_traders: tuple[TraderLineage, ...]
    missing_traders: tuple[TraderLineage, ...]
    provider_economics_incomplete: tuple[TraderLineage, ...]

    def __post_init__(self) -> None:
        if self.cross_trader_r_aggregation_authorized:
            raise CiboCapitalManagementError(
                "heterogeneous cross-Trader R aggregation is forbidden"
            )
        if self.usd_portfolio_replay_authorized != (
            self.status
            is Phase19ReadinessStatus.READY_FOR_USD_PORTFOLIO_REPLAY
        ):
            raise CiboCapitalManagementError(
                "Phase 19 USD authorization/status mismatch"
            )
        if self.phase18_population_complete != (not self.missing_traders):
            raise CiboCapitalManagementError(
                "Phase 19 population completeness mismatch"
            )


def assess_phase19_readiness(
    evidence: tuple[Phase19TraderEvidence, ...],
) -> Phase19Readiness:
    """Assess whether integrated USD portfolio replay is scientifically legal."""

    trader_ids = tuple(item.trader_id for item in evidence)
    if len(trader_ids) != len(set(trader_ids)):
        raise CiboCapitalManagementError(
            "duplicate Trader evidence in Phase 19 readiness"
        )

    evidence_by_trader = {item.trader_id: item for item in evidence}
    bound = tuple(
        trader for trader in PHASE19_REQUIRED_TRADERS if trader in evidence_by_trader
    )
    missing = tuple(
        trader
        for trader in PHASE19_REQUIRED_TRADERS
        if trader not in evidence_by_trader
    )
    incomplete = tuple(
        trader
        for trader in PHASE19_REQUIRED_TRADERS
        if trader in evidence_by_trader
        and evidence_by_trader[trader].economics_status
        is not ReplayEconomicsStatus.PROVIDER_ECONOMICS_COMPLETE
    )

    if missing:
        status = Phase19ReadinessStatus.BLOCKED_PHASE18_COVERAGE
    elif incomplete:
        status = Phase19ReadinessStatus.BLOCKED_PROVIDER_ECONOMICS
    else:
        status = Phase19ReadinessStatus.READY_FOR_USD_PORTFOLIO_REPLAY

    return Phase19Readiness(
        status=status,
        phase18_population_complete=not missing,
        usd_portfolio_replay_authorized=(
            status is Phase19ReadinessStatus.READY_FOR_USD_PORTFOLIO_REPLAY
        ),
        cross_trader_r_aggregation_authorized=False,
        bound_traders=bound,
        missing_traders=missing,
        provider_economics_incomplete=incomplete,
    )
