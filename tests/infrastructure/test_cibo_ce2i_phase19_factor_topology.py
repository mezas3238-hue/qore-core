from __future__ import annotations

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_factor_topology import (
    FactorDirection,
    FactorTopologyRelation,
    compare_factor_topology,
    directional_factor_exposures,
)


def test_fx_pair_topology_reverses_base_quote_direction_with_side() -> None:
    long = directional_factor_exposures(
        qore_symbol="GBPUSD",
        side="long",
    )
    short = directional_factor_exposures(
        qore_symbol="GBPUSD",
        side="short",
    )

    assert tuple((item.factor, item.direction) for item in long) == (
        ("GBP", FactorDirection.LONG),
        ("USD", FactorDirection.SHORT),
    )
    assert tuple((item.factor, item.direction) for item in short) == (
        ("GBP", FactorDirection.SHORT),
        ("USD", FactorDirection.LONG),
    )


def test_cross_pair_topology_distinguishes_same_and_opposing_factor() -> None:
    gbpjpy_long = directional_factor_exposures(
        qore_symbol="GBPJPY",
        side="long",
    )
    audjpy_long = directional_factor_exposures(
        qore_symbol="AUDJPY",
        side="long",
    )
    gbpusd_short = directional_factor_exposures(
        qore_symbol="GBPUSD",
        side="short",
    )

    same = compare_factor_topology(
        left=gbpjpy_long,
        right=audjpy_long,
    )
    opposing = compare_factor_topology(
        left=gbpjpy_long,
        right=gbpusd_short,
    )

    assert same.relation is FactorTopologyRelation.SAME_DIRECTION
    assert same.shared_factors == ("JPY",)
    assert opposing.relation is FactorTopologyRelation.OPPOSING_DIRECTION
    assert opposing.shared_factors == ("GBP",)


def test_nas100_uses_bespoke_equity_factor_without_fake_usd_leg() -> None:
    exposure = directional_factor_exposures(
        qore_symbol="NAS100",
        side="long",
    )

    assert tuple((item.factor, item.direction) for item in exposure) == (
        ("US_TECH_EQUITY_BETA", FactorDirection.LONG),
    )


def test_factor_topology_rejects_unknown_symbol_or_side() -> None:
    with pytest.raises(CiboCapitalManagementError, match="outside frozen"):
        directional_factor_exposures(qore_symbol="BTCUSD", side="long")
    with pytest.raises(CiboCapitalManagementError, match="long or short"):
        directional_factor_exposures(qore_symbol="GBPUSD", side="flat")
