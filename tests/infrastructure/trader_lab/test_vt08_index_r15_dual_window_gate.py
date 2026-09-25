from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r15_dual_window_gate as mod


def test_r15_dual_window_contract() -> None:
    assert mod.FIVE_YEAR_MIN_TRADES == 1500
    assert mod.FIVE_YEAR_MAX_TRADES == 1600
    assert mod.TWO_YEAR_MIN_TRADES == 600
    assert mod.TWO_YEAR_MAX_TRADES == 700
    assert mod.PF_MIN == Decimal("1.50")
    assert mod.DD_MAX == Decimal("6")


def test_r15_requires_same_scheme_on_both_windows() -> None:
    assert mod.IDENTITY == "VT08_INDEX_R15_DUAL_WINDOW_GATE_001"


def test_r15_secondary_stress_contract() -> None:
    assert mod.PRIMARY_STRESS == Decimal("0.05")
    assert mod.SECONDARY_STRESS == Decimal("0.10")
    assert mod.SECONDARY_PF_MIN == Decimal("1.30")
    assert mod.SECONDARY_DD_MAX == Decimal("8")
