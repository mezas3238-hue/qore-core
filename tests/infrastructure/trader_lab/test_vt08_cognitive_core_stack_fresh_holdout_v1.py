from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_fresh_holdout_v1 import (
    CONSUMED_BOUNDARY,
    MIN_CORE_STACK_PF,
    MIN_FRESH_TRADES,
)


def test_fresh_boundary_is_frozen_before_consumed_corpus() -> None:
    assert CONSUMED_BOUNDARY == datetime(2024, 8, 25, 21, 0, tzinfo=UTC)


def test_fresh_screen_gates_are_predeclared() -> None:
    assert MIN_FRESH_TRADES == 20
    assert MIN_CORE_STACK_PF == Decimal("1.00")
