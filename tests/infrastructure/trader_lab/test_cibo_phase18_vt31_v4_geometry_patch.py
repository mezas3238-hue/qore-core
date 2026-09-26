from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_PATCHER_PATH = (
    Path(__file__).parents[3]
    / "scripts"
    / "cibo_phase18_vt31_v4_geometry_patch.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "cibo_phase18_vt31_v4_geometry_patch",
    _PATCHER_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("unable to load VT31 V4 geometry patcher")
patcher = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(patcher)


def _minimal_source() -> str:
    return """payload = {
        "five_year_result": {
            "trade_count": len(selected),
            "metrics": metrics,
        }
    }
"""


def test_vt31_source_commit_is_frozen() -> None:
    assert patcher.SOURCE_CODE_GIT_SHA == (
        "cac38ed14f20e066536910145027426fd23f5939"
    )


def test_vt31_patch_serializes_selected_rows_only() -> None:
    patched = patcher.patch_source(_minimal_source())
    assert '"trade_rows": selected' in patched
    assert '"trade_count": len(selected)' in patched
    assert '"metrics": metrics' in patched


def test_vt31_patch_fails_closed_on_source_drift() -> None:
    with pytest.raises(ValueError, match="source drift"):
        patcher.patch_source("unexpected source")
