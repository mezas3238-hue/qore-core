#!/usr/bin/env python3
"""CEO P0 paired replay audit: all Trader signals received, OLD filter not used.

FULL-coverage management proposal vs sequential original-SL/Trader-exit QDLE
counterfactual. Does NOT turn revised economic stops into historical returns:
that needs an authentic intratrade price path + managed exits. No MT5 fills.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal as D
from pathlib import Path


class ManagerReplayAuditError(ValueError):
    pass


def compare(manager: dict, qdle: dict) -> dict:
    m = manager["receipts"]
    q = qdle["decisions"]
    if (len(m) != len(q) or len(m) != 3368
        or len({x["signal_fingerprint"] for x in m}) != 3368
        or len({x["signal_fingerprint"] for x in q}) != 3368):
        raise ManagerReplayAuditError("3,368 unique aligned receipts required")
    managers = {r["signal_fingerprint"]: r for r in m}
    if set(managers) != {d["signal_fingerprint"] for d in q}:
        raise ManagerReplayAuditError("Trader manager/QDLE identity lineage mismatch")
    if (manager["summary"]["old_cibo_cognitive_admission_gate_used"]
        or qdle["native_cibo_cognitive_decisions_consumed"] != 0):
        raise ManagerReplayAuditError("legacy Native CIBO admission screening present")
    if (manager["summary"]["signals_received"] != 3368
        or manager["summary"]["cibo_administration_receipts"] != 3368
        or qdle["economic_motor_mode"] != "independent_four_motors"
        or qdle["research_volume_policy"] != "broker_grid"
        or qdle["real_fundednext_fills"] != 0
        or qdle["intratrade_drawdown_measured"]
        or qdle["cibo_managed_exit_receipts_consumed"] != 0
        or qdle["certified"]):
        raise ManagerReplayAuditError("incorrect scenario: cannot claim real CIBO fills")
    by_symbol = defaultdict(Counter)
    statuses = Counter()
    funded_by_management = Counter()
    altered = 0
    financed_altered_original_stop = 0
    financed_total = 0
    shown = []
    for d in q:
        r = managers[d["signal_fingerprint"]]
        sym = d["symbol"]
        if (r["symbol"] != sym or r["trader_id"] != d["trader"]
            or r["intake"] != "CIBO_MANAGEMENT_RECEIVED"):
            raise ManagerReplayAuditError("receipt identity mismatch")
        alternative = r["proposed_protective_stop_price"] != r["structural_stop_price"]
        if r["proposed_protective_stop_price"] is None:
            alternative = False
        changed = ("ECONOMIC_PROTECTIVE_STOP_PROPOSED" in r["reason_codes"])
        if changed != alternative:
            raise ManagerReplayAuditError("economic stop claim vs geometry mismatch")
        altered += int(changed)
        funded = d["status"] == "RESERVED_FOR_TRADER"
        statuses[d["status"]] += 1
        by_symbol[sym]["received"] += 1
        if changed:
            by_symbol[sym]["economic_stop_shadow_proposed"] += 1
        else:
            by_symbol[sym]["structural_stop_kept"] += 1
        if funded:
            financed_total += 1
            funded_by_management["ECONOMIC_STOP_NEEDS_CAUSAL_EXIT_REBUILD" if changed
                                  else "ORIGINAL_STOP_HISTORICAL_PROXY"] += 1
            by_symbol[sym]["qdle_financed_original_stop"] += 1
            cap = D(d["nav_at_decision_usd"]) * D(".05")
            if D(d["planned_stop_usd"]) > cap + D(".000000001"):
                raise ManagerReplayAuditError("sequential QDLE violated 5pct")
            if D(d["lots"]) < D(".01"):
                raise ManagerReplayAuditError("QDLE funded subminimum volume")
            if changed:
                financed_altered_original_stop += 1
                # Crucial: this event used ORIGINAL stop and therefore can't
                # stand as the performance of an economic-stop treatment.
        shown.append({
            "signal_fingerprint": r["signal_fingerprint"],
            "symbol": sym, "trader": r["trader_id"],
            "intake": r["intake"],
            "manager_status_static_nav60": r["status"],
            "new_economic_protective_stop_price_shadow": (
                r["proposed_protective_stop_price"] if changed else None
            ),
            "qdle_original_stop_status": d["status"],
            "qdle_original_stop_lots": d["lots"],
            "qdle_original_stop_risk_usd": d.get("planned_stop_usd"),
            "in_modified_stop_treatment": changed,
            "modified_stop_result_outcome_known": False if changed else None,
        })
    if financed_total != qdle["research_financed_proposals"]:
        raise ManagerReplayAuditError("funded count mismatches QDLE report")
    if altered != 300:
        raise ManagerReplayAuditError("manager source economic stop candidate count drift")
    summary = {
        "schema": "qore.cibo.p0.manager-qdle-paired-replay.v1",
        "research_only": True,
        "cibo_selector_used": False,
        "received_signals": len(m),
        "qdle_evaluated": len(q),
        "structural_stop_unmodified": 3368 - altered,
        "economic_stop_shadow_candidates": altered,
        "qdle_original_stop_funded_proposals": financed_total,
        "qdle_original_stop_unfundable_or_invalid": (
            qdle["research_unfundable_or_invalid"]
        ),
        "qdle_funded_signals_with_alternative_stop_not_applied": financed_altered_original_stop,
        "management_subgroup_financed_with_original_stop": dict(funded_by_management),
        "original_stop_sequential_qore_ending_capital_proxy_usd": qdle["qore_ending_capital_usd"],
        "original_stop_sequential_closed_equity_dd_pct": qdle["max_closed_equity_drawdown_pct"],
        "original_stop_sequential_profit_factor_proxy": qdle["profit_factor_proxy"],
        "original_stop_commission_open_proxy_usd": qdle["opening_commission_paid_proxy_usd"],
        "original_stop_commission_close_proxy_usd": qdle["closing_commission_paid_proxy_usd"],
        "outcomes_from_new_economic_stops_measured": False,
        "atr_stops_replayed": False, "real_mt5_fills": 0,
        "new_economic_stop_pnl_or_dd": None,
        "by_symbol": {k:dict(sorted(v.items())) for k,v in sorted(by_symbol.items())},
        "qdle_original_stop_status_counts": dict(statuses),
        "caveat": (
            "Sequential PnL uses Trader structural exit R for ORIGINAL stops only; "
            "not CIBO economic stops or CIBO managed exits. Research margin/fees "
            "are proxies. Closed DD is NOT MTM; broker real fills are zero."
        ),
    }
    if sum(row["received"] for row in by_symbol.values()) != 3368:
        raise ManagerReplayAuditError("coverage mismatch")
    return {"summary": summary, "per_signal": shown}


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--manager",type=Path,required=True)
    p.add_argument("--qdle",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    d=compare(json.loads(a.manager.read_text()), json.loads(a.qdle.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print("CIBO_P0_MANAGED_QDLE_REPLAY",json.dumps(d["summary"],sort_keys=True))


if __name__=="__main__":
    main()
