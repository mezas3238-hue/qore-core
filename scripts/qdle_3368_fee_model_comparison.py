#!/usr/bin/env python3
"""Compare 3368 CIBO/QDLE research quotes across account tariff scenarios.

Never promotes SHADOW quotes to fills or constructs managed DD/PF from CONTROL.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal as D
from pathlib import Path

EXPECTED = 3368
LABELS = ("legacy", "stellar_instant", "general_per_side")


def compare_replays(reports: dict[str, dict]) -> dict:
    ids = None
    by_case = {}
    for label in LABELS:
        report = reports[label]
        rows = report["decisions"]
        if (len(rows) != EXPECTED or report["signal_count"] != EXPECTED
            or report.get("native_cibo_bank_medium_attack_instructions_consumed") != EXPECTED
            or report.get("real_fundednext_fills") != 0
            or report.get("cibo_managed_exit_receipts_consumed") != 0
            or report.get("cibo_manager_full_real_strategy_DD") is not None
            or report.get("cibo_manager_full_real_strategy_PF") is not None
            or report.get("broker_account_commission_verified") is not False):
            raise ValueError("Unreconciled/native/fill contaminated research report")
        by_id = {r["signal_fingerprint"]: r for r in rows}
        if len(by_id) != EXPECTED or (ids is not None and set(by_id) != ids):
            raise ValueError("Model run changes source population")
        ids = set(by_id)
        by_case[label] = by_id

    per_case = {}
    for label in LABELS:
        rows = by_case[label]
        stats = defaultdict(lambda: {
            "requested": 0, "quoted_positive": 0, "unfinanceable": 0,
            "lots_quoted_sum": D(0),
            "estimated_open_fee_quoted_usd": D(0),
            "estimated_close_fee_quoted_usd": D(0),
            "all_in_risk_quoted_usd": D(0),
            "binding_constraints": Counter(),
        })
        for r in rows.values():
            mode = r.get("cibo_max_native_management_mode")
            symbol = r.get("symbol")
            if not symbol or mode not in ("BANK", "MEDIUM", "ATTACK"):
                raise ValueError("Missing CIBO native mode/symbol")
            s = stats[(symbol, mode)]
            s["requested"] += 1
            lots = D(str(r["lots"]))
            if lots > 0:
                s["quoted_positive"] += 1
                s["lots_quoted_sum"] += lots
                s["estimated_open_fee_quoted_usd"] += (
                    lots * D(r["commission_open_estimated_usd_per_lot"]))
                s["estimated_close_fee_quoted_usd"] += (
                    lots * D(r["commission_close_estimated_usd_per_lot"]))
                s["all_in_risk_quoted_usd"] += D(r["planned_stop_usd"])
            else:
                s["unfinanceable"] += 1
                s["binding_constraints"][r.get("reason", "UNKNOWN")] += 1
        per_case[label] = {
            f"{k[0]}/{k[1]}": {
                **{n: str(v) if isinstance(v, D) else v
                   for n, v in s.items() if n != "binding_constraints"},
                "binding_constraints": dict(s["binding_constraints"].most_common()),
            } for k, s in sorted(stats.items())
        }

    changes = []
    delta = Counter()
    for sid in sorted(ids):
        old = by_case["legacy"][sid]
        new = by_case["stellar_instant"][sid]
        side = by_case["general_per_side"][sid]
        old_lots = D(old["lots"])
        new_lots = D(new["lots"])
        per_side_lots = D(side["lots"])
        if old_lots != new_lots or old_lots != per_side_lots:
            status = (
                "GAINED_FINANCING" if old_lots == 0 and new_lots > 0
                else "LOST_FINANCING" if old_lots > 0 and new_lots == 0
                else "VOLUME_CHANGED"
            )
            delta[status] += 1
            delta[old["symbol"] + "/" + old["cibo_max_native_management_mode"]] += 1
            changes.append({
                "signal_fingerprint": sid,
                "symbol": old["symbol"],
                "mode": old["cibo_max_native_management_mode"],
                "legacy_lots": str(old_lots),
                "stellar_instant_lots": str(new_lots),
                "general_per_side_lots": str(per_side_lots),
                "change": status,
            })

    totals = {}
    for label in LABELS:
        r = reports[label]
        totals[label] = {
            "fee_model": r["fee_model"],
            "native_requests": r["native_cibo_bank_medium_attack_instructions_consumed"],
            "positive_lot_quotes": r["cibo_manager_native_policy_qdle_quote_only"],
            "unfinanceable": r["research_unfundable_or_invalid"],
            "mode_positive_lot_quotes": r["native_cibo_modes_qdle_physically_quoted"],
            "mode_unfinanceable": r["native_cibo_modes_qdle_no_financeable_lot"],
            "quoted_lots_aggregate": r["cibo_manager_economic_stop_quoted_lots_not_filled"],
            "real_fundednext_fills": 0,
            "managed_full_dd_pct": None,
            "managed_full_profit_factor": None,
            "managed_full_nav_usd": None,
            "source_tariff_account_verified": False,
        }
        if totals[label]["positive_lot_quotes"] + totals[label]["unfinanceable"] != EXPECTED:
            raise ValueError("Incomplete QDLE accounting of the population")
    return {
        "schema": "qore.qdle.3368-stellar-instant-cost-sensitivity.v1",
        "research_only": True,
        "account_tariff_verified": False,
        "financial_certification": "REJECTED",
        "real_mt5_fills": 0,
        "managed_final_nav_usd": None,
        "managed_drawdown_pct": None,
        "managed_profit_factor": None,
        "source_signal_count": EXPECTED,
        "totals": totals,
        "by_symbol_and_native_mode": per_case,
        "signal_changes_legacy_vs_stellar": changes,
        "changes": {
            "old_to_stellar": dict(delta),
            "n_changed_in_either_scenario": len(changes),
        },
        "limitations": [
            "Static 2026 MT5 screenshot margins/contracts for burned 2019-2022 source",
            "USDJPY valuation from original manifest research proxy, not executable historical FX",
            "Published Stellar Instant tariff and general-rule ambiguity not verified with account deals",
            "No broker fills, no CIBO managed exits, no executable historical exit paths",
            "Prices in current-user screenshot do NOT measure past managed equity DD",
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    for label in LABELS:
        p.add_argument("--" + label.replace("_", "-"), type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    reports = {name: json.loads(getattr(args, name).read_text()) for name in LABELS}
    result = compare_replays(reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("QDLE_STELLAR_3368_FEE_COMPARISON", json.dumps({
        "totals": result["totals"],
        "changes": result["changes"],
        "financial_certification": result["financial_certification"],
        "managed_drawdown_pct": result["managed_drawdown_pct"],
    }, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
