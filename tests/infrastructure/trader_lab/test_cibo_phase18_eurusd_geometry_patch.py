from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_PATCHER_PATH = (
    Path(__file__).parents[3]
    / "scripts"
    / "cibo_phase18_eurusd_geometry_patch.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "cibo_phase18_eurusd_geometry_patch",
    _PATCHER_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("unable to load EURUSD geometry patcher")
patcher = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(patcher)


def _minimal_source() -> str:
    return """class ScaledTrade:
    entry_at: str

def run():
    rows.append(
            ScaledTrade(
                entry_at=runtime.entry_at.isoformat(),
            )
        )
    ledger = "r38-5y-corrected-trades.jsonl"
    report = "r38-5y-correction-report.json"
"""


def test_eurusd_source_commit_is_frozen() -> None:
    assert patcher.SOURCE_CODE_GIT_SHA == (
        "324fb91d44a6fa328e66de2e22ace7386630c7aa"
    )


def test_eurusd_patch_adds_geometry_only() -> None:
    patched = patcher.patch_r38_source(_minimal_source())
    assert "signal_at: str" in patched
    assert "entry_price: str" in patched
    assert "structural_stop: str" in patched
    assert "technical_target: str" in patched
    assert "signal_at=signal.cisd_at.isoformat()" in patched
    assert "entry_price=str(entry)" in patched
    assert "structural_stop=str(signal.protected_swing)" in patched
    assert "technical_target=str(decision.target.level)" in patched
    assert '"phase18-eurusd-r38-geometry-trades.jsonl"' in patched
    assert '"phase18-eurusd-r38-geometry-report.json"' in patched


def test_eurusd_patch_fails_closed_on_source_drift() -> None:
    with pytest.raises(ValueError, match="source drift"):
        patcher.patch_r38_source("unexpected source")
