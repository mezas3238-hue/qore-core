from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r37_frozen_r36_5y_validation as r37,
)


def test_r37_frozen_candidate_contract() -> None:
    assert r37.CANDIDATE_IDENTITY == "TURTLE_SOUP_GBPJPY_R36_CONFIDENCE_CANDIDATE_001"
    assert r37.FROZEN_ENSEMBLE == "R35_RANGE_DIRECTION_MINIMAL_ROBUST"
    assert r37.FROZEN_POLICY == "CONFIDENCE_100_050_010"


def test_r37_five_year_window_is_fixed() -> None:
    assert r37.EVAL_OPEN == datetime(2021, 9, 17, tzinfo=UTC)
    assert r37.EVAL_CLOSE == datetime(2026, 9, 17, tzinfo=UTC)


def test_r37_owner_five_year_gate_is_fixed() -> None:
    assert r37.MIN_TRADES == 800
    assert r37.MIN_PF_010 == Decimal("1.50")
    assert r37.MAX_DD_010 == Decimal("6.0")
    assert r37.REQUIRED_POSITIVE_ANNUAL_BLOCKS == 5
