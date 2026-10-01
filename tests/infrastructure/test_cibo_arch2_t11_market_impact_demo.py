from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


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


def test_adverse_price_to_usd_matches_usd_quote_contract_math() -> None:
    cost = runner.adverse_price_to_usd(
        side="long",
        bid=Decimal("1.10000"),
        ask=Decimal("1.10001"),
        fill_price=Decimal("1.10003"),
        filled_underlying_units=Decimal("1000"),
        quote_currency_to_usd=Decimal("1"),
    )

    assert cost == Decimal("0.02000")


def test_adverse_price_to_usd_converts_jpy_causally() -> None:
    cost = runner.adverse_price_to_usd(
        side="short",
        bid=Decimal("200.000"),
        ask=Decimal("200.003"),
        fill_price=Decimal("199.998"),
        filled_underlying_units=Decimal("1000"),
        quote_currency_to_usd=Decimal("0.00625"),
    )

    assert cost == Decimal("0.01250000")


def test_adverse_price_to_usd_never_turns_price_improvement_into_negative_cost() -> None:
    cost = runner.adverse_price_to_usd(
        side="long",
        bid=Decimal("100"),
        ask=Decimal("101"),
        fill_price=Decimal("100.5"),
        filled_underlying_units=Decimal("1"),
        quote_currency_to_usd=Decimal("1"),
    )

    assert cost == Decimal("0")


def test_adverse_price_to_usd_rejects_crossed_quote() -> None:
    with pytest.raises(CiboCapitalManagementError, match="quote is crossed"):
        runner.adverse_price_to_usd(
            side="long",
            bid=Decimal("2"),
            ask=Decimal("1"),
            fill_price=Decimal("1.5"),
            filled_underlying_units=Decimal("1"),
            quote_currency_to_usd=Decimal("1"),
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
