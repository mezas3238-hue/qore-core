#!/usr/bin/env python3
"""Causal *signal provenance* audit for 3368 frozen Trader opportunities.

Reads only predecision trader_opportunity fields as explanatory covariates;
realized PAPER outcomes enter the SEPARATE research outcome column. Historical
broker spreads and fresh out-of-sample edge are NOT established by this audit.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path
import json

FAMILY = {
    "R34_XAUUSD": "ICT_TURTLE_SOUP_H1_H4",
    "R38_EURUSD": "ICT_TURTLE_SOUP_H1_H4",
    "R38_GBPJPY": "ICT_TURTLE_SOUP_H1_H4",
    "R42_AUDJPY": "ICT_TURTLE_SOUP_H1_H4",
    "R43_GBPUSD": "ICT_TURTLE_SOUP_H1_H4",
    "VT31_NAS100": "NY_AM_SILVER_BULLET_M1",
    "VT08_FOREX": "H4_PO3_B01_M15",
}
PREDICTORS = ("ctx_timeframe", "ctx_session", "ctx_cisd_progress_bucket",
              "ctx_strategy_projected_r_bucket", "ctx_side",
              "cash_open_state", "reg_h1_range_state", "reg_h4_range_state",
              "reg_m5_displacement_alignment", "ctx_prior_body_alignment",
              "target_route")
ZERO = D(0)


def _summarize(items):
    closed = [x["net_usd"] for x in items if x["net_usd"] is not None]
    wins = [x for x in closed if x > ZERO]
    loses = [-x for x in closed if x < ZERO]
    win_sum, loss_sum = sum(wins, ZERO), sum(loses, ZERO)
    return {
        "source_signals": len(items),
        "paper_openings": sum(x["paper_open"] for x in items),
        "paper_settled": len(closed),
        "unresolved_openings": sum(x["paper_open"] for x in items) - len(closed),
        "winners": len(wins), "losers": len(loses),
        "flats": len(closed) - len(wins) - len(loses),
        "paper_net_usd": str(win_sum-loss_sum),
        "paper_pf": str(win_sum/loss_sum) if loss_sum > ZERO else None,
        "paper_winrate_pct": str(D(len(wins))*D(100)/D(len(closed)))
                             if closed else None,
    }


def audit(manifest: dict, replay: dict) -> dict:
    originals = manifest["opportunities"]
    decisions = replay["signal_decisions"]
    closes = replay["closed_trades"]
    if len(originals) != len(decisions) != 3368:
        raise ValueError("source/replay counts differ from frozen 3368")
    sources = {o["signal_fingerprint"]: o for o in originals}
    assessments = {d["signal_fingerprint"]: d for d in decisions}
    settled = {c["signal_fingerprint"]: c for c in closes}
    if (len(sources) != 3368 or len(assessments) != 3368
            or set(sources) != set(assessments)
            or len(settled) != len(closes)):
        raise ValueError("source fingerprints missing/duplicate/replaced")
    if (replay.get("certified") is not False
            or replay.get("broker_fills") != 0
            or replay.get("counts", {}).get("paper_open") != 540
            or len(settled) != 538):
        raise ValueError("expected the frozen, non-certified 540/538 PAPER cohort")
    if manifest.get("governance", {}).get("reused_burned_research_population") is not True:
        raise ValueError("research source lineage changed: preserve original governance")
    rows = []
    for fingerprint, source in sources.items():
        opportunity = source["trader_opportunity"]
        trader = source["trader_id"]
        if trader not in FAMILY or opportunity["trader_id"] != trader:
            raise ValueError("unknown source Trader/mismatched issuer")
        raw_context = opportunity["decision_context"]
        context = dict(raw_context)
        if len(context) != len(raw_context):
            raise ValueError("duplicate predecision context keys")
        evidence = {k: context.get(k) for k in PREDICTORS}
        decision = assessments[fingerprint]
        opened = decision.get("status") in (
            "PAPER_OPEN", "PAPER_OPEN_UNRESOLVED_NO_EXIT_PATH")
        has_close = fingerprint in settled
        if has_close and not opened:
            raise ValueError("closed PAPER trade without opening")
        year = datetime.fromisoformat(source["market_decision_at"]).year
        rows.append({
            "fingerprint": fingerprint, "trader": trader,
            "strategy_family": FAMILY[trader],
            "timeframe": context.get("ctx_timeframe"),
            "year": year, "side": opportunity["side"],
            "paper_open": opened,
            "net_usd": D(settled[fingerprint]["net_usd"]) if has_close else None,
            "predictors": evidence,
        })
    if sum(x["paper_open"] for x in rows) != 540 or sum(
        x["net_usd"] is not None for x in rows) != 538:
        raise ValueError("opening/closing identity drift")
    grouped = {}
    for dimension in ("trader", "strategy_family", "timeframe", "year", "side"):
        subsets = defaultdict(list)
        for x in rows:
            subsets[str(x[dimension])].append(x)
        grouped[dimension] = {key: _summarize(items)
                              for key, items in sorted(subsets.items())}
    # No post-entry truth is read from the manifest (settlement_outcome_research_only).
    for key in ("cash_open_state", "reg_h4_range_state",
                "ctx_cisd_progress_bucket", "ctx_strategy_projected_r_bucket"):
        sub = defaultdict(list)
        for x in rows:
            sub[str(x["predictors"][key])].append(x)
        grouped[key] = {name: _summarize(items)
                        for name, items in sorted(sub.items())}
    return {
        "schema": "qore.cibo.p0-trader-source-signal-audit-3368.v1",
        "classification": "RESEARCH_ONLY_FROZEN_BURNED_NOT_OOS",
        "source_reuse_governance": manifest["governance"],
        "paper_costs_verified_historical": False,
        "record_count": len(rows),
        "total": _summarize(rows),
        "groups": grouped,
        "source_paths": {
            "five_turtle": "src/qore/infrastructure/trader_lab/turtle_soup_eurusd_r1.py",
            "vt31": "src/qore/infrastructure/traders/vt31_silver_bullet_r2_2.py",
            "vt08": "src/qore/infrastructure/traders/vt08_b01_r3_8.py",
        },
        "restrictions": [
            "All group comparisons are descriptive, from selected, funded PAPER cohort",
            "Context features from trader_opportunity only; future settlement excluded from predictor",
            "Unknown historical bid/ask, commissions, provider specifications and intrabar path",
            "H4 group and per-Trader samples can be small, no OOS validation",
            "Do NOT use cohort-derived subgroup performance as CIBO/Trader live filter",
            "Temporal H1/H4 label describes source signals, M5 describes exit OHLC reconstruction",
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--replay", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    j = audit(json.loads(a.manifest.read_text()),
              json.loads(a.replay.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(j,indent=2,sort_keys=True)+"\n")
    print("CIBO_P0_SOURCE_SIGNAL_AUDIT_3368", json.dumps({
        "total": j["total"],"traders":j["groups"]["trader"],
        "timeframes":j["groups"]["timeframe"],
        "classification":j["classification"]},sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
