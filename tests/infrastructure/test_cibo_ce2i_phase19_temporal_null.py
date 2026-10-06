from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ChronologicalOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase19_temporal_null import (
    measure_phase19_temporal_null,
)


def _opportunity(
    trader: TraderLineage,
    *,
    index: int,
    base: datetime,
) -> Phase19ChronologicalOpportunity:
    entry = base + timedelta(minutes=index)
    return Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=f"{trader.value}-{index}",
        qore_symbol="TEST",
        entry_at=entry,
        exit_at=entry + timedelta(minutes=30),
    )


def test_temporal_null_is_deterministic_and_observational_only() -> None:
    start = datetime(2022, 1, 3, tzinfo=UTC)
    end = datetime(2022, 2, 28, 23, 59, tzinfo=UTC)
    base = datetime(2022, 1, 3, 12, 0, tzinfo=UTC)
    opportunities = tuple(
        _opportunity(trader, index=index, base=base)
        for index, trader in enumerate(PHASE19_REQUIRED_TRADERS)
    )

    first = measure_phase19_temporal_null(
        opportunities=opportunities,
        common_window_start=start,
        common_window_end=end,
        permutations=100,
        random_seed=731,
    )
    second = measure_phase19_temporal_null(
        opportunities=opportunities,
        common_window_start=start,
        common_window_end=end,
        permutations=100,
        random_seed=731,
    )

    assert first == second
    assert first.observed_cross_trader_overlap_pairs == 21
    assert len(first.pair_evidence) == 21
    assert first.outcomes_used is False
    assert first.sizing_used is False
    assert first.provider_economics_used is False
    assert first.allocation_authority is False
    assert first.risk_authority is False
    assert first.execution_authority is False


def test_temporal_null_rejects_incomplete_population() -> None:
    start = datetime(2022, 1, 3, tzinfo=UTC)
    end = datetime(2022, 2, 28, 23, 59, tzinfo=UTC)
    base = datetime(2022, 1, 3, 12, 0, tzinfo=UTC)
    opportunities = tuple(
        _opportunity(trader, index=index, base=base)
        for index, trader in enumerate(PHASE19_REQUIRED_TRADERS[:-1])
    )

    with pytest.raises(CiboCapitalManagementError, match="seven-Trader"):
        measure_phase19_temporal_null(
            opportunities=opportunities,
            common_window_start=start,
            common_window_end=end,
            permutations=100,
            random_seed=1,
        )


def test_temporal_null_rejects_too_few_permutations() -> None:
    start = datetime(2022, 1, 3, tzinfo=UTC)
    end = datetime(2022, 2, 28, 23, 59, tzinfo=UTC)
    base = datetime(2022, 1, 3, 12, 0, tzinfo=UTC)
    opportunities = tuple(
        _opportunity(trader, index=index, base=base)
        for index, trader in enumerate(PHASE19_REQUIRED_TRADERS)
    )

    with pytest.raises(CiboCapitalManagementError, match="at least 100"):
        measure_phase19_temporal_null(
            opportunities=opportunities,
            common_window_start=start,
            common_window_end=end,
            permutations=99,
            random_seed=1,
        )


def test_temporal_null_rejects_opportunity_outside_window() -> None:
    start = datetime(2022, 1, 3, tzinfo=UTC)
    end = datetime(2022, 2, 28, 23, 59, tzinfo=UTC)
    base = datetime(2022, 1, 3, 12, 0, tzinfo=UTC)
    opportunities = [
        _opportunity(trader, index=index, base=base)
        for index, trader in enumerate(PHASE19_REQUIRED_TRADERS)
    ]
    outside_entry = end + timedelta(minutes=1)
    opportunities[-1] = Phase19ChronologicalOpportunity(
        trader_id=PHASE19_REQUIRED_TRADERS[-1],
        signal_fingerprint="outside",
        qore_symbol="TEST",
        entry_at=outside_entry,
        exit_at=outside_entry + timedelta(minutes=1),
    )

    with pytest.raises(CiboCapitalManagementError, match="outside common window"):
        measure_phase19_temporal_null(
            opportunities=tuple(opportunities),
            common_window_start=start,
            common_window_end=end,
            permutations=100,
            random_seed=1,
        )
