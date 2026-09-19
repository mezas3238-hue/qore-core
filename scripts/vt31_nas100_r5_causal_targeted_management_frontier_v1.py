"""Targeted causal management frontier for VT31 NAS100 ALLOC_G.

Consumed development evidence only.

This frontier tests whether a partial runner should be applied only when the
decision-time state belongs to a context that was negative across all four
consumed ALLOC_G windows. CORE execution and positive/unresolved secondary
contexts are unchanged. Structural stop, target identity, lifecycle, trade
admission, monthly budget, structural rearm admission and ALLOC_G are preserved.

A small neighboring set is tested: 0.50R, 0.75R and 1.00R partial triggers.
Two bounded combinations add the already-tested 0.60 state-risk shield, and
one adds the previously tested REGIME_B CORE-breaker overlay. No date, fold
identity, terminal PnL, target trade count or future bar is a runtime input.
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
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as shield
import vt31_nas100_r5_core_breaker_regime_risk_frontier_v1 as regime
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.causal_targeted_management_frontier.v1"
MARKET = "NAS100"
BASE_PROFILE = "ALLOC_G_CORE_FAMILY_050"

VARIANTS: dict[str, tuple[Decimal | None, Decimal | None, str | None]] = {
    "BASELINE": (None, None, None),
    "NEG_P050": (Decimal("0.50"), None, None),
    "NEG_P075": (Decimal("0.75"), None, None),
    "NEG_P100": (Decimal("1.00"), None, None),
    "NEG_P050_SHIELD060": (
        Decimal("0.50"),
        Decimal("0.60"),
        None,
    ),
    "NEG_P075_SHIELD060": (
        Decimal("0.75"),
        Decimal("0.60"),
        None,
    ),
    "NEG_P050_SHIELD060_REGIME_B": (
        Decimal("0.50"),
        Decimal("0.60"),
        "REGIME_B",
    ),
    "NEG_P075_SHIELD060_REGIME_B": (
        Decimal("0.75"),
        Decimal("0.60"),
        "REGIME_B",
    ),
}


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


def _apply_layers(
    rows: list[dict[str, object]],
    *,
    shield_multiplier: Decimal | None,
    regime_overlay: str | None,
) -> list[dict[str, object]]:
    adjusted = rows
    if shield_multiplier is not None:
        adjusted = shield._apply_shield(
            adjusted,
            multiplier=shield_multiplier,
        )
    if regime_overlay is not None:
        adjusted = regime._apply_overlay(
            adjusted,
            overlay_name=regime_overlay,
        )
    return adjusted


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("targeted management frontier requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    variants: dict[str, object] = {}
    for name, (partial_r, shield_multiplier, regime_overlay) in VARIANTS.items():
        first_rows, first_diag = corrective._first_rows(
            by_day,
            context_by_day,
            evidence=evidence,
            alt_partial_r=partial_r,
            secondary_route_policy="ORIGINAL",
            secondary_partial_scope=(
                "CAUSAL_NEGATIVE" if partial_r is not None else "ALL"
            ),
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
        rows = _apply_layers(
            alloc_g,
            shield_multiplier=shield_multiplier,
            regime_overlay=regime_overlay,
        )

        metrics = _metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"CAUSAL_TARGETED_MANAGEMENT:{name}:{partition}",
        )
        annual = (
            _annual_blocks(rows, start=date(2022, 7, 18), years=2)
            if partition == "consumed_holdout"
            else []
        )
        partial_applied = sum(
            bool(row.get("secondary_partial_applied"))
            for row in first_rows
        )
        shielded = sum(
            bool(row.get("state_risk_shield_reasons"))
            for row in rows
        )
        regime_reasons: dict[str, int] = defaultdict(int)
        for row in rows:
            if "regime_risk_reason" in row:
                regime_reasons[str(row["regime_risk_reason"])] += 1

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
            "partial_applied_count": partial_applied,
            "shielded_trade_count": shielded,
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "partial_r": None if partial_r is None else format(partial_r, "f"),
            "shield_multiplier": (
                None
                if shield_multiplier is None
                else format(shield_multiplier, "f")
            ),
            "regime_overlay": regime_overlay,
            "regime_reason_counts": dict(sorted(regime_reasons.items())),
            "first_diagnostics": first_diag,
            "rearm_diagnostics": rearm_diag,
            "objectives": objectives,
            "passes_all_objectives": all(objectives.values()),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "base_profile": BASE_PROFILE,
        "variants": variants,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "predeclared_negative_context_management_only": True,
            "core_management_changed": False,
            "positive_context_management_changed": False,
            "trade_count_target_used_at_runtime": False,
            "entry_changed": False,
            "structural_stop_changed": False,
            "structural_target_identity_changed": False,
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
