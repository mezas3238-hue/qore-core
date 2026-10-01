import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

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


def test_source_volume_uses_frozen_cibo_contract_not_provider_lot_size() -> None:
    assert runner.source_minimum_volume(
        qore_symbol="EURUSD",
        min_native_volume=100000,
    ) == Decimal("0.01")
    assert runner.source_minimum_volume(
        qore_symbol="XAUUSD",
        min_native_volume=100,
    ) == Decimal("0.01")
    assert runner.source_minimum_volume(
        qore_symbol="NAS100",
        min_native_volume=10,
    ) == Decimal("0.01")


def test_pair_plan_balances_side_and_alternates_level_order() -> None:
    assert runner.pair_plan(1) == ("long", (1, 2))
    assert runner.pair_plan(2) == ("short", (2, 1))
    assert runner.pair_plan(3) == ("long", (1, 2))
    assert runner.pair_plan(4) == ("short", (2, 1))


def test_pair_plan_rejects_nonpositive_index() -> None:
    with pytest.raises(CiboCapitalManagementError, match="positive"):
        runner.pair_plan(0)


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
    freeze = runner.T11_NONLINEAR_INPUT_FREEZE.market_impact

    assert freeze.realized_settlement_cost_required is True
    assert freeze.deposit_asset_usd_required is True
    assert freeze.balanced_long_short_pairs_required is True
    assert freeze.alternating_level_order_required is True
    assert freeze.each_child_order_minimum_volume_required is True
