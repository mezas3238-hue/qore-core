"""Phase 19 integrated-portfolio replay readiness and chronology contracts.

Phase 19 may combine Traders in one chronological market timeline when every
required Phase-18 lineage is bound. USD capital arithmetic is a stronger claim:
it is authorized only when every lineage also carries comparable provider
economics.

R-denominated Trader results remain valid evidence, but heterogeneous R units
must never be summed into one portfolio capital pool.

Research-only. This module does not reserve capital, call QORE Risk, or mutate
broker state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


class ProviderEconomicsEvidenceClass(StrEnum):
    EXACT_HISTORICAL = "EXACT_HISTORICAL"
    PERIOD_STATIC_VERIFIED = "PERIOD_STATIC_VERIFIED"
    CURRENT_SNAPSHOT_ONLY = "CURRENT_SNAPSHOT_ONLY"
    MISSING = "MISSING"


@dataclass(frozen=True, slots=True)
class Phase19ProviderEconomicsEvidence:
    trader_id: TraderLineage
    provider_key: str
    evidence_id: str
    contract_terms: ProviderEconomicsEvidenceClass
    tick_value: ProviderEconomicsEvidenceClass
    spread: ProviderEconomicsEvidenceClass
    commission: ProviderEconomicsEvidenceClass
    slippage: ProviderEconomicsEvidenceClass
    margin: ProviderEconomicsEvidenceClass

    def __post_init__(self) -> None:
        if self.trader_id not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "Phase 19 provider evidence trader is outside supported CMA portfolio"
            )
        if not self.provider_key or not self.evidence_id:
            raise CiboCapitalManagementError(
                "Phase 19 provider evidence identity must be non-empty"
            )
        for name in (
            "contract_terms",
            "tick_value",
            "spread",
            "commission",
            "slippage",
            "margin",
        ):
            value = getattr(self, name)
            if type(value) is not ProviderEconomicsEvidenceClass:
                raise CiboCapitalManagementError(
                    f"Phase 19 provider evidence {name} classification is invalid"
                )

    @property
    def historical_usd_complete(self) -> bool:
        reusable = {
            ProviderEconomicsEvidenceClass.EXACT_HISTORICAL,
            ProviderEconomicsEvidenceClass.PERIOD_STATIC_VERIFIED,
        }
        return (
            self.contract_terms in reusable
            and self.tick_value in reusable
            and self.spread is ProviderEconomicsEvidenceClass.EXACT_HISTORICAL
            and self.commission in reusable
            and self.slippage in reusable
            and self.margin in reusable
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
    provider_economics: Phase19ProviderEconomicsEvidence | None = None

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
        if (
            self.provider_economics is not None
            and self.provider_economics.trader_id is not self.trader_id
        ):
            raise CiboCapitalManagementError(
                "Phase 19 provider economics Trader mismatch"
            )
        historical_complete = (
            self.provider_economics is not None
            and self.provider_economics.historical_usd_complete
        )
        status_complete = (
            self.economics_status
            is ReplayEconomicsStatus.PROVIDER_ECONOMICS_COMPLETE
        )
        if historical_complete != status_complete:
            raise CiboCapitalManagementError(
                "Phase 19 provider economics evidence/status mismatch"
            )


@dataclass(frozen=True, slots=True)
class Phase19Readiness:
    status: Phase19ReadinessStatus
    phase18_population_complete: bool
    chronology_replay_authorized: bool
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
        if self.chronology_replay_authorized != self.phase18_population_complete:
            raise CiboCapitalManagementError(
                "Phase 19 chronology authorization/population mismatch"
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


@dataclass(frozen=True, slots=True)
class Phase19ChronologicalOpportunity:
    trader_id: TraderLineage
    signal_fingerprint: str
    qore_symbol: str
    entry_at: datetime
    exit_at: datetime

    def __post_init__(self) -> None:
        if self.trader_id not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "Phase 19 opportunity trader is outside supported CMA portfolio"
            )
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "Phase 19 opportunity identity must be non-empty"
            )
        for name, value in (("entry_at", self.entry_at), ("exit_at", self.exit_at)):
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"Phase 19 {name} must be timezone-aware"
                )
        if self.exit_at <= self.entry_at:
            raise CiboCapitalManagementError(
                "Phase 19 opportunity exit must be strictly after entry"
            )


@dataclass(frozen=True, slots=True)
class Phase19IntegratedTimeline:
    opportunities: tuple[Phase19ChronologicalOpportunity, ...]
    trader_population: tuple[TraderLineage, ...]
    max_concurrent_positions: int
    overlapping_position_pairs: int
    usd_capital_arithmetic_performed: bool
    cross_trader_r_aggregation_performed: bool

    def __post_init__(self) -> None:
        if self.usd_capital_arithmetic_performed:
            raise CiboCapitalManagementError(
                "chronology-only Phase 19 timeline cannot perform USD arithmetic"
            )
        if self.cross_trader_r_aggregation_performed:
            raise CiboCapitalManagementError(
                "chronology-only Phase 19 timeline cannot aggregate Trader R"
            )


def assess_phase19_readiness(
    evidence: tuple[Phase19TraderEvidence, ...],
) -> Phase19Readiness:
    """Assess legal replay depth from independently bound Phase-18 evidence."""

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

    population_complete = not missing
    return Phase19Readiness(
        status=status,
        phase18_population_complete=population_complete,
        chronology_replay_authorized=population_complete,
        usd_portfolio_replay_authorized=(
            status is Phase19ReadinessStatus.READY_FOR_USD_PORTFOLIO_REPLAY
        ),
        cross_trader_r_aggregation_authorized=False,
        bound_traders=bound,
        missing_traders=missing,
        provider_economics_incomplete=incomplete,
    )


def build_phase19_integrated_timeline(
    opportunities: tuple[Phase19ChronologicalOpportunity, ...],
    *,
    readiness: Phase19Readiness,
) -> Phase19IntegratedTimeline:
    """Merge seven Trader paths without performing capital or R arithmetic."""

    if not isinstance(readiness, Phase19Readiness):
        raise CiboCapitalManagementError(
            "Phase 19 readiness must be Phase19Readiness"
        )
    if not readiness.chronology_replay_authorized:
        raise CiboCapitalManagementError(
            "Phase 19 chronology replay requires complete Phase-18 population"
        )
    if not opportunities:
        raise CiboCapitalManagementError(
            "Phase 19 integrated timeline requires opportunities"
        )

    keys = tuple(
        (item.trader_id, item.signal_fingerprint) for item in opportunities
    )
    if len(keys) != len(set(keys)):
        raise CiboCapitalManagementError(
            "duplicate Phase 19 Trader signal fingerprint"
        )

    population_set = {item.trader_id for item in opportunities}
    missing_population = tuple(
        trader for trader in PHASE19_REQUIRED_TRADERS if trader not in population_set
    )
    if missing_population:
        raise CiboCapitalManagementError(
            "Phase 19 integrated timeline is missing Trader population"
        )

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

    events: list[tuple[datetime, int]] = []
    for item in ordered:
        events.append((item.entry_at, 1))
        events.append((item.exit_at, -1))
    events.sort(key=lambda event: (event[0], event[1]))

    concurrent = 0
    max_concurrent = 0
    for _at, delta in events:
        concurrent += delta
        if concurrent < 0:
            raise CiboCapitalManagementError(
                "Phase 19 timeline concurrency accounting drift"
            )
        max_concurrent = max(max_concurrent, concurrent)
    if concurrent != 0:
        raise CiboCapitalManagementError(
            "Phase 19 timeline did not return to zero concurrency"
        )

    overlap_pairs = 0
    for left_index, left in enumerate(ordered):
        for right in ordered[left_index + 1 :]:
            if left.entry_at < right.exit_at and right.entry_at < left.exit_at:
                overlap_pairs += 1

    return Phase19IntegratedTimeline(
        opportunities=ordered,
        trader_population=PHASE19_REQUIRED_TRADERS,
        max_concurrent_positions=max_concurrent,
        overlapping_position_pairs=overlap_pairs,
        usd_capital_arithmetic_performed=False,
        cross_trader_r_aggregation_performed=False,
    )
