from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    cibo_phase18_gbpusd_r39_geometry_replay as phase18,
)


def test_phase18_gbpusd_reuses_frozen_r39_candidate_contract() -> None:
    assert phase18.CANDIDATE_IDENTITY == (
        "TURTLE_SOUP_GBPUSD_R37_STRUCTURAL_QUALITY_CANDIDATE_001"
    )
    assert phase18.SOURCE_R39_IDENTITY == (
        "TURTLE_SOUP_GBPUSD_R39_FROZEN_R37_5Y_VALIDATION_V1"
    )
    assert phase18.FAMILY_SET == "R37_G25_FIXED"
    assert phase18.STRUCTURAL_POLICY_NAME == "SQ3_H1_BALANCED"
    assert phase18.DRAWDOWN_GOVERNOR_NAME == "DD_1_3_SCALE_075_025"


def test_phase18_gbpusd_five_year_window_is_frozen() -> None:
    assert phase18.EVAL_OPEN == datetime(2021, 9, 17, tzinfo=UTC)
    assert phase18.EVAL_CLOSE == datetime(2026, 9, 17, tzinfo=UTC)


def test_phase18_gbpusd_r39_gate_is_reproduction_only() -> None:
    assert phase18.MIN_TRADES == 800
    assert phase18.MIN_PF_010 == Decimal("1.50")
    assert phase18.MAX_DD_010 == Decimal("6.0")


def test_phase18_gbpusd_trade_serializes_missing_exact_geometry() -> None:
    names = {item.name for item in fields(phase18.ScaledTrade)}
    assert {
        "signal_at",
        "entry_at",
        "entry_price",
        "structural_stop",
        "technical_target",
        "setup_context",
        "regime",
    } <= names
