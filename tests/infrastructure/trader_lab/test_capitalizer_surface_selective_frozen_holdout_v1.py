from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_surface_selective_frozen_holdout_v1 as frozen,
)


def test_frozen_selective_multiplier_contract() -> None:
    assert frozen._frozen_multiplier(
        current_dd=Decimal("5"),
        score=7,
        adverse_votes=0,
    ) == Decimal("0.20")
    assert frozen._frozen_multiplier(
        current_dd=Decimal("4"),
        score=7,
        adverse_votes=0,
    ) == Decimal("0.35")
    assert frozen._frozen_multiplier(
        current_dd=Decimal("3"),
        score=6,
        adverse_votes=0,
    ) == Decimal("0.55")
    assert frozen._frozen_multiplier(
        current_dd=Decimal("2"),
        score=5,
        adverse_votes=3,
    ) == Decimal("0.75")
    assert frozen._frozen_multiplier(
        current_dd=Decimal("2"),
        score=4,
        adverse_votes=0,
    ) == Decimal("1")


def test_frozen_source_equivalence_guard() -> None:
    frozen._assert_source_equivalence()


def test_reserved_window_is_fixed_before_evaluation() -> None:
    assert frozen.RESERVED_START == "2020-09-17T00:00:00+00:00"
    assert frozen.RESERVED_END == "2022-09-17T00:00:00+00:00"
