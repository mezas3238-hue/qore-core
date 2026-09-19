from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r53_cisd_reaction_quality_forensics as r53,
)


def test_r53_hypothesis_is_narrow_and_frozen() -> None:
    assert r53.REACTION_MAX_MINUTES == 15
    assert r53.MIN_FIVE_YEAR_SAMPLE == 50
    assert r53.MIN_TWO_YEAR_SAMPLE == 25
    assert r53.MIN_RAW_SECONDARY_PF == Decimal("1.10")


def test_r53_latest_liquidity_reaction_is_causal_and_fresh() -> None:
    signal_at = datetime(2026, 9, 19, 14, 15, tzinfo=UTC)
    structures = (
        {
            "kind": "order-block",
            "side": "bullish",
            "observed_at": (signal_at - timedelta(minutes=30)).isoformat(),
        },
        {
            "kind": "liquidity-sweep",
            "side": "bullish",
            "observed_at": (signal_at - timedelta(minutes=15)).isoformat(),
        },
        {
            "kind": "fvg",
            "side": "bullish",
            "observed_at": (signal_at - timedelta(minutes=15)).isoformat(),
        },
    )
    context = r53._classify_latest_reaction(
        structures,
        signal_at=signal_at,
    )
    assert context["reaction_event"] == "liquidity-take"
    assert context["reaction_structure_combo"] == "fvg+liquidity-sweep"
    assert context["minutes_reaction_to_signal"] == 15
    assert context["fresh_liquidity_take_15m"] is True


def test_r53_structure_retest_is_not_promoted_by_classifier() -> None:
    signal_at = datetime(2026, 9, 19, 14, 15, tzinfo=UTC)
    structures = (
        {
            "kind": "order-block",
            "side": "bearish",
            "observed_at": (signal_at - timedelta(minutes=15)).isoformat(),
        },
    )
    context = r53._classify_latest_reaction(
        structures,
        signal_at=signal_at,
    )
    assert context["reaction_event"] == "structure-retest"
    assert context["fresh_liquidity_take_15m"] is False


def test_r53_future_structure_is_fail_closed() -> None:
    signal_at = datetime(2026, 9, 19, 14, 15, tzinfo=UTC)
    structures = (
        {
            "kind": "liquidity-sweep",
            "side": "bullish",
            "observed_at": (signal_at + timedelta(minutes=15)).isoformat(),
        },
    )
    context = r53._classify_latest_reaction(
        structures,
        signal_at=signal_at,
    )
    assert context["reaction_event"] == "none-detected"
    assert context["fresh_liquidity_take_15m"] is False
