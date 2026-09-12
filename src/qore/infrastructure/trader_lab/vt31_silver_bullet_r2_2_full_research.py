"""Trader Lab research package for the frozen VT-31 R2.2 rebuild.

The package evaluates one pre-registered QORE execution profile over the source
model. It does not promote the profile to a TTrades rule and does not grant
DEMO_ELIGIBLE. Any hypothesis produced here consumes the current OOS evidence.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_2_backtest import (
    Vt31R22BacktestError,
)

_SCHEMA = "qore.trader_lab.vt31_r2_2_research_summary.v1"
_MIN_SAMPLE = 20
_STRESS_HAIRCUTS = (Decimal("0.05"), Decimal("0.10"))
_BOOTSTRAP_BLOCK = 3
_BOOTSTRAP_COUNT = 5000
_BOOTSTRAP_SEED = 312_2026
_DOMAIN = b"qore-vt31-r2.2-bootstrap-v1"
_BASELINE = {
    "label": "VT31_QORE_517_BASELINE_MISFORMALIZATION_EVIDENCE",
    "run_id": 34660383434,
    "head_sha": "5335f2fcd7593df04fb0f1277fdb5d1c185d8553",
    "artifact_id": 10287780783,
    "artifact_digest": "sha256:56e3bfe4ba658ea9d0880534b01a569cd55e4f131f8df62d5e5794be6484e27b",
    "setup_count": 113,
    "filled_count": 90,
    "target_count": 11,
    "stop_count": 70,
    "breakeven_count": 9,
    "win_rate": "0.1222222222222222222222222222",
    "expectancy_r": "-0.3817768522266935971772923311",
    "max_drawdown_r": "34.35991670040242374595630980",
    "final_qualification_valid": False,
}


class Vt31R22ResearchError(Vt31R22BacktestError):
    __slots__ = ()


def _object(value: object, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt31R22ResearchError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt31R22ResearchError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt31R22ResearchError(f"{name} must be non-empty text")
    return value


def _integer(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise Vt31R22ResearchError(f"{name} must be non-negative int")
    return value


def _decimal(value: object, name: str) -> Decimal:
    raw = _text(value, name)
    result = Decimal(raw)
    if not result.is_finite():
        raise Vt31R22ResearchError(f"{name} must be finite decimal")
    return result


def _timestamp(value: object, name: str) -> datetime:
    raw = _text(value, name)
    result = datetime.fromisoformat(raw)
    if result.tzinfo is None or result.utcoffset() is None:
        raise Vt31R22ResearchError(f"{name} must be timezone-aware")
    return result


def _load(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt31R22ResearchError("cannot read R2.2 backtest") from error
    payload = _object(decoded, "backtest")
    if _text(payload.get("schema"), "schema") != "qore.trader_lab.vt31_r2_2_backtest.v1":
        raise Vt31R22ResearchError("unexpected R2.2 backtest schema")
    if _text(payload.get("environment"), "environment") != "demo":
        raise Vt31R22ResearchError("research requires DEMO evidence")
    policy = _object(payload.get("execution_policy"), "execution_policy")
    if policy.get("source_rule") is not False:
        raise Vt31R22ResearchError("execution profile must remain non-source")
    if _integer(payload.get("daily_cardinality_violations"), "cardinality") != 0:
        raise Vt31R22ResearchError("daily cardinality must be clean")
    return payload


def _terminal_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    rows = [
        _object(item, "trade")
        for item in _array(payload.get("trades"), "trades")
    ]
    return [item for item in rows if item.get("r_multiple") is not None]


def _metrics(
    rows: list[dict[str, object]],
    haircut: Decimal = Decimal(0),
) -> dict[str, object]:
    values = tuple(
        _decimal(item.get("r_multiple"), "r_multiple") - haircut for item in rows
    )
    if not values:
        return {
            "sample_size": 0,
            "expectancy_r": "0",
            "win_rate": "0",
            "population_variance": "0",
            "max_drawdown_r": "0",
            "target_count": 0,
            "stop_count": 0,
            "breakeven_count": 0,
        }
    size = Decimal(len(values))
    mean = sum(values, Decimal(0)) / size
    variance = sum(((item - mean) ** 2 for item in values), Decimal(0)) / size
    equity = Decimal(0)
    peak = Decimal(0)
    drawdown = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    targets = sum(item.get("outcome") == "target" for item in rows)
    return {
        "sample_size": len(values),
        "expectancy_r": format(mean, "f"),
        "win_rate": format(Decimal(targets) / size, "f"),
        "population_variance": format(variance, "f"),
        "max_drawdown_r": format(drawdown, "f"),
        "target_count": targets,
        "stop_count": sum(item.get("outcome") == "stop" for item in rows),
        "breakeven_count": sum(item.get("outcome") == "breakeven" for item in rows),
    }


def _passes(metrics: dict[str, object]) -> bool:
    return (
        _integer(metrics.get("sample_size"), "sample_size") >= _MIN_SAMPLE
        and _decimal(metrics.get("expectancy_r"), "expectancy_r") >= 0
    )


def _draw_start(replicate: int, draw: int, sample_size: int) -> int:
    material = (
        _DOMAIN
        + b":"
        + str(_BOOTSTRAP_SEED).encode("ascii")
        + b":"
        + str(replicate).encode("ascii")
        + b":"
        + str(draw).encode("ascii")
    )
    return int.from_bytes(sha256(material).digest(), "big") % sample_size


def _bootstrap(rows: list[dict[str, object]]) -> dict[str, object]:
    values = tuple(_decimal(item.get("r_multiple"), "r_multiple") for item in rows)
    policy = {
        "family": "block_bootstrap",
        "algorithm": "deterministic-circular-block-mean-r-v1",
        "block_length": _BOOTSTRAP_BLOCK,
        "simulation_count": _BOOTSTRAP_COUNT,
        "seed": _BOOTSTRAP_SEED,
        "min_sample_size": _MIN_SAMPLE,
        "qualification": "5th-percentile-mean-r>=0",
    }
    if len(values) < max(_MIN_SAMPLE, _BOOTSTRAP_BLOCK):
        return {
            "status": "insufficient_sample",
            "sample_size": len(values),
            "policy": policy,
        }
    means: list[Decimal] = []
    blocks = (len(values) + _BOOTSTRAP_BLOCK - 1) // _BOOTSTRAP_BLOCK
    for replicate in range(_BOOTSTRAP_COUNT):
        drawn: list[Decimal] = []
        for draw in range(blocks):
            start = _draw_start(replicate, draw, len(values))
            for offset in range(_BOOTSTRAP_BLOCK):
                drawn.append(values[(start + offset) % len(values)])
                if len(drawn) == len(values):
                    break
            if len(drawn) == len(values):
                break
        means.append(sum(drawn, Decimal(0)) / Decimal(len(drawn)))
    means.sort()
    lower = means[int((len(means) - 1) * 0.05)]
    median = means[int((len(means) - 1) * 0.50)]
    upper = means[int((len(means) - 1) * 0.95)]
    return {
        "status": "qualified" if lower >= 0 else "threshold_violation",
        "sample_size": len(values),
        "source_mean_r": format(sum(values, Decimal(0)) / Decimal(len(values)), "f"),
        "lower_mean_r": format(lower, "f"),
        "median_mean_r": format(median, "f"),
        "upper_mean_r": format(upper, "f"),
        "policy": policy,
    }


def _group_metrics(rows: list[dict[str, object]], key: str) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        value = row.get(key)
        if type(value) is str:
            groups[value].append(row)
    return {name: _metrics(group) for name, group in sorted(groups.items())}


def _characterization(
    payload: dict[str, object],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    ledger_rows = [
        _object(item, "ledger")
        for item in _array(payload.get("ledgers"), "ledgers")
    ]
    return {
        "schema": "qore.trader_lab.vt31_r2_2_characterization.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "decision_funnel": {
            "eligible_market_days": payload.get("eligible_market_days"),
            "selected_setup_count": payload.get("selected_setup_count"),
            "filled_count": payload.get("filled_count"),
            "terminal_sample_size": payload.get("terminal_sample_size"),
            "abstain_counts": payload.get("abstain_counts"),
            "containment_counts": payload.get("containment_counts"),
        },
        "all_terminal": _metrics(rows),
        "by_side": _group_metrics(rows, "side"),
        "by_entry_family": _group_metrics(rows, "selected_family"),
        "by_outcome": dict(
            sorted(
                Counter(_text(item.get("outcome"), "outcome") for item in rows).items()
            )
        ),
        "both_sides_swept_days": sum(
            item.get("both_sides_swept") is True for item in ledger_rows
        ),
        "source_vs_execution_boundary": {
            "source_model_has_exact_entry_price": False,
            "execution_policy_source_rule": False,
            "entry_policy_id": _object(
                payload.get("execution_policy"), "policy"
            ).get("policy_id"),
        },
    }


def build_payloads(backtest_path: Path) -> dict[str, dict[str, object]]:
    payload = _load(backtest_path)
    rows = _terminal_rows(payload)
    ordered = sorted(
        rows,
        key=lambda item: _timestamp(item.get("signal_at"), "signal_at"),
    )
    split = (len(ordered) * 7) // 10
    in_sample = ordered[:split]
    oos = ordered[split:]
    is_metrics = _metrics(in_sample)
    oos_metrics = _metrics(oos)
    walk = {
        "schema": "qore.trader_lab.vt31_r2_2_walk_forward.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "configuration_selection": "pre-registered-single-operational-profile-no-search",
        "in_sample_fraction": "0.70",
        "oos_fraction": "0.30",
        "in_sample": is_metrics,
        "in_sample_pass": _passes(is_metrics),
        "oos": oos_metrics,
        "oos_pass": _passes(oos_metrics),
    }
    stress_rows: list[dict[str, object]] = []
    for haircut in _STRESS_HAIRCUTS:
        metrics = _metrics(oos, haircut)
        stress_rows.append(
            {
                "haircut_r": format(haircut, "f"),
                "metrics": metrics,
                "pass": _passes(metrics),
            }
        )
    stress_pass = (
        bool(stress_rows)
        and _passes(oos_metrics)
        and all(bool(item["pass"]) for item in stress_rows)
    )
    stress = {
        "schema": "qore.trader_lab.vt31_r2_2_stress.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "scenarios": stress_rows,
        "stress_pass": stress_pass,
    }
    monte = {
        "schema": "qore.trader_lab.vt31_r2_2_monte_carlo.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        **_bootstrap(oos),
    }
    characterization = _characterization(payload, rows)
    labels: list[str] = []
    all_metrics = _metrics(rows)
    if _decimal(all_metrics.get("expectancy_r"), "expectancy") < 0:
        labels.append("negative_expectancy")
    if not _passes(oos_metrics):
        labels.append("oos_generalization_failure")
    if not stress_pass:
        labels.append("stress_fragility")
    if sum(item.get("outcome") == "stop" for item in rows) * 2 > len(rows):
        labels.append("stop_dominance")
    family_metrics = _group_metrics(rows, "selected_family")
    family_signs = {
        name: _decimal(
            _object(metrics, "family metrics").get("expectancy_r"),
            "family expectancy",
        )
        >= 0
        for name, metrics in family_metrics.items()
    }
    if len(set(family_signs.values())) > 1:
        labels.append("entry_family_dependency_candidate")
    if not labels:
        labels.append("no_failure_rule_triggered_research_only")
    failure = {
        "schema": "qore.trader_lab.vt31_r2_2_failure_analysis.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "labels": labels,
        "causality_claimed": False,
    }
    register = {
        "schema": "qore.trader_lab.vt31_r2_2_hypothesis_register.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "hypotheses": [
            {
                "id": f"vt31-r2-2-{label}",
                "observed_signal": label,
                "enabled_for_modification": False,
                "fresh_holdout_required": True,
                "forbidden_reuse": (
                    "current 760-day evidence cannot independently certify a change "
                    "derived from it"
                ),
            }
            for label in labels
        ],
    }
    monte_status = _text(monte.get("status"), "monte status")
    summary = {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "trader_code": "vt-31",
        "trader_version": "r2.2-source-rebuild",
        "source_model_exact_entry_price_resolved": False,
        "execution_profile_is_source_rule": False,
        "walk_forward_in_sample_pass": walk["in_sample_pass"],
        "walk_forward_oos_pass": walk["oos_pass"],
        "stress_pass": stress_pass,
        "monte_carlo_status": monte_status,
        "economic_requalification_status": (
            "operational-profile-qualified-research-only"
            if walk["oos_pass"] is True
            and stress_pass
            and monte_status == "qualified"
            else "not-qualified"
        ),
        "demo_eligible": False,
        "demo_eligible_reason": (
            "source exact entry geometry remains unresolved and governed Risk/CIBO/"
            "Independent Validation authority is absent"
        ),
        "holdout_governance": {
            "current_evidence_consumed_for_research": True,
            "post_change_reuse_as_independent_holdout_prohibited": True,
            "fresh_previously_unseen_holdout_required_after_any_hypothesis_change": True,
        },
        "baseline_comparison": {
            "baseline": _BASELINE,
            "rebuilt": {
                "selected_setup_count": payload.get("selected_setup_count"),
                "filled_count": payload.get("filled_count"),
                "target_count": payload.get("target_count"),
                "stop_count": payload.get("stop_count"),
                "breakeven_count": payload.get("breakeven_count"),
                "win_rate": payload.get("win_rate"),
                "expectancy_r": payload.get("expectancy_r"),
                "max_drawdown_r": payload.get("max_drawdown_r"),
            },
            "economic_comparison_is_descriptive_not_rule_selection": True,
        },
        "stage_summary": {
            "research": "complete",
            "replay": "complete",
            "fast_forward": "complete_as_full_chronological_replay",
            "oos": "pass" if walk["oos_pass"] is True else "fail",
            "stress": "pass" if stress_pass else "fail",
            "monte_carlo": monte_status,
            "risk_review": "blocked_no_governed_authority",
            "cibo_review": "blocked_no_governed_authority",
            "independent_validation": "blocked_no_fresh_independent_holdout",
            "demo_eligible": False,
        },
    }
    return {
        "walk-forward.json": walk,
        "characterization.json": characterization,
        "stress.json": stress,
        "monte-carlo.json": monte,
        "failure-analysis.json": failure,
        "hypothesis-register.json": register,
        "research-summary.json": summary,
        "baseline-comparison.json": cast(dict[str, object], summary["baseline_comparison"]),
    }


def write_payloads(backtest_path: Path, output_dir: Path) -> dict[str, object]:
    payloads = build_payloads(backtest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        (output_dir / name).write_text(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
            encoding="utf-8",
        )
    return cast(dict[str, object], payloads["research-summary.json"])


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print(
            "usage: python -m qore.infrastructure.trader_lab."
            "vt31_silver_bullet_r2_2_full_research BACKTEST OUTDIR"
        )
        return 2
    try:
        summary = write_payloads(Path(args[0]), Path(args[1]))
    except Vt31SilverBulletV2BacktestError as error:
        print(f"VT-31 R2.2 research failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
