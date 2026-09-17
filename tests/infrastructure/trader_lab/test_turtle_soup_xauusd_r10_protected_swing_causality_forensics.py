from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Side,
    SourceCandle,
)
from qore.infrastructure.trader_lab.turtle_soup_xauusd_r10_protected_swing_causality_forensics import (
    _candle_geometry,
    _externality,
    _outcome_class,
    _post_ps_min_distance,
)


def _candle(
    minute: int,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> SourceCandle:
    opened = datetime(2026, 1, 1, 0, minute, tzinfo=UTC)
    return SourceCandle(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=5),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        m5=(),
    )


def test_long_protected_swing_geometry_is_directional() -> None:
    candle = _candle(0, "100", "104", "96", "102")
    body, rejection, close_away = _candle_geometry(candle, Side.LONG)
    assert body == Decimal("0.25")
    assert rejection == Decimal("0.5")
    assert close_away == Decimal("0.75")


def test_short_protected_swing_geometry_is_directional() -> None:
    candle = _candle(0, "100", "106", "98", "99")
    body, rejection, close_away = _candle_geometry(candle, Side.SHORT)
    assert body == Decimal("0.125")
    assert rejection == Decimal("0.75")
    assert close_away == Decimal("0.875")


def test_externality_measures_excursion_beyond_prior_lower_sources() -> None:
    lower = (
        _candle(0, "100", "102", "98", "101"),
        _candle(5, "101", "103", "97", "100"),
        _candle(10, "100", "101", "95", "99"),
    )
    value = _externality(
        lower=lower,
        extreme_index=2,
        side=Side.LONG,
        lookback=3,
        source_range=Decimal("10"),
    )
    assert value == Decimal("0.2")


def test_post_ps_min_distance_is_pre_confirmation_only() -> None:
    lower = (
        _candle(0, "100", "102", "95", "101"),
        _candle(5, "101", "103", "97", "102"),
        _candle(10, "102", "104", "99", "103"),
    )
    distance = _post_ps_min_distance(
        lower=lower,
        extreme_index=0,
        confirm_index=2,
        side=Side.LONG,
        protected_swing=Decimal("95"),
    )
    assert distance == Decimal("2")


def test_post_entry_label_is_diagnostic_class_only() -> None:
    assert _outcome_class("SELECTED_DOL_REACHED") == "TOUCHED_ANY_ACTIVE_DOL"
    assert (
        _outcome_class("INVALIDATED_BEFORE_ANY_ACTIVE_DOL")
        == "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"
    )
    assert (
        _outcome_class("NO_ACTIVE_DOL_REACHED_BEFORE_LIFECYCLE_EXIT")
        == "OTHER_DIAGNOSTIC"
    )
