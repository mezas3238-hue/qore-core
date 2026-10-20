from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2cj_rolling_cost_margin as r2cj,
)


def _row(market: str, at: str, gross: float) -> dict[str, object]:
    return {
        "market": market, "entry_opened_at": at,
        "source_opened_at": at, "c3_opened_at": at,
        "r_multiple": gross, "research_only": True,
    }


def test_cost_stress_no_trade_permission_and_exact_linear_friction() -> None:
    rows = (
        _row("AUDUSD", "2017-01-01T10:00:00+00:00", 1.5),
        _row("AUDUSD", "2017-01-02T10:00:00+00:00", -1.0),
        _row("AUDUSD", "2022-01-02T10:00:00+00:00", -1.0),
    )
    s = r2cj._stress("AUDUSD", rows)
    assert s["years"] == 10
    assert s["actual_trades"] == 3
    assert s["gross_and_cost_stress"]["COST_0R"]["total_r"] == -0.5
    assert s["gross_and_cost_stress"]["COST_0.02R"]["total_r"] == -0.56
    assert s["gross_and_cost_stress"]["COST_0.05R"]["total_r"] == -0.65
    assert s["independent_execution_fill_validated"] is False


def test_drawdown_and_profit_factor_recomputed_after_cost() -> None:
    stats = r2cj._stats((1.0, -0.5, -1.0, 2.0))
    assert stats["trades"] == 4
    assert stats["total_r"] == 1.5
    assert stats["profit_factor"] == 2.0
    assert stats["max_drawdown_r"] == 1.5


def test_original_archive_exact_trade_reconciliation(tmp_path: Path) -> None:
    row = _row("AUDUSD", "2018-05-10T01:00:00+00:00", 1.5)
    report = {
        "market": "AUDUSD", "identity": r2cj.AQ_ID,
        "base_competition_policy": r2cj.POLICY, "timing_lattice": "ROLLING_H4",
        "target_arm": r2cj.ARM,
        "full_window": {"trades": 1, "profit_factor": None, "total_r": 1.5},
        "annual": {
            "2017_2018": {"trades": 1, "profit_factor": None, "total_r": 1.5}
        },
    }
    out = r2cj._check_frozen("AUDUSD", "AQ", (row,), report)
    assert out["verified"]
    assert out["rows_count"] == 1
    bad = {**report, "full_window": {**report["full_window"], "total_r": 1.0}}
    with pytest.raises(ValueError, match="mismatch"):
        r2cj._check_frozen("AUDUSD", "AQ", (row,), bad)
    saved = tmp_path / "r2aq.jsonl"
    saved.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert len(r2cj._lines(saved)) == 1


def test_utc_timestamps_and_market_fail_closed() -> None:
    with pytest.raises(ValueError, match="Naive"):
        r2cj._time("2018-05-01T00:00:00")
    assert r2cj._time("2020-09-21T03:00:00+03:00") == datetime(
        2020, 9, 21, tzinfo=UTC
    )
    with pytest.raises(ValueError, match="Only AUDUSD and USDJPY"):
        r2cj.run_market(
            "BTCUSD", older_trades=Path("x"), older_report=Path("x"),
            recent_trades=Path("x"), recent_report=Path("x"),
        )


def test_same_source_year_window_splitting() -> None:
    rows = (
        _row("USDJPY", "2016-09-20T23:59:00+00:00", 1.5),
        _row("USDJPY", "2016-09-21T00:00:00+00:00", -1.0),
    )
    x = r2cj._stress("USDJPY", rows)
    annual = x["gross_and_cost_stress"]["COST_0R"]["annual"]
    assert annual["2015_2016"]["trades"] == 1
    assert annual["2016_2017"]["trades"] == 1
