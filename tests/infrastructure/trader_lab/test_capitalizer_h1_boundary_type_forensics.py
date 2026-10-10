from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_h1_boundary_type_forensics import (
    _boundary_type_state,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
)


def _trade() -> CapitalizerR0Trade:
    signal = datetime(2026, 1, 5, 3, 15, tzinfo=UTC)
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


def test_single_prior_episode_is_prior_only() -> None:
    trade = _trade()
    episode_index = {(trade.signal_at.isoformat(), trade.side): ("a",)}
    assert _boundary_type_state(
        trade,
        episode_index=episode_index,
        boundary_types={"a": "PRIOR_HIGH_LOW"},
    ) == "PRIOR_HIGH_LOW_ONLY"


def test_exact_episode_disagreement_is_mixed_boundary_type() -> None:
    trade = _trade()
    episode_index = {(trade.signal_at.isoformat(), trade.side): ("a", "b")}
    assert _boundary_type_state(
        trade,
        episode_index=episode_index,
        boundary_types={
            "a": "PRIOR_HIGH_LOW",
            "b": "SWING_HIGH_LOW",
        },
    ) == "MIXED_BOUNDARY_TYPE"
