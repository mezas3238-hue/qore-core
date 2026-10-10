from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_online_causal_memory_2r_v1 as lab,
)


def _row() -> dict[str, object]:
    return {
        "symbol": "NAS100",
        "session": "NEW_YORK",
        "side": "LONG",
        "provenance": "MAX_RECOVERY",
        "source_microstructure_family": "SOURCE_FIRST",
        "prior_same_session_selected": 2,
        "baseline_active_positions": 1,
        "prior_closed_trades_today": 2,
        "prior_realized_r_today": "-1",
        "completed_prior_sessions": ["ASIA", "LONDON"],
        "baseline_shared_factors": ["USD"],
        "baseline_same_direction_factors": [],
        "baseline_opposing_direction_factors": ["USD"],
        "microstructure_observations": [
            "ENTRY_MODE:FVG_CE_50",
            "LIQUIDITY_KIND:PREVIOUS_DAY_HIGH",
            "M5_CLOSEBACK_AT:2026-01-05T10:05:00+00:00",
        ],
    }


def test_features_exclude_timestamp_tokens() -> None:
    features = lab._features(_row())
    assert "MICRO=ENTRY_MODE:FVG_CE_50" in features
    assert "MICRO=LIQUIDITY_KIND:PREVIOUS_DAY_HIGH" in features
    assert not any("M5_CLOSEBACK_AT" in item for item in features)


def test_sign_and_bucket_are_deterministic() -> None:
    assert lab._sign(Decimal("-1")) == "NEGATIVE"
    assert lab._sign(Decimal("0")) == "ZERO"
    assert lab._sign(Decimal("1")) == "POSITIVE"
    assert lab._count_bucket(0) == "0"
    assert lab._count_bucket(2) == "2"
    assert lab._count_bucket(4) == "3_PLUS"
