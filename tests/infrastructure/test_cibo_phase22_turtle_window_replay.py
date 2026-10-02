from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import ModuleType

import pytest

from scripts.cibo_phase22_turtle_window_replay import (
    CONFIGS,
    FRESH_CANDIDATE_ID,
    FRESH_CLOSE,
    FRESH_OPEN,
    PARITY_CLOSE,
    PARITY_OPEN,
    TurtleReplayConfig,
    bind_replay_evaluation_window,
    validate_source_report_window,
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
        _row(datetime(2015, 10, 20, 10, tzinfo=UTC)),
        _row(datetime(2016, 4, 18, 10, tzinfo=UTC)),
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
    assert FRESH_CANDIDATE_ID == (
        "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
    )
    assert FRESH_OPEN == datetime(2015, 10, 19, tzinfo=UTC)
    assert FRESH_CLOSE == datetime(2016, 4, 19, tzinfo=UTC)

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
        _row(datetime(2015, 10, 20, 11, tzinfo=UTC)),
        _row(datetime(2015, 10, 20, 10, tzinfo=UTC)),
    )

    with pytest.raises(ValueError, match="not chronological"):
        validate_window_rows(rows=rows, config=config, mode="FRESH")



def _fake_replay_module() -> tuple[ModuleType, ModuleType, ModuleType]:
    root = ModuleType("phase22_test_root")
    r1 = ModuleType("phase22_test_r1")
    r3 = ModuleType("phase22_test_r3")
    for item in (root, r1, r3):
        item.EVAL_OPEN = PARITY_OPEN
        item.EVAL_CLOSE = PARITY_CLOSE
    root.r1 = r1
    root.r3 = r3
    return root, r1, r3


def test_fresh_window_binding_reaches_subordinate_setup_builder_and_restores() -> None:
    root, r1, r3 = _fake_replay_module()

    with bind_replay_evaluation_window(
        root,
        start=FRESH_OPEN,
        end=FRESH_CLOSE,
    ) as surfaces:
        assert surfaces == ("module", "r1", "r3")
        for item in (root, r1, r3):
            assert item.EVAL_OPEN == FRESH_OPEN
            assert item.EVAL_CLOSE == FRESH_CLOSE

    for item in (root, r1, r3):
        assert item.EVAL_OPEN == PARITY_OPEN
        assert item.EVAL_CLOSE == PARITY_CLOSE


def test_fresh_window_binding_fails_closed_without_r3_setup_window() -> None:
    root = ModuleType("phase22_test_missing_r3")
    root.EVAL_OPEN = PARITY_OPEN
    root.EVAL_CLOSE = PARITY_CLOSE

    with pytest.raises(ValueError, match="root and r3"):
        with bind_replay_evaluation_window(
            root,
            start=FRESH_OPEN,
            end=FRESH_CLOSE,
        ):
            pass


def test_source_report_must_bind_exact_requested_window() -> None:
    validate_source_report_window(
        report={
            "window": {
                "open": FRESH_OPEN.isoformat(),
                "close": FRESH_CLOSE.isoformat(),
            }
        },
        start=FRESH_OPEN,
        end=FRESH_CLOSE,
    )

    with pytest.raises(ValueError, match="window drift"):
        validate_source_report_window(
            report={
                "window": {
                    "open": PARITY_OPEN.isoformat(),
                    "close": PARITY_CLOSE.isoformat(),
                }
            },
            start=FRESH_OPEN,
            end=FRESH_CLOSE,
        )
