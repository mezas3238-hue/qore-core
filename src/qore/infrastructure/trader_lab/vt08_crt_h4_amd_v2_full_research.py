"""Full Trader Lab evidence family for source-bound VT-08 CRT H4 AMD V2.

The adapter consumes the canonical VT-08 V2 backtest and emits chronological
IS/OOS, characterization, stress, deterministic circular-block Monte Carlo,
failure analysis, Story Forensics, hypothesis governance and a research summary.
The methodology is frozen: this adapter performs no parameter search.

The 30% OOS segment is consumed for research.  Any strategy change therefore
requires a fresh previously unseen holdout before independent certification.
No output grants lifecycle, DEMO, LIVE, Risk, execution or real-capital authority.
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
from zoneinfo import ZoneInfo

from qore.infrastructure.research_block_bootstrap import _draw_start, _mean
from qore.infrastructure.research_resampling_envelope import _nearest_rank
from qore.kernel.errors import InfrastructureError

_BACKTEST_SCHEMA = "qore.trader_lab.vt08_crt_h4_amd_v2_backtest.v1"
_SCHEMA = "qore.trader_lab.vt08_crt_h4_amd_v2_full_research.v1"
_MIN_SAMPLE = 20
_IS_FRACTION = Decimal("0.70")
_STRESS_HAIRCUTS = (Decimal("0.05"), Decimal("0.10"))
_BOOTSTRAP_BLOCK = 3
_BOOTSTRAP_COUNT = 5000
_BOOTSTRAP_SEED = 808_2026
_NY = ZoneInfo("America/New_York")


class Vt08CrtH4AmdV2FullResearchError(InfrastructureError):
    """VT-08 V2 evidence packaging failed closed."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class _Trade:
    signal_at: datetime
    resolved_at: datetime
    side: str
    profile: str
    htf_closure: str
    entry_price: Decimal
    stop_loss: Decimal
    exit_price: Decimal
    outcome: str
    r_multiple: Decimal
    mfe_r: Decimal
    mae_r: Decimal
    h4_opened_at: datetime
    h4_closed_at: datetime


@dataclass(frozen=True, slots=True)
class _Metrics:
    sample_size: int
    expectancy_r: Decimal
    win_rate: Decimal
    variance_r: Decimal
    max_drawdown_r: Decimal
    stop_rate: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "sample_size": self.sample_size,
            "expectancy_r": format(self.expectancy_r, "f"),
            "win_rate": format(self.win_rate, "f"),
            "population_variance_r": format(self.variance_r, "f"),
            "max_drawdown_r": format(self.max_drawdown_r, "f"),
            "stop_rate": format(self.stop_rate, "f"),
        }


def _object(value: object, *, field: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be object")
    return cast(dict[str, object], value)


def _array(value: object, *, field: str) -> list[object]:
    if type(value) is not list:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be array")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if type(value) is not str or not value:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be non-empty str")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be bool")
    return value


def _integer(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be non-negative int")
    return value


def _timestamp(value: object, *, field: str) -> datetime:
    raw = _text(value, field=field)
    try:
        result = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be RFC3339") from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be timezone-aware")
    return result.astimezone(UTC)


def _decimal(value: object, *, field: str) -> Decimal:
    raw = _text(value, field=field)
    try:
        result = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be Decimal text") from error
    if not result.is_finite():
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be finite")
    return result


def _load(path: Path) -> tuple[dict[str, object], tuple[_Trade, ...]]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08CrtH4AmdV2FullResearchError("cannot read VT-08 V2 backtest") from error
    payload = _object(decoded, field="backtest")
    if _text(payload.get("schema"), field="schema") != _BACKTEST_SCHEMA:
        raise Vt08CrtH4AmdV2FullResearchError("unexpected VT-08 V2 backtest schema")
    if _text(payload.get("environment"), field="environment") != "demo":
        raise Vt08CrtH4AmdV2FullResearchError("VT-08 V2 research must be DEMO")
    if not _boolean(payload.get("read_only"), field="read_only"):
        raise Vt08CrtH4AmdV2FullResearchError("VT-08 V2 research must be read-only")
    if not _boolean(payload.get("research_only"), field="research_only"):
        raise Vt08CrtH4AmdV2FullResearchError("VT-08 V2 must remain research-only")
    rows = _array(payload.get("trades"), field="trades")
    trades: list[_Trade] = []
    for index, raw in enumerate(rows):
        row = _object(raw, field=f"trade[{index}]")
        side = _text(row.get("side"), field="side")
        profile = _text(row.get("profile"), field="profile")
        outcome = _text(row.get("outcome"), field="outcome")
        if side not in {"long", "short"}:
            raise Vt08CrtH4AmdV2FullResearchError("trade side must be long/short")
        if profile not in {"continuation-expansion", "reversal-expansion"}:
            raise Vt08CrtH4AmdV2FullResearchError("trade profile is not source canonical")
        if outcome not in {"stop", "h4_close"}:
            raise Vt08CrtH4AmdV2FullResearchError("trade outcome is not source canonical")
        trades.append(
            _Trade(
                signal_at=_timestamp(row.get("signal_at"), field="signal_at"),
                resolved_at=_timestamp(row.get("resolved_at"), field="resolved_at"),
                side=side,
                profile=profile,
                htf_closure=_text(row.get("htf_closure"), field="htf_closure"),
                entry_price=_decimal(row.get("entry_price"), field="entry_price"),
                stop_loss=_decimal(row.get("stop_loss"), field="stop_loss"),
                exit_price=_decimal(row.get("exit_price"), field="exit_price"),
                outcome=outcome,
                r_multiple=_decimal(row.get("r_multiple"), field="r_multiple"),
                mfe_r=_decimal(row.get("mfe_r"), field="mfe_r"),
                mae_r=_decimal(row.get("mae_r"), field="mae_r"),
                h4_opened_at=_timestamp(row.get("h4_opened_at"), field="h4_opened_at"),
                h4_closed_at=_timestamp(row.get("h4_closed_at"), field="h4_closed_at"),
            )
        )
    ordered = tuple(sorted(trades, key=lambda item: (item.signal_at, item.resolved_at)))
    if tuple(trades) != ordered:
        raise Vt08CrtH4AmdV2FullResearchError("trades must be chronological")
    if _integer(payload.get("terminal_sample_size"), field="terminal_sample_size") != len(
        ordered
    ):
        raise Vt08CrtH4AmdV2FullResearchError("terminal sample does not reconcile")
    return payload, ordered


def _metrics(trades: tuple[_Trade, ...]) -> _Metrics:
    values = tuple(item.r_multiple for item in trades)
    if not values:
        return _Metrics(0, Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0))
    mean = sum(values, Decimal(0)) / Decimal(len(values))
    variance = sum(((item - mean) ** 2 for item in values), Decimal(0)) / Decimal(len(values))
    wins = Decimal(sum(item > 0 for item in values)) / Decimal(len(values))
    stops = Decimal(sum(item.outcome == "stop" for item in trades)) / Decimal(len(trades))
    equity = Decimal(0)
    peak = Decimal(0)
    drawdown = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return _Metrics(len(values), mean, wins, variance, drawdown, stops)


def _screen(metrics: _Metrics) -> bool:
    return metrics.sample_size >= _MIN_SAMPLE and metrics.expectancy_r >= 0


def _split(trades: tuple[_Trade, ...]) -> tuple[tuple[_Trade, ...], tuple[_Trade, ...]]:
    if not trades:
        return (), ()
    split_at = int(Decimal(len(trades)) * _IS_FRACTION)
    split_at = max(1, min(split_at, len(trades) - 1)) if len(trades) > 1 else 1
    return trades[:split_at], trades[split_at:]


def _segment_payload(trades: tuple[_Trade, ...], attribute: str) -> dict[str, object]:
    groups: dict[str, list[_Trade]] = defaultdict(list)
    for item in trades:
        if attribute == "side":
            key = item.side
        elif attribute == "profile":
            key = item.profile
        elif attribute == "year":
            key = str(item.signal_at.astimezone(_NY).year)
        elif attribute == "month":
            key = item.signal_at.astimezone(_NY).strftime("%Y-%m")
        elif attribute == "h4_open_hour_ny":
            key = f"{item.h4_opened_at.astimezone(_NY).hour:02d}:00"
        else:
            raise Vt08CrtH4AmdV2FullResearchError("unsupported characterization segment")
        groups[key].append(item)
    return {key: _metrics(tuple(values)).payload() for key, values in sorted(groups.items())}


def _stress(oos: tuple[_Trade, ...]) -> dict[str, object]:
    source = tuple(item.r_multiple for item in oos)
    cases: list[dict[str, object]] = []
    for haircut in _STRESS_HAIRCUTS:
        stressed = tuple(item - haircut for item in source)
        mean = sum(stressed, Decimal(0)) / Decimal(len(stressed)) if stressed else Decimal(0)
        cases.append(
            {
                "haircut_r_per_trade": format(haircut, "f"),
                "sample_size": len(stressed),
                "expectancy_r": format(mean, "f"),
                "pass": len(stressed) >= _MIN_SAMPLE and mean >= 0,
            }
        )
    return {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_stress.v1",
        "research_only": True,
        "governed_stage_authority": False,
        "source_segment": "chronological-oos-30pct-consumed-for-research",
        "parameter_sensitivity": {
            "status": "not_applicable",
            "reason": "source-frozen VT-08 V2 exposes no authorized optimization parameter",
        },
        "cases": cases,
        "pass": bool(cases) and all(bool(item["pass"]) for item in cases),
    }


def _monte_carlo(oos: tuple[_Trade, ...]) -> dict[str, object]:
    values = tuple(item.r_multiple for item in oos)
    if len(values) < _BOOTSTRAP_BLOCK:
        return {
            "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_monte_carlo.v1",
            "research_only": True,
            "governed_stage_authority": False,
            "sample_size": len(values),
            "block_length": _BOOTSTRAP_BLOCK,
            "simulation_count": 0,
            "lower_mean_r": None,
            "median_mean_r": None,
            "upper_mean_r": None,
            "pass": False,
            "reason": "insufficient-oos-sample-for-circular-block-bootstrap",
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
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_monte_carlo.v1",
        "research_only": True,
        "governed_stage_authority": False,
        "sample_size": len(values),
        "block_length": _BOOTSTRAP_BLOCK,
        "simulation_count": _BOOTSTRAP_COUNT,
        "seed": _BOOTSTRAP_SEED,
        "quantile_method": "canonical-nearest-rank",
        "lower_mean_r": format(lower, "f"),
        "median_mean_r": format(median, "f"),
        "upper_mean_r": format(upper, "f"),
        "pass": len(values) >= _MIN_SAMPLE and lower >= 0,
    }


def _story(trades: tuple[_Trade, ...]) -> dict[str, object]:
    episodes: list[dict[str, object]] = []
    for index, item in enumerate(trades):
        episodes.append(
            {
                "episode_id": f"vt08-v2-{index:06d}-{int(item.signal_at.timestamp())}",
                "decision_time": {
                    "signal_at": item.signal_at.isoformat(timespec="microseconds"),
                    "side": item.side,
                    "profile": item.profile,
                    "htf_closure": item.htf_closure,
                    "entry_price": format(item.entry_price, "f"),
                    "stop_loss": format(item.stop_loss, "f"),
                    "h4_opened_at": item.h4_opened_at.isoformat(timespec="microseconds"),
                    "h4_closed_at": item.h4_closed_at.isoformat(timespec="microseconds"),
                },
                "post_outcome_oracle": {
                    "resolved_at": item.resolved_at.isoformat(timespec="microseconds"),
                    "exit_price": format(item.exit_price, "f"),
                    "outcome": item.outcome,
                    "r_multiple": format(item.r_multiple, "f"),
                    "mfe_r": format(item.mfe_r, "f"),
                    "mae_r": format(item.mae_r, "f"),
                },
            }
        )
    return {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_story_forensics.v1",
        "research_only": True,
        "visualization_is_not_evidence_source": True,
        "decision_time_oracle_separation": True,
        "episode_count": len(episodes),
        "episodes": episodes,
    }


def generate_full_research(backtest_path: Path, output_dir: Path) -> dict[str, object]:
    backtest, trades = _load(backtest_path)
    software_sha = _text(backtest.get("software_sha"), field="software_sha")
    symbol = _text(backtest.get("symbol"), field="symbol")
    is_trades, oos = _split(trades)
    all_metrics = _metrics(trades)
    is_metrics = _metrics(is_trades)
    oos_metrics = _metrics(oos)
    stress = _stress(oos)
    monte_carlo = _monte_carlo(oos)
    walk_forward = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_walk_forward.v1",
        "research_only": True,
        "software_sha": software_sha,
        "symbol": symbol,
        "source_frozen_configuration": True,
        "parameter_search_performed": False,
        "in_sample_fraction": "0.70",
        "oos_fraction": "0.30",
        "holdout_governance": {
            "state": "consumed_for_research",
            "post_change_reuse_as_independent_holdout_prohibited": True,
            "fresh_previously_unseen_holdout_required_after_any_change": True,
        },
        "screen_policy": {
            "minimum_terminal_sample": _MIN_SAMPLE,
            "expectancy_r_minimum": "0",
            "win_rate_is_standalone_gate": False,
        },
        "in_sample": is_metrics.payload(),
        "oos": oos_metrics.payload(),
        "in_sample_pass": _screen(is_metrics),
        "oos_pass": _screen(oos_metrics),
    }
    characterization = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_characterization.v1",
        "research_only": True,
        "software_sha": software_sha,
        "symbol": symbol,
        "decision_funnel": {
            "complete_h4_windows": _integer(
                backtest.get("complete_h4_windows"), field="complete_h4_windows"
            ),
            "eligible_h4_windows": _integer(
                backtest.get("eligible_h4_windows"), field="eligible_h4_windows"
            ),
            "setups": len(trades),
            "filled": len(trades),
            "stops": sum(item.outcome == "stop" for item in trades),
            "h4_close_exits": sum(item.outcome == "h4_close" for item in trades),
        },
        "all_history": all_metrics.payload(),
        "in_sample": is_metrics.payload(),
        "oos": oos_metrics.payload(),
        "by_side": _segment_payload(trades, "side"),
        "by_profile": _segment_payload(trades, "profile"),
        "by_year": _segment_payload(trades, "year"),
        "by_month": _segment_payload(trades, "month"),
        "by_h4_open_hour_ny": _segment_payload(trades, "h4_open_hour_ny"),
        "mean_mfe_r": format(
            sum((item.mfe_r for item in trades), Decimal(0)) / Decimal(len(trades))
            if trades
            else Decimal(0),
            "f",
        ),
        "mean_mae_r": format(
            sum((item.mae_r for item in trades), Decimal(0)) / Decimal(len(trades))
            if trades
            else Decimal(0),
            "f",
        ),
        "parameter_sensitivity": {
            "status": "not_applicable",
            "reason": "source-frozen methodology has no authorized optimization knob",
        },
    }
    failures: list[str] = []
    if not _screen(oos_metrics):
        failures.append("oos_generalization_failure")
    if not bool(stress["pass"]):
        failures.append("stress_fragility")
    if not bool(monte_carlo["pass"]):
        failures.append("monte_carlo_lower_envelope_not_positive")
    long_metrics = _metrics(tuple(item for item in trades if item.side == "long"))
    short_metrics = _metrics(tuple(item for item in trades if item.side == "short"))
    if (
        long_metrics.sample_size >= 10
        and short_metrics.sample_size >= 10
        and abs(long_metrics.expectancy_r - short_metrics.expectancy_r) >= Decimal("0.25")
    ):
        failures.append("directional_asymmetry")
    continuation = _metrics(
        tuple(item for item in trades if item.profile == "continuation-expansion")
    )
    reversal = _metrics(tuple(item for item in trades if item.profile == "reversal-expansion"))
    if (
        continuation.sample_size >= 10
        and reversal.sample_size >= 10
        and abs(continuation.expectancy_r - reversal.expectancy_r) >= Decimal("0.25")
    ):
        failures.append("continuation_reversal_asymmetry")
    if len(trades) < _MIN_SAMPLE:
        failures.append("sparse_opportunity")
    failure_analysis = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_failure_analysis.v1",
        "research_only": True,
        "software_sha": software_sha,
        "symbol": symbol,
        "failure_labels": failures,
        "diagnostic_only": True,
        "methodology_change_authorized": False,
    }
    story = _story(trades)
    hypothesis_register = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_hypothesis_register.v1",
        "research_only": True,
        "software_sha": software_sha,
        "symbol": symbol,
        "hypotheses": [
            {
                "family": "directional-specialization",
                "triggered": "directional_asymmetry" in failures,
                "predicted_improvement": "specialize only if fresh holdout confirms asymmetry",
                "falsification": "fresh unseen holdout shows no stable LONG/SHORT separation",
                "change_authorized": False,
            },
            {
                "family": "continuation-vs-reversal-specialization",
                "triggered": "continuation_reversal_asymmetry" in failures,
                "predicted_improvement": "separate source profiles only after fresh validation",
                "falsification": "fresh unseen holdout does not preserve profile separation",
                "change_authorized": False,
            },
            {
                "family": "h4-session-specialization",
                "triggered": False,
                "predicted_improvement": "study NY-local H4 anchors without retrospective gating",
                "falsification": "session effect fails on fresh unseen holdout",
                "change_authorized": False,
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
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": symbol,
        "trader_code": "vt-08",
        "trader_version": "v2",
        "methodology": "crt-h4-po3-amd-source-v2",
        "source_frozen_configuration": True,
        "terminal_sample_size": len(trades),
        "all_history": all_metrics.payload(),
        "oos_pass": _screen(oos_metrics),
        "stress_pass": bool(stress["pass"]),
        "monte_carlo_pass": bool(monte_carlo["pass"]),
        "failure_labels": failures,
        "governed_lifecycle_authority": False,
        "demo_eligible": False,
        "promotion_blocker": (
            "research OOS is consumed; any change requires fresh unseen holdout plus "
            "the governed Risk/CIBO/independent-validation/economic authority chain"
        ),
    }
    outputs = {
        "walk-forward.json": walk_forward,
        "characterization.json": characterization,
        "stress.json": stress,
        "monte-carlo.json": monte_carlo,
        "failure-analysis.json": failure_analysis,
        "story-forensics.json": story,
        "hypothesis-register.json": hypothesis_register,
        "research-summary.json": summary,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in outputs.items():
        (output_dir / name).write_text(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
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
    print(
        json.dumps(
            summary,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
