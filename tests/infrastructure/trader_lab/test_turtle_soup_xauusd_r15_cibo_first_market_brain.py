from __future__ import annotations

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r15_cibo_first_market_brain import (
    _candidate_route,
    _entry_mode,
    _market_posture,
    _target_index,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from datetime import UTC, datetime
from decimal import Decimal


def _regime(
    *,
    d1_trend: str,
    h4_trend: str,
    d1_range: str = "normal_0.75_1.25",
    h4_range: str = "normal_0.75_1.25",
) -> dict[str, str]:
    return {
        "d1_trend_state_20": d1_trend,
        "h4_trend_state_20": h4_trend,
        "d1_range_5v20": d1_range,
        "h4_range_3v20": h4_range,
    }


def test_market_posture_recognizes_expansion_and_opposition() -> None:
    assert _market_posture(
        _regime(
            d1_trend="persistent_with_trade",
            h4_trend="directional_with_trade",
        )
    ) == "EXPANSION_WITH_TRADE"
    assert _market_posture(
        _regime(
            d1_trend="persistent_against_trade",
            h4_trend="directional_against_trade",
        )
    ) == "OPPOSED_TREND"


def test_target_extension_only_one_ladder_step() -> None:
    supportive = _regime(
        d1_trend="persistent_with_trade",
        h4_trend="persistent_with_trade",
    )
    assert _target_index("EXPANSION_WITH_TRADE", supportive) == 1
    compressed = _regime(
        d1_trend="persistent_with_trade",
        h4_trend="persistent_with_trade",
        h4_range="compressed<=0.75",
    )
    assert _target_index("EXPANSION_WITH_TRADE", compressed) == 0
    assert _target_index("MIXED_CONTEXT", supportive) == 0


def test_candidate_route_maps_supported_cibo_families() -> None:
    base = dict(
        episode_id="e",
        level=Decimal("2000"),
        known_at=datetime(2026, 1, 1, tzinfo=UTC),
        touch_at=None,
    )
    assert _candidate_route(
        r3.TargetCandidate(
            **base,
            kind="SOURCE_OPPOSITE_BOUNDARY",
            timeframe="H1",
        )
    ) == "SOURCE_OPPOSITE"
    assert _candidate_route(
        r3.TargetCandidate(
            **base,
            kind="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY",
            timeframe="H4",
        )
    ) == "PRIOR_H4"
    assert _candidate_route(
        r3.TargetCandidate(
            **base,
            kind="ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
            timeframe="D1",
        )
    ) == "SWING_D1"


def test_entry_posture_uses_retest_for_defensive_context() -> None:
    class C:
        cisd_progress_bucket = "q2:<=0.50"

    class S:
        context = C()

    setup = S()
    assert _entry_mode(setup, "OPPOSED_TREND") == "CISD_THRESHOLD_RETEST"
    assert _entry_mode(setup, "RANGE_OR_COMPRESSION") == "CISD_THRESHOLD_RETEST"
    assert _entry_mode(setup, "DIRECTIONAL_WITH_TRADE") == "NEXT_SOURCE_OPEN"
