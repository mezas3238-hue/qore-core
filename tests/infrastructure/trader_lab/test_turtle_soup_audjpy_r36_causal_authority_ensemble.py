from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r36_causal_authority_ensemble as r36,
)


def test_r36_acceptance_contract_is_fixed() -> None:
    assert r36.MIN_TRADES == 350
    assert r36.MIN_PF_010 == Decimal("1.90")
    assert r36.MAX_DD_010 == Decimal("6.0")
    assert r36.MAX_LS_010 == 3


def test_r36_r32_core_is_first_authority_layer() -> None:
    assert r36.CORE == "R32_CORE_ROUTE_TYPES"
    for layers in r36.ENSEMBLES.values():
        assert layers[0][0] == r36.CORE
        assert set(layers[0][1]) == {r36.ROBUST, r36.MAJORITY}


def test_r36_expansion_excludes_falsified_range_memory() -> None:
    allowed = {r36.CORE, r36.DIRECTION, r36.TIMEFRAME, r36.MINIMAL}
    for layers in r36.ENSEMBLES.values():
        schemes = {scheme for scheme, _classes in layers}
        assert schemes <= allowed
        assert r36.RANGE_FALSIFIED not in schemes


def test_r36_risk_policy_preserves_full_core_risk() -> None:
    for core, robust, majority in r36.RISK_POLICIES.values():
        assert core == Decimal("1")
        assert Decimal("0") < robust <= Decimal("1")
        assert Decimal("0") < majority <= robust
