from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2ck_timing_attribution as r2ck,
)


def _row(label: str, year: int, r: float) -> dict[str, object]:
    return {
        "timing_triplet": label,
        "entry_opened_at": datetime(year, 10, 1, tzinfo=UTC).isoformat(),
        "r_multiple": r,
    }


def test_reconciled_six_frozen_labels_and_positive_year_diagnostics() -> None:
    records = tuple(
        _row(label, 2020, 1.5) for label in r2ck.SIX_STARTS
    ) + (_row("ROLLING_H4:1", 2021, -1),)
    x = r2ck._by_lattice(records, years=3, start_year=2020)
    assert x["reconciled"] is True
    assert x["all_six_labels_present"] is True
    assert x["all_starts"]["count"] == 7
    assert x["all_starts"]["gross"]["total_r"] == 8.0
    assert x["six_frozen_starts"]["ROLLING_H4:1"]["count"] == 2


def test_mislabelled_h4_start_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unexpected rolling-H4 timing labels"):
        r2ck._by_lattice(
            (_row("M15:FAKE", 2021, 1.0),), years=1, start_year=2021
        )


def test_market_start_hours_are_fixed_not_posthoc() -> None:
    assert r2ck.START_HOUR_NY == {
        "ROLLING_H4:1": 1, "ROLLING_H4:2": 5, "ROLLING_H4:3": 9,
        "ROLLING_H4:4": 13, "ROLLING_H4:5": 17, "ROLLING_H4:6": 21,
    }
    assert r2ck.STRESS_COST_R == 0.02


def test_empty_yearly_bucket_does_not_create_false_trade() -> None:
    empty = r2ck._bucket((), years=2, from_year=2020)
    assert empty["count"] == 0
    assert empty["gross"]["profit_factor"] is None
    assert empty["cost_0.02R"]["total_r"] == 0.0
