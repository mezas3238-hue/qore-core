from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from qore.infrastructure.trader_lab.first_cohort_failure_analysis import (
    FirstCohortFailureAnalysisError,
    run_failure_analysis,
)
from qore.infrastructure.trader_lab.first_cohort_failure_analysis_aggregate import (
    run_failure_analysis_aggregate,
)

_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")


def _trade(index: int, *, side: str = "long", return_rate: str = "-0.001") -> dict[str, object]:
    hour = index % 20
    return {
        "trader_code": "unused",
        "signal_at": f"2026-01-{index + 1:02d}T{hour:02d}:00:00+00:00",
        "filled_at": f"2026-01-{index + 1:02d}T{hour:02d}:05:00+00:00",
        "exited_at": f"2026-01-{index + 1:02d}T{hour:02d}:10:00+00:00",
        "side": side,
        "entry_price": "1",
        "stop_loss": "0.99",
        "take_profit": "1.01",
        "exit_price": "0.999",
        "return_rate": return_rate,
        "exit_reason": "stop",
    }


def _metric(sample: int, mean: str, win: str) -> dict[str, object]:
    return {
        "sample_size": sample,
        "mean_return": mean,
        "win_rate": win,
        "population_variance": "0.000001",
    }


def _assessment(
    code: str,
    *,
    value: int = 2,
    oos_pass: bool,
    stress_pass: bool,
) -> dict[str, object]:
    parameter_name = {
        "vt-01": "sweep_strength",
        "vt-08": "range_length",
        "vt-09": "swing_strength",
        "vt-31": "sweep_strength",
    }.get(code)
    return {
        "parameters": {} if parameter_name is None else {parameter_name: value},
        "config_fingerprint": f"cfg-{code}-{value}",
        "in_sample": _metric(40, "0.001", "0.60"),
        "in_sample_pass": True,
        "oos": _metric(12, "-0.001", "0.20"),
        "oos_pass": oos_pass,
        "stressed_oos": _metric(12, "-0.0012", "0.10"),
        "stress_pass": stress_pass,
    }


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    backtest_results: list[dict[str, object]] = []
    walk_results: list[dict[str, object]] = []
    for code in _CODES:
        trades = [_trade(index) for index in range(10)]
        for trade in trades:
            trade["trader_code"] = code
        backtest_results.append(
            {
                "trader_code": code,
                "execution_period": "M5",
                "setup_count": 30,
                "unfilled_setup_count": 20,
                "sample_size": 10,
                "mean_return": "-0.001",
                "win_rate": "0.20",
                "population_variance": "0.000001",
                "trades": trades,
            }
        )
        assessment = _assessment(code, oos_pass=False, stress_pass=False)
        assessments = [assessment]
        if code != "vt-17":
            assessments.append(
                {
                    **_assessment(
                        code,
                        value=3,
                        oos_pass=False,
                        stress_pass=False,
                    ),
                    "in_sample_pass": False,
                }
            )
        walk_results.append(
            {
                "trader_code": code,
                "assessed_configurations": len(assessments),
                "selected": assessment,
                "assessments": assessments,
            }
        )
    backtest = {
        "schema": "qore.trader_lab.first_cohort_backtest.v1",
        "environment": "demo",
        "read_only": True,
        "account_fingerprint": "a" * 64,
        "software_sha": "b" * 40,
        "symbol": "EURUSD",
        "checked_at": "2026-09-01T00:00:00+00:00",
        "execution_model": "limit-3bar-fill-24bar-hold-stop-first-v1",
        "results": backtest_results,
    }
    walk = {
        "schema": "qore.trader_lab.first_cohort_walk_forward.v2",
        "environment": "demo",
        "read_only": True,
        "account_fingerprint": "a" * 64,
        "software_sha": "b" * 40,
        "symbol": "EURUSD",
        "checked_at": "2026-09-01T00:00:00+00:00",
        "split_at": "2026-05-01T00:00:00+00:00",
        "results": walk_results,
    }
    backtest_path = tmp_path / "backtest.json"
    walk_path = tmp_path / "walk.json"
    backtest_path.write_text(json.dumps(backtest), encoding="utf-8")
    walk_path.write_text(json.dumps(walk), encoding="utf-8")
    return backtest_path, walk_path


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _list(value: object) -> list[object]:
    assert isinstance(value, list)
    return cast(list[object], value)


def test_failure_analysis_records_causal_signals_and_holdout_governance(tmp_path: Path) -> None:
    backtest_path, walk_path = _write_inputs(tmp_path)

    payload = run_failure_analysis(backtest_path, walk_path)

    assert payload["schema"] == "qore.trader_lab.first_cohort_failure_analysis.v1"
    governance = _dict(payload["holdout_governance"])
    assert governance["post_change_reuse_as_independent_holdout_prohibited"] is True
    first = _dict(_list(payload["results"])[0])
    assert first["trader_code"] == "vt-01"
    assert first["failure_stage"] == "oos"
    signals = set(cast(list[str], first["diagnostic_signals"]))
    assert signals >= {
        "sparse_activity",
        "poor_fill_conversion",
        "negative_expectancy",
        "low_hit_rate",
        "oos_collapse",
        "exit_stop_dominance",
    }
    assert "parameter_instability" in signals
    default = _dict(first["default_configuration"])
    assert default["max_losing_streak"] == 10
    assert default["exit_reason_counts"] == {"stop": 10}
    surface = _dict(first["parameter_surface"])
    robustness = _dict(surface["robustness"])
    assert robustness["classification"] == "narrow_optimum"


def test_failure_analysis_requires_v2_surface(tmp_path: Path) -> None:
    backtest_path, walk_path = _write_inputs(tmp_path)
    walk = cast(dict[str, object], json.loads(walk_path.read_text(encoding="utf-8")))
    walk["schema"] = "qore.trader_lab.first_cohort_walk_forward.v1"
    walk_path.write_text(json.dumps(walk), encoding="utf-8")

    with pytest.raises(FirstCohortFailureAnalysisError, match="walk-forward v2"):
        run_failure_analysis(backtest_path, walk_path)


def test_failure_analysis_aggregate_counts_recurring_cross_market_signals(tmp_path: Path) -> None:
    backtest_path, walk_path = _write_inputs(tmp_path)
    analyses: list[Path] = []
    symbols = ("AUDUSD", "EURUSD", "GBPUSD", "USDCAD", "USDJPY", "XAUUSD")
    for symbol in symbols:
        backtest = cast(
            dict[str, object], json.loads(backtest_path.read_text(encoding="utf-8"))
        )
        walk = cast(dict[str, object], json.loads(walk_path.read_text(encoding="utf-8")))
        backtest["symbol"] = symbol
        walk["symbol"] = symbol
        bp = tmp_path / f"{symbol}-backtest.json"
        wp = tmp_path / f"{symbol}-walk.json"
        bp.write_text(json.dumps(backtest), encoding="utf-8")
        wp.write_text(json.dumps(walk), encoding="utf-8")
        analysis = run_failure_analysis(bp, wp)
        ap = tmp_path / f"{symbol}-analysis.json"
        ap.write_text(json.dumps(analysis), encoding="utf-8")
        analyses.append(ap)

    multi: dict[str, object] = {
        "schema": "qore.trader_lab.first_cohort_multi_pair_walk_forward.v1",
        "account_fingerprint": "a" * 64,
        "software_sha": "b" * 40,
        "results": [
            {
                "trader_code": code,
                "robust_pass": False,
                "pooled_in_sample": _metric(100, "0.001", "0.60"),
                "pooled_oos": _metric(40, "-0.001", "0.20"),
                "pooled_stressed_oos": _metric(40, "-0.0012", "0.10"),
                "oos_pair_pass_count": 0,
                "stress_pair_pass_count": 0,
            }
            for code in _CODES
        ],
    }
    multi_path = tmp_path / "multi.json"
    multi_path.write_text(json.dumps(multi), encoding="utf-8")

    payload = run_failure_analysis_aggregate(multi_path, tuple(analyses))

    assert payload["instrument_count"] == 6
    first = _dict(_list(payload["results"])[0])
    assert first["research_disposition"] == "failure_analysis_required"
    counts = _dict(first["diagnostic_signal_counts"])
    assert counts["oos_collapse"] == 6
    assert "oos_collapse" in cast(list[str], first["recurring_signals"])
