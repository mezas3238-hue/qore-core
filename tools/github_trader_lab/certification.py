"""Certification-readiness reporting for the independent GitHub Trader Lab.

This module never certifies a Trader. It computes risk/edge diagnostics from
normalized R-series and fail-closed readiness gates. OOS is accepted only when
the profile explicitly binds evidence lanes to an OOS role; ordinary research
folds are never relabeled as OOS.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

PASS = "PASS"
FAIL = "FAIL"
NOT_EVALUATED = "NOT_EVALUATED"
REPORTED_ONLY = "REPORTED_ONLY"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _fmt(value: float | Decimal | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        if not value.is_finite():
            return None
        return format(value, "f")
    if not math.isfinite(value):
        return None
    return format(value, ".12g")


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return ordered[low]
    weight = pos - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _max_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    maximum = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _max_losing_streak(values: list[float]) -> int:
    current = 0
    maximum = 0
    for value in values:
        current = current + 1 if value < 0 else 0
        maximum = max(maximum, current)
    return maximum


def risk_adjusted_metrics(values_raw: list[object]) -> dict[str, Any]:
    """Return non-annualized per-trade diagnostics from net R observations."""

    values = [float(value) for value in values_raw]
    n = len(values)
    if n == 0:
        return {
            "sample": 0,
            "status": "INSUFFICIENT_SAMPLE",
        }

    mean = sum(values) / n
    total = sum(values)
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    variance = (
        sum((value - mean) ** 2 for value in values) / (n - 1)
        if n > 1
        else 0.0
    )
    std = math.sqrt(max(variance, 0.0))
    downside_dev = math.sqrt(
        sum(min(value, 0.0) ** 2 for value in values) / n
    )
    sharpe = mean / std if std > 0 else None
    sortino = mean / downside_dev if downside_dev > 0 else None
    max_dd = _max_drawdown(values)
    recovery = total / max_dd if max_dd > 0 else None
    p05 = _percentile(values, 0.05)
    p50 = _percentile(values, 0.50)
    p95 = _percentile(values, 0.95)
    tail_count = max(1, math.ceil(n * 0.05))
    cvar05 = sum(sorted(values)[:tail_count]) / tail_count

    skewness: float | None = None
    if n >= 3 and std > 0:
        skewness = sum((value - mean) ** 3 for value in values) / n / (std ** 3)

    return {
        "sample": n,
        "status": "OBSERVED",
        "basis": "net-R-per-trade",
        "annualized": False,
        "mean_r": _fmt(mean),
        "total_r": _fmt(total),
        "standard_deviation_r": _fmt(std),
        "downside_deviation_r_mar0": _fmt(downside_dev),
        "sharpe_per_trade_nonannualized": _fmt(sharpe),
        "sortino_per_trade_nonannualized_mar0": _fmt(sortino),
        "profit_factor": _fmt(gains / losses) if losses > 0 else None,
        "win_rate": _fmt(sum(value > 0 for value in values) / n),
        "loss_rate": _fmt(sum(value < 0 for value in values) / n),
        "max_drawdown_r": _fmt(max_dd),
        "recovery_factor_total_r_over_max_dd": _fmt(recovery),
        "max_losing_streak": _max_losing_streak(values),
        "worst_trade_r": _fmt(min(values)),
        "best_trade_r": _fmt(max(values)),
        "p05_trade_r": _fmt(p05),
        "median_trade_r": _fmt(p50),
        "p95_trade_r": _fmt(p95),
        "cvar_05_trade_r": _fmt(cvar05),
        "skewness": _fmt(skewness),
        "calmar_mar": {
            "status": NOT_EVALUATED,
            "reason": (
                "Annualized return/time horizon is not part of the normalized "
                "R-series; recovery factor is reported instead."
            ),
        },
    }


def _role(spec: dict[str, Any]) -> str:
    return str(spec.get("evidence_role", "DEVELOPMENT_RESEARCH"))


def _status_from_bool(value: bool) -> str:
    return PASS if value else FAIL


def evaluate_certification_readiness(
    profile: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
    scientific_battery: dict[str, Any],
) -> dict[str, Any]:
    policy = profile.get("certification_policy", {})
    hard_dd = _d(
        policy.get(
            "hard_dd_max_r",
            profile["science"]["hard_dd_max_r"],
        )
    )
    lanes = tuple(profile["lanes"])
    roles = {
        lane: _role(profile["lanes"][lane])
        for lane in lanes
    }
    fresh_oos_lanes = tuple(
        lane for lane in lanes if roles[lane] == "FRESH_OOS"
    )
    wfo_oos_lanes = tuple(
        lane for lane in lanes if roles[lane] == "WALK_FORWARD_OOS"
    )
    development_lanes = tuple(
        lane for lane in lanes if roles[lane] == "DEVELOPMENT_RESEARCH"
    )

    variants: dict[str, Any] = {}
    for variant, science_row in scientific_battery["variants"].items():
        lane_metrics: dict[str, Any] = {}
        all_observed_dd_pass = True
        for lane in lanes:
            row = payloads[lane]["variants"][variant]
            diagnostics = risk_adjusted_metrics(row["net_r_values"])
            dd = diagnostics.get("max_drawdown_r")
            dd_pass = (
                dd is not None
                and _d(dd) <= hard_dd
            )
            all_observed_dd_pass &= dd_pass
            lane_metrics[lane] = {
                "evidence_role": roles[lane],
                "risk_adjusted": diagnostics,
                "hard_dd_gate": {
                    "status": _status_from_bool(dd_pass),
                    "observed_r": dd,
                    "maximum_r": format(hard_dd, "f"),
                },
            }

        fresh_oos_status = (
            PASS
            if fresh_oos_lanes
            and all(
                lane_metrics[lane]["hard_dd_gate"]["status"] == PASS
                for lane in fresh_oos_lanes
            )
            else (
                FAIL
                if fresh_oos_lanes
                else NOT_EVALUATED
            )
        )
        wfo_oos_status = PASS if wfo_oos_lanes else NOT_EVALUATED
        pure_edge_flags = [
            bool(
                payloads[lane].get("governance", {}).get(
                    "pure_edge_replay",
                    False,
                )
            )
            and not bool(
                payloads[lane].get("governance", {}).get(
                    "sizing_for_certification_used",
                    True,
                )
            )
            for lane in lanes
        ]
        pure_edge_status = (
            PASS if pure_edge_flags and all(pure_edge_flags) else NOT_EVALUATED
        )

        pre_oos_pass = (
            all_observed_dd_pass
            and bool(science_row["development_survivor"])
            and pure_edge_status == PASS
        )
        ready_for_fresh_oos = (
            pre_oos_pass
            and (
                not bool(policy.get("walk_forward_oos_required", True))
                or wfo_oos_status == PASS
            )
        )
        if not pre_oos_pass:
            readiness = "NOT_READY_PRE_OOS"
        elif bool(policy.get("walk_forward_oos_required", True)) and wfo_oos_status != PASS:
            readiness = "BLOCKED_WALK_FORWARD_OOS"
        elif bool(policy.get("fresh_oos_required", True)) and fresh_oos_status != PASS:
            readiness = "READY_FOR_FRESH_OOS"
        else:
            readiness = "READY_FOR_SOVEREIGN_CERTIFICATION_REVIEW"

        variants[variant] = {
            "lanes": lane_metrics,
            "requirements": {
                "pure_edge_no_sizing": {
                    "status": pure_edge_status,
                    "required": True,
                },
                "observed_drawdown_at_most_6r": {
                    "status": _status_from_bool(all_observed_dd_pass),
                    "required": True,
                    "maximum_r": format(hard_dd, "f"),
                },
                "scientific_development_battery": {
                    "status": _status_from_bool(
                        bool(science_row["development_survivor"])
                    ),
                    "required": True,
                },
                "walk_forward_oos": {
                    "status": wfo_oos_status,
                    "required": bool(
                        policy.get("walk_forward_oos_required", True)
                    ),
                    "lanes": list(wfo_oos_lanes),
                },
                "fresh_oos_holdout": {
                    "status": fresh_oos_status,
                    "required": bool(policy.get("fresh_oos_required", True)),
                    "lanes": list(fresh_oos_lanes),
                },
                "sharpe": {
                    "status": REPORTED_ONLY,
                    "required_threshold": None,
                    "note": (
                        "Reported as non-annualized per-trade Sharpe. "
                        "No sovereign threshold is declared in this profile."
                    ),
                },
                "sortino": {
                    "status": REPORTED_ONLY,
                    "required_threshold": None,
                    "note": (
                        "Reported as non-annualized per-trade Sortino at MAR=0. "
                        "No sovereign threshold is declared in this profile."
                    ),
                },
            },
            "development_evidence_lanes": list(development_lanes),
            "walk_forward_oos_lanes": list(wfo_oos_lanes),
            "fresh_oos_lanes": list(fresh_oos_lanes),
            "ready_for_fresh_oos": ready_for_fresh_oos,
            "readiness_status": readiness,
            "certified": False,
            "certification_authorized": False,
        }

    return {
        "schema": "qore.github-trader-lab.certification-readiness.v1",
        "profile_id": profile["profile_id"],
        "subject": profile["subject"],
        "metric_conventions": {
            "return_basis": "net R per trade",
            "sharpe": "mean(R)/sample_stdev(R), non-annualized",
            "sortino": "mean(R)/downside_deviation(R, MAR=0), non-annualized",
            "recovery_factor": "total_R/max_drawdown_R",
            "calmar_mar": "not computed without annualized return horizon",
            "oos": (
                "Only explicitly bound WALK_FORWARD_OOS/FRESH_OOS lanes count; "
                "development folds never self-promote to OOS."
            ),
        },
        "evidence_roles": roles,
        "variants": variants,
        "governance": {
            "research_only": True,
            "fail_closed_oos": True,
            "fresh_holdout_opened_by_lab": False,
            "certification_claimed": False,
            "sovereign_certification_replaced": False,
        },
    }
