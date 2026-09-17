from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Side


def _target(*, kind: str, timeframe: str, level: str, known: int = 0, touch: int | None = None) -> r3.TargetCandidate:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    return r3.TargetCandidate(
        episode_id="episode",
        kind=kind,
        timeframe=timeframe,
        level=Decimal(level),
        known_at=base.replace(hour=known),
        touch_at=None if touch is None else base.replace(hour=touch),
    )


def test_target_routes_are_geometry_not_filter_score() -> None:
    assert r3._target_match("SOURCE_OPPOSITE", _target(kind="SOURCE_OPPOSITE_BOUNDARY", timeframe="H1", level="2050"))
    assert r3._target_match("PRIOR_H4", _target(kind="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY", timeframe="H4", level="2050"))
    assert r3._target_match("SWING_D1", _target(kind="ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY", timeframe="D1", level="2050"))
    assert not r3._target_match("PRIOR_H1", _target(kind="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY", timeframe="H4", level="2050"))


def test_active_target_must_be_known_ahead_and_not_preconsumed() -> None:
    at = datetime(2024, 1, 1, 2, tzinfo=UTC)
    rows = [
        _target(kind="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY", timeframe="H4", level="2050", known=1),
        _target(kind="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY", timeframe="H4", level="2040", known=1, touch=1),
        _target(kind="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY", timeframe="H4", level="2060", known=3),
        _target(kind="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY", timeframe="H4", level="1990", known=1),
    ]
    active = r3._active_targets(rows, at=at, side=Side.LONG, anchor=Decimal("2000"), route="PRIOR_H4")
    assert [item.level for item in active] == [Decimal("2050")]


def test_router_contract_has_no_positive_score_trade_gate() -> None:
    assert r3.IDENTITY == "TURTLE_SOUP_XAUUSD_R3_CIBO_JOURNEY_ROUTER"
    assert r3.TRAIN_CLOSE.isoformat() == "2022-09-17T00:00:00+00:00"
    assert ("CISD_THRESHOLD_RETEST", "PRIOR_H4") in r3.ACTIONS
    assert "PRIOR_D1" in r3.TARGET_ROUTES
    assert "SWING_D1" in r3.TARGET_ROUTES
