"""Trader Lab research evidence for reconstructed VT-08 H4 PO3 V2.

Consumes the corrected V2 backtest where target/stop are terminal outcomes and
H4-close leftovers are censored.  Positive mark-to-market at H4 close is kept as
descriptive path evidence and is never counted as a win.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from qore.infrastructure.research_block_bootstrap import _draw_start, _mean
from qore.infrastructure.research_resampling_envelope import _nearest_rank
from qore.kernel.errors import InfrastructureError

_BACKTEST_SCHEMA = "qore.trader_lab.vt08_crt_h4_amd_v2_backtest.v2"
_MIN_SAMPLE = 20
_BOOTSTRAP_COUNT = 5000
_BOOTSTRAP_BLOCK = 3
_BOOTSTRAP_SEED = 802_2026


class Vt08CrtH4AmdV2FullResearchError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class _Metrics:
    setup_count: int
    terminal_sample_size: int
    target_count: int
    stop_count: int
    censored_count: int
    win_rate_terminal_only: Decimal
    expectancy_r_terminal_only: Decimal
    variance_r_terminal_only: Decimal
    max_drawdown_r_terminal_only: Decimal
    mean_h4_close_mark_to_market_r: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "setup_count": self.setup_count,
            "terminal_sample_size": self.terminal_sample_size,
            "target_count": self.target_count,
            "stop_count": self.stop_count,
            "censored_count": self.censored_count,
            "win_rate_terminal_only": format(self.win_rate_terminal_only, "f"),
            "expectancy_r_terminal_only": format(
                self.expectancy_r_terminal_only, "f"
            ),
            "population_variance_terminal_r": format(
                self.variance_r_terminal_only, "f"
            ),
            "max_drawdown_terminal_r": format(
                self.max_drawdown_r_terminal_only, "f"
            ),
            "descriptive_mean_h4_close_mark_to_market_r": format(
                self.mean_h4_close_mark_to_market_r, "f"
            ),
        }


def _object(value: object, field: str) -> dict[str, object]:
    if type(value) is not dict:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be object")
    return cast(dict[str, object], value)


def _array(value: object, field: str) -> list[object]:
    if type(value) is not list:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be array")
    return cast(list[object], value)


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be non-empty str")
    return value


def _strict_int(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        raise Vt08CrtH4AmdV2FullResearchError(
            f"{field} must be non-negative int"
        )
    return value


def _decimal(value: object, field: str) -> Decimal:
    if type(value) is not str:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be Decimal text")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be decimal") from error
    if not result.is_finite():
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be finite")
    return result


def _timestamp(value: object, field: str) -> datetime:
    raw = _text(value, field)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _load(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08CrtH4AmdV2FullResearchError("cannot read reconstructed V2") from error
    payload = _object(decoded, "backtest")
    if _text(payload.get("schema"), "schema") != _BACKTEST_SCHEMA:
        raise Vt08CrtH4AmdV2FullResearchError("unexpected reconstructed V2 schema")
    if payload.get("research_only") is not True or payload.get("read_only") is not True:
        raise Vt08CrtH4AmdV2FullResearchError("V2 evidence must be read-only research")
    if payload.get("invalidates_prior_campaign") is not True:
        raise Vt08CrtH4AmdV2FullResearchError(
            "reconstructed V2 must explicitly invalidate prior campaign"
        )
    return payload


def _rows(payload: dict[str, object]) -> list[dict[str, object]]:
    result = [_object(item, "trade") for item in _array(payload.get("trades"), "trades")]
    result.sort(key=lambda row: _timestamp(row.get("signal_at"), "signal_at"))
    return result


def _terminal(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in rows if row.get("r_multiple") is not None]


def _metrics(rows: list[dict[str, object]]) -> _Metrics:
    terminal = _terminal(rows)
    values = tuple(_decimal(row.get("r_multiple"), "r_multiple") for row in terminal)
    target_count = sum(row.get("outcome") == "target" for row in terminal)
    stop_count = sum(row.get("outcome") == "stop" for row in terminal)
    if target_count + stop_count != len(terminal):
        raise Vt08CrtH4AmdV2FullResearchError(
            "terminal V2 sample must be exact target+stop"
        )
    expectancy = (
        sum(values, Decimal(0)) / Decimal(len(values)) if values else Decimal(0)
    )
    variance = (
        sum(((item - expectancy) ** 2 for item in values), Decimal(0))
        / Decimal(len(values))
        if values
        else Decimal(0)
    )
    equity = Decimal(0)
    peak = Decimal(0)
    drawdown = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    marks = tuple(
        _decimal(row.get("mark_to_market_r_at_h4_close"), "mark_to_market")
        for row in rows
    )
    return _Metrics(
        setup_count=len(rows),
        terminal_sample_size=len(terminal),
        target_count=target_count,
        stop_count=stop_count,
        censored_count=len(rows) - len(terminal),
        win_rate_terminal_only=(
            Decimal(target_count) / Decimal(len(terminal))
            if terminal
            else Decimal(0)
        ),
        expectancy_r_terminal_only=expectancy,
        variance_r_terminal_only=variance,
        max_drawdown_r_terminal_only=drawdown,
        mean_h4_close_mark_to_market_r=(
            sum(marks, Decimal(0)) / Decimal(len(marks)) if marks else Decimal(0)
        ),
    )


def _screen(metrics: _Metrics) -> bool:
    return (
        metrics.terminal_sample_size >= _MIN_SAMPLE
        and metrics.expectancy_r_terminal_only >= 0
    )


def _monte_carlo(rows: list[dict[str, object]]) -> dict[str, object]:
    values = tuple(
        _decimal(row.get("r_multiple"), "r_multiple") for row in _terminal(rows)
    )
    if len(values) < _BOOTSTRAP_BLOCK:
        return {
            "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_monte_carlo.v2",
            "research_only": True,
            "governed_stage_authority": False,
            "sample_size": len(values),
            "simulation_count": 0,
            "pass": False,
        }
    blocks = (len(values) + _BOOTSTRAP_BLOCK - 1) // _BOOTSTRAP_BLOCK
    means: list[Decimal] = []
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
            if len(sampled) == len(values):
                break
        means.append(_mean(tuple(sampled)))
    ordered = tuple(sorted(means))
    lower = _nearest_rank(ordered, 500)
    median = _nearest_rank(ordered, 5000)
    upper = _nearest_rank(ordered, 9500)
    return {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_monte_carlo.v2",
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
    rows = _rows(payload)
    split_at = int(len(rows) * 0.70)
    if len(rows) > 1:
        split_at = min(max(split_at, 1), len(rows) - 1)
    else:
        split_at = len(rows)
    ins, oos = rows[:split_at], rows[split_at:]
    all_metrics = _metrics(rows)
    is_metrics = _metrics(ins)
    oos_metrics = _metrics(oos)

    stress_cases: list[dict[str, object]] = []
    for haircut in (Decimal("0.05"), Decimal("0.10")):
        values = tuple(
            _decimal(row.get("r_multiple"), "r_multiple") - haircut
            for row in _terminal(oos)
        )
        expectancy = (
            sum(values, Decimal(0)) / Decimal(len(values)) if values else Decimal(0)
        )
        stress_cases.append(
            {
                "haircut_r_per_terminal_trade": format(haircut, "f"),
                "sample_size": len(values),
                "expectancy_r": format(expectancy, "f"),
                "pass": len(values) >= _MIN_SAMPLE and expectancy >= 0,
            }
        )
    stress_pass = bool(stress_cases) and all(
        cast(bool, case["pass"]) for case in stress_cases
    )
    stress = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_stress.v2",
        "research_only": True,
        "governed_stage_authority": False,
        "terminal_outcomes_only": True,
        "cases": stress_cases,
        "pass": stress_pass,
    }
    monte = _monte_carlo(oos)

    by_side: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_scenario: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_side[_text(row.get("side"), "side")].append(row)
        by_scenario[_text(row.get("scenario"), "scenario")].append(row)

    walk = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_walk_forward.v2",
        "research_only": True,
        "source_frozen_configuration": True,
        "parameter_search_performed": False,
        "in_sample_fraction": "0.70",
        "oos_fraction": "0.30",
        "in_sample": is_metrics.payload(),
        "oos": oos_metrics.payload(),
        "in_sample_pass": _screen(is_metrics),
        "oos_pass": _screen(oos_metrics),
        "holdout_governance": {
            "state": "consumed_for_research",
            "post_change_reuse_as_independent_holdout_prohibited": True,
            "fresh_previously_unseen_holdout_required_after_any_change": True,
        },
    }
    characterization = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_characterization.v2",
        "research_only": True,
        "decision_funnel": {
            "decision_days": _strict_int(payload.get("decision_days"), "decision_days"),
            "daily_bias_pass": _strict_int(
                payload.get("daily_bias_pass"), "daily_bias_pass"
            ),
            "candle2_setups": _strict_int(
                payload.get("candle2_setup_count"), "candle2_setup_count"
            ),
            "candle3_candidates": _strict_int(
                payload.get("candle3_candidate_count"), "candle3_candidate_count"
            ),
            "setups": len(rows),
            "terminal": all_metrics.terminal_sample_size,
            "censored": all_metrics.censored_count,
        },
        "all_history": all_metrics.payload(),
        "in_sample": is_metrics.payload(),
        "oos": oos_metrics.payload(),
        "by_side": {
            key: _metrics(value).payload() for key, value in sorted(by_side.items())
        },
        "by_scenario": {
            key: _metrics(value).payload()
            for key, value in sorted(by_scenario.items())
        },
        "source_equilibrium_filter": {
            "threshold_fraction": "0.5",
            "optimized": False,
            "status": "source-operationalization",
        },
        "positive_h4_close_mark_is_win": False,
    }

    failures: list[str] = []
    if not _screen(oos_metrics):
        failures.append("oos_generalization_failure")
    if not stress_pass:
        failures.append("stress_fragility")
    if not cast(bool, monte["pass"]):
        failures.append("monte_carlo_lower_envelope_not_positive")
    if all_metrics.terminal_sample_size < _MIN_SAMPLE:
        failures.append("sparse_terminal_opportunity")
    if rows and all_metrics.censored_count / len(rows) > 0.25:
        failures.append("high_h4_close_censoring")
    if len(rows) > _strict_int(payload.get("decision_days"), "decision_days"):
        raise Vt08CrtH4AmdV2FullResearchError(
            "reconstructed V2 violated maximum one setup per market/day"
        )
    failure_analysis = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_failure_analysis.v2",
        "research_only": True,
        "failure_labels": failures,
        "methodology_change_authorized": False,
        "prior_13468_campaign_valid_for_economics": False,
    }

    story = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_story_forensics.v2",
        "research_only": True,
        "decision_time_oracle_separation": True,
        "episode_count": len(rows),
        "episodes": [
            {
                "episode_id": f"vt08-v2r-{index:06d}",
                "decision_time": {
                    "signal_at": row.get("signal_at"),
                    "side": row.get("side"),
                    "scenario": row.get("scenario"),
                    "entry_price": row.get("entry_price"),
                    "stop_loss": row.get("stop_loss"),
                    "take_profit": row.get("take_profit"),
                    "cisd_level": row.get("cisd_level"),
                    "manipulation_fraction_of_reference": row.get(
                        "manipulation_fraction_of_reference"
                    ),
                },
                "post_outcome_oracle": {
                    "outcome": row.get("outcome"),
                    "r_multiple": row.get("r_multiple"),
                    "mark_to_market_r_at_h4_close": row.get(
                        "mark_to_market_r_at_h4_close"
                    ),
                    "mfe_r": row.get("mfe_r"),
                    "mae_r": row.get("mae_r"),
                },
            }
            for index, row in enumerate(rows)
        ],
    }
    hypothesis = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_hypothesis_register.v2",
        "research_only": True,
        "hypotheses": [
            {
                "family": "candle2-vs-candle3",
                "triggered": len(by_scenario) > 1,
                "change_authorized": False,
                "falsification": "fresh unseen holdout fails to preserve scenario separation",
            },
            {
                "family": "equilibrium-operationalization",
                "triggered": True,
                "change_authorized": False,
                "falsification": (
                    "manual source-labelled examples contradict the 50pct shallow/deep split"
                ),
            },
        ],
        "required_cycle": [
            "OBSERVE",
            "DIAGNOSE",
            "HYPOTHESIZE",
            "PRE-REGISTER",
            "MODIFY",
            "FRESH_HOLDOUT",
            "STRESS",
            "MONTE_CARLO",
            "AUTHORITY",
        ],
    }
    summary = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_full_research.v2",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "trader_code": "vt-08",
        "trader_version": "v2",
        "methodology": "ttrades-h4-po3-source-v2.1-reconstructed",
        "software_sha": _text(payload.get("software_sha"), "software_sha"),
        "symbol": _text(payload.get("symbol"), "symbol"),
        "invalidates_prior_campaign": True,
        "all_history": all_metrics.payload(),
        "oos_pass": _screen(oos_metrics),
        "stress_pass": stress_pass,
        "monte_carlo_pass": cast(bool, monte["pass"]),
        "failure_labels": failures,
        "governed_lifecycle_authority": False,
        "demo_eligible": False,
        "promotion_blocker": (
            "reconstruction consumed OOS; methodology fidelity adjudication and fresh unseen "
            "holdout plus governed authority chain are required"
        ),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "walk-forward.json": walk,
        "characterization.json": characterization,
        "stress.json": stress,
        "monte-carlo.json": monte,
        "failure-analysis.json": failure_analysis,
        "story-forensics.json": story,
        "hypothesis-register.json": hypothesis,
        "research-summary.json": summary,
    }
    for name, data in outputs.items():
        (output_dir / name).write_text(
            json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n",
            encoding="utf-8",
        )
    return summary


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        raise SystemExit(
            "usage: vt08_crt_h4_amd_v2_full_research <backtest.json> <output-dir>"
        )
    summary = generate_full_research(Path(args[0]), Path(args[1]))
    print(json.dumps(summary, sort_keys=True, separators=(",", ":"), allow_nan=False))


if __name__ == "__main__":
    main()
