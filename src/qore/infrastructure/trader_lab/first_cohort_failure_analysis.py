"""Deterministic failure analysis for one first-cohort Trader Lab instrument.

The analyzer consumes already-produced backtest and walk-forward evidence. It
never changes a Trader, ranks a new candidate, or grants execution authority.
Its purpose is to explain observed failure modes and formulate falsifiable
research hypotheses for a later, separately pre-registered cycle.

Because this analysis reads OOS evidence, any hypothesis derived from it makes
that OOS unsuitable as an independent post-change holdout. A modified strategy
must be validated on fresh, previously unseen evidence.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.first_cohort_backtest import FirstCohortBacktestError

_SCHEMA = "qore.trader_lab.first_cohort_failure_analysis.v1"
_WALK_FORWARD_SCHEMA = "qore.trader_lab.first_cohort_walk_forward.v2"
_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
_MIN_WIN_RATE = Decimal("0.50")
_SPARSE_SAMPLE = 20
_HIGH_UNFILLED_RATE = Decimal("0.50")


class FirstCohortFailureAnalysisError(FirstCohortBacktestError):
    __slots__ = ()


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise FirstCohortFailureAnalysisError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise FirstCohortFailureAnalysisError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise FirstCohortFailureAnalysisError(f"{name} must be a non-empty string")
    return value


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int or value < 0:
        raise FirstCohortFailureAnalysisError(f"{name} must be a non-negative int")
    return value


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise FirstCohortFailureAnalysisError(f"{name} must be bool")
    return value


def _decimal(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        result = Decimal(raw)
    except InvalidOperation as error:
        raise FirstCohortFailureAnalysisError(f"{name} must be decimal") from error
    if not result.is_finite():
        raise FirstCohortFailureAnalysisError(f"{name} must be finite")
    return result


def _read(path: Path, *, name: str) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortFailureAnalysisError(f"cannot read {name}") from error
    return _object(decoded, name=name)


def _metric_payload(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {
            "sample_size": 0,
            "mean_return": "0",
            "win_rate": "0",
            "best_return": "0",
            "worst_return": "0",
        }
    values = tuple(_decimal(item.get("return_rate"), name="trade return_rate") for item in rows)
    size = Decimal(len(values))
    mean = sum(values, Decimal(0)) / size
    wins = Decimal(sum(value > 0 for value in values)) / size
    return {
        "sample_size": len(values),
        "mean_return": format(mean, "f"),
        "win_rate": format(wins, "f"),
        "best_return": format(max(values), "f"),
        "worst_return": format(min(values), "f"),
    }


def _max_losing_streak(rows: list[dict[str, object]]) -> int:
    maximum = 0
    current = 0
    for row in rows:
        if _decimal(row.get("return_rate"), name="trade return_rate") <= 0:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def _temporal_quartiles(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    if not rows:
        return []
    ordered = sorted(rows, key=lambda item: _text(item.get("signal_at"), name="signal_at"))
    result: list[dict[str, object]] = []
    for index in range(4):
        start = (len(ordered) * index) // 4
        end = (len(ordered) * (index + 1)) // 4
        chunk = ordered[start:end]
        if not chunk:
            continue
        metrics = _metric_payload(chunk)
        metrics["quartile"] = index + 1
        metrics["first_signal_at"] = _text(chunk[0].get("signal_at"), name="signal_at")
        metrics["last_signal_at"] = _text(chunk[-1].get("signal_at"), name="signal_at")
        result.append(metrics)
    return result


def _selected_stage(selected: dict[str, object] | None) -> str:
    if selected is None:
        return "in_sample"
    if not _boolean(selected.get("oos_pass"), name="selected oos_pass"):
        return "oos"
    if not _boolean(selected.get("stress_pass"), name="selected stress_pass"):
        return "stress"
    return "per_instrument_screen_pass"


def _hypothesis(signal: str) -> dict[str, str]:
    mapping = {
        "sparse_activity": (
            "Signal preconditions may be too restrictive for this instrument.",
            "A pre-registered structure-preserving trigger change should increase sample size "
            "without degrading mean return on a fresh holdout.",
        ),
        "poor_fill_conversion": (
            "Entry geometry may be incompatible with the three-bar LIMIT validity window.",
            "A pre-registered entry-validity or limit-geometry variant should improve fill "
            "conversion while preserving OOS expectancy on fresh data.",
        ),
        "negative_expectancy": (
            "The observed setup/exit geometry does not produce positive average payoff.",
            "A structural filter targeting the dominant losing condition should make mean "
            "return non-negative on a new holdout without reducing sample below policy.",
        ),
        "low_hit_rate": (
            "Signal precision is below the current economic policy threshold.",
            "A pre-registered regime or session filter should increase win rate on fresh data "
            "without creating a single-parameter brittle optimum.",
        ),
        "parameter_instability": (
            "Any apparent edge may be concentrated in a narrow parameter point.",
            "A robust change should create a neighboring parameter plateau rather than one "
            "isolated passing configuration on fresh evidence.",
        ),
        "oos_collapse": (
            "In-sample qualification did not generalize to the untouched OOS partition.",
            "The revised hypothesis should survive multiple pre-registered temporal folds and "
            "a new final holdout before promotion is reconsidered.",
        ),
        "stress_fragility": (
            "Observed edge is smaller than the current transaction-cost stress buffer.",
            "A viable revision should remain positive after the same or stricter cost haircut "
            "on a fresh holdout.",
        ),
        "exit_stop_dominance": (
            "Losses are dominated by stop exits under the frozen execution model.",
            "A structural invalidation or entry-quality hypothesis should reduce stop dominance "
            "without simply widening risk and must improve fresh-holdout expectancy.",
        ),
        "direction_asymmetry": (
            "LONG and SHORT outcomes appear materially asymmetric.",
            "A pre-registered directional or regime hypothesis should reproduce the asymmetry "
            "on new data before any directional filter is accepted.",
        ),
    }
    rationale, prediction = mapping[signal]
    return {
        "signal": signal,
        "rationale": rationale,
        "falsifiable_prediction": prediction,
        "validation_requirement": "new previously unseen holdout required",
    }


def _analyze_trader(
    backtest: dict[str, object],
    walk: dict[str, object],
) -> dict[str, object]:
    code = _text(backtest.get("trader_code"), name="trader_code")
    if code != _text(walk.get("trader_code"), name="walk trader_code"):
        raise FirstCohortFailureAnalysisError("backtest/walk-forward trader mismatch")
    setups = _integer(backtest.get("setup_count"), name="setup_count")
    unfilled = _integer(backtest.get("unfilled_setup_count"), name="unfilled_setup_count")
    sample = _integer(backtest.get("sample_size"), name="sample_size")
    mean = _decimal(backtest.get("mean_return"), name="mean_return")
    win = _decimal(backtest.get("win_rate"), name="win_rate")
    trades = [
        _object(item, name="trade")
        for item in _array(backtest.get("trades"), name="trades")
    ]
    if len(trades) != sample:
        raise FirstCohortFailureAnalysisError("trade count differs from sample_size")

    assessments = [
        _object(item, name="assessment")
        for item in _array(walk.get("assessments"), name="assessments")
    ]
    assessed_count = _integer(
        walk.get("assessed_configurations"), name="assessed_configurations"
    )
    if len(assessments) != assessed_count:
        raise FirstCohortFailureAnalysisError(
            "assessment count differs from assessed_configurations"
        )
    selected_value = walk.get("selected")
    selected = None if selected_value is None else _object(selected_value, name="selected")

    exit_counts = Counter(_text(item.get("exit_reason"), name="exit_reason") for item in trades)
    side_rows: dict[str, list[dict[str, object]]] = {"long": [], "short": []}
    for item in trades:
        side = _text(item.get("side"), name="side").lower()
        if side not in side_rows:
            raise FirstCohortFailureAnalysisError("unsupported trade side")
        side_rows[side].append(item)

    signals: list[str] = []
    if sample < _SPARSE_SAMPLE:
        signals.append("sparse_activity")
    if setups > 0 and Decimal(unfilled) / Decimal(setups) >= _HIGH_UNFILLED_RATE:
        signals.append("poor_fill_conversion")
    if sample > 0 and mean < 0:
        signals.append("negative_expectancy")
    if sample > 0 and win < _MIN_WIN_RATE:
        signals.append("low_hit_rate")

    in_sample_passes = sum(
        _boolean(item.get("in_sample_pass"), name="in_sample_pass") for item in assessments
    )
    oos_passes = sum(_boolean(item.get("oos_pass"), name="oos_pass") for item in assessments)
    stress_passes = sum(
        _boolean(item.get("stress_pass"), name="stress_pass") for item in assessments
    )
    if assessed_count > 1 and in_sample_passes <= 1:
        signals.append("parameter_instability")
    stage = _selected_stage(selected)
    if stage == "oos":
        signals.append("oos_collapse")
    elif stage == "stress":
        signals.append("stress_fragility")

    if sample > 0 and exit_counts.get("stop", 0) * 2 > sample:
        signals.append("exit_stop_dominance")
    long_metrics = _metric_payload(side_rows["long"])
    short_metrics = _metric_payload(side_rows["short"])
    if side_rows["long"] and side_rows["short"]:
        long_mean = _decimal(long_metrics["mean_return"], name="long mean")
        short_mean = _decimal(short_metrics["mean_return"], name="short mean")
        if (long_mean < 0 <= short_mean) or (short_mean < 0 <= long_mean):
            signals.append("direction_asymmetry")

    unique_signals = tuple(dict.fromkeys(signals))
    fill_rate = Decimal(0)
    if setups:
        fill_rate = Decimal(setups - unfilled) / Decimal(setups)

    return {
        "trader_code": code,
        "failure_stage": stage,
        "default_configuration": {
            "execution_period": _text(backtest.get("execution_period"), name="execution_period"),
            "setup_count": setups,
            "unfilled_setup_count": unfilled,
            "fill_rate": format(fill_rate, "f"),
            "sample_size": sample,
            "mean_return": format(mean, "f"),
            "win_rate": format(win, "f"),
            "population_variance": _text(
                backtest.get("population_variance"), name="population_variance"
            ),
            "max_losing_streak": _max_losing_streak(trades),
            "exit_reason_counts": dict(sorted(exit_counts.items())),
            "side_metrics": {
                "long": long_metrics,
                "short": short_metrics,
            },
            "temporal_quartiles": _temporal_quartiles(trades),
        },
        "parameter_surface": {
            "assessed_configurations": assessed_count,
            "in_sample_pass_count": in_sample_passes,
            "oos_pass_count": oos_passes,
            "stress_pass_count": stress_passes,
            "selected": selected,
            "assessments": assessments,
        },
        "diagnostic_signals": list(unique_signals),
        "hypotheses_to_test": [_hypothesis(signal) for signal in unique_signals],
    }


def run_failure_analysis(backtest_path: Path, walk_forward_path: Path) -> dict[str, object]:
    backtest = _read(backtest_path, name="backtest evidence")
    walk = _read(walk_forward_path, name="walk-forward evidence")
    for payload, name in ((backtest, "backtest"), (walk, "walk-forward")):
        if _text(payload.get("environment"), name=f"{name} environment") != "demo":
            raise FirstCohortFailureAnalysisError(f"{name} evidence must be DEMO")
        if not _boolean(payload.get("read_only"), name=f"{name} read_only"):
            raise FirstCohortFailureAnalysisError(f"{name} evidence must be read-only")
    if _text(walk.get("schema"), name="walk-forward schema") != _WALK_FORWARD_SCHEMA:
        raise FirstCohortFailureAnalysisError("failure analysis requires walk-forward v2")
    symbol = _text(backtest.get("symbol"), name="backtest symbol")
    if symbol != _text(walk.get("symbol"), name="walk-forward symbol"):
        raise FirstCohortFailureAnalysisError("backtest/walk-forward symbol mismatch")
    fingerprint = _text(backtest.get("account_fingerprint"), name="account fingerprint")
    if fingerprint != _text(walk.get("account_fingerprint"), name="walk account fingerprint"):
        raise FirstCohortFailureAnalysisError("backtest/walk-forward account mismatch")

    backtest_rows = {
        _text(row.get("trader_code"), name="backtest trader_code"): row
        for row in (
            _object(item, name="backtest result")
            for item in _array(backtest.get("results"), name="backtest results")
        )
    }
    walk_rows = {
        _text(row.get("trader_code"), name="walk trader_code"): row
        for row in (
            _object(item, name="walk result")
            for item in _array(walk.get("results"), name="walk results")
        )
    }
    if tuple(backtest_rows) != _CODES or tuple(walk_rows) != _CODES:
        raise FirstCohortFailureAnalysisError("first-cohort identity/order changed")

    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "symbol": symbol,
        "account_fingerprint": fingerprint,
        "source_checked_at": _text(backtest.get("checked_at"), name="checked_at"),
        "holdout_governance": {
            "oos_observed_by_failure_analysis": True,
            "post_change_reuse_as_independent_holdout_prohibited": True,
            "new_previously_unseen_holdout_required_after_any_hypothesis_change": True,
        },
        "results": [
            _analyze_trader(backtest_rows[code], walk_rows[code]) for code in _CODES
        ],
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        print(
            "usage: python -m qore.infrastructure.trader_lab.first_cohort_failure_analysis "
            "BACKTEST_JSON WALK_FORWARD_JSON"
        )
        return 2
    try:
        payload = run_failure_analysis(Path(arguments[0]), Path(arguments[1]))
    except FirstCohortFailureAnalysisError as error:
        print(f"first-cohort failure analysis failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
