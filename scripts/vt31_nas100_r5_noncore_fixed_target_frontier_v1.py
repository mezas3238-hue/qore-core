"""Focused fixed-target frontier for weak VT31 NAS100 non-CORE tiers.

Consumed development evidence only.

CORE keeps its exact structural plan. SECONDARY and REARM keep the same
authorization, entry, structural stop and lifecycle, but their target is
replaced before entry with a fixed R multiple. This tests whether the weak
tiers are suffering from overextended destination selection rather than bad
entry authorization.

No terminal outcome, fold identity, or future state selects the target.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.noncore_fixed_target_frontier.v1"
MARKET = "NAS100"
GLOBAL_SCALAR = Decimal("0.60")
TARGETS = (
    Decimal("0.75"),
    Decimal("1.00"),
    Decimal("1.25"),
)


def _retarget(setup: object, target_r: Decimal) -> object:
    entry = getattr(setup, "entry_price")
    risk = getattr(setup, "initial_risk")
    side = getattr(setup, "side").value
    target = (
        entry + risk * target_r
        if side == "long"
        else entry - risk * target_r
    )
    return replace(setup, target_price=target)


def _run_variant(
    *,
    by_day: dict[date, tuple[object, ...]],
    context_by_day: dict[
        date,
        tuple[Decimal | None, Decimal | None, tuple[object, ...]],
    ],
    evidence: str,
    secondary_target_r: Decimal | None,
    rearm_target_r: Decimal | None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    first_rows, first_diag = corrective._first_rows(
        by_day,
        context_by_day,
        evidence=evidence,
        alt_partial_r=None,
        secondary_route_policy="ORIGINAL",
    )

    # Re-simulate only non-CORE first positions when a fixed target is requested.
    if secondary_target_r is not None:
        rebuilt: list[dict[str, object]] = []
        # Preserve CORE rows exactly. Reconstruct SECONDARY/SCOUT from the
        # original causal day selection via the same helper, but monkeypatch
        # baseline simulation only for the non-CORE setup.
        original_simulate = specialist.baseline._simulate

        def fixed_simulate(
            day_bars: tuple[object, ...],
            setup: object,
        ) -> dict[str, object]:
            retargeted = _retarget(setup, secondary_target_r)
            return original_simulate(day_bars, retargeted)

        specialist.baseline._simulate = fixed_simulate
        try:
            rebuilt, first_diag = corrective._first_rows(
                by_day,
                context_by_day,
                evidence=evidence,
                alt_partial_r=None,
                secondary_route_policy="ORIGINAL",
            )
        finally:
            specialist.baseline._simulate = original_simulate

        # CORE uses _simulate_selected_plan and is therefore unchanged by the
        # temporary baseline patch.
        first_rows = rebuilt

    if rearm_target_r is None:
        rearm_rows, rearm_diag = corrective._rearm_rows(
            by_day,
            context_by_day,
            first_rows,
            evidence=evidence,
            rearm_partial_r=None,
        )
    else:
        original_protection = (
            corrective.protection._simulate_single_structural_trail
        )

        def fixed_rearm_protection(
            day_bars: tuple[object, ...],
            setup: object,
            *,
            required_confirmations: int | None,
        ) -> dict[str, object]:
            retargeted = _retarget(setup, rearm_target_r)
            return original_protection(
                day_bars,
                retargeted,
                required_confirmations=required_confirmations,
            )

        corrective.protection._simulate_single_structural_trail = (
            fixed_rearm_protection
        )
        try:
            rearm_rows, rearm_diag = corrective._rearm_rows(
                by_day,
                context_by_day,
                first_rows,
                evidence=evidence,
                rearm_partial_r=None,
            )
        finally:
            corrective.protection._simulate_single_structural_trail = (
                original_protection
            )

    combined = sorted(
        [*first_rows, *rearm_rows],
        key=lambda row: cast(str, row["signal_at"]),
    )
    scaled = engine._scale_capital_rows(
        combined,
        scalar=GLOBAL_SCALAR,
    )
    return scaled, {
        "first_diagnostics": first_diag,
        "rearm_diagnostics": rearm_diag,
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    (
        series,
        account,
        evidence,
        checked,
        evidence_sha,
        provider,
    ) = load_market_evidence(path)
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("fixed-target frontier requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    specs: dict[str, tuple[Decimal | None, Decimal | None]] = {}
    for target in TARGETS:
        tag = format(target, "f").replace(".", "")
        specs[f"SECONDARY_T{tag}"] = (target, None)
        specs[f"REARM_T{tag}"] = (None, target)
        specs[f"BOTH_T{tag}"] = (target, target)

    variants: dict[str, object] = {}
    for name, (secondary_target, rearm_target) in specs.items():
        rows, diagnostics = _run_variant(
            by_day=by_day,
            context_by_day=context_by_day,
            evidence=evidence,
            secondary_target_r=secondary_target,
            rearm_target_r=rearm_target,
        )
        metrics = engine._capital_metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"NONCORE_FIXED_TARGET:{name}:{partition}",
        )
        variants[name] = {
            "trade_count": len(rows),
            "tier_counts": dict(
                sorted(
                    {
                        tier: sum(
                            1 for row in rows
                            if str(row.get("tier")) == tier
                        )
                        for tier in {
                            str(row.get("tier")) for row in rows
                        }
                    }.items()
                )
            ),
            "metrics": metrics,
            "monte_carlo": mc,
            "secondary_target_r": (
                None
                if secondary_target is None
                else format(secondary_target, "f")
            ),
            "rearm_target_r": (
                None
                if rearm_target is None
                else format(rearm_target, "f")
            ),
            "diagnostics": diagnostics,
            "objectives": {
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
                    Decimal(
                        cast(str, mc["positive_terminal_probability"])
                    )
                    >= Decimal("0.90")
                ),
                "mc_p95_dd_le_15": (
                    Decimal(cast(str, mc["p95_max_drawdown_r"]))
                    <= Decimal("15")
                ),
            },
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
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
            "core_plan_changed": False,
            "entry_authorization_changed": False,
            "structural_stop_changed": False,
            "lifecycle_changed": False,
            "noncore_target_selected_pre_entry": True,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "trade_count_target_used_at_runtime": False,
            "policy_promoted": False,
            "opens_new_holdout": False,
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
