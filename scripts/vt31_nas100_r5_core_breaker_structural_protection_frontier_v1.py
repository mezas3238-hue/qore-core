"""CORE breaker structural protection frontier for VT31 NAS100 ALLOC_G.

Consumed development evidence only.

This frontier keeps strategy identity, authorization, entry, initial structural
stop, target, lifecycle, ALLOC_G, and ACTIVITY_L unchanged. It changes only
post-fill management for CORE breaker positions with FULL_STRUCTURAL_BOUNDARY.

A protective swing is confirmed on a closed M1 bar and can improve the stop
only from the next M1 bar. The stop never widens and never crosses the target.
Structural rearm is recomputed from the resulting first-position exit time.

No fold identity, date label, terminal PnL, or future bar is a runtime input.
"""
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

SCHEMA = "qore.vt31.nas100.r5.core_breaker_structural_protection_frontier.v1"
MARKET = "NAS100"
BASE_PROFILE = "ALLOC_G_CORE_FAMILY_050"

VARIANTS: dict[str, tuple[int | None, str]] = {
    "BASELINE": (None, "NONE"),
    "FRAGILE_SWING1": (1, "FRAGILE"),
    "FRAGILE_SWING2": (2, "FRAGILE"),
    "ALL_SWING1": (1, "ALL"),
    "ALL_SWING2": (2, "ALL"),
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


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("CORE breaker structural protection requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    variants: dict[str, object] = {}
    for name, (confirmations, scope) in VARIANTS.items():
        first_rows, first_diag = corrective._first_rows(
            by_day,
            context_by_day,
            evidence=evidence,
            alt_partial_r=None,
            secondary_route_policy="ORIGINAL",
            core_breaker_protection_confirmations=confirmations,
            core_breaker_protection_scope=scope,
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
        rows = allocation._apply_profile(
            nominal,
            profile=allocation.PROFILES[BASE_PROFILE],
        )
        metrics = _metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"CORE_BREAKER_STRUCTURAL_PROTECTION:{name}:{partition}",
        )
        annual = (
            _annual_blocks(rows, start=date(2022, 7, 18), years=2)
            if partition == "consumed_holdout"
            else []
        )
        protection_applied = sum(
            bool(row.get("core_breaker_protection_applied"))
            for row in first_rows
        )
        protected_exit_reasons: dict[str, int] = defaultdict(int)
        for row in first_rows:
            if row.get("core_breaker_protection_applied"):
                protected_exit_reasons[str(row.get("exit_reason"))] += 1

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
            "first_trade_count": len(first_rows),
            "rearm_trade_count": len(rearm_rows),
            "protection_applied_count": protection_applied,
            "protected_exit_reasons": dict(sorted(protected_exit_reasons.items())),
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
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
            "entry_changed": False,
            "initial_stop_changed": False,
            "initial_stop_widening": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "protective_swing_confirmed_on_closed_m1": True,
            "protective_stop_effective_next_bar": True,
            "single_protective_stop_move_max": True,
            "full_structural_target_plan_only": True,
            "rearm_recomputed_after_managed_exit": True,
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
