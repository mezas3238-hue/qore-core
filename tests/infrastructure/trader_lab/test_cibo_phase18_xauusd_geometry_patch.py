from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_PATH = Path(__file__).parents[3] / "scripts" / "cibo_phase18_xauusd_geometry_patch.py"
_SPEC = importlib.util.spec_from_file_location("cibo_phase18_xauusd_geometry_patch", _PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("unable to load XAUUSD geometry patcher")
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
    ledger = "r34-5y-scaled-trades.jsonl"
    report = "r34-5y-validation-report.json"
"""


def test_xauusd_source_commit_is_frozen() -> None:
    assert patcher.SOURCE_CODE_GIT_SHA == "56ef138ee5ea1cde6d0bcf4c9e25e8b661c04e84"


def test_xauusd_patch_adds_geometry_only() -> None:
    patched = patcher.patch_r34_source(_minimal_source())
    assert "signal_at: str" in patched
    assert "entry_price: str" in patched
    assert "structural_stop: str" in patched
    assert "technical_target: str" in patched
    assert "signal_at=signal.cisd_at.isoformat()" in patched
    assert '"phase18-xauusd-r34-geometry-trades.jsonl"' in patched
    assert '"phase18-xauusd-r34-geometry-report.json"' in patched


def test_xauusd_patch_fails_closed_on_source_drift() -> None:
    with pytest.raises(ValueError, match="source drift"):
        patcher.patch_r34_source("unexpected source")
