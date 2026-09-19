"""Reasoning-sovereign event frontier for VT31 NAS100.

Consumed development evidence only. Tests whether density can be sourced from
new structural events that re-enter the normal Situation Model -> Reasoning
path, rather than from same-source fallback after WAIT/ABSTAIN.

No new holdout is opened. No policy is promoted.
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

SCHEMA = "qore.vt31.nas100.r5.reasoning_sovereign_event_frontier.v1"
MARKET = "NAS100"
PROFILE = allocation.PROFILES["ALLOC_G_CORE_FAMILY_050"]
VARIANTS = {
    "BASELINE": ("NONE", False),
    "SOVEREIGN_ABSTAIN": ("ABSTAIN", False),
    "SOVEREIGN_ABSTAIN_REARM": ("ABSTAIN", True),
    "SOVEREIGN_ALL_NONCORE_REARM": ("ALL", True),
}


def _objectives(
    rows: list[dict[str, object]],
    metrics: dict[str, object],
    mc: dict[str, object],
) -> dict[str, bool]:
    count = len(rows)
    pf = Decimal(str(metrics["profit_factor"]))
    dd = Decimal(str(metrics["max_drawdown_r"]))
    positive = Decimal(str(mc["positive_terminal_probability"]))
    p95 = Decimal(str(mc["p95_max_drawdown_r"]))
    return {
        "density_300_350": 300 <= count <= 350,
        "pf_ge_1_50": pf >= Decimal("1.50"),
        "max_dd_le_6": dd <= Decimal("6"),
        "mc_positive_ge_0_90": positive >= Decimal("0.90"),
        "mc_p95_dd_le_15": p95 <= Decimal("15"),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("reasoning-sovereign frontier requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    variants: dict[str, object] = {}
    for name, (alt_scope, sovereign_rearm) in VARIANTS.items():
        first_rows, first_diag = corrective._first_rows(
            by_day,
            context_by_day,
            evidence=evidence,
            alt_partial_r=None,
            reasoning_sovereign_alt_scope=alt_scope,
        )
        rearm_rows, rearm_diag = corrective._rearm_rows(
            by_day,
            context_by_day,
            first_rows,
            evidence=evidence,
            rearm_partial_r=None,
            reasoning_sovereign_rearm=sovereign_rearm,
        )
        nominal = sorted(
            [*first_rows, *rearm_rows],
            key=lambda row: cast(str, row["signal_at"]),
        )
        allocated = allocation._apply_profile(nominal, profile=PROFILE)
        metrics = engine._capital_metrics(allocated)
        mc = engine._monte_carlo(
            allocated,
            variant=f"SOVEREIGN_EVENT:{name}:{partition}",
        )
        variants[name] = {
            "trade_count": len(allocated),
            "first_trade_count": len(first_rows),
            "rearm_trade_count": len(rearm_rows),
            "metrics": metrics,
            "monte_carlo": mc,
            "objectives": _objectives(allocated, metrics, mc),
            "first_diagnostics": first_diag,
            "rearm_diagnostics": rearm_diag,
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "allocation_profile": "ALLOC_G_CORE_FAMILY_050",
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
            "new_event_requires_new_raid": True,
            "new_event_requires_new_confirmation": True,
            "new_event_requires_new_decision": True,
            "sovereign_routes_require_reasoning_execute": True,
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
