from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType


def _load() -> ModuleType:
    path = Path("scripts/cibo_arch2_t16_demo_execution_calibration.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_arch2_t16_demo_execution_calibration",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Architect-2 T16 calibration")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


probe = _load()


def test_t16_cost_bound_uses_half_spread_per_execution_leg() -> None:
    quote = {"bid": "99", "ask": "101"}
    spread = probe._spread_bps(quote)
    assert spread == Decimal("200")
    assert spread / Decimal(2) == Decimal("100")


def test_t16_signed_slippage_is_adverse_positive_for_both_sides() -> None:
    quote = {"bid": "99", "ask": "101"}
    buy = probe._signed_slippage_bps(
        side=probe._BUY,
        quote=quote,
        fill_price=Decimal("102"),
    )
    sell = probe._signed_slippage_bps(
        side=probe._SELL,
        quote=quote,
        fill_price=Decimal("98"),
    )
    assert buy > 0
    assert sell > 0


def test_t16_zero_slippage_at_touch() -> None:
    quote = {"bid": "99", "ask": "101"}
    assert probe._signed_slippage_bps(
        side=probe._BUY,
        quote=quote,
        fill_price=Decimal("101"),
    ) == 0
    assert probe._signed_slippage_bps(
        side=probe._SELL,
        quote=quote,
        fill_price=Decimal("99"),
    ) == 0
