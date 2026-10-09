#!/usr/bin/env python3
"""P0 scientific audit: why CIBO_COMPOUND binds 2782 of 3368 signals.

Input: immutable CEO CIBO manager+QDLE economic-stop replay. NO gate changes,
NO invented fills, NO counterfactual outcome PnL; compare per-entry finance
envelopes only. The provider margin lookup is a separately labeled static
2026 screenshot proxy, never real/historical MT5 preflight.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal as D, localcontext
from pathlib import Path

# Snapshot only, matched to scripts/qdle_3368_dual_ledger_replay.py
MARGIN_2026_SCENARIO = {
    "AUDJPY": {"BUY": D("2318.93"), "SELL": D("2318.67")},
    "EURUSD": {"BUY": D("3735.03"), "SELL": D("3734.77")},
    "GBPJPY": {"BUY": D("4407.40"), "SELL": D("4407.40")},
    "GBPUSD": {"BUY": D("4407.63"), "SELL": D("4407.63")},
    "NDX100": {"BUY": D("61481.98"), "SELL": D("61478.78")},
    "XAUUSD": {"BUY": D("53637.48"), "SELL": D("53629.68")},
}
CIBO_REASON = "BROKER_MINIMUM_UNFINANCEABLE_BY_CIBO_COMPOUND"
HALF = D("0.5")
FIVE = D("0.05")
MIN_LOT = D("0.01")
TOL = D("0.000000001")


class CompoundAuditError(ValueError):
    """Fail closed when the original 3368 replay inputs are not coherent."""


def _d(value: object, field: str) -> D:
    try:
        result = D(str(value))
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise CompoundAuditError(f"{field}: invalid decimal") from exc
    if not result.is_finite():
        raise CompoundAuditError(f"{field}: nonfinite")
    return result


def classify(event: dict) -> dict:
    """Exactly one audited primary reason; no changing legacy motor decisions."""
    rid = str(event["signal_fingerprint"])
    symbol = event["symbol"]
    if symbol not in MARGIN_2026_SCENARIO:
        raise CompoundAuditError("unrecognized symbol")
    if not event.get("cibo_manager_received"):
        raise CompoundAuditError("Trader opportunity not managed")
    action = event["cibo_manager_action"]
    if action not in (
        "ECONOMIC_PROTECTIVE_STOP_PROPOSED", "STRUCTURAL_STOP_AFFORDABLE_MIN_LOT",
        "ECONOMIC_STOP_AND_QDLE_QUOTE",
    ):
        raise CompoundAuditError(f"unsupported manager action {action}")
    caps = event.get("four_engine_caps_usd")
    if not caps or "CIBO_COMPOUND" not in caps or "SIZING" not in caps:
        raise CompoundAuditError("four-motor economic evidence absent")
    nav = _d(event["nav_at_decision_usd"], "nav")
    if nav <= 0:
        raise CompoundAuditError("nonpositive NAV")
    with localcontext() as ctx:
        ctx.prec=100
        risk5 = nav * FIVE
        compound = _d(caps["CIBO_COMPOUND"], "compound")
        sizing = _d(caps["SIZING"], "sizing")
        portfolio = _d(caps["PORTFOLIO_COMPOUND_AVAILABLE_SOURCE"], "portfolio")
        stop_per_lot = _d(event["stop_loss_usd_per_lot"], "stop_per_lot")
        fee_per_lot = _d(event["commission_roundtrip_proxy_per_lot"], "fee_per_lot")
        cost_min = MIN_LOT * (stop_per_lot + fee_per_lot)
        margin_budget = _d(event["leverage_margin_budget_usd"], "margin_budget")
        leverage_max = _d(event["leverage_max_lots"], "max_lots")
        # Side is NOT inferred from stop movements (they may be identical):
        # for proxy margin, conservatively use the higher of BUY and SELL.
        margin_min = max(MARGIN_2026_SCENARIO[symbol].values()) * MIN_LOT
        reason_codes = event["four_engine_reason_codes"]["CIBO_COMPOUND"]
        haircut = "THREE_SETTLED_LOSSES_HAIR_CUT" in reason_codes
        compound_half = abs(compound - risk5 * HALF) <= TOL
        compound_full = abs(compound - risk5) <= TOL
        blocked = event.get("reason") == CIBO_REASON
        other_caps = {
            "SIZING": sizing >= cost_min - TOL,
            "PORTFOLIO_SOURCE": portfolio >= cost_min - TOL,
            "LEVERAGE_MAX_LOTS": leverage_max >= MIN_LOT,
            "MARGIN_2026_PROXY": margin_budget >= margin_min,
        }
        theoretical_without_haircut = (
            risk5 >= cost_min - TOL and all(other_caps.values())
        )
        cause = (
            "THREE_SETTLED_LOSSES_HALF_RISK_BUDGET"
            if blocked and haircut and compound_half and
               compound < cost_min <= risk5 + TOL
            else "OTHER_COMPOUND_BINDING_NEEDS_INVESTIGATION" if blocked
            else "NOT_COMPOUND_FIRST_BINDING"
        )
        return {
            "signal_fingerprint": rid,
            "trader_id": event["trader"],
            "symbol": symbol,
            "at": event["at"],
            "manager_action": action,
            "qdle_state": event["status"],
            "qdle_primary_reason": event.get("reason"),
            "compound_first_binding": blocked,
            "compound_primary_subcause": cause,
            "three_settled_losses_haircut": haircut,
            "compound_budget_exact_half_nav5": compound_half,
            "compound_budget_equal_full_nav5": compound_full,
            "qore_nav_control_path_usd": str(nav),
            "original_risk_5pct_nav_usd": str(risk5),
            "compound_authorized_risk_usd": str(compound),
            "qore_risk_shortfall_due_to_haircut_usd": str(max(D(0), cost_min-compound)),
            "broker_min_lot": str(MIN_LOT),
            "min_lot_stop_loss_plus_roundtrip_fee_proxy_usd": str(cost_min),
            "open_close_fee_proxy_per_full_lot_usd": str(fee_per_lot),
            "sizing_cap_usd": str(sizing),
            "portfolio_source_cap_usd": str(portfolio),
            "leverage_max_lots": str(leverage_max),
            "leverage_approved_margin_usd": str(margin_budget),
            "broker_min_lot_margin_2026_static_proxy_usd": str(margin_min),
            "other_proxy_caps_sufficient_for_minlot": other_caps,
            "no_haircut_one_trade_price_and_caps_sensitivity": theoretical_without_haircut,
            "no_haircut_replay_pnl_usd": None,
            "broker_order_checked": False,
        }


def audit(report: dict) -> dict:
    events=report["decisions"]
    if (len(events)!=3368
        or len({e["signal_fingerprint"] for e in events})!=3368
        or not report["cibo_manager_experimental_activated"]
        or report["native_cibo_cognitive_decisions_consumed"]!=0
        or report["real_fundednext_fills"]!=0):
        raise CompoundAuditError("not same sealed CEO 3368 manager research run")
    census=[classify(x) for x in events]
    primary=Counter(r["compound_primary_subcause"] for r in census)
    other=Counter()
    per_symbol=defaultdict(Counter)
    action=Counter()
    for r in census:
        per_symbol[r["symbol"]]["received"]+=1
        if r["compound_first_binding"]:
            per_symbol[r["symbol"]]["compound_primary_block"]+=1
            action[r["manager_action"]]+=1
            for cap, enough in r["other_proxy_caps_sufficient_for_minlot"].items():
                if not enough:
                    other[cap]+=1
            if not r["no_haircut_one_trade_price_and_caps_sensitivity"]:
                other["NO_HAIRCUT_SINGLE_SIGNAL_STILL_NOT_PRICABLE"]+=1
    if (primary["THREE_SETTLED_LOSSES_HALF_RISK_BUDGET"]!=2782
        or primary["OTHER_COMPOUND_BINDING_NEEDS_INVESTIGATION"]!=0
        or report["unfundable_binding_constraints"].get("CIBO_COMPOUND")!=2782
        or sum(v for k,v in report["unfundable_binding_constraints"].items() if k!="CIBO_COMPOUND")!=18
        or other):
        raise CompoundAuditError(f"unexpected compound cause drift: {primary}, {other}")
    summary={
        "schema":"qore.cibo.p0.compound-3368-first-binding-causal-diagnostic.v1",
        "signals_received":len(events),
        "compound_primary_block":2782,
        "compound_root_cause_counts":dict(sorted(primary.items())),
        "blocked_by_manager_action":dict(sorted(action.items())),
        "other_constraints_insufficient_in_2782_at_static_proxy":dict(other),
        "every_compound_block_had_three_realized_losses_defense":True,
        "every_compound_block_had_2p5pct_instead_of_5pct_dynamic_nav":True,
        "every_compound_block_single_minlot_cost_within_full_5pct_proxy":True,
        "isolated_removal_half_risk_cap_minlot_price_feasibility":2782,
        "isolated_removal_half_risk_cap_sequential_qdle_proposals":None,
        "isolated_removal_half_risk_cap_reconstructed_pnl":None,
        "risk_policy_changed":False,
        "live_broker_rules_verified":False,
        "real_mt5_fills":0,
        "protected_reserve_observation":"REPLAY SETS protected_capital_usd=0, floating_loss_reserve_usd=0; DO NOT generalize to live treasury",
        "five_pct_nav_is_from":"UNMANAGED_STRUCTURAL_TRADER_EXIT_CONTROL_REPLAY, NOT AUTHENTIC CIBO MANAGED NAV",
        "broker_spec_assumptions":"2026 screenshots + fee proxies, min volume 0.01, incomplete historic spreads/stops; NO historical broker proof",
        "preregistered_policy":"Never disable three-loss hair-cut based on volume increase alone; require fresh-out-of-sample improved net PF, credible MTM DD <=25pct, full USD risk and fee controls, no additional sovereign breaches",
        "by_symbol":{k:dict(sorted(v.items())) for k,v in sorted(per_symbol.items())},
    }
    return {"summary":summary,"decision_audit":census}


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    d=audit(json.loads(args.report.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(d,sort_keys=True,indent=2)+"\n")
    print("CIBO_COMPOUND_3368_ROOT_CAUSE",json.dumps(d["summary"],sort_keys=True))


if __name__=="__main__":
    main()
