from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_h1_source_age_forensics import (
    _episode_age_state,
    _source_age_state,
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


def test_episode_age_uses_natural_h1_buckets() -> None:
    decision = datetime(2026, 1, 5, 3, 15, tzinfo=UTC)
    assert _episode_age_state(
        decision_at=decision,
        created_at=datetime(2026, 1, 5, 3, 0, tzinfo=UTC),
    ) == "CURRENT_H1_SOURCE"
    assert _episode_age_state(
        decision_at=decision,
        created_at=datetime(2026, 1, 5, 2, 0, tzinfo=UTC),
    ) == "PRIOR_H1_SOURCE"
    assert _episode_age_state(
        decision_at=decision,
        created_at=datetime(2026, 1, 5, 1, 0, tzinfo=UTC),
    ) == "OLDER_H1_SOURCE"


def test_multiple_exact_episodes_can_express_source_age_conflict() -> None:
    trade = _trade()
    episode_index = {
        (trade.signal_at.isoformat(), trade.side): ("a", "b")
    }
    boundaries = {
        "a": ("101.25", datetime(2026, 1, 5, 3, 0, tzinfo=UTC)),
        "b": ("101.50", datetime(2026, 1, 5, 2, 0, tzinfo=UTC)),
    }

    assert _source_age_state(
        trade,
        episode_index=episode_index,
        boundaries=boundaries,
    ) == "MIXED_H1_SOURCE_AGE"
