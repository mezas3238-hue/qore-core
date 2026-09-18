from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r35_confidence_tier_ensemble as r35,
)


def test_r35_acceptance_contract_is_fixed() -> None:
    assert r35.MIN_TRADES == 350
    assert r35.MIN_PF_010 == Decimal("1.90")
    assert r35.MAX_DD_010 == Decimal("6.0")
    assert r35.MAX_LS_010 == 3


def test_r35_range_is_first_authority_layer() -> None:
    for layers in r35.ENSEMBLES.values():
        assert layers[0][0] == r35.CORE
        assert set(layers[0][1]) == {r35.ROBUST, r35.MAJORITY}


def test_r35_expansion_is_predeclared_and_gbpjpy_memory_only() -> None:
    allowed = {r35.CORE, r35.DIRECTION, r35.MINIMAL, r35.TIMEFRAME}
    for layers in r35.ENSEMBLES.values():
        assert {scheme for scheme, _classes in layers} <= allowed


def test_risk_policy_preserves_full_core_risk() -> None:
    for core, robust, majority in r35.RISK_POLICIES.values():
        assert core == Decimal("1")
        assert Decimal("0") < robust <= Decimal("1")
        assert Decimal("0") < majority <= robust


def test_fixed_policy_does_not_scale_any_tier() -> None:
    assert r35.RISK_POLICIES["FIXED_1R"] == (
        Decimal("1"),
        Decimal("1"),
        Decimal("1"),
    )
