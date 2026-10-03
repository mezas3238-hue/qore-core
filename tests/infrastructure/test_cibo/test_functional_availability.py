from __future__ import annotations

import pytest

from qore.infrastructure.cibo.functional_availability import (
    cibo_function_availability,
    CiboFunctionAvailabilityState,
)
from qore.infrastructure.trader_lab import cibo_functional_receipt


_MARKETS = (
    "EURUSD",
    "BTCUSD",
    "USDCAD",
    "EURAUD",
    "XAUUSD",
    "NAS100",
    "ETHUSD",
    "BTC/USD",
    "ZZZXYZ",
)

_POPULATIONS = (
    "used-holdout",
    "fresh-oos",
    "replay",
    "development",
    "stress",
    "custom-research-v9",
)


@pytest.mark.parametrize("market_symbol", _MARKETS)
@pytest.mark.parametrize("population", _POPULATIONS)
def test_every_cibo_capability_is_permanently_available_for_any_scope(
    market_symbol: str,
    population: str,
) -> None:
    for function in cibo_functional_receipt.CIBO_TRADER_LAB_FUNCTION_SEQUENCE:
        availability = cibo_function_availability(
            function,
            market_symbol=market_symbol,
            population=population,
        )
        assert availability.state is CiboFunctionAvailabilityState.UNLOCKED
        assert availability.scope.market_symbol == market_symbol
        assert availability.scope.population == population


def test_universal_availability_includes_functions_compound_and_portfolio() -> None:
    values = tuple(item.value for item in cibo_functional_receipt.CIBO_TRADER_LAB_FUNCTION_SEQUENCE)
    assert values[0].startswith("cf01.")
    assert any(value.startswith("cf20.") for value in values)
    assert any(value.startswith("cc01.") for value in values)
    assert any(value.startswith("cc16.") for value in values)
    assert values[-1].startswith("pc01.")
