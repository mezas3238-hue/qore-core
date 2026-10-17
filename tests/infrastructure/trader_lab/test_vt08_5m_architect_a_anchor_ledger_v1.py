"""Outcome-blind per-anchor density ledger regressions."""
from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab.vt08_5m_architect_a_anchor_ledger_v1 import (
    _event_id,
    summarize_rows,
)


def _row(event: str, day: str, hour: int, reason: str) -> dict[str, object]:
    return {
        "event_id": event,
        "ny_date": day,
        "anchor_ny_hour": hour,
        "first_failure": reason,
    }


def test_yearly_and_daily_reconciliation_no_pnl() -> None:
    rows = [
        _row("a", "2024-12-31", 1, "C2_CLOSE_NOT_INSIDE_REFERENCE"),
        _row("b", "2025-01-02", 1, "MECHANICAL_CANDIDATE"),
        _row("c", "2025-01-02", 5, "MECHANICAL_CANDIDATE"),
        _row("d", "2025-01-03", 9, "MECHANICAL_CANDIDATE"),
    ]
    report = summarize_rows(rows)
    assert report["observed_anchor_bars"] == 4
    assert report["mechanical_candidates"] == 3
    assert report["candidate_unique_ny_dates"] == 2
    assert report["daily_cardinality_ambiguous_candidates"] == 2
    assert report["one_per_day_selected_candidates"] == 1
    assert report["by_year_first_failure"]["2024"] == {
        "C2_CLOSE_NOT_INSIDE_REFERENCE": 1
    }
    assert report["by_year_first_failure"]["2025"] == {
        "MECHANICAL_CANDIDATE": 3
    }
    assert report["replay_fills_measured"] is False
    assert report["trade_pnl_used"] is False
    assert report["methodology_changed"] is False


def test_duplicate_causal_identity_fail_closed() -> None:
    row = _row("dup", "2025-01-02", 1, "MECHANICAL_CANDIDATE")
    with pytest.raises(ValueError, match="duplicate"):
        summarize_rows([row, deepcopy(row)])


def test_unrecognized_failure_and_hour_fail_closed() -> None:
    with pytest.raises(ValueError, match="approved ledger"):
        summarize_rows([_row("x", "2025-01-03", 1, "WINNER")])
    with pytest.raises(ValueError, match="approved ledger"):
        summarize_rows([_row("x", "2025-01-03", 13, "MECHANICAL_CANDIDATE")])


def test_event_identity_changes_with_asof_and_market() -> None:
    x = _event_id("EURJPY", "2025-01-03T06:00:00+00:00")
    assert len(x) == len("vt08-anchor:") + 64
    assert x == _event_id("EURJPY", "2025-01-03T06:00:00+00:00")
    assert x != _event_id("USDCHF", "2025-01-03T06:00:00+00:00")
    assert x != _event_id("EURJPY", "2025-01-03T10:00:00+00:00")
