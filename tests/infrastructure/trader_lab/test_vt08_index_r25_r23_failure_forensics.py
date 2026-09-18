from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r25_r23_failure_forensics as mod


def test_r25_is_forensics_only_identity() -> None:
    assert mod.IDENTITY == "VT08_INDEX_R25_R23_FAILURE_FORENSICS_001"
    assert mod.STRESS == Decimal("0.05")


def test_r25_quality_tiers_are_diagnostic_labels_not_new_weights() -> None:
    assert mod.r24.BASE_QUALITY.base_weight == Decimal("0.005")
    assert mod.r24.BASE_QUALITY.tier_a_weight == Decimal("1.50")
    assert mod.r24.BASE_QUALITY.tier_b_weight == Decimal("0.75")
    assert mod.r24.BASE_QUALITY.tier_c_weight == Decimal("0.10")


def test_r25_keeps_r23_realized_governor_fixed() -> None:
    assert mod.r24.BASE_RISK.rolling_trades == 60
    assert mod.r24.BASE_RISK.warn_dd_r == Decimal("1.25")
    assert mod.r24.BASE_RISK.hard_dd_r == Decimal("1.50")
    assert mod.r24.BASE_RISK.portfolio_risk_budget_r == Decimal("0.75")
