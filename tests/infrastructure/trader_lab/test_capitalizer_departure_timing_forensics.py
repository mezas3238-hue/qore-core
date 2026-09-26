from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_departure_timing_forensics import (
    H1_DURATION_MINUTES,
    _timing_state,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
)


def _trade() -> CapitalizerR0Trade:
    signal = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    return CapitalizerR0Trade(
        symbol="USDJPY",
        side=CapitalizerSide.LONG,
        signal_at=signal,
        entry_at=signal,
        exit_at=signal + timedelta(minutes=5),
        event_labels=("HIGH_ACCEPTANCE",),
        entry_price=Decimal("100"),
        stop_price=Decimal("99"),
        target_price=Decimal("102"),
        initial_risk_price=Decimal("1"),
        planned_reward_r=Decimal("2"),
        realized_gross_r=Decimal("1"),
        exit_reason="TARGET",
        bars_held=1,
        same_bar_stop_target_ambiguity=False,
    )


def test_h1_boundary_is_structural_duration_not_optimized_threshold() -> None:
    assert H1_DURATION_MINUTES == 60
    trade = _trade()
    episode_index = {
        (trade.signal_at.isoformat(), trade.side): ("a", "b")
    }
    timing = {
        "a": {"source": 25, "cisd": 35},
        "b": {"source": 55, "cisd": 60},
    }

    assert _timing_state(
        trade,
        dimension="source",
        episode_index=episode_index,
        timing=timing,
    ) == "ALL_WITHIN_H1"
    assert _timing_state(
        trade,
        dimension="cisd",
        episode_index=episode_index,
        timing=timing,
    ) == "ANY_CROSS_H1"


def test_any_episode_crossing_h1_marks_the_exact_departure_conflicted_in_time() -> None:
    trade = _trade()
    episode_index = {
        (trade.signal_at.isoformat(), trade.side): ("a", "b")
    }
    timing = {
        "a": {"source": 10, "cisd": 20},
        "b": {"source": 75, "cisd": 25},
    }

    assert _timing_state(
        trade,
        dimension="source",
        episode_index=episode_index,
        timing=timing,
    ) == "ANY_CROSS_H1"
