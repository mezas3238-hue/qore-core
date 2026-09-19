"""Early post-fill path forensics for VT31_NAS100 DEAD_ON_ARRIVAL.

Consumed development evidence only. Diagnostic-only.

The current reference identity is preserved:
- ALLOC_G_CORE_FAMILY_050
- SHIELD_060
- loss-cluster shield 0.60
- SECONDARY Breaker closed +1R checkpoint with +0.25R lock

This lab does not alter any trade. It snapshots the path after 1/2/3/5 fully
closed post-fill M1 bars, only when the trade is still alive at that close.
Terminal outcome labels are attached afterward for research. The purpose is to
discover whether DEAD_ON_ARRIVAL losses have a causal early-path signature
that generalizes across R5/R6/R8/consumed before any new management rule is
tested.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_alloc_g_breaker_journey_management_frontier_v1 as breaker
import vt31_nas100_loss_cluster_risk_shield_frontier_v1 as loss_shield
import vt31_nas100_ny_journey_bifurcation_forensics_v1 as journey
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as shield
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.doa_early_path_forensics.v1"
MARKET = "NAS100"
BASE_PROFILE = "ALLOC_G_CORE_FAMILY_050"
BASE_SHIELD = Decimal("0.60")
LOSS_CLUSTER_SHIELD = Decimal("0.60")
BREAKER_LOCK_R = Decimal("0.25")
CHECKPOINTS = (1, 2, 3, 5)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _bucket_mfe(value: Decimal) -> str:
    if value < Decimal("0.10"):
        return "lt_0_10R"
    if value < Decimal("0.25"):
        return "0_10_0_25R"
    if value < Decimal("0.50"):
        return "0_25_0_50R"
    return "ge_0_50R"


def _bucket_mae(value: Decimal) -> str:
    if value < Decimal("0.25"):
        return "lt_0_25R"
    if value < Decimal("0.50"):
        return "0_25_0_50R"
    if value < Decimal("0.75"):
        return "0_50_0_75R"
    return "ge_0_75R"


def _bucket_close(value: Decimal) -> str:
    if value <= Decimal("-0.50"):
        return "le_m0_50R"
    if value <= Decimal("-0.25"):
        return "m0_50_m0_25R"
    if value < Decimal("0"):
        return "m0_25_0R"
    if value < Decimal("0.25"):
        return "0_0_25R"
    return "ge_0_25R"


def _bucket_ratio(value: Decimal) -> str:
    if value < Decimal("0.25"):
        return "lt_0_25"
    if value < Decimal("0.50"):
        return "0_25_0_50"
    if value < Decimal("0.75"):
        return "0_50_0_75"
    return "ge_0_75"


def _bucket_dominance(value: Decimal) -> str:
    if value < Decimal("1.0"):
        return "lt_1"
    if value < Decimal("2.0"):
        return "1_2"
    if value < Decimal("4.0"):
        return "2_4"
    return "ge_4"


def _outcome_class(row: dict[str, object]) -> str:
    net = _d(row["capital_weighted_net_r"])
    if net >= 0:
        return "NON_LOSS"
    reason = str(row.get("exit_reason"))
    mfe_raw = row.get("mfe_r")
    mfe = Decimal(0) if mfe_raw is None else _d(mfe_raw)
    if reason == "breakeven-stop":
        return "BREAKEVEN_FRICTION_LOSS"
    if mfe >= Decimal("1.00"):
        return "GIVEBACK_AFTER_1R_PLUS"
    if reason == "initial-stop" and mfe < Decimal("0.50"):
        return "DEAD_ON_ARRIVAL"
    if reason == "initial-stop" and mfe < Decimal("1.00"):
        return "WEAK_FOLLOW_THROUGH"
    if reason == "16:00-lifecycle":
        return "NEGATIVE_LIFECYCLE_CLOSE"
    return "OTHER_LOSS"


def _observation(
    row: dict[str, object],
    bars: tuple[object, ...],
    *,
    checkpoint_bars: int,
) -> dict[str, object] | None:
    required = (
        "entry",
        "initial_stop",
        "structural_target",
        "filled_at",
        "exit_at",
    )
    if any(field not in row for field in required):
        return None

    side = str(row["side"])
    entry = _d(row["entry"])
    stop = _d(row["initial_stop"])
    risk = abs(entry - stop)
    if risk <= 0:
        return None

    filled_at = datetime.fromisoformat(cast(str, row["filled_at"]))
    exit_at = datetime.fromisoformat(cast(str, row["exit_at"]))

    observed: list[object] = []
    for bar in bars:
        opened_at = cast(datetime, getattr(bar, "opened_at"))
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        if opened_at < filled_at:
            continue
        # A decision at this close is only causal if the baseline/current
        # position is still alive after the close.
        if closed_at >= exit_at:
            break
        observed.append(bar)
        if len(observed) == checkpoint_bars:
            break

    if len(observed) != checkpoint_bars:
        return None

    mfe = Decimal(0)
    mae = Decimal(0)
    for bar in observed:
        favorable, adverse = specialist.baseline._favorable_adverse(
            bar,
            side,
            entry,
            risk,
        )
        mfe = max(mfe, favorable)
        mae = max(mae, adverse)

    last = observed[-1]
    close = _d(getattr(last, "close"))
    close_r = (
        (close - entry) / risk
        if side == "long"
        else (entry - close) / risk
    )
    path = tuple(observed)
    efficiency = journey._path_efficiency(path, side=side, entry=entry)
    overlap = journey._overlap_rate(path)
    close_ratio = journey._directional_close_ratio(
        path,
        side=side,
        entry=entry,
    )
    body_ratio = journey._directional_body_ratio(path, side=side)
    dominance = (mae + Decimal("0.05")) / (mfe + Decimal("0.05"))

    mfe_bucket = _bucket_mfe(mfe)
    mae_bucket = _bucket_mae(mae)
    close_bucket = _bucket_close(close_r)
    efficiency_bucket = _bucket_ratio(efficiency)
    overlap_bucket = _bucket_ratio(overlap)
    close_ratio_bucket = _bucket_ratio(close_ratio)
    body_ratio_bucket = _bucket_ratio(body_ratio)
    dominance_bucket = _bucket_dominance(dominance)

    outcome = _outcome_class(row)
    return {
        "partition": row.get("partition"),
        "local_date": row["local_date"],
        "signal_at": row["signal_at"],
        "tier": row.get("tier"),
        "family": row.get("entry_family"),
        "side": row.get("side"),
        "checkpoint_bars": checkpoint_bars,
        "checkpoint_at": cast(
            datetime, getattr(last, "closed_at")
        ).isoformat(),
        "mfe_r": format(mfe, "f"),
        "mfe_bucket": mfe_bucket,
        "mae_r": format(mae, "f"),
        "mae_bucket": mae_bucket,
        "close_r": format(close_r, "f"),
        "close_bucket": close_bucket,
        "path_efficiency": format(efficiency, "f"),
        "path_efficiency_bucket": efficiency_bucket,
        "overlap_rate": format(overlap, "f"),
        "overlap_rate_bucket": overlap_bucket,
        "directional_close_ratio": format(close_ratio, "f"),
        "directional_close_ratio_bucket": close_ratio_bucket,
        "directional_body_ratio": format(body_ratio, "f"),
        "directional_body_ratio_bucket": body_ratio_bucket,
        "adverse_dominance": format(dominance, "f"),
        "adverse_dominance_bucket": dominance_bucket,
        "mfe_mae_state": f"{mfe_bucket}|{mae_bucket}",
        "mfe_close_state": f"{mfe_bucket}|{close_bucket}",
        "mae_close_state": f"{mae_bucket}|{close_bucket}",
        "preentry_h1_state": row.get("h1_state"),
        "preentry_premarket_state": row.get("premarket_state"),
        "preentry_cash_open_state": row.get("cash_open_state"),
        "preentry_last_structure_family": row.get(
            "last_structure_event_family"
        ),
        "preentry_confirmation_latency_minutes": row.get(
            "confirmation_latency_minutes"
        ),
        "outcome_class": outcome,
        "is_doa": outcome == "DEAD_ON_ARRIVAL",
        "is_non_loss": outcome == "NON_LOSS",
        "outcome_label_research_only": True,
    }


FEATURE_FIELDS = (
    "mfe_bucket",
    "mae_bucket",
    "close_bucket",
    "path_efficiency_bucket",
    "overlap_rate_bucket",
    "directional_close_ratio_bucket",
    "directional_body_ratio_bucket",
    "adverse_dominance_bucket",
    "mfe_mae_state",
    "mfe_close_state",
    "mae_close_state",
    "family",
    "tier",
    "side",
)


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    n = len(rows)
    doa = sum(bool(row["is_doa"]) for row in rows)
    non_loss = sum(bool(row["is_non_loss"]) for row in rows)
    return {
        "sample": n,
        "doa_count": doa,
        "doa_rate": (
            "0" if n == 0 else format(Decimal(doa) / Decimal(n), "f")
        ),
        "non_loss_count": non_loss,
        "non_loss_rate": (
            "0"
            if n == 0
            else format(Decimal(non_loss) / Decimal(n), "f")
        ),
        "outcome_counts": dict(
            sorted(Counter(str(row["outcome_class"]) for row in rows).items())
        ),
    }


def _diagnostics(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    baseline = _stats(rows)
    baseline_doa = _d(baseline["doa_rate"])
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for field in FEATURE_FIELDS:
            grouped[f"{field}={row.get(field)}"].append(row)

    result: dict[str, dict[str, object]] = {}
    for key, items in sorted(grouped.items()):
        item = _stats(items)
        item["doa_rate_delta_vs_checkpoint"] = format(
            _d(item["doa_rate"]) - baseline_doa,
            "f",
        )
        result[key] = item
    return result


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("DOA early path forensics requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    first_rows, first_diag = corrective._first_rows(
        by_day,
        context_by_day,
        evidence=evidence,
        alt_partial_r=None,
        secondary_route_policy="ORIGINAL",
    )
    rearm_rows, rearm_diag = corrective._rearm_rows(
        by_day,
        context_by_day,
        first_rows,
        evidence=evidence,
        rearm_partial_r=None,
    )
    nominal = sorted(
        [*first_rows, *rearm_rows],
        key=lambda row: cast(str, row["signal_at"]),
    )

    managed, breaker_diag = breaker._apply_management(
        nominal,
        by_day,
        scope="ALL",
        lock_r=BREAKER_LOCK_R,
    )
    alloc_g = allocation._apply_profile(
        managed,
        profile=allocation.PROFILES[BASE_PROFILE],
    )
    state_shielded = shield._apply_shield(
        alloc_g,
        multiplier=BASE_SHIELD,
    )
    current_rows = loss_shield._apply_loss_cluster_shield(
        state_shielded,
        multiplier=LOSS_CLUSTER_SHIELD,
    )

    observations: list[dict[str, object]] = []
    status: Counter[str] = Counter()
    for row in current_rows:
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        bars = by_day.get(local_day)
        if not bars:
            status["missing-day-bars"] += 1
            continue
        if any(
            field not in row
            for field in ("entry", "initial_stop", "structural_target")
        ):
            status["missing-geometry-preserved-outside-forensics"] += 1
            continue
        for checkpoint in CHECKPOINTS:
            obs = _observation(
                row,
                bars,
                checkpoint_bars=checkpoint,
            )
            if obs is None:
                status[f"checkpoint-{checkpoint}-unavailable"] += 1
                continue
            obs["partition"] = partition
            observations.append(obs)
            status[f"checkpoint-{checkpoint}-observed"] += 1

    by_checkpoint: dict[str, object] = {}
    for checkpoint in CHECKPOINTS:
        selected = [
            row
            for row in observations
            if int(cast(int, row["checkpoint_bars"])) == checkpoint
        ]
        by_checkpoint[str(checkpoint)] = {
            "baseline": _stats(selected),
            "feature_diagnostics": _diagnostics(selected),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "base_profile": BASE_PROFILE,
        "base_state_shield": "SHIELD_060",
        "base_loss_cluster_shield": "LOSS_CLUSTER_SHIELD_060",
        "breaker_management": "LOCK025_AFTER_CLOSED_1R",
        "checkpoints_closed_m1": list(CHECKPOINTS),
        "by_checkpoint": by_checkpoint,
        "observations": observations,
        "status_counts": dict(sorted(status.items())),
        "diagnostics": {
            "first": first_diag,
            "rearm": rearm_diag,
            "breaker": breaker_diag,
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "post_outcome_labels_research_only": True,
            "checkpoint_uses_closed_post_fill_m1_only": True,
            "trade_count_changed": False,
            "trade_admission_changed": False,
            "management_changed": False,
            "silver_bullet_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_future_bars_for_checkpoint_features": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_date_at_runtime": False,
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
                "by_checkpoint": payload["by_checkpoint"],
                "status_counts": payload["status_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
