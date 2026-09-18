from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r18_formation_quality_dual_governor as mod,
)


def test_r18_contract() -> None:
    assert mod.FIVE_YEAR_MIN_TRADES == 1500
    assert mod.FIVE_YEAR_MAX_TRADES == 1600
    assert mod.TWO_YEAR_MIN_TRADES == 600
    assert mod.TWO_YEAR_MAX_TRADES == 700
    assert mod.PF_MIN == Decimal("1.50")
    assert mod.DD_MAX == Decimal("6")
    assert mod.MIN_EFFECTIVE_WEIGHT == Decimal("0.025")


def test_r18_scheme_space_is_bounded() -> None:
    schemes = mod._schemes()
    assert schemes
    assert len(schemes) <= 400
    for scheme in schemes:
        assert scheme.base_weight >= Decimal("0.10")
        assert scheme.hard_multiplier == Decimal("0.25")


def test_r18_minimum_effective_weight_is_nonzero() -> None:
    for scheme in mod._schemes():
        assert scheme.base_weight * scheme.hard_multiplier >= mod.MIN_EFFECTIVE_WEIGHT
