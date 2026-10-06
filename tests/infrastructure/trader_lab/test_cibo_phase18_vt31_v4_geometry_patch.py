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

_REARM_PATCHER_PATH = (
    Path(__file__).parents[3]
    / "scripts"
    / "cibo_phase18_vt31_rearm_geometry_patch.py"
)
_REARM_SPEC = importlib.util.spec_from_file_location(
    "cibo_phase18_vt31_rearm_geometry_patch",
    _REARM_PATCHER_PATH,
)
if _REARM_SPEC is None or _REARM_SPEC.loader is None:
    raise RuntimeError("unable to load VT31 rearm geometry patcher")
rearm_patcher = importlib.util.module_from_spec(_REARM_SPEC)
_REARM_SPEC.loader.exec_module(rearm_patcher)


def _minimal_source() -> str:
    return """    adjusted, binding_diag = physical._physicalize(rows, by_day=by_day)
    selected = [
        row for row in adjusted
        if START_DATE
        <= date.fromisoformat(cast(str, row["local_date"]))
        < END_EXCLUSIVE_DATE
    ]
    metrics = _metrics(selected)
    payload = {
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
    assert '"trade_rows": phase18_trade_rows' in patched
    assert 'getattr(residual.corrective, "_PHASE18_REARM_GEOMETRY", {})' in patched
    assert "phase18_adjusted = []" in patched
    assert "authoritative_rows = []" not in patched
    assert 'authoritative_row.pop("entry")' not in patched
    assert '"trade_count": len(selected)' in patched
    assert '"metrics": metrics' in patched


def test_vt31_patch_fails_closed_on_source_drift() -> None:
    with pytest.raises(ValueError, match="source drift"):
        patcher.patch_source("unexpected source")


def _minimal_rearm_source() -> str:
    return """    policy = Vt31R22ExecutionPolicy()
    raw_rows: list[dict[str, object]] = []
        row.update(
            {
                "local_date": local_day.isoformat(),
                "used_for_runtime_decision": False,
            }
        )
        raw_rows.append(row)
"""


def test_vt31_rearm_source_commit_is_frozen() -> None:
    assert rearm_patcher.SOURCE_CODE_GIT_SHA == (
        "cac38ed14f20e066536910145027426fd23f5939"
    )


def test_vt31_rearm_patch_captures_geometry_without_mutating_row() -> None:
    patched = rearm_patcher.patch_source(_minimal_rearm_source())
    assert "global _PHASE18_REARM_GEOMETRY" in patched
    assert "_PHASE18_REARM_GEOMETRY = {}" in patched
    assert 'format(setup.entry_price, "f")' in patched
    assert 'format(setup.stop_price, "f")' in patched
    assert 'format(setup.target_price, "f")' in patched
    assert '"_phase18_rearm_geometry_instrumented"' not in patched
    assert '"entry": format(setup.entry_price, "f")' not in patched
    assert '"initial_stop": format(setup.stop_price, "f")' not in patched
    assert '"structural_target": format(setup.target_price, "f")' not in patched


def test_vt31_rearm_patch_fails_closed_on_source_drift() -> None:
    with pytest.raises(ValueError, match="source drift"):
        rearm_patcher.patch_source("unexpected source")
