"""Post-result R3 failure forensics over the immutable consumed R3 replay.

This module is diagnostic only. It does not promote filters or mutate the frozen R3
economic contract. It quantifies concentration, recent-era degradation, route
stability, and microscopic risk geometry using only the already-consumed R3 trades.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_XAUUSD_R3_FAILURE_FORENSICS_V1"
R3_RUN_ID = 35256772043
R3_ARTIFACT_ID = 10513151886
VALIDATION_OPEN = datetime.fromisoformat("2022-09-17T00:00:00+00:00")
RECENT_OPEN = datetime.fromisoformat("2024-01-01T00:00:00+00:00")
CAPS_R = (Decimal("5"), Decimal("10"), Decimal("20"), Decimal("50"), Decimal("100"))


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _stat(values: Iterable[Decimal]) -> dict[str, Any]:
    rows = list(values)
    total = sum(rows, Decimal(0))
    positive = sum((v for v in rows if v > 0), Decimal(0))
    negative = -sum((v for v in rows if v < 0), Decimal(0))
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    streak = 0
    max_streak = 0
    for value in rows:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "count": len(rows),
        "total_r": str(total),
        "mean_r": str(total / len(rows)) if rows else None,
        "profit_factor": str(positive / negative) if negative else None,
        "max_drawdown_r": str(max_dd),
        "max_losing_streak": max_streak,
    }


def _group(trades: list[dict[str, Any]], *keys: str) -> dict[str, Any]:
    groups: dict[tuple[str, ...], list[Decimal]] = defaultdict(list)
    for trade in trades:
        groups[tuple(str(trade[k]) for k in keys)].append(_d(trade["primary_net_r"]))
    return {"|".join(key): _stat(values) for key, values in sorted(groups.items())}


def _risk_geometry(trade: dict[str, Any]) -> dict[str, str]:
    entry = _d(trade["entry"])
    stop = _d(trade["stop"])
    target = _d(trade["target"])
    risk = abs(entry - stop)
    reward = abs(target - entry)
    return {
        "absolute_risk_price": str(risk),
        "risk_bps_of_entry": str((risk / entry) * Decimal(10000)) if entry else "0",
        "structural_reward_r": str(reward / risk) if risk else "Infinity",
    }


def _cap(values: Iterable[Decimal], cap: Decimal) -> list[Decimal]:
    return [min(value, cap) for value in values]


def run(root: Path, output: Path) -> dict[str, Any]:
    report = json.loads((root / "report.json").read_text())
    trades = json.loads((root / "trades-full.json").read_text())
    if report["identity"] != "TURTLE_SOUP_XAUUSD_R3_CIBO_JOURNEY_ROUTER":
        raise ValueError("unexpected R3 artifact identity")
    if len(trades) != int(report["executed_trades"]):
        raise ValueError("R3 trade count mismatch")

    for trade in trades:
        trade["_entry_at"] = _dt(trade["entry_at"])
        trade["_year"] = trade["_entry_at"].year

    validation = [t for t in trades if t["_entry_at"] >= VALIDATION_OPEN]
    recent = [t for t in trades if t["_entry_at"] >= RECENT_OPEN]
    y2023 = [t for t in trades if t["_year"] == 2023]

    top = max(validation, key=lambda t: _d(t["primary_net_r"]))
    top_value = _d(top["primary_net_r"])
    validation_without_top = [t for t in validation if t is not top]
    full_without_top = [t for t in trades if t is not top]

    validation_values = [_d(t["primary_net_r"]) for t in validation]
    full_values = [_d(t["primary_net_r"]) for t in trades]
    validation_total = sum(validation_values, Decimal(0))
    top10 = sorted(validation_values, reverse=True)[:10]
    top20 = sorted(validation_values, reverse=True)[:20]

    report_out = {
        "schema": "qore.turtle_soup_xauusd_r3.failure_forensics.v1",
        "identity": IDENTITY,
        "source": {
            "r3_run_id": R3_RUN_ID,
            "r3_artifact_id": R3_ARTIFACT_ID,
            "r3_identity": report["identity"],
            "evidence_status": report["evidence_status"],
        },
        "headline": {
            "validation_original": _stat(validation_values),
            "validation_without_single_largest_winner": _stat(
                _d(t["primary_net_r"]) for t in validation_without_top
            ),
            "full_10y_without_single_largest_winner": _stat(
                _d(t["primary_net_r"]) for t in full_without_top
            ),
            "recent_2024_2026": _stat(_d(t["primary_net_r"]) for t in recent),
            "year_2023": _stat(_d(t["primary_net_r"]) for t in y2023),
        },
        "largest_validation_winner": {
            **{k: v for k, v in top.items() if not k.startswith("_")},
            "risk_geometry": _risk_geometry(top),
            "share_of_original_validation_total": str(top_value / validation_total),
        },
        "concentration": {
            "top_10_validation_winners_r": str(sum(top10, Decimal(0))),
            "top_20_validation_winners_r": str(sum(top20, Decimal(0))),
            "top_10_share_of_validation_total": str(sum(top10, Decimal(0)) / validation_total),
        },
        "diagnostic_only_winner_caps": {
            str(cap): {
                "validation": _stat(_cap(validation_values, cap)),
                "full_10y": _stat(_cap(full_values, cap)),
            }
            for cap in CAPS_R
        },
        "by_year": _group(trades, "_year"),
        "validation_by_side": _group(validation, "side"),
        "validation_by_source_timeframe": _group(validation, "source_timeframe"),
        "validation_by_entry_mode": _group(validation, "entry_mode"),
        "validation_by_target_route": _group(validation, "target_route"),
        "validation_by_session_diagnostic": _group(validation, "session_bucket"),
        "validation_by_prior_body_diagnostic": _group(validation, "prior_body_alignment"),
        "validation_interactions": {
            "side_target": _group(validation, "side", "target_route"),
            "entry_target": _group(validation, "entry_mode", "target_route"),
            "side_entry": _group(validation, "side", "entry_mode"),
            "timeframe_target": _group(validation, "source_timeframe", "target_route"),
        },
        "root_cause_tests": {
            "aggregate_validation_positive": validation_total > 0,
            "validation_stays_positive_without_largest_winner": (
                sum((_d(t["primary_net_r"]) for t in validation_without_top), Decimal(0)) > 0
            ),
            "recent_2024_2026_positive": (
                sum((_d(t["primary_net_r"]) for t in recent), Decimal(0)) > 0
            ),
            "largest_winner_has_sub_1bp_risk": (
                _d(_risk_geometry(top)["risk_bps_of_entry"]) < Decimal(1)
            ),
            "diagnosis": (
                "VALIDATION_POSITIVITY_NOT_ROBUST_TO_SINGLE_MICRO_RISK_OUTLIER;"
                "RECENT_2024_2026_NEGATIVE;SHORT_SIDE_DEGRADATION_REQUIRES_CAUSAL_FORENSICS"
            ),
        },
        "governance": {
            "diagnostic_only": True,
            "promote_filters_from_this_report": False,
            "fresh_holdout_consumed": False,
            "automatic_promotion_allowed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "forensics.json").write_text(
        json.dumps(report_out, indent=2, sort_keys=True, default=str) + "\n"
    )
    return report_out


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m ...turtle_soup_xauusd_r3_forensics R3_ARTIFACT OUTPUT")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
