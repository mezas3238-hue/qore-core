from __future__ import annotations

import importlib.util
from pathlib import Path

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r32_causal_memory_defragmentation as r32,
)

_SPEC = importlib.util.spec_from_file_location(
    "build_gbpusd_r43_live_memory",
    Path("scripts/build_gbpusd_r43_live_memory.py"),
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(builder)


def test_live_memory_source_binding_is_exact() -> None:
    assert builder.SOURCE_RUN_ID == 35339237432
    assert builder.SOURCE_ARTIFACT_ID == 10544098544
    assert builder.SCHEME == "R32_REGIME_ROUTE_TYPES"
    assert builder.SOURCE_OBSERVATIONS_SHA256 == (
        "cc9176146a6d20b27ae8c55d0ec807156c7de3a82f651a9c2bca308d733b719c"
    )


def test_live_memory_scheme_is_frozen() -> None:
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
