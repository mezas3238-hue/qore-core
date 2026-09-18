from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r35_r32_core_expansion as r35,
)


def test_r35_acceptance_is_fixed() -> None:
    assert r35.MIN_TRADES == 350
    assert r35.MIN_PF_010 == Decimal("1.90")
    assert r35.MAX_DD_010 == Decimal("6.0")


def test_r35_excludes_r33_falsified_and_unstable_families() -> None:
    for families in r35.FAMILY_SETS.values():
        assert r35.F1 not in families
        assert r35.F3 not in families


def test_r35_uses_r32_regime_core_scheme() -> None:
    fields, route_mode = r35.r32.SCHEMES["R32_REGIME_ROUTE_TYPES"]
    assert route_mode == "TYPES_ONLY"
    assert "cisd_progress_bucket" not in fields


def test_r35_expansion_sets_are_predeclared() -> None:
    assert r35.FAMILY_SETS["R35_G456"] == (r35.F4, r35.F5, r35.F6)
    assert r35.FAMILY_SETS["R35_G256"] == (r35.F2, r35.F5, r35.F6)
