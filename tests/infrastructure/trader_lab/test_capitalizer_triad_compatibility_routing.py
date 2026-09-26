from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
)
from qore.infrastructure.trader_lab.capitalizer_triad_compatibility_routing import (
    _asia_jpy_split_reason,
    _select,
)


def _candidate(
    symbol: str,
    side: CapitalizerSide,
    *,
    at: datetime,
) -> CapitalizerExposureCandidate:
    return CapitalizerExposureCandidate(
        symbol=symbol,
        side=side,
        signal_at=at,
        entry_at=at,
        exit_at=at + timedelta(minutes=15),
        event_labels=("HIGH_ACCEPTANCE",),
        planned_reward_r=Decimal("2"),
        state_family="NO_RECLAIM_FRESH",
        cisd_timing_state="ALL_WITHIN_H1",
        source_age_state="CURRENT_H1_SOURCE",
        boundary_type_state="PRIOR_HIGH_LOW_ONLY",
        reclaim_phase="NO_RECLAIM_OBSERVED",
        realized_r=Decimal("1"),
    )


def test_asia_jpy_split_detects_both_mirror_orientations() -> None:
    base = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)

    for common, opposite in (
        (CapitalizerSide.LONG, CapitalizerSide.SHORT),
        (CapitalizerSide.SHORT, CapitalizerSide.LONG),
    ):
        audjpy = _candidate("AUDJPY", common, at=base)
        usdjpy = _candidate(
            "USDJPY",
            common,
            at=base + timedelta(minutes=5),
        )
        gbpjpy = _candidate(
            "GBPJPY",
            opposite,
            at=base + timedelta(minutes=10),
        )
        assert _asia_jpy_split_reason(gbpjpy, (audjpy, usdjpy)) == (
            "ASIA_JPY_SPLIT_GBP_OPPOSES_AUDJPY_USDJPY"
        )


def test_asia_jpy_split_does_not_block_aligned_jpy_triad() -> None:
    base = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    rows = (
        _candidate("AUDJPY", CapitalizerSide.LONG, at=base),
        _candidate(
            "USDJPY",
            CapitalizerSide.LONG,
            at=base + timedelta(minutes=5),
        ),
        _candidate(
            "GBPJPY",
            CapitalizerSide.LONG,
            at=base + timedelta(minutes=10),
        ),
    )

    assert _asia_jpy_split_reason(rows[2], rows[:2]) is None
    selected, rejected = _select(
        rows,
        policy="BLOCK_ASIA_JPY_SPLIT_GBP_OPPOSES_V1",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == rows
    assert rejected == ()


def test_asia_jpy_split_veto_applies_only_when_third_slot_completes_state() -> None:
    base = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    audjpy = _candidate("AUDJPY", CapitalizerSide.SHORT, at=base)
    usdjpy = _candidate(
        "USDJPY",
        CapitalizerSide.SHORT,
        at=base + timedelta(minutes=5),
    )
    gbpjpy = _candidate(
        "GBPJPY",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=10),
    )
    audusd = _candidate(
        "AUDUSD",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=15),
    )

    selected, rejected = _select(
        (audjpy, usdjpy, gbpjpy, audusd),
        policy="BLOCK_ASIA_JPY_SPLIT_GBP_OPPOSES_V1",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == (audjpy, usdjpy, audusd)
    assert len(rejected) == 1
    assert rejected[0][0] == gbpjpy
    assert rejected[0][1] == "ASIA_JPY_SPLIT_GBP_OPPOSES_AUDJPY_USDJPY"
    assert rejected[0][2] == 3


def test_combined_policy_preserves_london_new_york_pair_routing() -> None:
    base = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
    eurusd = _candidate("EURUSD", CapitalizerSide.SHORT, at=base)
    gbpusd = _candidate(
        "GBPUSD",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=5),
    )

    selected, rejected = _select(
        (eurusd, gbpusd),
        policy="BLOCK_LONDON_NY_PLUS_ASIA_JPY_SPLIT_V1",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == (eurusd,)
    assert len(rejected) == 1
    assert "EURUSD_SHORT+GBPUSD_LONG" in rejected[0][1]


def test_baseline_preserves_owner_max3_ceiling() -> None:
    base = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    rows = (
        _candidate("AUDJPY", CapitalizerSide.SHORT, at=base),
        _candidate(
            "USDJPY",
            CapitalizerSide.SHORT,
            at=base + timedelta(minutes=5),
        ),
        _candidate(
            "GBPJPY",
            CapitalizerSide.LONG,
            at=base + timedelta(minutes=10),
        ),
        _candidate(
            "AUDUSD",
            CapitalizerSide.LONG,
            at=base + timedelta(minutes=15),
        ),
    )

    selected, rejected = _select(
        rows,
        policy="MAX3_BASELINE",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == rows[:3]
    assert rejected == ()
