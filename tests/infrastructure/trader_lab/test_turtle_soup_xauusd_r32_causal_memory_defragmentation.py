from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r32_causal_memory_defragmentation as r32,
)


def test_r32_acceptance_is_fixed() -> None:
    assert r32.MIN_TRADES == 350
    assert r32.MIN_PF_010 == Decimal("1.90")
    assert r32.MAX_DD_010 == Decimal("6.0")
    assert r32.MAX_LS_010 == 3


def test_route_family_normalization_is_structural() -> None:
    route = (
        "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1+"
        "SOURCE_OPPOSITE_BOUNDARY:H1"
    )
    assert r32._route_family(route, "TYPES_ONLY") == (
        "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY+SOURCE_OPPOSITE_BOUNDARY"
    )
    assert r32._route_family(route, "TYPES_AND_HORIZONS") == (
        "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY+SOURCE_OPPOSITE_BOUNDARY@H1"
    )


def test_r32_schemes_are_predeclared() -> None:
    assert set(r32.SCHEMES) == {
        "R32_ANATOMY_ROUTE_TYPES_HORIZON",
        "R32_ANATOMY_ROUTE_TYPES",
        "R32_CORE_ROUTE_TYPES",
        "R32_REGIME_ROUTE_TYPES",
    }
