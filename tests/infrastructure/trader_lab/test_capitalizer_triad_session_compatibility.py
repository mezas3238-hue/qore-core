from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
)
from qore.infrastructure.trader_lab.capitalizer_triad_session_compatibility import (
    _observations,
    _selected_by_session,
)


def _candidate(
    symbol: str,
    side: CapitalizerSide,
    *,
    at: datetime,
    minutes: int,
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


def test_complete_triad_tracks_order_sides_and_overlap() -> None:
    base = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
    first = _candidate(
        "NAS100",
        CapitalizerSide.LONG,
        at=base,
        minutes=60,
    )
    second = _candidate(
        "USDCAD",
        CapitalizerSide.SHORT,
        at=base + timedelta(minutes=5),
        minutes=45,
    )
    third = _candidate(
        "XAUUSD",
        CapitalizerSide.SHORT,
        at=base + timedelta(minutes=10),
        minutes=20,
        realized="-1",
    )

    selected = _selected_by_session(
        (first, second, third),
        tie_policy="SYMBOL_ASC",
    )
    observations = _observations(selected)

    assert len(observations) == 1
    observation = observations[0]
    assert observation.session == "NEW_YORK"
    assert observation.first.symbol == "NAS100"
    assert observation.first.side is CapitalizerSide.LONG
    assert observation.second.symbol == "USDCAD"
    assert observation.second.side is CapitalizerSide.SHORT
    assert observation.third.symbol == "XAUUSD"
    assert observation.third.side is CapitalizerSide.SHORT
    assert observation.first_active_at_third_entry is True
    assert observation.second_active_at_third_entry is True
    assert observation.second_relation == "NO_SHARED_FACTOR"
    assert observation.third_relation in {
        "SHARED_FACTOR_SAME_DIRECTION",
        "SHARED_FACTOR_OPPOSING_DIRECTION",
        "SHARED_FACTOR_MIXED",
    }


def test_only_complete_three_trade_sessions_are_profiled() -> None:
    base = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
    first = _candidate(
        "EURUSD",
        CapitalizerSide.LONG,
        at=base,
        minutes=20,
    )
    second = _candidate(
        "GBPUSD",
        CapitalizerSide.LONG,
        at=base + timedelta(minutes=5),
        minutes=20,
    )

    selected = _selected_by_session(
        (first, second),
        tie_policy="SYMBOL_ASC",
    )
    assert _observations(selected) == ()


def test_duplicate_symbol_does_not_form_cross_market_triad() -> None:
    base = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    rows = (
        _candidate(
            "USDJPY",
            CapitalizerSide.LONG,
            at=base,
            minutes=20,
        ),
        _candidate(
            "USDJPY",
            CapitalizerSide.SHORT,
            at=base + timedelta(minutes=5),
            minutes=20,
        ),
        _candidate(
            "AUDJPY",
            CapitalizerSide.LONG,
            at=base + timedelta(minutes=10),
            minutes=20,
        ),
    )

    selected = _selected_by_session(rows, tie_policy="SYMBOL_ASC")
    assert _observations(selected) == ()
