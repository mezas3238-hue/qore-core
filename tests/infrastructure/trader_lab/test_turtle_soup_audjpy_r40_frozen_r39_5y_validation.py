from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r40_frozen_r39_5y_validation as r40,
)


def test_r40_frozen_candidate_contract() -> None:
    assert r40.CANDIDATE_IDENTITY == (
        "TURTLE_SOUP_AUDJPY_R39_STRUCTURAL_RISK_CANDIDATE_001"
    )
    assert r40.FROZEN_ENSEMBLE == "R38_FROZEN_SIGNAL_BASELINE"
    assert r40.FROZEN_POLICY == "AUDJPY_CONFIDENCE_100_075_025"


def test_r40_five_year_window_is_fixed() -> None:
    assert r40.EVAL_OPEN == datetime(2021, 9, 17, tzinfo=UTC)
    assert r40.EVAL_CLOSE == datetime(2026, 9, 17, tzinfo=UTC)


def test_r40_owner_five_year_gate_is_fixed() -> None:
    assert r40.MIN_TRADES == 800
    assert r40.MIN_PF_010 == Decimal("1.50")
    assert r40.MAX_DD_010 == Decimal("6.0")
    assert r40.REQUIRED_POSITIVE_ANNUAL_BLOCKS == 5
