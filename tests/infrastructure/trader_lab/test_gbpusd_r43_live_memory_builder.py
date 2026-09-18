from __future__ import annotations

import importlib.util
from pathlib import Path

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r32_causal_memory_defragmentation as r32,
)


def _builder():
    path = Path(__file__).parents[3] / "scripts" / "build_gbpusd_r43_live_memory.py"
    spec = importlib.util.spec_from_file_location("gbpusd_r43_live_memory_builder", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live_memory_source_binding_is_exact() -> None:
    builder = _builder()
    assert builder.SOURCE_RUN_ID == 35339237432
    assert builder.SOURCE_ARTIFACT_ID == 10544098544
    assert builder.SCHEME == "R32_REGIME_ROUTE_TYPES"
    assert builder.SOURCE_OBSERVATIONS_SHA256 == (
        "cc9176146a6d20b27ae8c55d0ec807156c7de3a82f651a9c2bca308d733b719c"
    )


def test_live_memory_scheme_is_frozen() -> None:
    builder = _builder()
    fields, route_mode = r32.SCHEMES[builder.SCHEME]
    assert route_mode == "TYPES_ONLY"
    assert fields == (
        "timeframe",
        "prior_body_alignment",
        "protected_risk_range_bucket",
        "h4_range_state",
        "d1_range_state",
        "m5_volatility_state",
    )
