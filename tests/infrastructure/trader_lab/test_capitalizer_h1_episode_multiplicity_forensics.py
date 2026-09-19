from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_h1_episode_multiplicity_forensics import (
    _multiplicity_tags,
)
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


def test_single_episode_is_single_source_boundary() -> None:
    trade = _trade()
    episode_index = {
        (trade.signal_at.isoformat(), trade.side): ("a",)
    }
    boundaries = {
        "a": ("101.250", datetime(2026, 1, 5, 0, 0, tzinfo=UTC))
    }

    assert _multiplicity_tags(
        trade,
        episode_index=episode_index,
        boundaries=boundaries,
    ) == ("SINGLE_EPISODE", "SINGLE_SOURCE_BOUNDARY")


def test_multi_episode_distinguishes_distinct_source_boundaries() -> None:
    trade = _trade()
    episode_index = {
        (trade.signal_at.isoformat(), trade.side): ("a", "b")
    }
    boundaries = {
        "a": ("101.250", datetime(2026, 1, 5, 0, 0, tzinfo=UTC)),
        "b": ("101.500", datetime(2026, 1, 4, 23, 0, tzinfo=UTC)),
    }

    assert _multiplicity_tags(
        trade,
        episode_index=episode_index,
        boundaries=boundaries,
    ) == ("MULTI_EPISODE", "MULTI_SOURCE_BOUNDARY")
