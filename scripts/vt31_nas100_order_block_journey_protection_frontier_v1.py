"""Order-Block +1R journey protection on the current VT31_NAS100 stack.

Consumed development evidence only.

Order Block remains negative across R5/R6/R8/consumed even after the current
risk shields, and its residual losses include givebacks after +1R. This lab
tests whether an earned CLOSED-M1 +1R checkpoint can protect OB positions
without filtering any trade or changing the initial strategy geometry.

Current base stack is produced by Alt Tier Bifurcation V1:
- ALLOC_G_CORE_FAMILY_050
- SHIELD_060
- SECONDARY Breaker +1R -> +0.25R lock
- loss-cluster X0.35
- stable Breaker Regime Shield X0.35
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

import vt31_nas100_alloc_g_breaker_journey_management_frontier_v1 as journey_mgmt
import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_causal_hybrid_density_v2 as hybrid
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.order_block_journey_protection_frontier.v1"
MARKET = "NAS100"
CHECKPOINT_R = Decimal("1.00")

VARIANTS = {
    "BASE": None,
    "OB_BE100": Decimal("0.00"),
    "OB_LOCK025_100": Decimal("0.25"),
    "OB_LOCK050_100": Decimal("0.50"),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _apply_ob_management(
    rows: list[dict[str, object]],
    by_day: dict[date, tuple[object, ...]],
    *,
    lock_r: Decimal,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    adjusted: list[dict[str, object]] = []
    counts: Counter[str] = Counter()

    for row in rows:
        updated = dict(row)
        updated["ob_journey_management_applied"] = False
        updated["ob_journey_management_ambiguous"] = False
        updated["ob_journey_lock_r"] = format(lock_r, "f")

        if str(row.get("entry_family")) != "order-block":
            counts["unchanged-non-order-block"] += 1
            adjusted.append(updated)
            continue

        if any(
            key not in row
            for key in ("entry", "initial_stop", "structural_target", "filled_at", "exit_at")
        ):
            counts["missing-geometry-preserved"] += 1
            adjusted.append(updated)
            continue

        local_day = date.fromisoformat(cast(str, row["local_date"]))
        bars = by_day.get(local_day)
        if not bars:
            counts["missing-day-bars"] += 1
            adjusted.append(updated)
            continue

        checkpoint = journey_mgmt._checkpoint(bars, row)
        if checkpoint is None:
            counts["checkpoint-not-earned-before-baseline-exit"] += 1
            adjusted.append(updated)
            continue

        checkpoint_index, features = checkpoint
        counts["checkpoint-earned"] += 1
        for key, value in features.items():
            updated[f"ob_journey_{key}"] = (
                format(value, "f") if isinstance(value, Decimal) else value
            )

        side = str(row["side"])
        entry = _d(row["entry"])
        initial_stop = _d(row["initial_stop"])
        target = _d(row["structural_target"])
        risk = abs(entry - initial_stop)
        if risk <= 0:
            counts["invalid-risk-preserved"] += 1
            adjusted.append(updated)
            continue

        protective_level = (
            entry + risk * lock_r
            if side == "long"
            else entry - risk * lock_r
        )
        original_exit_at = datetime.fromisoformat(cast(str, row["exit_at"]))
        checkpoint_at = datetime.fromisoformat(cast(str, features["checkpoint_at"]))
        applied = False

        for bar in bars[checkpoint_index + 1 :]:
            opened_at = getattr(bar, "opened_at")
            closed_at = getattr(bar, "closed_at")
            if opened_at < checkpoint_at:
                continue
            if closed_at > original_exit_at:
                break

            if not journey_mgmt._touches_stop(bar, side, protective_level):
                continue

            if journey_mgmt._touches_target(bar, side, target):
                counts["ambiguous-protect-vs-target-same-m1"] += 1
                updated["ob_journey_management_ambiguous"] = True
                break

            managed_r = journey_mgmt._protective_fill_r(
                bar,
                side=side,
                entry=entry,
                risk=risk,
                protective_level=protective_level,
                lock_r=lock_r,
            )
            requested = _d(row["requested_risk_r"])
            updated["r_multiple"] = format(managed_r, "f")
            updated["capital_weighted_net_r"] = format(
                requested * (managed_r - hybrid.FRICTION),
                "f",
            )
            updated["exit_at"] = closed_at.isoformat()
            updated["exit_reason"] = (
                "order-block-journey-breakeven"
                if lock_r == 0
                else "order-block-journey-lock"
            )
            updated["ob_journey_management_applied"] = True
            updated["ob_journey_protective_level"] = format(
                protective_level, "f"
            )
            counts["management-protective-exit"] += 1
            applied = True
            break

        if not applied and not updated["ob_journey_management_ambiguous"]:
            counts["checkpoint-earned-baseline-exit-preserved"] += 1
        adjusted.append(updated)

    adjusted.sort(key=lambda row: cast(str, row["signal_at"]))
    return adjusted, dict(sorted(counts.items()))


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence_fp, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("order-block journey protection requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }

    base_rows, evidence, diagnostics, stats = alt._current_rows(path)
    variants: dict[str, object] = {}

    for name, lock_r in VARIANTS.items():
        if lock_r is None:
            rows = [dict(row) for row in base_rows]
            management = {"baseline": len(rows)}
        else:
            rows, management = _apply_ob_management(
                base_rows,
                by_day,
                lock_r=lock_r,
            )

        metrics = residual._metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"OB_JOURNEY:{name}:{partition}",
        )
        annual = (
            annuals._annual_blocks(
                rows,
                start=date(2022, 7, 18),
                years=2,
            )
            if partition == "consumed_holdout"
            else []
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
            "lock_r": None if lock_r is None else format(lock_r, "f"),
            "management": management,
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "objectives": objectives,
            "passes_economic_objectives": all(objectives.values()),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "checkpoint_r": format(CHECKPOINT_R, "f"),
        "variants": variants,
        "source_stats": stats,
        "diagnostics": diagnostics,
        "evidence": {
            **evidence,
            "account_fingerprint": account,
            "evidence_fingerprint": evidence_fp,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "order_block_only": True,
            "checkpoint_requires_closed_m1_plus_1r": True,
            "protection_activates_after_checkpoint": True,
            "trade_count_changed": False,
            "silver_bullet_changed": False,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed_at_entry": False,
            "structural_target_changed": False,
            "rearm_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_future_journey_label_at_runtime": False,
            "uses_calendar_date_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
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
