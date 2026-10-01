from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType


def _load_probe_module() -> ModuleType:
    path = Path("scripts/cibo_t16_ctrader_demo_post_declaration_probe.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_t16_ctrader_demo_post_declaration_probe",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load T16 post-declaration probe")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


probe = _load_probe_module()


def test_t16_probe_canonicalizes_decimal_without_promoting_costs() -> None:
    payload = probe._canonical(
        {
            "spread_bps": Decimal("1.2500"),
            "realized_slippage_observed": False,
            "full_hedge_cost_model_ready": False,
        }
    )

    assert payload == {
        "full_hedge_cost_model_ready": False,
        "realized_slippage_observed": False,
        "spread_bps": "1.2500",
    }
    assert probe._digest(payload).startswith("sha256:")
