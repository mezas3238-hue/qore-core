from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r34_coarse_causal_memory as r34,
)


def test_r34_acceptance_is_fixed() -> None:
    assert r34.MIN_TRADES == 350
    assert r34.MIN_PF_010 == Decimal("1.90")
    assert r34.MAX_DD_010 == Decimal("6.0")
    assert r34.MAX_LS_010 == 3


def test_route_family_normalization_is_structural() -> None:
    route = (
        "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1+"
        "SOURCE_OPPOSITE_BOUNDARY:H1"
    )
    assert r34._route_family(route, "TYPES_ONLY") == (
        "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY+SOURCE_OPPOSITE_BOUNDARY"
    )


def test_r34_schemes_are_predeclared_and_lower_dimensional() -> None:
    assert set(r34.SCHEMES) == {
        "R34_TIMEFRAME_REGIME_ROUTE_TYPES",
        "R34_DIRECTION_REGIME_ROUTE_TYPES",
        "R34_MINIMAL_ROUTE_TYPES",
        "R34_RANGE_ROUTE_TYPES",
    }
    assert max(len(fields) for fields, _ in r34.SCHEMES.values()) <= 6
    assert all(mode == "TYPES_ONLY" for _, mode in r34.SCHEMES.values())
