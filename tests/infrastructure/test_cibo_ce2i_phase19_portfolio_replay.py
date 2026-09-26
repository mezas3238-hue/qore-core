from __future__ import annotations

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
    Phase19ReadinessStatus,
    Phase19TraderEvidence,
    assess_phase19_readiness,
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
    assert result.usd_portfolio_replay_authorized is False
    assert result.cross_trader_r_aggregation_authorized is False
    assert result.missing_traders == PHASE19_REQUIRED_TRADERS[5:]


def test_phase19_seven_of_seven_r_only_blocks_usd_portfolio_replay() -> None:
    result = assess_phase19_readiness(
        tuple(
            _evidence(
                trader,
                status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
            )
            for trader in PHASE19_REQUIRED_TRADERS
        )
    )

    assert result.status is Phase19ReadinessStatus.BLOCKED_PROVIDER_ECONOMICS
    assert result.phase18_population_complete is True
    assert result.usd_portfolio_replay_authorized is False
    assert result.cross_trader_r_aggregation_authorized is False
    assert result.provider_economics_incomplete == PHASE19_REQUIRED_TRADERS


def test_phase19_requires_all_provider_economics_complete() -> None:
    result = assess_phase19_readiness(
        tuple(
            _evidence(
                trader,
                status=ReplayEconomicsStatus.PROVIDER_ECONOMICS_COMPLETE,
            )
            for trader in PHASE19_REQUIRED_TRADERS
        )
    )

    assert (
        result.status
        is Phase19ReadinessStatus.READY_FOR_USD_PORTFOLIO_REPLAY
    )
    assert result.phase18_population_complete is True
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
