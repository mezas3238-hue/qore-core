from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from scripts.cibo_phase22_turtle_window_replay import (
    CONFIGS,
    FRESH_CLOSE,
    FRESH_OPEN,
    TurtleReplayConfig,
    validate_window_rows,
)


def _row(at: datetime) -> dict[str, str]:
    return {
        "signal_at": at.isoformat(),
        "entry_at": (at + timedelta(minutes=5)).isoformat(),
        "exit_at": (at + timedelta(hours=1)).isoformat(),
        "side": "long",
    }


def test_fresh_rows_are_window_and_causality_checked() -> None:
    config = CONFIGS["GBPJPY_R38"]
    rows = (
        _row(datetime(2017, 1, 3, 10, tzinfo=UTC)),
        _row(datetime(2017, 6, 30, 10, tzinfo=UTC)),
    )

    validate_window_rows(rows=rows, config=config, mode="FRESH")


def test_fresh_row_outside_window_fails_closed() -> None:
    config = CONFIGS["GBPUSD_R43"]
    with pytest.raises(ValueError, match="outside FRESH window"):
        validate_window_rows(
            rows=(_row(FRESH_CLOSE),),
            config=config,
            mode="FRESH",
        )


def test_parity_population_is_exact() -> None:
    config = TurtleReplayConfig(
        trader_id="TEST",
        expected_parity_rows=2,
        geometry_filename="trades.jsonl",
        symbol="TEST",
    )
    rows = (
        _row(datetime(2021, 9, 17, 1, tzinfo=UTC)),
        _row(datetime(2021, 9, 17, 2, tzinfo=UTC)),
    )
    validate_window_rows(rows=rows, config=config, mode="PARITY")

    with pytest.raises(ValueError, match="parity population drift"):
        validate_window_rows(rows=rows[:1], config=config, mode="PARITY")


def test_fresh_window_is_exact_six_month_candidate() -> None:
    assert FRESH_OPEN == datetime(2017, 1, 1, tzinfo=UTC)
    assert FRESH_CLOSE == datetime(2017, 7, 1, tzinfo=UTC)

def test_parity_preserves_frozen_nonchronological_serialization() -> None:
    config = TurtleReplayConfig(
        trader_id="TEST",
        expected_parity_rows=2,
        geometry_filename="trades.jsonl",
        symbol="TEST",
    )
    rows = (
        _row(datetime(2021, 9, 17, 2, tzinfo=UTC)),
        _row(datetime(2021, 9, 17, 1, tzinfo=UTC)),
    )

    validate_window_rows(rows=rows, config=config, mode="PARITY")


def test_fresh_rejects_nonchronological_serialization() -> None:
    config = CONFIGS["AUDJPY_R42"]
    rows = (
        _row(datetime(2017, 1, 3, 11, tzinfo=UTC)),
        _row(datetime(2017, 1, 3, 10, tzinfo=UTC)),
    )

    with pytest.raises(ValueError, match="not chronological"):
        validate_window_rows(rows=rows, config=config, mode="FRESH")

