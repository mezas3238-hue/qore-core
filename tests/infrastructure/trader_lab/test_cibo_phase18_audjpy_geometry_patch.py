from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_PATCHER_PATH = (
    Path(__file__).parents[3]
    / "scripts"
    / "cibo_phase18_audjpy_geometry_patch.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "cibo_phase18_audjpy_geometry_patch",
    _PATCHER_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("unable to load AUDJPY geometry patcher")
patcher = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(patcher)


def _minimal_r40_source() -> str:
    return """class ScaledTrade:
    entry_at: str

def run():
    rows.append(
            ScaledTrade(
                entry_at=runtime.entry_at.isoformat(),
            )
        )
    ledger = "r40-5y-scaled-trades.jsonl"
    report = "r40-5y-validation-report.json"
"""


def test_audjpy_phase18_source_commit_is_immutable() -> None:
    assert patcher.SOURCE_CODE_GIT_SHA == (
        "a332b077598e070a42b2497b3766d55e731f7dca"
    )
    assert patcher.SOURCE_RELATIVE_PATH.endswith(
        "turtle_soup_audjpy_r40_frozen_r39_5y_validation.py"
    )


def test_patch_adds_geometry_without_changing_existing_trade_fields() -> None:
    patched = patcher.patch_r40_source(_minimal_r40_source())

    assert "signal_at: str" in patched
    assert "entry_price: str" in patched
    assert "structural_stop: str" in patched
    assert "technical_target: str" in patched
    assert "entry_at: str" in patched

    assert "signal_at=signal.cisd_at.isoformat()" in patched
    assert "entry_price=str(entry)" in patched
    assert "structural_stop=str(signal.protected_swing)" in patched
    assert "technical_target=str(decision.target.level)" in patched

    assert '"phase18-audjpy-r40-geometry-trades.jsonl"' in patched
    assert '"phase18-audjpy-r40-geometry-report.json"' in patched
    assert '"r40-5y-scaled-trades.jsonl"' not in patched
    assert '"r40-5y-validation-report.json"' not in patched


def test_patch_fails_closed_on_source_drift() -> None:
    with pytest.raises(ValueError, match="source drift"):
        patcher.patch_r40_source("unexpected source")
