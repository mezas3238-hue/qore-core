#!/usr/bin/env python3
"""CIBO P0 4-arm config preflight and physical lot/risk primitives.

Research POLICY primitives, not a 3368 market replay and not real broker
quotes. Does not mutate QDLE or transmit orders. Fail closed on causal gaps.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

D = Decimal
ZERO = D("0")
MAX_RISK = D("0.05")
SCENARIOS = {("A", "X"), ("A", "Y"), ("B", "X"), ("B", "Y")}
FOREX = {"EURUSD", "GBPUSD", "GBPJPY", "AUDJPY"}
JPY = {"GBPJPY", "AUDJPY"}
REQUIRED_EVIDENCE = (
    "one_canonical_sqlite_book",
    "original_3368_seven_trader_manifest",
    "causal_vt31_m1_executable_quotes",
    "native_timeframe_predecision_atr14",
    "historical_usdjpy_at_epoch",
    "historical_instrument_bidask",
    "historical_account_commission_receipts",
    "four_fresh_economic_motor_votes",
    "portfolio_mtm_price_path",
)
FIVE_PCT = D("0.05")


class ResearchBlockedError(ValueError):
    """Attempt to call a counterfactual observation a real historical replay."""


def dec(raw, name: str, *, allow_zero: bool = True) -> Decimal:
    if type(raw) not in (str, Decimal, int):
        raise ResearchBlockedError(name + ": unsupported numeric value")
    try:
        value = D(str(raw))
    except Exception as exc:
        raise ResearchBlockedError(name + ": invalid decimal") from exc
    if not value.is_finite() or value < 0 or (not allow_zero and value == ZERO):
        raise ResearchBlockedError(name + ": expected finite nonnegative value")
    return value


def validate_config(config: dict) -> None:
    if config.get("schema") != "qore.cibo.p0.four_arm_atr_5pct.v1":
        raise ResearchBlockedError("unknown exact 4-arm config schema")
    acc = config.get("account", {})
    if (dec(acc.get("starting_qore_usd"), "initial capital") != D("60")
        or dec(acc.get("maximum_risk_per_entry_fraction"), "trade max") != MAX_RISK
        or dec(acc.get("maximum_total_held_stop_risk_fraction"), "total max") != MAX_RISK
        or acc.get("broker_execution_allowed") is not False
        or acc.get("vps_allowed") is not False
        or acc.get("singleton_paper_sqlite_required") is not True
        or dec(acc.get("lot_min"), "min lot") != D("0.01")
        or dec(acc.get("lot_step"), "step") != D("0.01")):
        raise ResearchBlockedError("account scope/risk/real-execution invariants changed")
    if (config.get("input", {}).get("exact_original_signal_count")!=3368
        or config.get("input", {}).get("trader_count")!=7
        or config["input"].get("years")!=[2019,2020,2021,2022]):
        raise ResearchBlockedError("frozen 3368 / seven-Trader corpus mismatch")
    modes = config.get("mode_risk", {})
    for mode in ("BANK", "MEDIUM", "ATTACK"):
        row = modes.get(mode, {})
        for policy in ("A", "B"):
            allowed = D("0.0125") if (mode, policy)==("BANK", "A") else FIVE_PCT
            if dec(row.get(policy), "mode risk") != allowed:
                raise ResearchBlockedError("4-arm mode risk contract changed")
    atr = config.get("atr14", {})
    if (atr.get("method") != "WILDER_PREDECISION_FULLY_CLOSED_NATIVE_TF"
        or dec(atr.get("BANK"), "BANK ATR") != D("0.5")
        or dec(atr.get("MEDIUM"), "MEDIUM ATR") != D("1.0")):
        raise ResearchBlockedError("ATR14 must be causally native and mode-specific")
    for sym,table in {
        "AUDJPY":{"M15":"1.5","H1":"1.75","H4":"2.0"},
        "EURUSD":{"H1":"1.5","H4":"1.75"},
        "GBPJPY":{"M15":"1.75","H1":"2.0","H4":"2.0"},
        "GBPUSD":{"M15":"1.5","H1":"1.75","H4":"2.0"},
        "NDX100":{"M1":"2.0"},
        "XAUUSD":{"H1":"2.0","H4":"2.0"},
    }.items():
        if atr.get("ATTACK",{}).get(sym)!=table:
            raise ResearchBlockedError(sym+": unsupported ATTACK ATR table changed")
    fees=config.get("fees",{})
    if (dec(fees.get("forex_fee_usd_per_lot_open"),"forex fee") != D(7)
        or dec(fees.get("forex_fee_usd_per_lot_close"),"forex closing fee") != ZERO
        or dec(fees.get("gold_open_notional_rate"),"gold fee") != D("0.000016")
        or dec(fees.get("gold_close_rate"),"gold closing fee") != ZERO
        or dec(fees.get("index_usd_per_lot_open_X"),"NDX X fee") != ZERO
        or dec(fees.get("index_usd_per_lot_open_Y"),"NDX Y fee") != D(20)
        or fees.get("index_fee_Y_classification")!="COUNTERFACTUAL_STRESS_NOT_PROVIDER_REAL"):
        raise ResearchBlockedError("fee variant cannot impersonate historical broker")
    arms=config.get("scenarios",[])
    if (not isinstance(arms,list) or len(arms)!=4
        or {(v.get("risk_policy"),v.get("ndx_fee_model")) for v in arms} != SCENARIOS
        or len({v.get("arm") for v in arms})!=4
        or any(v.get("arm") != v.get("risk_policy")+"-"+v.get("ndx_fee_model")
               for v in arms)):
        raise ResearchBlockedError("requires exactly four A/B x X/Y distinct arms")
    if any(arm["ndx_fee_classification"]!="SYNTHETIC_STRESS"
           for arm in arms if arm["ndx_fee_model"]=="Y"):
        raise ResearchBlockedError("NDX $20 stress cannot be called a real fee")
    if (config.get("certification",{}).get("no_live") is not True
        or config["certification"].get("no_vps") is not True):
        raise ResearchBlockedError("PAPER-only certification contract changed")


def atr_multiplier(config: dict, symbol: str, timeframe: str, mode: str) -> Decimal:
    if mode in ("BANK", "MEDIUM"):
        return dec(config["atr14"][mode], "ATR multiplier", allow_zero=False)
    if mode != "ATTACK":
        raise ResearchBlockedError("unrecognized Native MAX mode")
    try:
        return dec(config["atr14"]["ATTACK"][symbol][timeframe],
                   "ATTACK multiplier", allow_zero=False)
    except KeyError as exc:
        raise ResearchBlockedError(
            "UNASSESSABLE_UNDEFINED_ATR_MULTIPLIER") from exc


def commission_open_per_lot(config: dict, symbol: str, entry_price: Decimal,
                            contract_size: Decimal, ndx_variant: str) -> Decimal:
    entry=dec(entry_price, "entry", allow_zero=False)
    contract=dec(contract_size, "contract size", allow_zero=False)
    fees=config["fees"]
    if symbol in FOREX:
        return dec(fees["forex_fee_usd_per_lot_open"], "forex fee")
    if symbol=="XAUUSD":
        return entry*contract*dec(fees["gold_open_notional_rate"], "gold rate")
    if symbol=="NDX100" and ndx_variant in ("X","Y"):
        return dec(fees["index_usd_per_lot_open_"+ndx_variant],"index tariff")
    raise ResearchBlockedError("unsupported instrument or fee variant")


def stop_loss_usd_per_lot(*, symbol: str, entry: Decimal, stop: Decimal,
                          contract_size: Decimal, usd_jpy: Decimal | None = None) -> Decimal:
    entry=dec(entry,"entry",allow_zero=False)
    stop=dec(stop,"stop",allow_zero=False)
    contract=dec(contract_size,"contract size",allow_zero=False)
    distance=abs(entry-stop)
    if distance==ZERO:
        raise ResearchBlockedError("nonzero stop distance required")
    if symbol in JPY:
        if usd_jpy is None:
            raise ResearchBlockedError("UNASSESSABLE_NO_HISTORICAL_USDJPY")
        return distance*contract/dec(usd_jpy,"USDJPY at epoch",allow_zero=False)
    if symbol in ("EURUSD","GBPUSD","XAUUSD","NDX100"):
        return distance*contract
    raise ResearchBlockedError("unsupported instrument")


def physical_order_quote(config: dict, *, arm: str, mode: str, symbol: str,
                         timeframe: str, side: str, entry: Decimal,
                         structural_stop: Decimal, atr14: Decimal,
                         contract_size: Decimal, nav: Decimal,
                         held_risk: Decimal, free_margin: Decimal,
                         margin_per_lot: Decimal, usd_jpy: Decimal | None = None,
                         other_all_in_cost_usd_per_lot: Decimal = ZERO,
                         lot_min: Decimal = D("0.01"),
                         lot_step: Decimal = D("0.01")) -> dict:
    """One counterfactual PAPER budget, not an authorization to fill.

    QDLE remains responsible for real live physical volume and settlement.
    """
    validate_config(config)
    matched=[x for x in config["scenarios"] if x["arm"]==arm]
    if len(matched)!=1:
        raise ResearchBlockedError("unknown scenario arm")
    policy,variant=matched[0]["risk_policy"],matched[0]["ndx_fee_model"]
    if side not in ("BUY","SELL"):
        raise ResearchBlockedError("BUY/SELL required")
    entry=dec(entry,"entry",allow_zero=False)
    structural_stop=dec(structural_stop,"original Trader SL",allow_zero=False)
    atr=dec(atr14,"prior 14 bars ATR",allow_zero=False)
    contract=dec(contract_size,"contract",allow_zero=False)
    nav=dec(nav,"current NAV")
    held=dec(held_risk,"held portfolio stop risk")
    free=dec(free_margin,"free margin")
    margin=dec(margin_per_lot,"margin per lot",allow_zero=False)
    other=dec(other_all_in_cost_usd_per_lot,"other cost")
    lot_min=dec(lot_min,"minimum lot",allow_zero=False)
    lot_step=dec(lot_step,"lot step",allow_zero=False)
    if held > nav*MAX_RISK:
        raise ResearchBlockedError("portfolio 5% already breached; reconcile first")
    mult=atr_multiplier(config,symbol,timeframe,mode)
    stop=entry - mult*atr if side=="BUY" else entry + mult*atr
    if ((side=="BUY" and not structural_stop<entry)
        or (side=="SELL" and not structural_stop>entry)):
        raise ResearchBlockedError("invalid original structural SL geometry")
    structural_distance=abs(entry-structural_stop)
    economic_distance=abs(entry-stop)
    if economic_distance>structural_distance:
        return {"status":"RESEARCH_ATR_STOP_WIDENS_TRADER_STRUCTURAL_RISK",
                "lots":"0","atr_multiplier":str(mult),
                "economic_stop":str(stop),"original_stop":str(structural_stop),
                "broker_fills":0}
    cash_limit=nav*MAX_RISK
    mode_request=nav*dec(config["mode_risk"][mode][policy],"mode budget")
    available=max(ZERO,min(cash_limit-held,mode_request))
    cost=stop_loss_usd_per_lot(
        symbol=symbol,entry=entry,stop=stop,contract_size=contract,usd_jpy=usd_jpy
    )+commission_open_per_lot(config,symbol,entry,contract,variant)+other
    if cost<=0:
        raise ResearchBlockedError("nonpositive all-in risk per lot")
    opening_fee_per_lot=commission_open_per_lot(
        config,symbol,entry,contract,variant)
    # OPEN fees debit cash/NAV immediately. Reserve against AFTER-FEE NAV:
    # held_stop_risk + new_stop_risk <= 5%*(NAV-new_open_fee)
    # => lots*(all_in_risk_per_lot+5%*open_fee_per_lot)
    #    <= 5%*NAV - currently_held_stop_risk.
    # A weaker before-fee inequality admits portfolio 5% breaches.
    fee_adjusted_denom=cost+FIVE_PCT*opening_fee_per_lot
    risk_grid=(available/fee_adjusted_denom/lot_step).to_integral_value(
        rounding=ROUND_FLOOR)*lot_step
    margin_grid=(free/margin/lot_step).to_integral_value(rounding=ROUND_FLOOR)*lot_step
    lots=max(ZERO,min(risk_grid,margin_grid))
    return {
        "status":"RESEARCH_POSITIVE_PHYSICAL_LOT_QUOTE" if lots>=lot_min else
                 "UNFUNDABLE_MIN_LOT_RISK_OR_MARGIN",
        "lots":str(lots if lots>=lot_min else ZERO),
        "risk_usd":str(lots*cost if lots>=lot_min else ZERO),
        "mode_risk_requested_usd":str(mode_request),
        "portfolio_new_risk_limit_usd":str(available),
        "held_risk_before_usd":str(held),
        "fee_open_usd_per_lot":str(opening_fee_per_lot),
        "nav_after_open_fee_usd":str(nav-lots*opening_fee_per_lot if lots>=lot_min else nav),
        "stop_loss_usd_per_lot":str(cost),
        "margin_usd":str(lots*margin if lots>=lot_min else ZERO),
        "atr_multiplier":str(mult),
        "economic_stop":str(stop),
        "original_stop":str(structural_stop),
        "source":"RESEARCH_SCENARIO_NOT_EXECUTED_OR_HISTORICALLY_CERTIFIED",
        "broker_fills":0,
    }


def readiness(config: dict, evidence: dict | None = None) -> dict:
    validate_config(config)
    evidence = evidence if isinstance(evidence,dict) else {}
    # self-certified booleans must NOT activate an empirical replay.
    receipts=evidence.get("validated_receipts",{})
    missing=[]
    for name in REQUIRED_EVIDENCE:
        item=receipts.get(name) if isinstance(receipts,dict) else None
        if not (isinstance(item,dict)
                and item.get("independent_gate_status") == "PASS"
                and isinstance(item.get("artifact_sha256"),str)
                and item["artifact_sha256"].startswith("sha256:")
                and len(item["artifact_sha256"])==71
                and isinstance(item.get("source_run_url"),str)
                and item["source_run_url"].startswith("https://github.com/")):
            missing.append(name)
    return {
        "schema":"qore.cibo.p0.four-arm-readiness.v1",
        "config_schema":config["schema"],
        "status":"BLOCKED_MISSING_EMPIRICAL_PROVENANCE" if missing
                else "RESEARCH_PRECHECK_RECEIPTS_PRESENT_NOT_YET_REPLAY_CERTIFIED",
        "blocked_gates":missing,
        "ready_for_claim_of_historical_profits":False,
        "ndx20_stress_never_real":True,
        "four_arms":[v["arm"] for v in config["scenarios"]],
        "no_live":True,"broker_fills":0,
        "note":"Even PASS receipt descriptors need GitHub artifact independent cross-check; metadata is not a broker fill.",
    }


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True,type=Path)
    p.add_argument("--evidence",type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    config=json.loads(args.config.read_text())
    evidence=json.loads(args.evidence.read_text()) if args.evidence else {}
    result=readiness(config,evidence)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("CIBO_P0_FOUR_ARM_READINESS",json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
