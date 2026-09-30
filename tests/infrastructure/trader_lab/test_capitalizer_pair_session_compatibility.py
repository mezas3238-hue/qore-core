from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_pair_session_compatibility import (
    _pair_observations,
    _relation,
    _selected_by_session,
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
)


def _candidate(
    symbol: str,
    side: CapitalizerSide,
    *,
    at: datetime,
    minutes: int = 30,
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


def test_relation_detects_opposing_shared_jpy_factor() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    first = _candidate("USDJPY", CapitalizerSide.LONG, at=at)
    second = _candidate(
        "AUDJPY",
        CapitalizerSide.SHORT,
        at=at + timedelta(minutes=5),
    )
    assert _relation(first, second) == "SHARED_FACTOR_OPPOSING_DIRECTION"


def test_pair_observation_profiles_session_sides_order_and_overlap() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    first = _candidate("USDJPY", CapitalizerSide.LONG, at=at, minutes=40)
    second = _candidate(
        "AUDJPY",
        CapitalizerSide.SHORT,
        at=at + timedelta(minutes=5),
        minutes=20,
        realized="-1",
    )
    third = _candidate(
        "AUDUSD",
        CapitalizerSide.LONG,
        at=at + timedelta(minutes=10),
        minutes=10,
    )

    selected = _selected_by_session(
        (first, second, third),
        tie_policy="SYMBOL_ASC",
    )
    observations = _pair_observations(selected)

    assert len(observations) == 3
    target = next(
        item
        for item in observations
        if {item.symbol_a, item.symbol_b} == {"AUDJPY", "USDJPY"}
    )
    assert target.session == "ASIA"
    assert target.symbol_a == "AUDJPY"
    assert target.side_a is CapitalizerSide.SHORT
    assert target.symbol_b == "USDJPY"
    assert target.side_b is CapitalizerSide.LONG
    assert target.first.symbol == "USDJPY"
    assert target.second.symbol == "AUDJPY"
    assert target.first_ordinal == 1
    assert target.second_ordinal == 2
    assert target.active_overlap is True
    assert target.relation == "SHARED_FACTOR_OPPOSING_DIRECTION"


def test_max3_selection_remains_ceiling_not_quota() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    rows = (
        _candidate("USDJPY", CapitalizerSide.LONG, at=at),
        _candidate(
            "AUDJPY",
            CapitalizerSide.LONG,
            at=at + timedelta(minutes=1),
        ),
        _candidate(
            "AUDUSD",
            CapitalizerSide.SHORT,
            at=at + timedelta(minutes=2),
        ),
        _candidate(
            "GBPJPY",
            CapitalizerSide.SHORT,
            at=at + timedelta(minutes=3),
        ),
    )

    selected = _selected_by_session(rows, tie_policy="SYMBOL_ASC")
    assert sum(len(value) for value in selected.values()) == 3
