import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    T11_NONLINEAR_INPUT_FREEZE,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _load() -> ModuleType:
    path = Path("scripts/cibo_arch2_t11_market_impact_demo.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_arch2_t11_market_impact_demo",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load T11 market-impact runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = _load()


def test_source_minimum_volume_math_is_provider_native_and_exact() -> None:
    assert runner._source_minimum_volume(
        min_native_volume=100000,
        lot_size_units=Decimal("100000"),
    ) == Decimal("0.01")
    assert runner._source_minimum_volume(
        min_native_volume=100,
        lot_size_units=Decimal("100"),
    ) == Decimal("0.01")
    assert runner._source_minimum_volume(
        min_native_volume=10,
        lot_size_units=Decimal("1"),
    ) == Decimal("0.1")


def test_level_order_helper_alternates_matched_pair_order() -> None:
    assert runner._levels_for_pair(1) == (1, 2)
    assert runner._levels_for_pair(2) == (2, 1)
    assert runner._levels_for_pair(3) == (1, 2)
    assert runner._levels_for_pair(4) == (2, 1)


def test_realized_settlement_cost_floors_profitable_roundtrip_at_zero() -> None:
    cost = runner.realized_settlement_cost_usd(
        entry_commission_usd=Decimal("-0.03"),
        gross_profit_usd=Decimal("0.10"),
        swap_usd=Decimal("0"),
        close_commission_usd=Decimal("-0.03"),
        pnl_conversion_fee_usd=Decimal("0"),
    )

    assert cost == Decimal("0")


def test_realized_settlement_cost_captures_all_in_loss() -> None:
    cost = runner.realized_settlement_cost_usd(
        entry_commission_usd=Decimal("-0.03"),
        gross_profit_usd=Decimal("-0.02"),
        swap_usd=Decimal("0"),
        close_commission_usd=Decimal("-0.03"),
        pnl_conversion_fee_usd=Decimal("0"),
    )

    assert cost == Decimal("0.08")


def test_realized_settlement_cost_rejects_nonfinite_component() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="finite Decimal",
    ):
        runner.realized_settlement_cost_usd(
            entry_commission_usd=Decimal("NaN"),
            gross_profit_usd=Decimal("0"),
            swap_usd=Decimal("0"),
            close_commission_usd=Decimal("0"),
            pnl_conversion_fee_usd=Decimal("0"),
        )


def test_frozen_experiment_size_is_144_episodes_and_216_child_entries() -> None:
    calibration_pairs = (
        runner.MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL
    )
    validation_pairs = (
        runner.MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL
    )
    symbols = len(runner.REQUIRED_SYMBOLS)

    episodes = symbols * (calibration_pairs + validation_pairs) * 2
    child_entries = symbols * (calibration_pairs + validation_pairs) * 3

    assert episodes == 144
    assert child_entries == 216


def test_freeze_requires_settlement_usd_and_simultaneous_minimum_children() -> None:
    freeze = T11_NONLINEAR_INPUT_FREEZE.market_impact

    assert freeze.realized_settlement_cost_required is True
    assert freeze.deposit_asset_usd_required is True
    assert freeze.balanced_long_short_pairs_required is True
    assert freeze.alternating_level_order_required is True
    assert freeze.each_child_order_minimum_volume_required is True
