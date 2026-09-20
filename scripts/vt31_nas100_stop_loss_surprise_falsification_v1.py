"""Stop-loss surprise falsification for VT31_NAS100.

Diagnostic-only research over consumed evidence.

Purpose:
- explain every negative terminal outcome by stop/lifecycle anatomy;
- distinguish valid structural invalidation from premature/timing failures;
- detect cases where the original structural target was reached only AFTER a
  stop, using strictly later M1 bars to avoid same-bar ordering assumptions;
- intersect stop anatomy with causal pre-entry and already-closed sequence state;
- expose states that reproduce across R5/R6/R8/consumed.

No policy is changed. No alternative stop is selected here.
Silver Bullet remains frozen.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_sequence_state_interaction_forensics_v1 as seq

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.stop_loss_surprise_falsification.v1"
MARKET = "NAS100"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _opt_d(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _dt(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _touches_target(
    bar: object,
    *,
    side: str,
    target: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= target
    return _d(getattr(bar, "low")) <= target


def _mfe_bucket(value: object) -> str:
    v = _opt_d(value) or Decimal(0)
    if v < Decimal("0.10"):
        return "lt_0_10R"
    if v < Decimal("0.50"):
        return "0_10_0_50R"
    if v < Decimal("1.00"):
        return "0_50_1R"
    return "ge_1R"


def _mae_bucket(value: object) -> str:
    v = _opt_d(value) or Decimal(0)
    if v < Decimal("0.25"):
        return "lt_0_25R"
    if v < Decimal("0.50"):
        return "0_25_0_50R"
    if v < Decimal("0.75"):
        return "0_50_0_75R"
    return "ge_0_75R"


def _delay_bucket(minutes: int | None) -> str:
    if minutes is None:
        return "not_reached"
    if minutes <= 5:
        return "le_5m"
    if minutes <= 15:
        return "6_15m"
    if minutes <= 30:
        return "16_30m"
    if minutes <= 60:
        return "31_60m"
    return "gt_60m"


def _loss_class(row: dict[str, object]) -> str:
    path = str(row.get("loss_path_class"))
    reason = str(row.get("exit_reason"))
    if reason == "initial-stop":
        if path == "DEAD_ON_ARRIVAL":
            return "INITIAL_STOP_DOA"
        if path == "WEAK_FOLLOW_THROUGH":
            return "INITIAL_STOP_WEAK_FOLLOW"
        return "INITIAL_STOP_OTHER"
    if reason == "breakeven-stop":
        return "BREAKEVEN_STOP"
    if "journey-lock" in reason or "journey-be" in reason:
        return "PROTECTIVE_MANAGEMENT_STOP"
    if reason == "16:00-lifecycle":
        return "NEGATIVE_LIFECYCLE_CLOSE"
    return f"OTHER:{reason}"


def _post_exit_target(
    row: dict[str, object],
    day_bars: tuple[object, ...],
) -> tuple[bool, int | None]:
    target = _opt_d(row.get("structural_target"))
    if target is None:
        return False, None
    side = str(row.get("side"))
    exit_at = _dt(row["exit_at"])

    # Strictly later M1 bars only: no same-bar ordering inference.
    for bar in day_bars:
        opened = cast(datetime, getattr(bar, "opened_at"))
        if opened < exit_at:
            continue
        if _wall(opened) >= (16, 0, 0):
            break
        if _touches_target(bar, side=side, target=target):
            minutes = max(
                0,
                int((opened - exit_at).total_seconds() // 60),
            )
            return True, minutes
    return False, None


def _state_metrics(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    values = [_d(row["capital_weighted_net_r"]) for row in rows]
    reached = [
        row
        for row in rows
        if bool(row.get("post_exit_target_reached"))
    ]
    return {
        "sample": len(rows),
        "total_r": format(sum(values, Decimal(0)), "f"),
        "mean_r": (
            "0"
            if not rows
            else format(
                sum(values, Decimal(0)) / Decimal(len(rows)),
                "f",
            )
        ),
        "post_exit_target_count": len(reached),
        "post_exit_target_rate": (
            "0"
            if not rows
            else format(
                Decimal(len(reached)) / Decimal(len(rows)),
                "f",
            )
        ),
        "loss_class_counts": dict(
            Counter(str(row["stop_loss_class"]) for row in rows)
        ),
        "post_target_delay_counts": dict(
            Counter(
                str(row["post_target_delay_bucket"])
                for row in reached
            )
        ),
    }


def _group(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = "|".join(f"{field}={row.get(field)}" for field in fields)
        grouped[key].append(row)
    return {
        key: _state_metrics(items)
        for key, items in sorted(grouped.items())
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, stats = alt._current_rows(path)
    annotated = seq._annotate(rows)

    (
        series,
        account,
        fingerprint,
        checked,
        evidence_sha,
        provider,
    ) = load_market_evidence(path)
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError(
            "stop-loss surprise falsification requires NAS100"
        )

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    losses: list[dict[str, object]] = []
    censored_geometry = 0
    for row in annotated:
        if _d(row["capital_weighted_net_r"]) >= 0:
            continue

        updated = dict(row)
        updated["stop_loss_class"] = _loss_class(updated)
        updated["mfe_bucket"] = _mfe_bucket(updated.get("mfe_r"))
        updated["mae_bucket"] = _mae_bucket(updated.get("mae_r"))

        local_day = date.fromisoformat(str(updated["local_date"]))
        day_bars = by_day.get(local_day)
        if day_bars is None or updated.get("exit_at") is None:
            updated["post_exit_target_reached"] = False
            updated["post_exit_target_delay_minutes"] = None
            updated["post_target_delay_bucket"] = "unavailable"
            censored_geometry += 1
        else:
            reached, minutes = _post_exit_target(updated, day_bars)
            updated["post_exit_target_reached"] = reached
            updated["post_exit_target_delay_minutes"] = minutes
            updated["post_target_delay_bucket"] = _delay_bucket(minutes)

        if str(updated["stop_loss_class"]).startswith("INITIAL_STOP"):
            updated["structural_stop_interpretation"] = (
                "PREMATURE_OR_TIMING_FAILURE"
                if bool(updated["post_exit_target_reached"])
                else "STRUCTURAL_INVALIDATION_NOT_FALSIFIED"
            )
        elif updated["stop_loss_class"] in {
            "BREAKEVEN_STOP",
            "PROTECTIVE_MANAGEMENT_STOP",
        }:
            updated["structural_stop_interpretation"] = (
                "PROTECTION_CUT_WINNING_JOURNEY"
                if bool(updated["post_exit_target_reached"])
                else "PROTECTION_NOT_FALSIFIED_BY_LATER_TARGET"
            )
        else:
            updated["structural_stop_interpretation"] = (
                "NON_INITIAL_STOP_OR_LIFECYCLE"
            )
        losses.append(updated)

    fields = (
        ("stop_loss_class",),
        ("loss_path_class",),
        ("mfe_bucket",),
        ("mae_bucket",),
        ("tier",),
        ("entry_family",),
        ("side",),
        ("pre_loss_streak_bucket",),
        ("entry_family", "pre_loss_streak_bucket"),
        ("tier", "entry_family"),
        ("reference_volatility_state",),
        ("current_path_bucket",),
        ("risk_ref_bucket",),
        ("reclaim_age_bucket",),
        ("confirmation_latency_bucket",),
        ("entry_family", "current_path_bucket"),
        ("entry_family", "risk_ref_bucket"),
        ("entry_family", "confirmation_latency_bucket"),
    )

    initial = [
        row
        for row in losses
        if str(row["stop_loss_class"]).startswith("INITIAL_STOP")
    ]
    protective = [
        row
        for row in losses
        if row["stop_loss_class"]
        in {"BREAKEVEN_STOP", "PROTECTIVE_MANAGEMENT_STOP"}
    ]
    post_target = [
        row
        for row in losses
        if bool(row["post_exit_target_reached"])
    ]

    return {
        "schema": SCHEMA,
        "partition": partition,
        "loss_count": len(losses),
        "loss_metrics": residual._metrics(losses),
        "overall_stop_anatomy": _state_metrics(losses),
        "initial_stop_anatomy": _state_metrics(initial),
        "protective_stop_anatomy": _state_metrics(protective),
        "post_exit_target_recovery": _state_metrics(post_target),
        "dimensions": {
            "|".join(spec): _group(losses, spec)
            for spec in fields
        },
        "censored_geometry_count": censored_geometry,
        "source_stats": stats,
        "diagnostics": diagnostics,
        "evidence": {
            **evidence,
            "account_fingerprint": account,
            "evidence_fingerprint": fingerprint,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "strictly_later_m1_for_post_stop_target": True,
            "same_bar_ordering_inferred": False,
            "current_terminal_pnl_runtime_input": False,
            "post_exit_target_runtime_input": False,
            "trade_policy_changed": False,
            "risk_policy_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "target_changed": False,
            "silver_bullet_changed": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "loss_count": payload["loss_count"],
                "overall_stop_anatomy": payload["overall_stop_anatomy"],
                "initial_stop_anatomy": payload["initial_stop_anatomy"],
                "protective_stop_anatomy": payload["protective_stop_anatomy"],
                "censored_geometry_count": payload[
                    "censored_geometry_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
