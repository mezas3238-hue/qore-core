from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r21_concurrent_quality_budget as mod


def test_r21_contract() -> None:
    assert mod.FIVE_YEAR_MIN_TRADES == 1500
    assert mod.FIVE_YEAR_MAX_TRADES == 1600
    assert mod.PRIMARY_PF_GOAL == Decimal("1.50")
    assert mod.PRIMARY_DD_GOAL == Decimal("6")
    assert mod.SECONDARY_PF_GOAL == Decimal("1.30")
    assert mod.SECONDARY_DD_GOAL == Decimal("8")


def test_batch_budget_scales_pro_rata_without_suppression() -> None:
    assigned, scaled = mod._allocate_batch(
        (Decimal("1"), Decimal("1")),
        active_risk=Decimal("0.5"),
        budget=Decimal("1.5"),
    )
    assert scaled
    assert assigned == (Decimal("0.5"), Decimal("0.5"))
    assert all(value > 0 for value in assigned)


def test_batch_floor_never_drops_signal_to_zero() -> None:
    assigned, scaled = mod._allocate_batch(
        (Decimal("0.25"), Decimal("0.25"), Decimal("0.25")),
        active_risk=Decimal("2"),
        budget=Decimal("1.5"),
    )
    assert scaled
    assert assigned == (
        mod.MIN_EFFECTIVE_WEIGHT,
        mod.MIN_EFFECTIVE_WEIGHT,
        mod.MIN_EFFECTIVE_WEIGHT,
    )


def test_r21_scheme_space_is_bounded() -> None:
    schemes = mod._schemes()
    assert len(schemes) == 864
    assert all(scheme.portfolio_risk_budget_r > 0 for scheme in schemes)
