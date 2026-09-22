from __future__ import annotations

import importlib.util
from pathlib import Path

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r35_confidence_tier_ensemble as r35,
)


def _builder():
    path = Path(__file__).parents[3] / "scripts" / "build_gbpjpy_r38_live_memory.py"
    spec = importlib.util.spec_from_file_location("gbpjpy_r38_live_memory_builder", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live_memory_source_binding_is_exact() -> None:
    builder = _builder()
    assert builder.SOURCE_RUN_ID == 35349300927
    assert builder.SOURCE_ARTIFACT_ID == 10549575964
    assert builder.SOURCE_OBSERVATIONS_SHA256 == (
        "6b3c7ecf75616ba6d428d23286ec2d9c525aca50ee090c687b9c91e9b2b63066"
    )
    assert builder.SELECTED_ENSEMBLE == "R35_RANGE_DIRECTION_MINIMAL_ROBUST"
    assert builder.SELECTED_POLICY == "CONFIDENCE_100_050_010"


def test_live_memory_layers_match_frozen_r35_candidate() -> None:
    builder = _builder()
    assert tuple(r35.ENSEMBLES[builder.SELECTED_ENSEMBLE]) == builder.EXPECTED_LAYERS
    assert builder.EXPECTED_LAYERS == (
        ("R34_RANGE_ROUTE_TYPES", (r35.ROBUST, r35.MAJORITY)),
        ("R34_DIRECTION_REGIME_ROUTE_TYPES", (r35.ROBUST, r35.MAJORITY)),
        ("R34_MINIMAL_ROUTE_TYPES", (r35.ROBUST,)),
    )
