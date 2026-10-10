from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
)
from qore.infrastructure.trader_lab.capitalizer_session_compatibility_routing import (
    _select,
)


def _candidate(
    symbol: str,
    side: CapitalizerSide,
    *,
    at: datetime,
    minutes: int = 20,
    realized: str = "1",
) -> CapitalizerExposureCandidate:
    return CapitalizerExposureCandidate(
        symbol=symbol,
        side=side,
        signal_at=at,
        entry_at=at,
        exit_at=at + timedelta(minutes=minutes),
        event_labels=("HIGH_ACCEPTANCE",),
        planned_reward_r=Decimal("2"),
        state_family="NO_RECLAIM_FRESH",
        cisd_timing_state="ALL_WITHIN_H1",
        source_age_state="CURRENT_H1_SOURCE",
        boundary_type_state="PRIOR_HIGH_LOW_ONLY",
        reclaim_phase="NO_RECLAIM_OBSERVED",
        realized_r=Decimal(realized),
    )


def test_core_router_blocks_asia_weak_side_pair_regardless_of_order() -> None:
    base = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    audjpy = _candidate("AUDJPY", CapitalizerSide.SHORT, at=base)
    usdjpy = _candidate(
        "USDJPY",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=5),
    )

    selected, rejected = _select(
        (audjpy, usdjpy),
        policy="BLOCK_CORE_WEAK_SIDE_PAIRS_V1",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == (audjpy,)
    assert len(rejected) == 1
    assert rejected[0][0] == usdjpy
    assert "AUDJPY_SHORT+USDJPY_LONG" in rejected[0][1]

    selected_reverse, rejected_reverse = _select(
        (usdjpy, audjpy),
        policy="BLOCK_CORE_WEAK_SIDE_PAIRS_V1",
        tie_policy="SYMBOL_ASC",
    )
    assert len(selected_reverse) == 1
    assert len(rejected_reverse) == 1


def test_router_preserves_strong_london_same_side_pair() -> None:
    base = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
    eurusd = _candidate("EURUSD", CapitalizerSide.LONG, at=base)
    gbpusd = _candidate(
        "GBPUSD",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=5),
    )

    selected, rejected = _select(
        (eurusd, gbpusd),
        policy="BLOCK_CORE_WEAK_SIDE_PAIRS_V1",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == (eurusd, gbpusd)
    assert rejected == ()


def test_core_plus_xau_rule_blocks_ny_ordinal2_same_direction_shared_factor() -> None:
    base = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
    usdcad = _candidate(
        "USDCAD",
        CapitalizerSide.SHORT,
        at=base,
        minutes=40,
    )
    xauusd = _candidate(
        "XAUUSD",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=5),
        minutes=20,
    )
    nas100 = _candidate(
        "NAS100",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=10),
    )

    selected, rejected = _select(
        (usdcad, xauusd, nas100),
        policy="BLOCK_CORE_WEAK_SIDE_PAIRS_PLUS_XAUUSD_ORD2_SHARED_V1",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == (usdcad, nas100)
    assert len(rejected) == 1
    assert rejected[0][0] == xauusd
    assert rejected[0][1] == "XAUUSD_NY_ORD2_SAME_DIRECTION_SHARED_FACTOR"
    assert rejected[0][2] == 2


def test_baseline_keeps_owner_max3_ceiling() -> None:
    base = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
    rows = (
        _candidate("NAS100", CapitalizerSide.LONG, at=base),
        _candidate(
            "USDCAD",
            CapitalizerSide.LONG,
            at=base + timedelta(minutes=1),
        ),
        _candidate(
            "XAUUSD",
            CapitalizerSide.SHORT,
            at=base + timedelta(minutes=2),
        ),
        _candidate(
            "NAS100",
            CapitalizerSide.SHORT,
            at=base + timedelta(minutes=3),
        ),
    )

    selected, rejected = _select(
        rows,
        policy="MAX3_BASELINE",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == rows[:3]
    assert rejected == ()


def test_session_ablation_policy_does_not_block_other_session_weak_pair() -> None:
    base = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
    eurusd = _candidate("EURUSD", CapitalizerSide.SHORT, at=base)
    gbpusd = _candidate(
        "GBPUSD",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=5),
    )

    selected, rejected = _select(
        (eurusd, gbpusd),
        policy="BLOCK_ASIA_WEAK_SIDE_PAIR_ONLY_V1",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == (eurusd, gbpusd)
    assert rejected == ()

    selected_london, rejected_london = _select(
        (eurusd, gbpusd),
        policy="BLOCK_LONDON_WEAK_SIDE_PAIR_ONLY_V1",
        tie_policy="SYMBOL_ASC",
    )
    assert selected_london == (eurusd,)
    assert len(rejected_london) == 1
    assert "EURUSD_SHORT+GBPUSD_LONG" in rejected_london[0][1]
