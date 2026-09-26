from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    cibo_phase18_gbpjpy_r37_geometry_replay as phase18,
)


def test_phase18_gbpjpy_reuses_frozen_r37_candidate_contract() -> None:
    assert phase18.CANDIDATE_IDENTITY == "TURTLE_SOUP_GBPJPY_R36_CONFIDENCE_CANDIDATE_001"
    assert phase18.SOURCE_R37_IDENTITY == (
        "TURTLE_SOUP_GBPJPY_R37_FROZEN_R36_5Y_VALIDATION_V1"
    )
    assert phase18.FROZEN_ENSEMBLE == "R35_RANGE_DIRECTION_MINIMAL_ROBUST"
    assert phase18.FROZEN_POLICY == "CONFIDENCE_100_050_010"


def test_phase18_gbpjpy_five_year_window_is_frozen() -> None:
    assert phase18.EVAL_OPEN == datetime(2021, 9, 17, tzinfo=UTC)
    assert phase18.EVAL_CLOSE == datetime(2026, 9, 17, tzinfo=UTC)


def test_phase18_gbpjpy_r37_gate_is_reproduction_only() -> None:
    assert phase18.MIN_TRADES == 800
    assert phase18.MIN_PF_010 == Decimal("1.50")
    assert phase18.MAX_DD_010 == Decimal("6.0")
    assert phase18.REQUIRED_POSITIVE_ANNUAL_BLOCKS == 5


def test_phase18_trade_serializes_missing_exact_geometry() -> None:
    names = {item.name for item in fields(phase18.ScaledTrade)}
    assert {
        "signal_at",
        "entry_at",
        "entry_price",
        "structural_stop",
        "technical_target",
    } <= names
