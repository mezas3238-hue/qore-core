from datetime import UTC, datetime

import pytest

from scripts.cibo_phase22_eurusd_r38_window_replay import (
    FRESH_CLOSE,
    FRESH_OPEN,
    PARITY_CLOSE,
    PARITY_OPEN,
    SOURCE_CODE_GIT_SHA,
    replay_window,
)


def test_eurusd_phase22_source_and_windows_are_frozen() -> None:
    assert SOURCE_CODE_GIT_SHA == (
        "324fb91d44a6fa328e66de2e22ace7386630c7aa"
    )
    assert replay_window("PARITY") == (
        datetime(2021, 9, 17, tzinfo=UTC),
        datetime(2026, 9, 17, tzinfo=UTC),
    )
    assert replay_window("FRESH") == (
        datetime(2017, 1, 1, tzinfo=UTC),
        datetime(2017, 7, 1, tzinfo=UTC),
    )
    assert PARITY_OPEN < PARITY_CLOSE
    assert FRESH_OPEN < FRESH_CLOSE
    assert FRESH_CLOSE <= PARITY_OPEN


def test_eurusd_phase22_rejects_arbitrary_window_mode() -> None:
    with pytest.raises(ValueError, match="PARITY or FRESH"):
        replay_window("TUNED")
