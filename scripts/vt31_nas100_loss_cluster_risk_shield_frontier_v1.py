"""Loss-cluster risk shield frontier for VT31_NAS100.

Consumed development evidence only.

The base identity is:
ALLOC_G_CORE_FAMILY_050
+ SHIELD_060
+ SECONDARY Breaker journey protection after a closed +1R checkpoint,
  locking +0.25R on the next M1 when revisited.

This frontier adds only a bounded capital reduction at decision time for two
predeclared states that the existing Loss Sequence Root Cause aggregate found
negative across all four consumed development folds:
- entry_family == order-block
- confirmation_latency_minutes >= 11

No trade is removed. Silver Bullet, admission, entry, initial stop, structural
target, rearm, lifecycle and FVG management remain unchanged.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_alloc_g_breaker_journey_management_frontier_v1 as breaker
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as shield
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.loss_cluster_risk_shield_frontier.v1"
MARKET = "NAS100"
BASE_PROFILE = "ALLOC_G_CORE_FAMILY_050"
BASE_SHIELD = Decimal("0.60")
BREAKER_LOCK_R = Decimal("0.25")

VARIANTS = {
    "BASE_BREAKER_LOCK025": Decimal("1.00"),
    "LOSS_CLUSTER_SHIELD_075": Decimal("0.75"),
    "LOSS_CLUSTER_SHIELD_060": Decimal("0.60"),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _loss_cluster_reasons(row: dict[str, object]) -> tuple[str, ...]:
    reasons: list[str] = []
    if str(row.get("entry_family")) == "order-block":
        reasons.append("ORDER_BLOCK_FAMILY_4OF4_NEGATIVE")

    latency_raw = row.get("confirmation_latency_minutes")
    if latency_raw is not None and int(latency_raw) >= 11:
        reasons.append("CONFIRMATION_LATENCY_11M_PLUS_4OF4_NEGATIVE")

    return tuple(reasons)


def _apply_loss_cluster_shield(
    rows: list[dict[str, object]],
    *,
    multiplier: Decimal,
) -> list[dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        reasons = _loss_cluster_reasons(updated)
        applied = multiplier if reasons else Decimal("1.00")
        updated["loss_cluster_shield_reasons"] = list(reasons)
        updated["loss_cluster_shield_multiplier"] = format(applied, "f")
        updated["requested_risk_r"] = format(
            _d(updated["requested_risk_r"]) * applied,
            "f",
        )
        updated["capital_weighted_net_r"] = format(
            _d(updated["capital_weighted_net_r"]) * applied,
            "f",
        )
        adjusted.append(updated)
    return adjusted


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("loss-cluster risk shield requires NAS100")

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

    managed, management_diag = breaker._apply_management(
        nominal,
        by_day,
        scope="ALL",
        lock_r=BREAKER_LOCK_R,
    )
    alloc_g = allocation._apply_profile(
        managed,
        profile=allocation.PROFILES[BASE_PROFILE],
    )
    shielded = shield._apply_shield(
        alloc_g,
        multiplier=BASE_SHIELD,
    )

    variants: dict[str, object] = {}
    for name, multiplier in VARIANTS.items():
        rows = _apply_loss_cluster_shield(
            shielded,
            multiplier=multiplier,
        )
        metrics = shield._metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"LOSS_CLUSTER_SHIELD:{name}:{partition}",
        )
        annual = (
            shield._annual_blocks(
                rows,
                start=date(2022, 7, 18),
                years=2,
            )
            if partition == "consumed_holdout"
            else []
        )

        shielded_count = 0
        reason_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            reasons = cast(list[str], row["loss_cluster_shield_reasons"])
            if reasons:
                shielded_count += 1
            for reason in reasons:
                reason_counts[reason] += 1

        objectives = {
            "density_300_350": 300 <= len(rows) <= 350,
            "pf_ge_1_50": (
                metrics["profit_factor"] is not None
                and _d(metrics["profit_factor"]) >= Decimal("1.50")
            ),
            "dd_le_6": _d(metrics["max_drawdown_r"]) <= Decimal("6"),
            "mc_positive_ge_0_90": (
                _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
            ),
            "mc_p95_dd_le_15": (
                _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
            ),
        }
        if annual:
            objectives["both_consumed_years_positive"] = all(
                bool(block["positive"]) for block in annual
            )

        variants[name] = {
            "trade_count": len(rows),
            "loss_cluster_shielded_trade_count": shielded_count,
            "loss_cluster_reason_counts": dict(sorted(reason_counts.items())),
            "loss_cluster_multiplier": format(multiplier, "f"),
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "objectives": objectives,
            "passes_economic_objectives": all(objectives.values()),
        }

    status_counts = cast(
        dict[str, int],
        management_diag["status_counts"],
    )

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "base_profile": BASE_PROFILE,
        "base_state_shield": "SHIELD_060",
        "breaker_management": {
            "scope": "SECONDARY_BREAKER_ALL",
            "checkpoint_r": "1.00",
            "lock_r": format(BREAKER_LOCK_R, "f"),
            "eligible_count": status_counts.get("management-eligible", 0),
            "applied_count": status_counts.get("management-protective-exit", 0),
            "ambiguity_count": status_counts.get(
                "ambiguous-protect-vs-target-same-m1",
                0,
            ),
        },
        "variants": variants,
        "diagnostics": {
            "first": first_diag,
            "rearm": rearm_diag,
            "breaker_management": management_diag,
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
            "predeclared_4of4_negative_contexts_only": True,
            "risk_only_extension": True,
            "trade_count_changed": False,
            "silver_bullet_changed": False,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed_at_entry": False,
            "structural_target_changed": False,
            "rearm_changed": False,
            "fvg_management_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_future_journey_label_at_runtime": False,
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
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
