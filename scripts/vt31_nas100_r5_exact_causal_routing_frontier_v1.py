"""Exact causal routing frontier on top of VT31 NAS100 ALLOC_G.

Consumed evidence only. The frontier tests a very small set of routing rules
supported by prior cross-period forensics:

- all SECONDARY breaker fallbacks were repeatedly weak,
- order-block LONG was repeatedly weak,
- CORE breaker remains untouched.

Renewal always requires a new raid, confirmation, and decision after the
rejected fallback. ALLOC_G capital weights are then applied unchanged.
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

SCHEMA = "qore.vt31.nas100.r5.exact_causal_routing_frontier.v1"
MARKET = "NAS100"
PROFILE_NAME = "ALLOC_G_CORE_FAMILY_050"
ROUTE_POLICIES = (
    "ORIGINAL",
    "RENEW_ALL_SECONDARY_BREAKER",
    "RENEW_EXACT_STABLE_NEGATIVE",
    "ABSTAIN_EXACT_STABLE_NEGATIVE",
)


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("exact causal routing frontier requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    profile = allocation.PROFILES[PROFILE_NAME]

    variants: dict[str, object] = {}
    for route_policy in ROUTE_POLICIES:
        first_rows, first_diag = corrective._first_rows(
            by_day,
            context_by_day,
            evidence=evidence,
            alt_partial_r=None,
            secondary_route_policy=route_policy,
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
        adjusted = allocation._apply_profile(nominal, profile=profile)
        metrics = engine._capital_metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"EXACT_ROUTING:{route_policy}:{partition}",
        )
        variants[route_policy] = {
            "trade_count": len(adjusted),
            "base_trade_count": len(first_rows),
            "rearm_trade_count": len(rearm_rows),
            "metrics": metrics,
            "monte_carlo": mc,
            "first_diagnostics": first_diag,
            "rearm_diagnostics": rearm_diag,
            "objectives": {
                "density_300_350": 300 <= len(adjusted) <= 350,
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
        "allocation_profile": PROFILE_NAME,
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
            "routing_uses_pre_entry_state_only": True,
            "renewal_requires_new_raid_confirmation_decision": True,
            "core_breaker_routing_changed": False,
            "entry_grammar_changed": False,
            "source_stop_changed": False,
            "target_lifecycle_changed": False,
            "allocation_profile_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_time_at_runtime": False,
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
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
