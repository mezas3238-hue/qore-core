#!/usr/bin/env python3
"""Forensic report for completed, SHA-pinned PAPER 3368 CIBO Native MAX + QDLE.

Consumes an existing Trader Lab artifact. No market data, broker orders or
hindsight decisions are changed. Distinguishes cognitive coverage from physical
0.01 lot feasibility and cash drawdown from unmeasured global MTM.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path


def audit(payload: dict) -> dict:
    assert payload["signal_count"] == 3368
    rows = payload["signal_decisions"]
    assert len(rows) == 3368
    assert len({r["signal_fingerprint"] for r in rows}) == 3368
    status, mode, symbol = Counter(), Counter(), Counter()
    binding = Counter()
    no_lot_binding = Counter()
    mode_financing = defaultdict(Counter)
    symbol_financing = defaultdict(Counter)
    native_error = Counter()
    four_motor_cardinality = Counter()
    mode_net = defaultdict(lambda:Decimal("0"))
    symbol_net = defaultdict(lambda:Decimal("0"))
    mode_gross_positive=defaultdict(lambda:Decimal("0"))
    mode_gross_negative=defaultdict(lambda:Decimal("0"))
    no_lot_examples = []
    cognitive_note_by_mode=defaultdict(Counter)
    cognitive_gate_by_mode=defaultdict(Counter)
    cognitive_abstention_by_mode=defaultdict(Counter)
    min_lot_shortfall_by_mode=defaultdict(Counter)
    new_cognitive_trace_count = 0
    for row in rows:
        st = str(row.get("status", "UNKNOWN"))
        mo = str(row.get("mode", "UNKNOWN"))
        sy = str(row.get("symbol", "UNKNOWN"))
        status[st] += 1
        mode[mo] += 1
        symbol[sy] += 1
        mode_financing[mo][st] += 1
        symbol_financing[sy][st] += 1
        four_motor_cardinality[str(row.get("four_motor_voted_count", "MISSING"))] += 1
        for code in row.get("qdle_binding_limits", ()):
            binding[str(code)] += 1
            if st == "QDLE_NO_FINANCEABLE_LOT":
                no_lot_binding[str(code)] += 1
        cognitive=row.get("native_max_cognitive_receipt") or {}
        if "native_calibration_note" in cognitive:
            new_cognitive_trace_count += 1
            cognitive_note_by_mode[mo][str(cognitive["native_calibration_note"])] += 1
            cognitive_abstention_by_mode[mo][str(cognitive["native_abstention_required"])] += 1
            for gate in cognitive.get("native_decision_gate_codes", []):
                cognitive_gate_by_mode[mo][str(gate)] += 1
        if "minimum_lot_risk_shortfall_usd" in row:
            shortage=Decimal(row["minimum_lot_risk_shortfall_usd"])
            min_lot_shortfall_by_mode[mo]["positive" if shortage>0 else "zero"]+=1
        if row.get("native_max_recomputed") is False:
            native_error[str(row.get("native_max_error", "NONE"))] += 1
        if st == "QDLE_NO_FINANCEABLE_LOT" and len(no_lot_examples) < 12:
            no_lot_examples.append({
                "symbol":sy,"mode":mo,
                "binding_limits":row.get("qdle_binding_limits",[]),
                "risk_budget_snapshot_usd":row.get("bank_at_entry"),
                "all_in_risk":row.get("qdle_all_in_risk"),
            })
    close_reasons = Counter()
    closed = payload["closed_trades"]
    for trade in closed:
        value = Decimal(trade["net_usd"])
        mode_net[trade["mode"]] += value
        symbol_net[trade["symbol"]] += value
        (mode_gross_positive if value>0 else mode_gross_negative)[trade["mode"]] += abs(value)
        close_reasons[trade["exit_reason"]] += 1
    assert len(closed) == payload["counts"]["settled"]
    assert sum(status.values()) == payload["counts"]["received"] == 3368
    assert payload["counts"]["native_max_recomputed"] == 3368
    assert payload["counts"]["qdle_assessed"] == 3368
    assert not native_error
    assert sum(four_motor_cardinality.values()) == 3368
    assert payload["counts"]["four_motor_voted"] == 4 * four_motor_cardinality["4"]
    assert payload["research_persistent_qdle_single_account"] is True
    assert payload["legacy_qdle_quote_decisions_consumed"] is False
    assert payload["certified"] is False
    return {
        "schema":"qore.trader-lab.cibo-p0-forensic-behavior-audit.v1",
        "paper":True,"certified":False,
        "base_manifest_sha256":payload["origin_manifest_sha256"],
        "counts":payload["counts"],
        "status":dict(status.most_common()),
        "by_mode_received":dict(mode.most_common()),
        "by_symbol_received":dict(symbol.most_common()),
        "four_motor_receipts_per_signal":dict(four_motor_cardinality.most_common()),
        "qdle_binding_limits_any":dict(binding.most_common()),
        "qdle_no_financeable_lot_binding_limits":dict(no_lot_binding.most_common()),
        "qdle_unfundable_examples":no_lot_examples,
        "native_errors":dict(native_error.most_common()),
        "cognitive_reason_traces_available_count":new_cognitive_trace_count,
        "native_bank_reason_by_mode":{
            k:dict(v.most_common()) for k,v in sorted(cognitive_note_by_mode.items())
        },
        "native_abstention_by_mode":{
            k:dict(v.most_common()) for k,v in sorted(cognitive_abstention_by_mode.items())
        },
        "native_decision_gates_by_mode":{
            k:dict(v.most_common()) for k,v in sorted(cognitive_gate_by_mode.items())
        },
        "minimum_physical_lot_risk_shortfall_by_mode":{
            k:dict(v) for k,v in sorted(min_lot_shortfall_by_mode.items())
        },
        "mode_financing":{k:dict(v) for k,v in sorted(mode_financing.items())},
        "symbol_financing":{k:dict(v) for k,v in sorted(symbol_financing.items())},
        "settlement_reason_counts":dict(close_reasons.most_common()),
        "settled_net_by_mode_usd":{k:str(v) for k,v in sorted(mode_net.items())},
        "settled_net_by_symbol_usd":{k:str(v) for k,v in sorted(symbol_net.items())},
        "settled_profit_factor_by_mode":{
            k: str(mode_gross_positive[k]/mode_gross_negative[k])
            if mode_gross_negative[k] > 0 else None for k in sorted(mode_net)
        },
        "paper_cash_remaining_usd":payload["shadow_paper_cash_balance_after_known_events_usd"],
        "paper_cash_drawdown_pct":payload["shadow_projected_closed_cash_max_dd_pct"],
        "paper_profit_factor":payload["shadow_projected_settled_profit_factor"],
        "paper_net_usd":payload["shadow_projected_settled_net_pnl_usd"],
        "unresolved_positions":payload["open_positions_missing_full_path"],
        "mtm_dd_certified":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=audit(json.loads(args.report.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("CIBO_P0_FORENSIC_BEHAVIOR_RESULT",json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
