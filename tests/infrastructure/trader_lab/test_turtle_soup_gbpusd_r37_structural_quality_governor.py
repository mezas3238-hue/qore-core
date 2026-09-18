from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r37_structural_quality_governor as r37,
)


def test_r37_keeps_g25_execution_set() -> None:
    assert r37.FAMILY_SETS == {"R37_G25_FIXED": (r37.F2, r37.F5)}


def test_r37_acceptance_contract_is_unchanged() -> None:
    assert r37.MIN_TRADES == 350
    assert r37.MIN_PF_010 == Decimal("1.90")
    assert r37.MAX_DD_010 == Decimal("6.0")


def test_r37_structural_policies_never_zero_risk() -> None:
    for policy in r37.STRUCTURAL_POLICIES.values():
        assert Decimal(str(policy["core_robust"])) > 0
        assert Decimal(str(policy["core_majority"])) > 0
        assert Decimal(str(policy["f5"])) > 0
        assert Decimal(str(policy["f2_strong"])) > 0
        assert Decimal(str(policy["f2_weak"])) > 0


def test_r37_f2_strong_rule_is_preentry_structural() -> None:
    features = {
        "protected_risk_range_bucket": "q2:<=0.50",
        "h1_range_state": "compressed",
        "close_location_bucket": "q4:>0.75",
    }
    assert r37._f2_is_strong(features, "PRISK_Q2")
