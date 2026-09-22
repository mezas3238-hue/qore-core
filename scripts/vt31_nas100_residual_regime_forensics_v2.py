"""Residual regime forensics for the current VT31_NAS100 reference stack.

Consumed development evidence only. Diagnostic-only.

Reference stack:
- ALLOC_G_CORE_FAMILY_050
- SHIELD_060
- SECONDARY Breaker closed +1R -> +0.25R lock
- LOSS_CLUSTER_SHIELD_060

The consumed Y1/Y2 split is diagnostic only. Calendar identity, fold identity,
terminal PnL and future journey labels are never runtime inputs.

Primary causal analysis intentionally excludes H4/H1 state. Silver Bullet is
frozen to its native M1/reference/session anatomy.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

import vt31_nas100_alloc_g_breaker_journey_management_frontier_v1 as breaker
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_loss_cluster_risk_shield_frontier_v1 as loss_shield
import vt31_nas100_r5_alloc_g_regime_root_cause_forensics_v1 as regime
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as shield
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_r5_loss_sequence_root_cause_forensics_v1 as loss_root
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.residual_regime_forensics.v2"
MARKET = "NAS100"
BASE_PROFILE = "ALLOC_G_CORE_FAMILY_050"
BASE_SHIELD = Decimal("0.60")
LOSS_CLUSTER_SHIELD = Decimal("0.60")
BREAKER_LOCK_R = Decimal("0.25")

CONSUMED_BLOCKS = {
    "Y1_WEAK": (date(2022, 7, 18), date(2023, 7, 18)),
    "Y2_RECOVERY": (date(2023, 7, 18), date(2024, 7, 18)),
}

FEATURE_FIELDS = (
    "tier",
    "entry_family",
    "side",
    "reference_volatility_state",
    "prior_day_state",
    "premarket_state",
    "cash_open_state",
    "last_structure_event_family",
    "current_path_bucket",
    "risk_ref_bucket",
    "reclaim_age_bucket",
    "confirmation_latency_bucket",
    "authorization_reason",
)

INTERACTIONS = {
    "tier_x_family": ("tier", "entry_family"),
    "tier_x_side": ("tier", "side"),
    "family_x_side": ("entry_family", "side"),
    "family_x_reference_volatility": (
        "entry_family",
        "reference_volatility_state",
    ),
    "family_x_premarket": ("entry_family", "premarket_state"),
    "family_x_cash_open": ("entry_family", "cash_open_state"),
    "family_x_last_structure": (
        "entry_family",
        "last_structure_event_family",
    ),
    "family_x_current_path": ("entry_family", "current_path_bucket"),
    "family_x_risk_ref": ("entry_family", "risk_ref_bucket"),
    "family_x_reclaim_age": ("entry_family", "reclaim_age_bucket"),
    "family_x_confirmation_latency": (
        "entry_family",
        "confirmation_latency_bucket",
    ),
    "tier_x_family_x_reference_volatility": (
        "tier",
        "entry_family",
        "reference_volatility_state",
    ),
    "tier_x_family_x_premarket": (
        "tier",
        "entry_family",
        "premarket_state",
    ),
    "tier_x_family_x_cash_open": (
        "tier",
        "entry_family",
        "cash_open_state",
    ),
    "tier_x_family_x_current_path": (
        "tier",
        "entry_family",
        "current_path_bucket",
    ),
    "tier_x_family_x_confirmation_latency": (
        "tier",
        "entry_family",
        "confirmation_latency_bucket",
    ),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _decorate(row: dict[str, object]) -> dict[str, object]:
    updated = regime._decorate(row)
    updated["loss_path_class"] = loss_root._path_class(updated)
    return updated


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return engine._capital_metrics(
        sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    )


def _state_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    metrics = _metrics(rows)
    losses = [
        row
        for row in rows
        if _d(row["capital_weighted_net_r"]) < 0
    ]
    path_counts: dict[str, int] = defaultdict(int)
    for row in losses:
        path_counts[str(row["loss_path_class"])] += 1
    return {
        "sample": len(rows),
        "metrics": metrics,
        "loss_rate": (
            "0"
            if not rows
            else format(Decimal(len(losses)) / Decimal(len(rows)), "f")
        ),
        "loss_path_counts": dict(sorted(path_counts.items())),
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


def _analysis(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "trade_count": len(rows),
        "metrics": _metrics(rows),
        "single_features": {
            field: _group(rows, (field,))
            for field in FEATURE_FIELDS
        },
        "interactions": {
            name: _group(rows, fields)
            for name, fields in INTERACTIONS.items()
        },
    }


def _reference_rows(
    path: Path,
) -> tuple[
    list[dict[str, object]],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("residual regime forensics requires NAS100")

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
    current = loss_shield._apply_loss_cluster_shield(
        state_shielded,
        multiplier=LOSS_CLUSTER_SHIELD,
    )
    decorated = [_decorate(row) for row in current]
    evidence_info = {
        "account_fingerprint": account,
        "evidence_fingerprint": evidence,
        "checked_at": checked.isoformat(),
        "evidence_software_sha": evidence_sha,
        "provider_symbol_name": provider,
    }
    diagnostics = {
        "first": first_diag,
        "rearm": rearm_diag,
        "breaker": breaker_diag,
    }
    return decorated, evidence_info, diagnostics, {
        "by_day_count": len(by_day),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence_info, diagnostics, source_stats = _reference_rows(path)

    blocks: dict[str, object] = {}
    if partition == "consumed_holdout":
        for name, (start, end) in CONSUMED_BLOCKS.items():
            selected = [
                row
                for row in rows
                if start
                <= date.fromisoformat(cast(str, row["local_date"]))
                < end
            ]
            blocks[name] = {
                "start": start.isoformat(),
                "end_exclusive": end.isoformat(),
                **_analysis(selected),
            }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "reference_stack": {
            "allocation": BASE_PROFILE,
            "state_shield": "SHIELD_060",
            "breaker_management": "LOCK025_AFTER_CLOSED_1R",
            "loss_cluster_shield": "LOSS_CLUSTER_SHIELD_060",
        },
        "overall": _analysis(rows),
        "consumed_blocks": blocks,
        "source_stats": source_stats,
        "diagnostics": diagnostics,
        "evidence": evidence_info,
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "current_reference_stack_replayed": True,
            "h4_h1_excluded_from_primary_causal_features": True,
            "calendar_blocks_diagnostic_only": True,
            "calendar_blocks_used_at_runtime": False,
            "trade_authorization_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_future_journey_label_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "policy_promoted": False,
            "opens_new_holdout": False,
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
                "overall": payload["overall"]["metrics"],
                "consumed_blocks": payload["consumed_blocks"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
