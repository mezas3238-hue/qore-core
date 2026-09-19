"""Adverse partial de-risk frontier for VT31_NAS100.

Consumed development evidence only.

The reference identity is unchanged:
- ALLOC_G_CORE_FAMILY_050
- SHIELD_060
- LOSS_CLUSTER_SHIELD_060
- SECONDARY Breaker closed +1R checkpoint with +0.25R lock

This lab adds the one management capability missing from Core: partial
de-risk on a stable adverse post-fill state. A fixed fraction is realized at
the next M1 open after the causal checkpoint; the remaining fraction keeps
the original frozen management outcome. No trade is filtered.

The adverse states are predeclared from DOA Early Path Forensics V1:
- CP1 close <= -0.50R
- CP1 adverse-dominance >= 4

If the next M1 opens through the original stop/target geometry, the baseline
trade is preserved rather than inventing execution precedence.
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
import vt31_nas100_causal_early_adverse_management_frontier_v1 as adverse
import vt31_nas100_causal_hybrid_density_v2 as hybrid
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_loss_cluster_risk_shield_frontier_v1 as loss_shield
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as shield
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.adverse_partial_derisk_frontier.v1"
MARKET = "NAS100"
BASE_PROFILE = "ALLOC_G_CORE_FAMILY_050"
BASE_SHIELD = Decimal("0.60")
LOSS_CLUSTER_SHIELD = Decimal("0.60")
BREAKER_LOCK_R = Decimal("0.25")

VARIANTS: dict[str, tuple[str, Decimal] | None] = {
    "BASE": None,
    "CP1_CLOSE_M050_DERISK25": ("CLOSE_LE_M050", Decimal("0.25")),
    "CP1_CLOSE_M050_DERISK50": ("CLOSE_LE_M050", Decimal("0.50")),
    "CP1_DOM_GE4_DERISK25": ("ADVERSE_DOM_GE4", Decimal("0.25")),
    "CP1_DOM_GE4_DERISK50": ("ADVERSE_DOM_GE4", Decimal("0.50")),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _partial_row(
    row: dict[str, object],
    bars: tuple[object, ...],
    *,
    rule: str,
    fraction: Decimal,
) -> tuple[dict[str, object], str]:
    updated = dict(row)
    updated["adverse_partial_rule"] = rule
    updated["adverse_partial_fraction"] = format(fraction, "f")
    updated["adverse_partial_applied"] = False

    features = adverse._checkpoint_features(
        row,
        bars,
        checkpoint_bars=1,
    )
    if features is None:
        if any(
            field not in row
            for field in ("entry", "initial_stop", "structural_target")
        ):
            return updated, "missing-geometry-preserved"
        return updated, "checkpoint-unavailable-before-baseline-exit"

    checkpoint_at, close_r, mfe, dominance = features
    updated["adverse_partial_checkpoint_at"] = checkpoint_at.isoformat()
    updated["adverse_partial_close_r"] = format(close_r, "f")
    updated["adverse_partial_mfe_r"] = format(mfe, "f")
    updated["adverse_partial_dominance"] = format(dominance, "f")

    if not adverse._qualifies(
        rule,
        close_r=close_r,
        adverse_dominance=dominance,
    ):
        return updated, "state-not-triggered"

    baseline_exit_at = datetime.fromisoformat(cast(str, row["exit_at"]))
    next_bar: object | None = None
    for bar in bars:
        opened_at = cast(datetime, getattr(bar, "opened_at"))
        if opened_at == checkpoint_at:
            next_bar = bar
            break
    if next_bar is None:
        return updated, "next-m1-missing"

    next_opened_at = cast(datetime, getattr(next_bar, "opened_at"))
    if next_opened_at >= baseline_exit_at:
        return updated, "baseline-exit-precedes-next-open"

    side = str(row["side"])
    entry = _d(row["entry"])
    stop = _d(row["initial_stop"])
    target = _d(row["structural_target"])
    risk = abs(entry - stop)
    if risk <= 0:
        return updated, "invalid-risk"

    opened = _d(getattr(next_bar, "open"))
    if adverse._open_through_geometry(
        side=side,
        opened=opened,
        stop=stop,
        target=target,
    ):
        updated["adverse_partial_next_open_ambiguous"] = True
        return updated, "next-open-through-stop-or-target"

    realized_r = (
        (opened - entry) / risk
        if side == "long"
        else (entry - opened) / risk
    )
    baseline_r = _d(row["r_multiple"])
    runner_fraction = Decimal("1.00") - fraction
    combined_r = fraction * realized_r + runner_fraction * baseline_r

    requested_risk = _d(row["requested_risk_r"])
    updated["r_multiple"] = format(combined_r, "f")
    updated["capital_weighted_net_r"] = format(
        requested_risk * (combined_r - hybrid.FRICTION),
        "f",
    )
    updated["adverse_partial_applied"] = True
    updated["adverse_partial_realized_r"] = format(realized_r, "f")
    updated["adverse_partial_runner_fraction"] = format(
        runner_fraction, "f"
    )
    updated["adverse_partial_runner_baseline_r"] = format(
        baseline_r, "f"
    )
    updated["adverse_partial_combined_r"] = format(combined_r, "f")
    updated["adverse_partial_at"] = next_opened_at.isoformat()
    return updated, "partial-derisk-applied"


def _apply_partial(
    rows: list[dict[str, object]],
    by_day: dict[date, tuple[object, ...]],
    *,
    rule: str,
    fraction: Decimal,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    adjusted: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    for row in rows:
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        bars = by_day.get(local_day)
        if bars is None:
            counts["missing-day-bars"] += 1
            adjusted.append(dict(row))
            continue
        updated, status = _partial_row(
            row,
            bars,
            rule=rule,
            fraction=fraction,
        )
        counts[status] += 1
        adjusted.append(updated)

    adjusted.sort(key=lambda row: cast(str, row["signal_at"]))
    return adjusted, dict(sorted(counts.items()))


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("adverse partial de-risk requires NAS100")

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
    base_rows = loss_shield._apply_loss_cluster_shield(
        state_shielded,
        multiplier=LOSS_CLUSTER_SHIELD,
    )

    variants: dict[str, object] = {}
    for name, spec in VARIANTS.items():
        if spec is None:
            rows = [dict(row) for row in base_rows]
            status_counts = {"baseline": len(rows)}
        else:
            rule, fraction = spec
            rows, status_counts = _apply_partial(
                base_rows,
                by_day,
                rule=rule,
                fraction=fraction,
            )

        metrics = shield._metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"ADVERSE_PARTIAL:{name}:{partition}",
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
        applied = sum(
            bool(row.get("adverse_partial_applied"))
            for row in rows
        )
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
            "spec": (
                None
                if spec is None
                else {
                    "checkpoint_bars": 1,
                    "rule": spec[0],
                    "partial_fraction": format(spec[1], "f"),
                }
            ),
            "partial_applied_count": applied,
            "status_counts": status_counts,
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "objectives": objectives,
            "passes_economic_objectives": all(objectives.values()),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "base_profile": BASE_PROFILE,
        "base_state_shield": "SHIELD_060",
        "base_loss_cluster_shield": "LOSS_CLUSTER_SHIELD_060",
        "breaker_management": "LOCK025_AFTER_CLOSED_1R",
        "variants": variants,
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
            "new_adverse_partial_capability_was_missing_from_core": True,
            "rules_derived_from_stable_4of4_doa_forensics": True,
            "closed_m1_checkpoint_only": True,
            "partial_realized_next_m1_open": True,
            "runner_keeps_original_management": True,
            "trade_count_changed": False,
            "trade_admission_changed": False,
            "silver_bullet_changed": False,
            "entry_changed": False,
            "initial_stop_changed_at_entry": False,
            "structural_target_changed": False,
            "rearm_changed": False,
            "uses_terminal_pnl_to_trigger_partial": False,
            "uses_outcome_class_at_runtime": False,
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
