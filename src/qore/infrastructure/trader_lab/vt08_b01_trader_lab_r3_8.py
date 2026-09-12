"""Trader Lab diagnostics for the VT-08 R3.8 narrow B01 replay.

This module consumes the frozen B01 backtest plus the exact read-only market evidence.
It reuses the first-cohort economic screen thresholds, performs chronological IS/OOS
screening, cost stress, deep behavioral segmentation, close-path MFE/MAE diagnostics,
and a counterfactual next-H4 continuation diagnostic for the explicit H4-containment
research policy. It never changes the Trader, grants DEMO_ELIGIBLE, or promotes a
research hypothesis.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.first_cohort_walk_forward import (
    _MAX_VARIANCE,
    _MIN_MEAN,
    _MIN_SAMPLE,
    _MIN_WIN_RATE,
    _STRESS_HAIRCUT,
)
from qore.infrastructure.trader_lab.vt08_b01_backtest_r3_8 import (
    Vt08B01BacktestError,
    Vt08B01Bar,
    _load,
)

_SCHEMA = "qore.trader_lab.vt08_b01_diagnostics.r3.8.v1"
_BACKTEST_SCHEMA = "qore.trader_lab.vt08_b01_backtest.r3.8.v1"
_NY = ZoneInfo("America/New_York")


class Vt08B01TraderLabError(Vt08B01BacktestError):
    __slots__ = ()


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08B01TraderLabError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08B01TraderLabError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08B01TraderLabError(f"{name} must be non-empty text")
    return value


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int or value < 0:
        raise Vt08B01TraderLabError(f"{name} must be a non-negative int")
    return value


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise Vt08B01TraderLabError(f"{name} must be bool")
    return value


def _timestamp(value: object, *, name: str) -> datetime:
    raw = _text(value, name=name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08B01TraderLabError(f"{name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08B01TraderLabError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08B01TraderLabError(f"{name} must be decimal text") from error
    if not parsed.is_finite():
        raise Vt08B01TraderLabError(f"{name} must be finite")
    return parsed


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        return Decimal(0)
    return sum(values, Decimal(0)) / Decimal(len(values))


def _metrics(values: tuple[Decimal, ...]) -> dict[str, object]:
    if not values:
        return {
            "sample_size": 0,
            "mean_return": "0",
            "win_rate": "0",
            "population_variance": "0",
            "gross_profit": "0",
            "gross_loss": "0",
            "profit_factor": None,
            "mean_win": "0",
            "mean_loss": "0",
            "payoff_ratio": None,
            "compounded_return": "0",
            "maximum_drawdown": "0",
            "max_losing_streak": 0,
            "best_return": "0",
            "worst_return": "0",
        }
    mean = _mean(values)
    variance = sum(((value - mean) ** 2 for value in values), Decimal(0)) / Decimal(
        len(values)
    )
    positive = tuple(value for value in values if value > 0)
    negative = tuple(value for value in values if value < 0)
    gross_profit = sum(positive, Decimal(0))
    gross_loss = abs(sum(negative, Decimal(0)))
    equity = Decimal(1)
    peak = equity
    max_drawdown = Decimal(0)
    losing_streak = 0
    current_losing_streak = 0
    for value in values:
        equity *= Decimal(1) + value
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
        if value <= 0:
            current_losing_streak += 1
            losing_streak = max(losing_streak, current_losing_streak)
        else:
            current_losing_streak = 0
    mean_win = _mean(positive)
    mean_loss = _mean(negative)
    return {
        "sample_size": len(values),
        "mean_return": format(mean, "f"),
        "win_rate": format(Decimal(len(positive)) / Decimal(len(values)), "f"),
        "population_variance": format(variance, "f"),
        "gross_profit": format(gross_profit, "f"),
        "gross_loss": format(gross_loss, "f"),
        "profit_factor": None if gross_loss == 0 else format(gross_profit / gross_loss, "f"),
        "mean_win": format(mean_win, "f"),
        "mean_loss": format(mean_loss, "f"),
        "payoff_ratio": (
            None
            if not positive or not negative
            else format(mean_win / abs(mean_loss), "f")
        ),
        "compounded_return": format(equity - Decimal(1), "f"),
        "maximum_drawdown": format(max_drawdown, "f"),
        "max_losing_streak": losing_streak,
        "best_return": format(max(values), "f"),
        "worst_return": format(min(values), "f"),
    }


def _passes(metrics: dict[str, object]) -> bool:
    return (
        _integer(metrics.get("sample_size"), name="sample_size") >= _MIN_SAMPLE
        and _decimal(metrics.get("mean_return"), name="mean_return") >= _MIN_MEAN
        and _decimal(metrics.get("win_rate"), name="win_rate") >= _MIN_WIN_RATE
        and _decimal(
            metrics.get("population_variance"), name="population_variance"
        )
        <= _MAX_VARIANCE
    )


def _bucket(rows: list[dict[str, object]]) -> dict[str, object]:
    return _metrics(
        tuple(_decimal(row.get("return_rate"), name="return_rate") for row in rows)
    )


def _segments(
    rows: list[dict[str, object]],
    *,
    key_name: str,
) -> dict[str, dict[str, object]]:
    buckets: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        buckets[_text(row.get(key_name), name=key_name)].append(row)
    return {key: _bucket(bucket) for key, bucket in sorted(buckets.items())}


def _trade_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for value in _array(payload.get("trades"), name="trades"):
        trade = _object(value, name="trade")
        signal_at = _timestamp(trade.get("signal_at"), name="signal_at")
        exited_at = _timestamp(trade.get("exited_at"), name="exited_at")
        if exited_at < signal_at:
            raise Vt08B01TraderLabError("trade exit cannot predate signal")
        side = _text(trade.get("side"), name="side")
        if side not in {"long", "short"}:
            raise Vt08B01TraderLabError("trade side must be long or short")
        row = dict(trade)
        row["signal_at_parsed"] = signal_at
        row["exited_at_parsed"] = exited_at
        local = signal_at.astimezone(_NY)
        row["signal_hour_ny"] = str(local.hour)
        row["signal_weekday_ny"] = str(local.weekday())
        row["signal_month"] = str(local.month)
        row["signal_year"] = str(local.year)
        rows.append(row)
    rows.sort(key=lambda item: cast(datetime, item["signal_at_parsed"]))
    return rows


def _quartiles(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for index in range(4):
        start = (len(rows) * index) // 4
        end = (len(rows) * (index + 1)) // 4
        result[str(index + 1)] = _bucket(rows[start:end])
    return result


def _path_diagnostics(
    rows: list[dict[str, object]],
    *,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> dict[str, object]:
    mfe_values: list[Decimal] = []
    mae_values: list[Decimal] = []
    risk_mfe: list[Decimal] = []
    risk_mae: list[Decimal] = []
    bars_to_exit: list[Decimal] = []
    containment_counterfactual = Counter[str]()
    for row in rows:
        signal_at = cast(datetime, row["signal_at_parsed"])
        exited_at = cast(datetime, row["exited_at_parsed"])
        entry = _decimal(row.get("entry"), name="entry")
        stop = _decimal(row.get("stop"), name="stop")
        target = _decimal(row.get("target"), name="target")
        side = _text(row.get("side"), name="side")
        retained: list[Vt08B01Bar] = []
        cursor = signal_at
        while cursor < exited_at:
            bar = bars_by_open.get(cursor)
            if bar is None:
                break
            retained.append(bar)
            cursor += timedelta(minutes=15)
        if retained:
            highs = tuple(bar.high for bar in retained)
            lows = tuple(bar.low for bar in retained)
            if side == "long":
                mfe = (max(highs) - entry) / entry
                mae = (entry - min(lows)) / entry
            else:
                mfe = (entry - min(lows)) / entry
                mae = (max(highs) - entry) / entry
            mfe_values.append(max(mfe, Decimal(0)))
            mae_values.append(max(mae, Decimal(0)))
            risk = abs(entry - stop) / entry
            if risk > 0:
                risk_mfe.append(max(mfe, Decimal(0)) / risk)
                risk_mae.append(max(mae, Decimal(0)) / risk)
            bars_to_exit.append(Decimal(len(retained)))

        if _text(row.get("exit_reason"), name="exit_reason") != "h4_containment_exit":
            continue
        cursor = exited_at
        outcome = "unresolved_next_h4"
        for _index in range(16):
            bar = bars_by_open.get(cursor)
            if bar is None:
                outcome = "incomplete_next_h4"
                break
            stop_hit = bar.low <= stop <= bar.high
            target_hit = bar.low <= target <= bar.high
            if stop_hit:
                outcome = "stop_before_or_same_bar_as_target"
                break
            if target_hit:
                outcome = "target_before_stop"
                break
            cursor += timedelta(minutes=15)
        containment_counterfactual[outcome] += 1

    return {
        "mfe_fraction": _metrics(tuple(mfe_values)),
        "mae_fraction": _metrics(tuple(mae_values)),
        "risk_normalized_mfe": _metrics(tuple(risk_mfe)),
        "risk_normalized_mae": _metrics(tuple(risk_mae)),
        "bars_to_exit": _metrics(tuple(bars_to_exit)),
        "measurement": "M15 path; no intrabar ordering inferred",
        "same_bar_stop_target_policy": "stop-first-conservative",
        "h4_containment_counterfactual_next_h4": dict(
            sorted(containment_counterfactual.items())
        ),
        "counterfactual_is_hypothesis_only": True,
    }


def _hypotheses(
    *,
    full_metrics: dict[str, object],
    exit_counts: Counter[str],
    by_side: dict[str, dict[str, object]],
    oos_pass: bool,
    stress_pass: bool,
    is_pass: bool,
) -> list[dict[str, str]]:
    signals: list[str] = []
    sample = _integer(full_metrics.get("sample_size"), name="sample_size")
    if sample > 0 and _decimal(full_metrics.get("mean_return"), name="mean_return") < 0:
        signals.append("negative_expectancy")
    if sample > 0 and _decimal(full_metrics.get("win_rate"), name="win_rate") < _MIN_WIN_RATE:
        signals.append("low_hit_rate")
    if sample > 0 and exit_counts.get("stop", 0) * 2 > sample:
        signals.append("exit_stop_dominance")
    long_mean = _decimal(by_side.get("long", {}).get("mean_return", "0"), name="long_mean")
    short_mean = _decimal(
        by_side.get("short", {}).get("mean_return", "0"), name="short_mean"
    )
    if long_mean * short_mean < 0:
        signals.append("direction_asymmetry")
    if is_pass and not oos_pass:
        signals.append("oos_collapse")
    if oos_pass and not stress_pass:
        signals.append("stress_fragility")

    mapping = {
        "negative_expectancy": (
            "The frozen B01 geometry has negative average payoff on this market.",
            "A source-authorized structural change must make fresh-holdout mean return "
            "non-negative without weakening source fidelity.",
        ),
        "low_hit_rate": (
            "Signal precision is below the frozen first-cohort economic threshold.",
            "A pre-registered regime or context hypothesis must improve fresh-holdout "
            "win rate without post-hoc selection.",
        ),
        "exit_stop_dominance": (
            "More than half of modeled trades terminate at the structural stop.",
            "A source-supported entry/PS-quality hypothesis must reduce stop dominance "
            "on new data without simply widening risk.",
        ),
        "direction_asymmetry": (
            "LONG and SHORT mean returns have opposite signs.",
            "The asymmetry must reproduce on a new holdout before any directional filter.",
        ),
        "oos_collapse": (
            "In-sample qualification does not generalize to chronological OOS.",
            "Any revision must be pre-registered and tested on a new untouched holdout.",
        ),
        "stress_fragility": (
            "OOS edge does not survive the existing transaction-cost stress haircut.",
            "A viable revision must survive the same or stricter stress on fresh data.",
        ),
    }
    return [
        {
            "signal": signal,
            "rationale": mapping[signal][0],
            "falsifiable_prediction": mapping[signal][1],
            "validation_requirement": "new previously unseen holdout required",
        }
        for signal in signals
    ]


def run_vt08_b01_trader_lab(
    market_path: Path,
    backtest_path: Path,
) -> dict[str, object]:
    fingerprint, symbol, checked_at, software_sha, bars = _load(market_path)
    try:
        decoded: object = json.loads(backtest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08B01TraderLabError("cannot read B01 backtest") from error
    payload = _object(decoded, name="B01 backtest")
    if _text(payload.get("schema"), name="schema") != _BACKTEST_SCHEMA:
        raise Vt08B01TraderLabError("unexpected B01 backtest schema")
    if _text(payload.get("environment"), name="environment") != "demo":
        raise Vt08B01TraderLabError("B01 backtest must be DEMO")
    if not _boolean(payload.get("read_only"), name="read_only"):
        raise Vt08B01TraderLabError("B01 backtest must be read-only")
    if _text(payload.get("symbol"), name="symbol") != symbol:
        raise Vt08B01TraderLabError("market/backtest symbol mismatch")
    if _text(payload.get("account_fingerprint"), name="account_fingerprint") != fingerprint:
        raise Vt08B01TraderLabError("market/backtest account mismatch")
    if _text(payload.get("software_sha"), name="software_sha") != software_sha:
        raise Vt08B01TraderLabError("market/backtest software SHA mismatch")
    if _integer(payload.get("daily_cardinality_violations"), name="cardinality") != 0:
        raise Vt08B01TraderLabError("B01 cardinality violation")

    rows = _trade_rows(payload)
    declared_sample = _integer(payload.get("sample_size"), name="sample_size")
    if len(rows) != declared_sample:
        raise Vt08B01TraderLabError("trade rows differ from declared sample_size")
    values = tuple(_decimal(row.get("return_rate"), name="return_rate") for row in rows)
    full_metrics = _metrics(values)

    split_index = (len(rows) * 7) // 10
    train_rows = rows[:split_index]
    oos_rows = rows[split_index:]
    train_metrics = _bucket(train_rows)
    oos_metrics = _bucket(oos_rows)
    stressed_values = tuple(
        _decimal(row.get("return_rate"), name="return_rate") - _STRESS_HAIRCUT
        for row in oos_rows
    )
    stressed_metrics = _metrics(stressed_values)
    in_sample_pass = _passes(train_metrics)
    oos_pass = _passes(oos_metrics)
    stress_pass = _passes(stressed_metrics)

    exit_counts = Counter(_text(row.get("exit_reason"), name="exit_reason") for row in rows)
    by_side = _segments(rows, key_name="side")
    bars_by_open = {bar.opened_at: bar for bar in bars}
    path = _path_diagnostics(rows, bars_by_open=bars_by_open)
    if oos_pass and stress_pass:
        stage = "PER_INSTRUMENT_SCREEN_PASS"
    elif in_sample_pass and not oos_pass:
        stage = "OOS_FAIL"
    elif oos_pass and not stress_pass:
        stage = "STRESS_FAIL"
    else:
        stage = "IN_SAMPLE_OR_ECONOMIC_FAIL"

    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "trader_code": "vt-08",
        "profile": _text(payload.get("profile"), name="profile"),
        "bundle_id": _text(payload.get("bundle_id"), name="bundle_id"),
        "symbol": symbol,
        "account_fingerprint": fingerprint,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "methodology_fingerprint": _text(
            payload.get("methodology_fingerprint"), name="methodology_fingerprint"
        ),
        "execution_model": _text(payload.get("execution_model"), name="execution_model"),
        "operational_containments": _array(
            payload.get("operational_containments"), name="operational_containments"
        ),
        "sample_size": declared_sample,
        "candidate_count": _integer(payload.get("candidate_count"), name="candidate_count"),
        "abstain_reasons": _object(
            payload.get("abstain_reasons"), name="abstain_reasons"
        ),
        "exit_reason_counts": dict(sorted(exit_counts.items())),
        "full_period": full_metrics,
        "walk_forward": {
            "policy_id": "first-demo-economic-v1",
            "in_sample_fraction": "0.70",
            "oos_fraction": "0.30",
            "split_index": split_index,
            "split_at": (
                cast(datetime, oos_rows[0]["signal_at_parsed"]).isoformat()
                if oos_rows
                else None
            ),
            "in_sample": train_metrics,
            "in_sample_pass": in_sample_pass,
            "oos": oos_metrics,
            "oos_pass": oos_pass,
            "stressed_oos": stressed_metrics,
            "stress_pass": stress_pass,
            "stress_return_haircut": format(_STRESS_HAIRCUT, "f"),
        },
        "characterization": {
            "by_side": by_side,
            "by_exit_reason": _segments(rows, key_name="exit_reason"),
            "by_signal_hour_ny": _segments(rows, key_name="signal_hour_ny"),
            "by_signal_weekday_ny": _segments(rows, key_name="signal_weekday_ny"),
            "by_calendar_month": _segments(rows, key_name="signal_month"),
            "by_calendar_year": _segments(rows, key_name="signal_year"),
            "by_chronological_quartile": _quartiles(rows),
            "path": path,
            "parameter_sensitivity": {
                "classification": "frozen-source-bundle-no-tunable-parameter-grid",
                "parameter_grid_applied": False,
            },
        },
        "failure_analysis": {
            "stage": stage,
            "hypotheses": _hypotheses(
                full_metrics=full_metrics,
                exit_counts=exit_counts,
                by_side=by_side,
                oos_pass=oos_pass,
                stress_pass=stress_pass,
                is_pass=in_sample_pass,
            ),
            "holdout_governance": {
                "state": "consumed_for_research",
                "post_change_reuse_as_independent_holdout_prohibited": True,
                "new_previously_unseen_holdout_required_after_any_hypothesis_change": True,
            },
        },
        "lifecycle_gate": {
            "replay": "complete",
            "fast_forward": "represented-by-chronological-full-replay",
            "oos": "pass" if oos_pass else "fail",
            "stress": "pass" if stress_pass else "fail",
            "monte_carlo": (
                "blocked-until-oos-and-stress-pass"
                if not (oos_pass and stress_pass)
                else "requires-governed-sampling-frame"
            ),
            "risk_review": "not_granted",
            "cibo_review": "not_granted",
            "independent_validation": "not_granted",
            "economic_evidence": "research_only",
            "demo_eligible": False,
        },
        "trade_records": [
            {
                "signal_at": cast(datetime, row["signal_at_parsed"]).isoformat(),
                "exited_at": cast(datetime, row["exited_at_parsed"]).isoformat(),
                "side": _text(row.get("side"), name="side"),
                "exit_reason": _text(row.get("exit_reason"), name="exit_reason"),
                "return_rate": format(
                    _decimal(row.get("return_rate"), name="return_rate"), "f"
                ),
            }
            for row in rows
        ],
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        print(
            "usage: python -m qore.infrastructure.trader_lab.vt08_b01_trader_lab_r3_8 "
            "MARKET_EVIDENCE B01_BACKTEST",
            file=sys.stderr,
        )
        return 2
    try:
        payload = run_vt08_b01_trader_lab(Path(arguments[0]), Path(arguments[1]))
    except Vt08B01BacktestError as error:
        print(f"VT-08 B01 Trader Lab failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
