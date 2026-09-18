"""Contextual breakeven frontier for VT31 NAS100 SECONDARY/SCOUT.

Consumed-evidence development only.

The cross-period diagnostics found one stable-positive SECONDARY context
(FVG + H1 mixed) and several stable-negative contexts. This lab keeps all
authorization, entries, structural stops, structural targets, lifecycle,
ACTIVITY_L rearm admission and global risk scalar unchanged. It only arms
breakeven earlier, from the next bar, in selected causal contexts.

No future PnL, fold identity, or date label is used.
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
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.contextual_breakeven_frontier.v1"
MARKET = "NAS100"
GLOBAL_SCALAR = Decimal("0.60")

VARIANTS = {
    "NEG_BE075": ("STABLE_NEGATIVE", Decimal("0.75")),
    "NEG_BE100": ("STABLE_NEGATIVE", Decimal("1.00")),
    "NEG_BE125": ("STABLE_NEGATIVE", Decimal("1.25")),
    "NONPOS_BE075": ("ALL_EXCEPT_STABLE_POSITIVE", Decimal("0.75")),
    "NONPOS_BE100": ("ALL_EXCEPT_STABLE_POSITIVE", Decimal("1.00")),
    "SCOUT_NEG_BE075": (
        "SCOUT_OR_STABLE_NEGATIVE",
        Decimal("0.75"),
    ),
    "SCOUT_NEG_BE100": (
        "SCOUT_OR_STABLE_NEGATIVE",
        Decimal("1.00"),
    ),
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
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("contextual BE frontier requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    variants: dict[str, object] = {}
    for name, (scope, be_r) in VARIANTS.items():
        first_rows, first_diag = corrective._first_rows(
            by_day,
            context_by_day,
            evidence=evidence,
            alt_partial_r=None,
            secondary_route_policy="ORIGINAL",
            secondary_be_r=be_r,
            secondary_be_scope=scope,
        )
        rearm_rows, rearm_diag = corrective._rearm_rows(
            by_day,
            context_by_day,
            first_rows,
            evidence=evidence,
            rearm_partial_r=None,
        )
        combined = sorted(
            [*first_rows, *rearm_rows],
            key=lambda row: cast(str, row["signal_at"]),
        )
        rows = engine._scale_capital_rows(
            combined,
            scalar=GLOBAL_SCALAR,
        )
        metrics = engine._capital_metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"CONTEXTUAL_BE:{name}:{partition}",
        )
        applied = sum(
            1 for row in first_rows
            if row.get("secondary_be_applied") is True
        )
        variants[name] = {
            "trade_count": len(rows),
            "base_trade_count": len(first_rows),
            "rearm_trade_count": len(rearm_rows),
            "be_applied_count": applied,
            "metrics": metrics,
            "monte_carlo": mc,
            "scope": scope,
            "be_r": format(be_r, "f"),
            "first_diagnostics": first_diag,
            "rearm_diagnostics": rearm_diag,
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
            "authorization_changed": False,
            "entry_changed": False,
            "structural_stop_changed": False,
            "structural_target_changed": False,
            "lifecycle_changed": False,
            "be_scope_uses_pre_entry_context_only": True,
            "be_activates_no_earlier_than_next_bar": True,
            "stable_positive_context_left_unmodified_in_neg_variants": True,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_target_trade_count_at_runtime": False,
            "global_risk_scalar": "0.60",
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
