from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_portfolio_competition_forensics import (
    _select,
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
)


def _candidate(
    symbol: str,
    side: CapitalizerSide,
    *,
    at: datetime,
    exit_after_min: int,
    realized: str = "1",
) -> CapitalizerExposureCandidate:
    return CapitalizerExposureCandidate(
        symbol=symbol,
        side=side,
        signal_at=at,
        entry_at=at,
        exit_at=at + timedelta(minutes=exit_after_min),
        event_labels=("HIGH_ACCEPTANCE",),
        planned_reward_r=Decimal("2"),
        state_family="NO_RECLAIM_FRESH",
        cisd_timing_state="ALL_WITHIN_H1",
        source_age_state="CURRENT_H1_SOURCE",
        boundary_type_state="PRIOR_HIGH_LOW_ONLY",
        reclaim_phase="NO_RECLAIM_OBSERVED",
        realized_r=Decimal(realized),
    )


def test_xauusd_new_york_second_shared_factor_ablation_is_categorical() -> None:
    base = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
    first = _candidate(
        "USDCAD",
        CapitalizerSide.LONG,
        at=base,
        exit_after_min=60,
    )
    xau = _candidate(
        "XAUUSD",
        CapitalizerSide.SHORT,
        at=base + timedelta(minutes=10),
        exit_after_min=30,
        realized="-1",
    )
    later = _candidate(
        "NAS100",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=20),
        exit_after_min=20,
    )

    selected, rejected = _select(
        (first, xau, later),
        policy="BLOCK_XAUUSD_NY_ORD2_ANY_SHARED_FACTOR",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == (first, later)
    assert len(rejected) == 1
    assert rejected[0][0] == xau
    assert rejected[0][1] == "XAUUSD_NY_ORD2_ANY_SHARED_FACTOR"
    assert rejected[0][2] == 2


def test_gbpjpy_asia_third_ablation_allows_later_candidate_to_compete() -> None:
    base = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    first = _candidate(
        "USDJPY",
        CapitalizerSide.LONG,
        at=base,
        exit_after_min=5,
    )
    second = _candidate(
        "AUDUSD",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=10),
        exit_after_min=5,
    )
    blocked = _candidate(
        "GBPJPY",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=20),
        exit_after_min=5,
        realized="-1",
    )
    replacement = _candidate(
        "AUDJPY",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=30),
        exit_after_min=5,
    )

    selected, rejected = _select(
        (first, second, blocked, replacement),
        policy="BLOCK_GBPJPY_ASIA_ORD3",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == (first, second, replacement)
    assert len(rejected) == 1
    assert rejected[0][0] == blocked
    assert rejected[0][1] == "GBPJPY_ASIA_ORD3"
    assert rejected[0][2] == 3


def test_baseline_preserves_owner_max3_contract() -> None:
    base = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    candidates = tuple(
        _candidate(
            symbol,
            CapitalizerSide.LONG,
            at=base + timedelta(minutes=index * 10),
            exit_after_min=5,
        )
        for index, symbol in enumerate(
            ("USDJPY", "AUDUSD", "GBPJPY", "AUDJPY")
        )
    )

    selected, rejected = _select(
        candidates,
        policy="MAX3_BASELINE",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == candidates[:3]
    assert rejected == ()
