from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r3_cibo_journey import (
    RoutedTrade,
)
from qore.infrastructure.trader_lab.turtle_soup_xauusd_r11_situation_recognition_engine import (
    SituationState,
)
from qore.infrastructure.trader_lab.turtle_soup_xauusd_r13_autonomous_2y_behavior_replay import (
    EVAL_CLOSE,
    EVAL_OPEN,
    EXECUTABLE_STATES,
    IDENTITY,
    _decimal_summary,
    _trade_geometry,
)


def _trade() -> RoutedTrade:
    return RoutedTrade(
        source_timeframe="H1",
        side="long",
        entry_mode="NEXT_SOURCE_OPEN",
        target_route="PRIOR_H4",
        episode_id="E1",
        entry_at=datetime(2025, 1, 2, 12, tzinfo=UTC),
        exit_at=datetime(2025, 1, 2, 14, tzinfo=UTC),
        entry=Decimal("2600"),
        stop=Decimal("2595"),
        target=Decimal("2615"),
        target_kind="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY",
        target_timeframe="H4",
        gross_r=Decimal("3"),
        primary_net_r=Decimal("2.95"),
        stress_net_r=Decimal("2.90"),
        exit_reason="TARGET",
        session_bucket="NY",
        prior_body_alignment="opposed",
    )


def test_identity_and_two_year_window_are_frozen() -> None:
    assert IDENTITY == "TURTLE_SOUP_XAUUSD_R13_AUTONOMOUS_2Y_BEHAVIOR_REPLAY_V1"
    assert EVAL_OPEN == datetime(2024, 9, 17, tzinfo=UTC)
    assert EVAL_CLOSE == datetime(2026, 9, 17, tzinfo=UTC)


def test_total_freedom_keeps_non_invalid_states_executable() -> None:
    assert SituationState.STRUCTURALLY_VALID_CANDIDATE in EXECUTABLE_STATES
    assert SituationState.CONFLICTED in EXECUTABLE_STATES
    assert SituationState.UNKNOWN in EXECUTABLE_STATES
    assert SituationState.KNOWN_INVALID not in EXECUTABLE_STATES


def test_trade_geometry_measures_stop_target_rr_and_duration() -> None:
    result = _trade_geometry(_trade())
    assert result["risk_price"] == Decimal("5")
    assert result["reward_price"] == Decimal("15")
    assert result["initial_rr"] == Decimal("3")
    assert result["stop_entry_fraction"] == Decimal("5") / Decimal("2600")
    assert result["target_entry_fraction"] == Decimal("15") / Decimal("2600")
    assert result["duration_minutes"] == Decimal("120")


def test_decimal_summary_is_deterministic() -> None:
    result = _decimal_summary(
        [Decimal("1"), Decimal("3"), Decimal("2")]
    )
    assert result == {
        "n": 3,
        "min": "1",
        "median": "2",
        "mean": "2",
        "max": "3",
    }


def test_empty_decimal_summary_is_explicit() -> None:
    result = _decimal_summary([])
    assert result["n"] == 0
    assert result["min"] is None
    assert result["median"] is None
    assert result["mean"] is None
    assert result["max"] is None
