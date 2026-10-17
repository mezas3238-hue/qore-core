from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2cf_strict_nested_wait_journal as r2cf,
)
from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureReasoningAction as Action,
)


def _start(year: int) -> datetime:
    return datetime(year, 9, 21, tzinfo=UTC)


@dataclass(frozen=True)
class _Record:
    key: str
    year: int


def _slice(
    records: tuple[_Record, ...], start: datetime, end: datetime
) -> tuple[_Record, ...]:
    return tuple(row for row in records if start <= _start(row.year) < end)


def _fit(records: tuple[_Record, ...]) -> tuple[set[str], dict[str, Any]]:
    return {row.key for row in records}, {"fit_count": len(records)}


def _decide(model: set[str], row: _Record) -> SimpleNamespace:
    # Mark WAIT only after there is at least one prior record in fitted model.
    return SimpleNamespace(action=Action.WAIT if model else Action.ABSTAIN)


def test_nested_inner_warmup_requires_full_four_years() -> None:
    assert r2cf._inner_fit_span(2014, earliest_year=2011, year_start=_start) is None
    assert r2cf._inner_fit_span(2015, earliest_year=2011, year_start=_start) == (
        _start(2011), _start(2015)
    )


def test_prior_only_nested_history_excludes_warmup_rows() -> None:
    rows = tuple(_Record(str(y), y) for y in range(2011, 2019))
    actions, meta = r2cf._nested_membership(
        rows,
        start=_start(2011),
        end=_start(2019),
        year_start=_start,
        slice_records=_slice,
        initial_fit=_fit,
        initial_decision=_decide,
        record_key=lambda row: row.key,
    )
    assert len(actions) == 4
    assert set(actions) == {"2015", "2016", "2017", "2018"}
    assert all(action is Action.WAIT for action in actions.values())
    assert meta[2014]["status"] == "INSUFFICIENT_FOUR_YEAR_WARMUP"
    assert meta[2015]["training_start"] == _start(2011).isoformat()
    assert meta[2015]["training_end_exclusive"] == meta[2015]["observed_start"]


def test_nested_training_cohort_preserves_support_and_terminal_accounting() -> None:
    rows = (_Record("missing", 2013), _Record("w", 2016), _Record("t", 2016))
    actions = {"w": Action.WAIT, "t": Action.WAIT}
    delayed = {
        "w": SimpleNamespace(delayed_trade=object()),
        "t": SimpleNamespace(delayed_trade=None),
    }
    eligible, diagnostics = r2cf._nested_cohort(
        rows, actions=actions, delayed_by_key=delayed, record_key=lambda row: row.key
    )
    assert len(eligible) == 1
    assert diagnostics == {
        "WAIT": 2,
        "WAIT_TERMINAL": 1,
        "WAIT_VIABLE": 1,
        "WARMUP_EXCLUDED": 1,
    }


def test_only_frozen_markets_and_no_sizing() -> None:
    assert r2cf.ARMS == ("CONTROL_ALL", "STRICT_NESTED_WAIT_4Y")
    assert r2cf.INNER_YEARS == 4
    assert r2cf.MIN_DENSITY_PER_YEAR == 170.0
