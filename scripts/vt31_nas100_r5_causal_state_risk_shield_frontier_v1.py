"""Causal persistent-negative state risk shield for VT31 NAS100 ALLOC_G.

Consumed development evidence only.

This frontier tests a single predeclared mechanism: when decision-time state
belongs to a context that was negative in all four consumed windows in the
ALLOC_G root-cause forensics, reduce capital at risk while leaving strategy
identity, entry, stop, target, lifecycle, trade count, and structural rearm
unchanged.

Only two neighboring shield multipliers are tested (0.75x and 0.60x).  No date,
fold identity, terminal PnL, target trade count, or future bar is used at
runtime.
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

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.causal_state_risk_shield_frontier.v1"
MARKET = "NAS100"
BASE_PROFILE = "ALLOC_G_CORE_FAMILY_050"

VARIANTS = {
    "BASELINE": Decimal("1.00"),
    "SHIELD_075": Decimal("0.75"),
    "SHIELD_060": Decimal("0.60"),
}


def _decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _negative_state_reasons(row: dict[str, object]) -> tuple[str, ...]:
    tier = str(row.get("tier"))
    family = str(row.get("entry_family"))
    reasons: list[str] = []

    risk_ref = _decimal(row.get("risk_ref"))
    current_path = _decimal(row.get("current_path_vs_previous"))
    latency_raw = row.get("confirmation_latency_minutes")
    latency = None if latency_raw is None else int(latency_raw)

    if family == "fair-value-gap" and row.get("premarket_state") == "rotation":
        reasons.append("FVG_PREMARKET_ROTATION_4OF4_NEGATIVE")
    if family == "fair-value-gap" and row.get("h1_state") == "bullish":
        reasons.append("FVG_H1_BULLISH_4OF4_NEGATIVE")
    if (
        family == "order-block"
        and risk_ref is not None
        and risk_ref < Decimal("0.30")
    ):
        reasons.append("ORDER_BLOCK_LOW_RISK_REF_4OF4_NEGATIVE")
    if (
        family == "order-block"
        and current_path is not None
        and current_path < Decimal("0.75")
    ):
        reasons.append("ORDER_BLOCK_LOW_CURRENT_PATH_4OF4_NEGATIVE")
    if tier == "SECONDARY" and family == "breaker":
        reasons.append("SECONDARY_BREAKER_4OF4_NEGATIVE")
    if tier == "REARM" and latency is not None and 3 <= latency <= 5:
        reasons.append("REARM_CONFIRMATION_3_5M_4OF4_NEGATIVE")
    if tier == "REARM" and row.get("premarket_state") == "rotation":
        reasons.append("REARM_PREMARKET_ROTATION_4OF4_NEGATIVE")
    if tier == "REARM" and row.get("cash_open_state") == "bullish":
        reasons.append("REARM_CASH_OPEN_BULLISH_4OF4_NEGATIVE")

    return tuple(reasons)


def _apply_shield(
    rows: list[dict[str, object]],
    *,
    multiplier: Decimal,
) -> list[dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        reasons = _negative_state_reasons(updated)
        applied = multiplier if reasons else Decimal("1.00")
        updated["state_risk_shield_reasons"] = list(reasons)
        updated["state_risk_shield_multiplier"] = format(applied, "f")
        updated["requested_risk_r"] = format(
            Decimal(cast(str, updated["requested_risk_r"])) * applied,
            "f",
        )
        updated["capital_weighted_net_r"] = format(
            Decimal(cast(str, updated["capital_weighted_net_r"])) * applied,
            "f",
        )
        adjusted.append(updated)
    return adjusted


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return engine._capital_metrics(
        sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    )


def _annual_blocks(
    rows: list[dict[str, object]],
    *,
    start: date,
    years: int,
) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for idx in range(years):
        block_start = date(start.year + idx, start.month, start.day)
        block_end = date(start.year + idx + 1, start.month, start.day)
        selected = [
            row
            for row in rows
            if block_start
            <= date.fromisoformat(cast(str, row["local_date"]))
            < block_end
        ]
        metrics = _metrics(selected)
        blocks.append(
            {
                "year_block": idx + 1,
                "start": block_start.isoformat(),
                "end_exclusive": block_end.isoformat(),
                "trade_count": len(selected),
                "metrics": metrics,
                "positive": (
                    bool(selected)
                    and Decimal(cast(str, metrics["total_r"])) > 0
                ),
            }
        )
    return blocks


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("causal state risk shield requires NAS100")

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
    alloc_g = allocation._apply_profile(
        nominal,
        profile=allocation.PROFILES[BASE_PROFILE],
    )

    variants: dict[str, object] = {}
    for name, multiplier in VARIANTS.items():
        rows = _apply_shield(alloc_g, multiplier=multiplier)
        metrics = _metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"CAUSAL_STATE_RISK_SHIELD:{name}:{partition}",
        )
        annual = (
            _annual_blocks(rows, start=date(2022, 7, 18), years=2)
            if partition == "consumed_holdout"
            else []
        )
        reason_counts: dict[str, int] = defaultdict(int)
        shielded = 0
        for row in rows:
            reasons = cast(list[str], row["state_risk_shield_reasons"])
            if reasons:
                shielded += 1
            for reason in reasons:
                reason_counts[reason] += 1

        objectives = {
            "density_300_350": 300 <= len(rows) <= 350,
            "pf_ge_1_50": (
                metrics["profit_factor"] is not None
                and Decimal(cast(str, metrics["profit_factor"]))
                >= Decimal("1.50")
            ),
            "dd_le_6": (
                Decimal(cast(str, metrics["max_drawdown_r"]))
                <= Decimal("6")
            ),
            "mc_positive_ge_0_90": (
                Decimal(cast(str, mc["positive_terminal_probability"]))
                >= Decimal("0.90")
            ),
            "mc_p95_dd_le_15": (
                Decimal(cast(str, mc["p95_max_drawdown_r"]))
                <= Decimal("15")
            ),
        }
        if annual:
            objectives["both_consumed_years_positive"] = all(
                bool(block["positive"]) for block in annual
            )

        variants[name] = {
            "trade_count": len(rows),
            "shielded_trade_count": shielded,
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "reason_counts": dict(sorted(reason_counts.items())),
            "shield_multiplier": format(multiplier, "f"),
            "objectives": objectives,
            "passes_all_objectives": all(objectives.values()),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "base_profile": BASE_PROFILE,
        "variants": variants,
        "diagnostics": {
            "first": first_diag,
            "rearm": rearm_diag,
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
            "bounded_risk_shield_only": True,
            "minimum_multiplier": "0.60",
            "maximum_multiplier": "1.00",
            "trade_count_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_admission_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_time_at_runtime": False,
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
