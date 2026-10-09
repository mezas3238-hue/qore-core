#!/usr/bin/env python3
"""Fail-closed financial certification audit for QDLE research simulations.

A successful program exit means the AUDIT is valid, not that the strategy is
certified. Historical R, screenshot margin, missing fees and shared budget caps
must NEVER be presented as four independently profitable current modules.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal as D
from pathlib import Path


def audit(report: dict) -> dict:
    events = report["decisions"]
    if len(events) != 3368 or len({e["signal_fingerprint"] for e in events}) != 3368:
        raise AssertionError("NOT_ALL_3368_UNIQUE_OPPORTUNITIES")
    if report["certified"] or report["real_fundednext_fills"] != 0:
        raise AssertionError("SYNTHETIC_EVENTS_IMPERSONATE_CERTIFIED_BROKER_FILLS")
    if report["risk_policy"] != "CONSTANT_5PCT_QORE_NAV_DYNAMIC_USD":
        raise AssertionError("NOT_THE_SOVEREIGN_FIVE_PERCENT_POLICY")

    status = Counter(x["status"] for x in events)
    checks = Counter()
    actual = D("0")
    entry_fees = D("0")
    symbols = {}
    for e in events:
        lots = D(e.get("lots", "0"))
        if lots == 0:
            continue
        symbol = e["symbol"]
        per = symbols.setdefault(symbol, Counter())
        per["sized"] += 1
        checks["sized"] += 1
        if lots < D("0.01") or lots % D("0.01"):
            raise AssertionError("BROKER_LOT_GRID_VIOLATION")
        nav = D(e["nav_at_decision_usd"])
        if nav <= 0:
            raise AssertionError("NONPOSITIVE_QORE_CAPITAL_AUTHORIZED")
        budget = nav * D("0.05")
        reserved = D(e["planned_stop_usd"])
        fee = D(e["fees_entry_usd_proxy"])
        if reserved > budget + D("0.000000001"):
            raise AssertionError("RESERVATION_EXCEEDS_5PCT_CAP")
        if symbol in {"AUDJPY", "EURUSD", "GBPJPY", "GBPUSD"}:
            # Baseline: opening only; new scenario: $7 open + $7 close per lot.
            fx_roundtrip = report.get("economic_motor_mode") == "independent_four_motors"
            expected_per_lot = D("14") if fx_roundtrip else D("7")
            if abs(fee - expected_per_lot * lots) > D("0.000000001"):
                raise AssertionError("FOREX_FEE_NOT_MATCHING_DECLARED_SCENARIO")
        if symbol == "NDX100":
            if report.get("economic_motor_mode") == "independent_four_motors":
                sensitivity = D(report["ndx_assumed_total_fee_usd_per_lot"])
                if abs(fee - sensitivity * lots) > D("0.000000001"):
                    raise AssertionError("INDEX_SENSITIVITY_FEE_INCONSISTENT")
                checks["INDEX_FEE_UNKNOWN_USING_EXPLICIT_SENSITIVITY"] += 1
            else:
                checks["INDEX_FEE_MISSING_ASSUMED_ZERO"] += 1
            per["index_fee_unknown"] += 1
        if (e.get("four_engine_caps_usd", {}).get("SIZING") ==
                e.get("four_engine_caps_usd", {}).get("CIBO_COMPOUND")):
            checks["SIZING_COMPOUND_IDENTICAL_CAP"] += 1
        checks["entry_fee_records"] += 1
        entry_fees += fee
        if "realized_pnl_usd_proxy" in e:
            net = D(e["realized_pnl_usd_proxy"])
            actual += net
            checks["realized_research_pnl"] += 1
            if -net > budget:
                checks["REALIZED_LOSS_GT_FIVE_PERCENT"] += 1
                per["realized_loss_gt_5pct"] += 1
            if -net > reserved:
                checks["REALIZED_LOSS_GT_RESERVED_STOP"] += 1
                per["realized_loss_gt_reserved_stop"] += 1
    if checks["sized"] != report["research_financed_proposals"]:
        raise AssertionError("REPORT_SIZE_TOTAL_MISMATCH")
    if abs(entry_fees - D(report["entry_cost_proxy_usd"])) > D("0.000000001"):
        raise AssertionError("COMMITTED_FULL_ROUNDTRIP_FEE_TOTAL_MISMATCH")
    if report.get("economic_motor_mode") == "independent_four_motors":
        opening = D(report["opening_commission_paid_proxy_usd"])
        closing = D(report["closing_commission_paid_proxy_usd"])
        pending = D(report["unsettled_future_close_fee_not_charged_usd"])
        full = D(report["roundtrip_total_commission_committed_proxy_usd"])
        if (any(x < D("0") for x in (opening, closing, pending))
                or abs(opening + closing + pending - full) > D("0.000000001")):
            raise AssertionError("OPEN_CLOSE_COMMISSION_CASHBOOK_DOES_NOT_RECONCILE")
        checks["SEPARATE_OPEN_CLOSE_COMMISSION_ACCOUNTING"] += 1
    # On stopped-provider scenarios, unresolved positions are not settled;
    # only validate net PnL against NAV when all assumed positions closed.
    if not report["provider_stopped"]:
        if abs(actual - D(report["net_research_pnl_usd"])) > D("0.000000001"):
            raise AssertionError("NAV_VS_REALIZED_PNL_MISMATCH")

    blockers = [
        "ONLY_HISTORICAL_2019_2022_R_OUTCOMES_AVAILABLE",
        "SCREENSHOT_2026_MARGINS_BACKDATED_AS_HISTORICAL_SNAPSHOT",
        ("FOUR_INDEPENDENT_MOTORS_USING_SIMULATED_NOT_AUTHENTICATED_ECONOMIC_OBSERVATIONS"
         if report.get("economic_motor_mode") == "independent_four_motors"
         else "NO_FOUR_INDEPENDENT_ENGINE_DECISIONS_OR_ABLATIONS"),
        "NO_MT5_BID_ASK_FILL_OR_REALIZED_TRADE_RECEIPTS",
        "NO_VERIFIED_FLOATING_EQUITY_DRAWNDOWN",
        ("ROUNDTRIP_COSTS_ARE_RESEARCH_SENSITIVITY_NOT_BROKER_STATEMENT"
         if report.get("economic_motor_mode") == "independent_four_motors"
         else "CLOSE_SIDE_COMMISSIONS_AND_SPREAD_UNVERIFIED"),
        "XAU_PERCENT_COMMISSION_BASIS_UNKNOWN",
        "NDX100_BROKER_COMMISSION_UNKNOWN",
        "SWAP_ROLLOVER_TIMESTAMP_NOT_SERVER_VERIFIED",
    ]
    if checks["REALIZED_LOSS_GT_FIVE_PERCENT"]:
        blockers.append("REALIZED_RESEARCH_LOSSES_EXCEED_5PCT_INITIAL_STOP_BUDGET")
    return {
        "schema": "qore.qdle.financial-truth-gate.v1",
        "financial_certification": "REJECTED",
        "four_motor_independent_attribution": False,
        "broker_real_time_current_market_simulation": False,
        "audit_integrity": "PASSED",
        "original_signals": len(events),
        "original_signals_unique": len({x["signal_fingerprint"] for x in events}),
        "lot_proposals_research_only": checks["sized"],
        "actual_mt5_fills": 0,
        "status_counts": dict(status),
        "checks": dict(checks),
        "by_symbol": {k: dict(v) for k, v in sorted(symbols.items())},
        "entry_fee_proxy_usd": str(entry_fees),
        "research_pnl_usd": str(actual),
        "blockers": blockers,
        "provenance": "RESEARCH_ONLY_SEALED_2019_2022_SIGNALS__2026_SCREENSHOT_SPECS",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = audit(json.loads(args.report.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    print("QDLE_TRUTH_GATE", json.dumps({
        "audit_integrity": result["audit_integrity"],
        "financial_certification": result["financial_certification"],
        "lot_proposals": result["lot_proposals_research_only"],
        "loss_over_5pct": result["checks"].get("REALIZED_LOSS_GT_FIVE_PERCENT", 0),
        "unknown_ndx_fee": result["checks"].get("INDEX_FEE_MISSING_ASSUMED_ZERO", 0),
    }, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
