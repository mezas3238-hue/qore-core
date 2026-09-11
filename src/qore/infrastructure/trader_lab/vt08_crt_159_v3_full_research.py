"""Full Trader Lab evidence packaging for VT-08 CRT 1-5-9 V3."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from qore.infrastructure.research_block_bootstrap import _draw_start, _mean
from qore.infrastructure.research_resampling_envelope import _nearest_rank
from qore.kernel.errors import InfrastructureError

_BACKTEST_SCHEMA = "qore.trader_lab.vt08_crt_159_v3_backtest.v1"
_SCHEMA = "qore.trader_lab.vt08_crt_159_v3_full_research.v1"
_MIN_SAMPLE = 20
_BOOTSTRAP_COUNT = 5000
_BOOTSTRAP_BLOCK = 3
_BOOTSTRAP_SEED = 159_2026


class Vt08Crt159V3FullResearchError(InfrastructureError):
    __slots__ = ()


def _object(value: object, field: str) -> dict[str, object]:
    if type(value) is not dict:
        raise Vt08Crt159V3FullResearchError(f"{field} must be object")
    return cast(dict[str, object], value)


def _array(value: object, field: str) -> list[object]:
    if type(value) is not list:
        raise Vt08Crt159V3FullResearchError(f"{field} must be array")
    return cast(list[object], value)


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value:
        raise Vt08Crt159V3FullResearchError(f"{field} must be non-empty str")
    return value


def _decimal(value: object, field: str) -> Decimal:
    raw = _text(value, field)
    try:
        result = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08Crt159V3FullResearchError(f"{field} must be decimal") from error
    if not result.is_finite():
        raise Vt08Crt159V3FullResearchError(f"{field} must be finite")
    return result


def _timestamp(value: object, field: str) -> datetime:
    raw = _text(value, field)
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08Crt159V3FullResearchError(f"{field} must be aware")
    return parsed.astimezone(UTC)


def _load(path: Path) -> dict[str, object]:
    payload = _object(json.loads(path.read_text(encoding="utf-8")), "backtest")
    if _text(payload.get("schema"), "schema") != _BACKTEST_SCHEMA:
        raise Vt08Crt159V3FullResearchError("unexpected V3 backtest schema")
    if payload.get("research_only") is not True or payload.get("read_only") is not True:
        raise Vt08Crt159V3FullResearchError("V3 evidence must remain read-only research")
    return payload


def _trade_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    return [_object(item, "trade") for item in _array(payload.get("trades"), "trades")]


def _terminal(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in rows if row.get("r_multiple") is not None]


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    terminal = _terminal(rows)
    values = tuple(_decimal(row.get("r_multiple"), "r_multiple") for row in terminal)
    wins = sum(value > 0 for value in values)
    if values:
        mean = sum(values, Decimal(0)) / Decimal(len(values))
        variance = sum(((value - mean) ** 2 for value in values), Decimal(0)) / Decimal(len(values))
    else:
        mean = variance = Decimal(0)
    equity = peak = drawdown = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {
        "setup_count": len(rows),
        "terminal_sample_size": len(values),
        "expectancy_r": format(mean, "f"),
        "win_rate": format(Decimal(wins) / Decimal(len(values)) if values else Decimal(0), "f"),
        "population_variance_r": format(variance, "f"),
        "max_drawdown_r": format(drawdown, "f"),
        "target_count": sum(row.get("outcome") == "target" for row in terminal),
        "stop_count": sum(row.get("outcome") == "stop" for row in terminal),
        "censored_count": len(rows) - len(terminal),
    }


def _screen(metrics: dict[str, object]) -> bool:
    return int(metrics["terminal_sample_size"]) >= _MIN_SAMPLE and Decimal(str(metrics["expectancy_r"])) >= 0


def _monte_carlo(rows: list[dict[str, object]]) -> dict[str, object]:
    values = tuple(_decimal(row.get("r_multiple"), "r_multiple") for row in _terminal(rows))
    if len(values) < _BOOTSTRAP_BLOCK:
        return {
            "schema": "qore.trader_lab.vt08_crt_159_v3_monte_carlo.v1",
            "research_only": True,
            "governed_stage_authority": False,
            "sample_size": len(values),
            "simulation_count": 0,
            "pass": False,
        }
    means: list[Decimal] = []
    blocks = (len(values) + _BOOTSTRAP_BLOCK - 1) // _BOOTSTRAP_BLOCK
    for replicate in range(_BOOTSTRAP_COUNT):
        sampled: list[Decimal] = []
        for draw in range(blocks):
            start = _draw_start(
                seed=_BOOTSTRAP_SEED,
                replicate=replicate,
                draw=draw,
                sample_size=len(values),
            )
            for offset in range(_BOOTSTRAP_BLOCK):
                sampled.append(values[(start + offset) % len(values)])
                if len(sampled) == len(values):
                    break
        means.append(_mean(tuple(sampled)))
    ordered = tuple(sorted(means))
    lower = _nearest_rank(ordered, 500)
    median = _nearest_rank(ordered, 5000)
    upper = _nearest_rank(ordered, 9500)
    return {
        "schema": "qore.trader_lab.vt08_crt_159_v3_monte_carlo.v1",
        "research_only": True,
        "governed_stage_authority": False,
        "sample_size": len(values),
        "simulation_count": _BOOTSTRAP_COUNT,
        "block_length": _BOOTSTRAP_BLOCK,
        "seed": _BOOTSTRAP_SEED,
        "lower_mean_r": format(lower, "f"),
        "median_mean_r": format(median, "f"),
        "upper_mean_r": format(upper, "f"),
        "pass": len(values) >= _MIN_SAMPLE and lower >= 0,
    }


def generate_full_research(backtest_path: Path, output_dir: Path) -> dict[str, object]:
    payload = _load(backtest_path)
    rows = _trade_rows(payload)
    rows.sort(key=lambda row: _timestamp(row.get("signal_at"), "signal_at"))
    split_at = int(len(rows) * 0.70)
    split_at = min(max(split_at, 1), len(rows) - 1) if len(rows) > 1 else len(rows)
    ins = rows[:split_at]
    oos = rows[split_at:]
    all_metrics = _metrics(rows)
    is_metrics = _metrics(ins)
    oos_metrics = _metrics(oos)
    stress_cases = []
    for haircut in (Decimal("0.05"), Decimal("0.10")):
        terminal = _terminal(oos)
        values = tuple(_decimal(row.get("r_multiple"), "r_multiple") - haircut for row in terminal)
        expectancy = sum(values, Decimal(0)) / Decimal(len(values)) if values else Decimal(0)
        stress_cases.append(
            {
                "haircut_r_per_trade": format(haircut, "f"),
                "sample_size": len(values),
                "expectancy_r": format(expectancy, "f"),
                "pass": len(values) >= _MIN_SAMPLE and expectancy >= 0,
            }
        )
    stress = {
        "schema": "qore.trader_lab.vt08_crt_159_v3_stress.v1",
        "research_only": True,
        "governed_stage_authority": False,
        "cases": stress_cases,
        "pass": bool(stress_cases) and all(case["pass"] for case in stress_cases),
    }
    monte = _monte_carlo(oos)
    by_side: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_side[_text(row.get("side"), "side")].append(row)
    characterization = {
        "schema": "qore.trader_lab.vt08_crt_159_v3_characterization.v1",
        "research_only": True,
        "decision_funnel": {
            "decision_days": int(payload.get("decision_days", 0)),
            "daily_context_pass": int(payload.get("daily_context_pass", 0)),
            "h4_159_pass": int(payload.get("h4_159_pass", 0)),
            "h1_nested_pass": int(payload.get("h1_nested_pass", 0)),
            "m15_nested_pass": int(payload.get("m15_nested_pass", 0)),
            "direction_agreement_pass": int(payload.get("direction_agreement_pass", 0)),
            "setups": len(rows),
        },
        "all_history": all_metrics,
        "in_sample": is_metrics,
        "oos": oos_metrics,
        "by_side": {key: _metrics(value) for key, value in sorted(by_side.items())},
        "daily_target_touch_count": int(payload.get("daily_target_touch_count", 0)),
        "parameter_sensitivity": {
            "status": "not_applicable",
            "reason": "source-frozen V3 has no authorized optimization parameter",
        },
    }
    walk = {
        "schema": "qore.trader_lab.vt08_crt_159_v3_walk_forward.v1",
        "research_only": True,
        "source_frozen_configuration": True,
        "parameter_search_performed": False,
        "in_sample_fraction": "0.70",
        "oos_fraction": "0.30",
        "in_sample": is_metrics,
        "oos": oos_metrics,
        "in_sample_pass": _screen(is_metrics),
        "oos_pass": _screen(oos_metrics),
        "holdout_governance": {
            "state": "consumed_for_research",
            "post_change_reuse_as_independent_holdout_prohibited": True,
            "fresh_previously_unseen_holdout_required_after_any_change": True,
        },
    }
    failures: list[str] = []
    if not walk["oos_pass"]:
        failures.append("oos_generalization_failure")
    if not stress["pass"]:
        failures.append("stress_fragility")
    if not monte["pass"]:
        failures.append("monte_carlo_lower_envelope_not_positive")
    if int(all_metrics["terminal_sample_size"]) < _MIN_SAMPLE:
        failures.append("sparse_opportunity")
    if rows and int(all_metrics["censored_count"]) / len(rows) > 0.25:
        failures.append("high_context_expiry_censoring")
    failure_analysis = {
        "schema": "qore.trader_lab.vt08_crt_159_v3_failure_analysis.v1",
        "research_only": True,
        "failure_labels": failures,
        "methodology_change_authorized": False,
    }
    story = {
        "schema": "qore.trader_lab.vt08_crt_159_v3_story_forensics.v1",
        "research_only": True,
        "decision_time_oracle_separation": True,
        "episode_count": len(rows),
        "episodes": [
            {
                "episode_id": f"vt08-v3-{index:06d}",
                "decision_time": {
                    "signal_at": row.get("signal_at"),
                    "side": row.get("side"),
                    "entry_price": row.get("entry_price"),
                    "stop_loss": row.get("stop_loss"),
                    "take_profit": row.get("take_profit"),
                },
                "post_outcome_oracle": {
                    "outcome": row.get("outcome"),
                    "r_multiple": row.get("r_multiple"),
                    "mfe_r": row.get("mfe_r"),
                    "mae_r": row.get("mae_r"),
                    "daily_target_touched": row.get("daily_target_touched"),
                },
            }
            for index, row in enumerate(rows)
        ],
    }
    hypotheses = {
        "schema": "qore.trader_lab.vt08_crt_159_v3_hypothesis_register.v1",
        "research_only": True,
        "hypotheses": [
            {
                "family": "nesting-depth",
                "predicted_improvement": "test whether all four aligned levels add value",
                "falsification": "fresh holdout shows equal or better performance with fewer levels",
                "change_authorized": False,
            },
            {
                "family": "context-expiry",
                "predicted_improvement": "study censored 13:00 outcomes without inventing exits",
                "falsification": "fresh holdout shows no persistent post-13:00 continuation",
                "change_authorized": False,
            },
        ],
        "fresh_holdout_required_before_change": True,
    }
    summary = {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": payload.get("software_sha"),
        "symbol": payload.get("symbol"),
        "trader_code": "vt-08",
        "trader_version": "v3",
        "methodology": "crt-159-fractal-nested-v3",
        "all_history": all_metrics,
        "oos_pass": walk["oos_pass"],
        "stress_pass": stress["pass"],
        "monte_carlo_pass": monte["pass"],
        "failure_labels": failures,
        "governed_lifecycle_authority": False,
        "demo_eligible": False,
        "promotion_blocker": "research OOS consumed; fresh unseen holdout plus governed authority chain required",
    }
    outputs = {
        "walk-forward.json": walk,
        "characterization.json": characterization,
        "stress.json": stress,
        "monte-carlo.json": monte,
        "failure-analysis.json": failure_analysis,
        "story-forensics.json": story,
        "hypothesis-register.json": hypotheses,
        "research-summary.json": summary,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, item in outputs.items():
        (output_dir / name).write_text(
            json.dumps(item, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n",
            encoding="utf-8",
        )
    return summary


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        raise SystemExit("usage: vt08_crt_159_v3_full_research <backtest.json> <output-dir>")
    print(
        json.dumps(
            generate_full_research(Path(args[0]), Path(args[1])),
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
