from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    capitalizer_drawdown_chronology_semantics_audit_v1 as audit,
)


@dataclass(frozen=True)
class _FakeTrade:
    symbol: str
    entry_at: str
    exit_at: str
    realized_gross_r: str


def test_exit_batches_are_atomic() -> None:
    rows = cast(
        Any,
        (
            _FakeTrade(
                symbol="A",
                entry_at="2026-01-01T00:00:00+00:00",
                exit_at="2026-01-01T00:10:00+00:00",
                realized_gross_r="1",
            ),
            _FakeTrade(
                symbol="B",
                entry_at="2026-01-01T00:01:00+00:00",
                exit_at="2026-01-01T00:10:00+00:00",
                realized_gross_r="-2",
            ),
            _FakeTrade(
                symbol="C",
                entry_at="2026-01-01T00:02:00+00:00",
                exit_at="2026-01-01T00:20:00+00:00",
                realized_gross_r="2",
            ),
        ),
    )

    result = audit._exit_batch_metrics(rows)

    assert result["total_r"] == "1"
    assert result["max_drawdown_r"] == "1"
    assert result["exit_batches"] == 2
    assert result["max_simultaneous_exit_batch"] == 2
    assert audit._max_concurrent(rows) == 3


def test_rank_diagnostic_detects_exit_reordering() -> None:
    rows = cast(
        Any,
        (
            _FakeTrade(
                symbol="A",
                entry_at="2026-01-01T00:00:00+00:00",
                exit_at="2026-01-01T00:20:00+00:00",
                realized_gross_r="1",
            ),
            _FakeTrade(
                symbol="B",
                entry_at="2026-01-01T00:01:00+00:00",
                exit_at="2026-01-01T00:10:00+00:00",
                realized_gross_r="-1",
            ),
        ),
    )

    changed, mean_shift, max_shift = audit._rank_diagnostics(rows)

    assert changed == 2
    assert str(mean_shift) == "1"
    assert max_shift == 1


def test_chronology_audit_contract() -> None:
    assert audit.IDENTITY == (
        "QORE_CAPITALIZER_DRAWDOWN_CHRONOLOGY_SEMANTICS_AUDIT_V1"
    )
