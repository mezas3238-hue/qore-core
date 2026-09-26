from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    ReplayEconomicsStatus,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ChronologicalOpportunity,
    Phase19ReadinessStatus,
    Phase19TraderEvidence,
    assess_phase19_readiness,
    build_phase19_integrated_timeline,
)


def _evidence(
    trader: TraderLineage,
    *,
    status: ReplayEconomicsStatus,
) -> Phase19TraderEvidence:
    return Phase19TraderEvidence(
        trader_id=trader,
        evidence_id=f"artifact:{trader.value}",
        row_count=100,
        economics_status=status,
    )


def _full_readiness(
    status: ReplayEconomicsStatus = ReplayEconomicsStatus.R_DENOMINATED_ONLY,
):
    return assess_phase19_readiness(
        tuple(_evidence(trader, status=status) for trader in PHASE19_REQUIRED_TRADERS)
    )


def _opportunity(
    trader: TraderLineage,
    *,
    minute: int,
    duration_minutes: int = 10,
) -> Phase19ChronologicalOpportunity:
    entry_at = datetime(2026, 9, 1, 13, minute, tzinfo=UTC)
    return Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=f"{trader.value}:{minute}",
        qore_symbol=trader.value,
        entry_at=entry_at,
        exit_at=entry_at + timedelta(minutes=duration_minutes),
    )


def test_phase19_five_of_seven_is_blocked_by_phase18_coverage() -> None:
    bound = PHASE19_REQUIRED_TRADERS[:5]
    result = assess_phase19_readiness(
        tuple(
            _evidence(
                trader,
                status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
            )
            for trader in bound
        )
    )

    assert result.status is Phase19ReadinessStatus.BLOCKED_PHASE18_COVERAGE
    assert result.phase18_population_complete is False
    assert result.chronology_replay_authorized is False
    assert result.usd_portfolio_replay_authorized is False
    assert result.cross_trader_r_aggregation_authorized is False
    assert result.missing_traders == PHASE19_REQUIRED_TRADERS[5:]


def test_phase19_seven_of_seven_r_only_allows_chronology_but_blocks_usd() -> None:
    result = _full_readiness()

    assert result.status is Phase19ReadinessStatus.BLOCKED_PROVIDER_ECONOMICS
    assert result.phase18_population_complete is True
    assert result.chronology_replay_authorized is True
    assert result.usd_portfolio_replay_authorized is False
    assert result.cross_trader_r_aggregation_authorized is False
    assert result.provider_economics_incomplete == PHASE19_REQUIRED_TRADERS


def test_phase19_requires_all_provider_economics_complete_for_usd() -> None:
    result = _full_readiness(ReplayEconomicsStatus.PROVIDER_ECONOMICS_COMPLETE)

    assert (
        result.status
        is Phase19ReadinessStatus.READY_FOR_USD_PORTFOLIO_REPLAY
    )
    assert result.phase18_population_complete is True
    assert result.chronology_replay_authorized is True
    assert result.usd_portfolio_replay_authorized is True
    assert result.provider_economics_incomplete == ()


def test_phase19_rejects_duplicate_or_unsupported_trader_evidence() -> None:
    first = _evidence(
        TraderLineage.R38_GBPJPY,
        status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
    )
    with pytest.raises(CiboCapitalManagementError, match="duplicate Trader"):
        assess_phase19_readiness((first, first))

    with pytest.raises(
        CiboCapitalManagementError,
        match="outside supported CMA portfolio",
    ):
        Phase19TraderEvidence(
            trader_id=TraderLineage.VT08_INDEX,
            evidence_id="artifact:vt08-index",
            row_count=1,
            economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
        )


def test_phase19_timeline_merges_seven_traders_without_usd_or_r_arithmetic() -> None:
    readiness = _full_readiness()
    opportunities = tuple(
        _opportunity(trader, minute=index, duration_minutes=10)
        for index, trader in enumerate(PHASE19_REQUIRED_TRADERS)
    )

    result = build_phase19_integrated_timeline(
        tuple(reversed(opportunities)),
        readiness=readiness,
    )

    assert result.trader_population == PHASE19_REQUIRED_TRADERS
    assert tuple(item.entry_at for item in result.opportunities) == tuple(
        sorted(item.entry_at for item in opportunities)
    )
    assert result.max_concurrent_positions == 7
    assert result.overlapping_position_pairs == 21
    assert result.usd_capital_arithmetic_performed is False
    assert result.cross_trader_r_aggregation_performed is False


def test_phase19_timeline_requires_complete_population() -> None:
    partial = assess_phase19_readiness(
        tuple(
            _evidence(
                trader,
                status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
            )
            for trader in PHASE19_REQUIRED_TRADERS[:5]
        )
    )
    opportunities = tuple(
        _opportunity(trader, minute=index)
        for index, trader in enumerate(PHASE19_REQUIRED_TRADERS[:5])
    )

    with pytest.raises(CiboCapitalManagementError, match="complete Phase-18"):
        build_phase19_integrated_timeline(opportunities, readiness=partial)


def test_phase19_timeline_rejects_missing_trader_or_duplicate_signal() -> None:
    readiness = _full_readiness()
    opportunities = tuple(
        _opportunity(trader, minute=index)
        for index, trader in enumerate(PHASE19_REQUIRED_TRADERS)
    )

    with pytest.raises(CiboCapitalManagementError, match="missing Trader population"):
        build_phase19_integrated_timeline(
            opportunities[:-1],
            readiness=readiness,
        )

    with pytest.raises(CiboCapitalManagementError, match="duplicate Phase 19"):
        build_phase19_integrated_timeline(
            (*opportunities, opportunities[0]),
            readiness=readiness,
        )


def test_phase19_opportunity_requires_causal_aware_interval() -> None:
    with pytest.raises(CiboCapitalManagementError, match="timezone-aware"):
        Phase19ChronologicalOpportunity(
            trader_id=TraderLineage.R38_EURUSD,
            signal_fingerprint="signal",
            qore_symbol="EURUSD",
            entry_at=datetime(2026, 9, 1, 13, 0),
            exit_at=datetime(2026, 9, 1, 13, 1),
        )

    at = datetime(2026, 9, 1, 13, 0, tzinfo=UTC)
    with pytest.raises(CiboCapitalManagementError, match="strictly after"):
        Phase19ChronologicalOpportunity(
            trader_id=TraderLineage.R38_EURUSD,
            signal_fingerprint="signal",
            qore_symbol="EURUSD",
            entry_at=at,
            exit_at=at,
        )
