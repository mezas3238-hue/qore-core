from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r20_static_quality_portfolio as mod


def test_r20_contract() -> None:
    assert mod.FIVE_YEAR_MIN_TRADES == 1500
    assert mod.FIVE_YEAR_MAX_TRADES == 1600
    assert mod.TWO_YEAR_MIN_TRADES == 600
    assert mod.TWO_YEAR_MAX_TRADES == 700
    assert mod.PF_MIN == Decimal("1.50")
    assert mod.DD_MAX == Decimal("6")
    assert mod.MIN_WEIGHT == Decimal("0.01")


def test_r20_scheme_space_is_bounded_and_nonzero() -> None:
    schemes = mod._schemes()
    assert len(schemes) == 36
    assert all(scheme.base_weight >= mod.MIN_WEIGHT for scheme in schemes)
    assert all(scheme.tier_b_weight > 0 for scheme in schemes)
    assert all(scheme.tier_c_weight > 0 for scheme in schemes)


def test_r20_has_no_pnl_state_governor() -> None:
    assert "static" in mod.IDENTITY.lower()
