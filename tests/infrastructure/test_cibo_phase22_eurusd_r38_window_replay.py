from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import pytest

_ADAPTER_PATH = (
    Path(__file__).parents[2]
    / "scripts"
    / "cibo_phase22_eurusd_r38_window_replay.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "cibo_phase22_eurusd_r38_window_replay",
    _ADAPTER_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("unable to load EURUSD Phase22 replay adapter")
adapter = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(adapter)


def test_eurusd_phase22_source_and_windows_are_frozen() -> None:
    assert adapter.SOURCE_CODE_GIT_SHA == (
        "324fb91d44a6fa328e66de2e22ace7386630c7aa"
    )
    assert adapter.replay_window("PARITY") == (
        datetime(2021, 9, 17, tzinfo=UTC),
        datetime(2026, 9, 17, tzinfo=UTC),
    )
    assert adapter.replay_window("FRESH") == (
        datetime(2017, 1, 1, tzinfo=UTC),
        datetime(2017, 7, 1, tzinfo=UTC),
    )
    assert adapter.PARITY_OPEN < adapter.PARITY_CLOSE
    assert adapter.FRESH_OPEN < adapter.FRESH_CLOSE
    assert adapter.FRESH_CLOSE <= adapter.PARITY_OPEN


def test_eurusd_phase22_rejects_arbitrary_window_mode() -> None:
    with pytest.raises(ValueError, match="PARITY or FRESH"):
        adapter.replay_window("TUNED")
