#!/usr/bin/env python3
"""Frozen-cohort CIBO rolling-PF allocation P0. PAPER scenario, no LIVE authority.

All chosen risk weights are functions only of outcomes ALREADY SETTLED for
trades previously admitted by the *same scenario*. Skipped trades do not enter
the learning history. The 540 original financed fills are frozen candidates:
no new signal, no re-entry and no claim of a full QDLE/MT5 account rerun.

Open costs and settlements are booked separately; volumes stay on 0.01 grid,
never exceed baseline financeable lots, and obey dynamic PAPER cash, active stop
exposure and PAPER broker margin. Differences in alternative cash NAV mean
broker pricing and future source eligibility would need a genuine rerun.
"""
from __future__ import annotations

import argparse
import heapq
import json
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

D = Decimal
ZERO = D(0)
ONE = D(1)
FIVE = D(".05")
MIN_LOT = D(".01")
INITIAL = D("60")
BROKER_MARGIN = D("2000")
MODES = ("BASELINE", "ROLLING_PF", "COOLDOWN", "ROLLING_PF_AND_COOLDOWN")
WINDOW = 30
MIN_SETTLED = 12
PRIOR_GAIN_USD = D("3")
PRIOR_LOSS_USD = D("3")
PAUSE_BELOW_PF = D(".6")
COOLDOWN_OPPORTUNITIES = 10


def as_time(value):
    at = datetime.fromisoformat(value)
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("timezone aware event timestamp required")
    return at


def _floor_lot(value):
    return (value / MIN_LOT).to_integral_value(rounding=ROUND_FLOOR) * MIN_LOT


@dataclass
class RollingTrader:
    outcomes: deque
    loss_streak: int = 0
    cooldown_left: int = 0
    probation_due: bool = False
    last_settlement_at: datetime | None = None

    def __init__(self):
        self.outcomes = deque(maxlen=WINDOW)
        self.loss_streak = 0
        self.cooldown_left = 0
        self.probation_due = False
        self.last_settlement_at = None

    def update(self, pnl: Decimal, at: datetime):
        if self.last_settlement_at is not None and at < self.last_settlement_at:
            raise ValueError("out of order rolling outcome")
        self.last_settlement_at = at
        self.outcomes.append(pnl)
        self.loss_streak = self.loss_streak + 1 if pnl < ZERO else 0
        if self.loss_streak >= 10:
            self.cooldown_left = COOLDOWN_OPPORTUNITIES
            self.probation_due = True
            self.loss_streak = 0

    def pf(self):
        gains = sum((p for p in self.outcomes if p > ZERO), ZERO)
        losses = sum((-p for p in self.outcomes if p < ZERO), ZERO)
        return (gains + PRIOR_GAIN_USD) / (losses + PRIOR_LOSS_USD)

    def decide(self, *, mode: str):
        prior_count = len(self.outcomes)
        pf = self.pf()
        if mode not in MODES:
            raise ValueError("unknown research mode")
        use_pf = mode in ("ROLLING_PF", "ROLLING_PF_AND_COOLDOWN")
        use_pause = mode in ("COOLDOWN", "ROLLING_PF_AND_COOLDOWN")
        if use_pause and self.cooldown_left > 0:
            self.cooldown_left -= 1
            return ZERO, "PAPER_CAUSAL_COOLDOWN", prior_count, pf
        # After a cooldown, accept a probation attempt to permit recovery
        # without consuming any suppressed trades' future paper outcomes.
        probation = bool(use_pause and self.probation_due)
        if probation:
            self.probation_due = False
        if use_pause and not probation and prior_count >= MIN_SETTLED and pf < PAUSE_BELOW_PF:
            self.cooldown_left = COOLDOWN_OPPORTUNITIES - 1
            self.probation_due = True
            return ZERO, "PAPER_ROLLING_PF_COOLDOWN", prior_count, pf
        weight = ONE
        if use_pf and prior_count >= MIN_SETTLED:
            weight = min(ONE, max(D(".25"), pf))
        return weight, ("PAPER_PROBATION" if probation else "PAPER_ROLLING_PF"
                        if weight < ONE else "PAPER_NEUTRAL"), prior_count, pf


def frozen_inputs(manifest, replay):
    signals = manifest["opportunities"]
    source = {x["signal_fingerprint"]:x["trader_id"] for x in signals}
    if len(source) != 3368 or len(signals) != 3368:
        raise ValueError("not the 3368 immutable signal cohort")
    if manifest.get("governance", {}).get("fresh_oos_claimed") is not False:
        raise ValueError("source governance must be reused/burned, not future OOS")
    rows = replay["signal_decisions"]
    deals = replay["closed_trades"]
    if replay["counts"]["received"] != 3368 or replay["counts"]["paper_open"] != 540 or len(deals) != 538:
        raise ValueError("not the frozen 540 PAPER cohort")
    if replay.get("certified") is not False or replay.get("broker_fills") != 0:
        raise ValueError("LIVE provenance is not permitted")
    winners = [x for x in rows if x.get("status") in ("PAPER_OPEN","PAPER_OPEN_UNRESOLVED_NO_EXIT_PATH")]
    if len(winners) != 540 or len({x["signal_fingerprint"] for x in winners}) != 540:
        raise ValueError("opening population drift")
    by_id = {x["signal_fingerprint"]:x for x in deals}
    if len(by_id) != 538 or any(x not in source for x in by_id):
        raise ValueError("closing population drift")
    if any(x["signal_fingerprint"] not in source for x in winners):
        raise ValueError("original Trader missing from manifest")
    return sorted(winners,key=lambda r:(r["paper_entry_at"],r["signal_fingerprint"])), by_id, source


def summarize(closed):
    gains = sum((x["pnl"] for x in closed if x["pnl"] > ZERO),ZERO)
    losses = sum((-x["pnl"] for x in closed if x["pnl"] < ZERO),ZERO)
    n = len(closed)
    return {
        "closed": n,
        "wins": sum(x["pnl"] > ZERO for x in closed),
        "losses": sum(x["pnl"] < ZERO for x in closed),
        "flats": sum(x["pnl"] == ZERO for x in closed),
        "net_usd": str(gains - losses), "gross_wins_usd": str(gains),
        "gross_losses_usd": str(losses),
        "profit_factor": str(gains / losses) if losses else None,
        "win_rate_pct": str(D(100) * D(sum(x["pnl"] > ZERO for x in closed)) / D(n))
                        if n else None,
    }


def simulate_mode(rows, deals, traders, mode):
    rolling = defaultdict(RollingTrader)
    cash = INITIAL
    equity_peak_cash = INITIAL
    max_cash_dd = ZERO
    pending = []
    active = {}
    settled = []
    assessments = []
    reasons = Counter()
    observed_future_outcomes_before_entry = 0
    opening_fees_total = ZERO
    for row in rows:
        sid = row["signal_fingerprint"]
        at = as_time(row["paper_entry_at"])
        while pending and pending[0][0] <= at:
            exit_at, close_sid, pnl, gross = heapq.heappop(pending)
            pos = active.pop(close_sid)
            cash += gross
            settled.append({"signal":close_sid,"trader":pos["trader"],
                            "entry_at":pos["entry_at"].isoformat(),
                            "exit_at":exit_at.isoformat(),"pnl":pnl})
            rolling[pos["trader"]].update(pnl,exit_at)
            equity_peak_cash = max(equity_peak_cash,cash)
            max_cash_dd = max(max_cash_dd,(equity_peak_cash-cash)/equity_peak_cash)
        trader = traders[sid]
        context = rolling[trader]
        weight,reason,n,pf = context.decide(mode=mode)
        original_lots = D(row["qdle_lots"])
        orig_risk = D(row["qdle_all_in_risk"])
        orig_margin = D(row["qdle_margin_usd"])
        original_fee = D(row["paper_open_fee_usd"])
        nominal = original_lots if mode=="BASELINE" else _floor_lot(original_lots * weight)
        held_risk = sum((v["risk"] for v in active.values()),ZERO)
        held_margin = sum((v["margin"] for v in active.values()),ZERO)
        if mode != "BASELINE" and nominal:
            # No invented below-min-lot fills and no risk that exceeds dynamic
            # current QORE cash, source availability or proxy margin capacity.
            max_by_stop = _floor_lot(
                max(ZERO,min(cash*FIVE, cash-held_risk)) * original_lots / orig_risk
            ) if orig_risk > ZERO else ZERO
            free_margin = max(ZERO, BROKER_MARGIN + cash-INITIAL-held_margin)
            max_by_margin = _floor_lot(
                free_margin * original_lots / orig_margin
            ) if orig_margin > ZERO else ZERO
            nominal = min(nominal,max_by_stop,max_by_margin,original_lots)
        if nominal < MIN_LOT:
            nominal = ZERO
        reasons[reason]+=1
        if not nominal:
            reasons["PAPER_ABSTAIN_OR_PHYSICAL_MIN_LOT"]+=1
            assessments.append({"id":sid,"trader":trader,"entry_at":at.isoformat(),
                                "rolling_pf_predecision":str(pf),"prior_settled_n":n,
                                "weight":str(weight),"reason":reason,
                                "actual_lot":"0","admitted":False})
            continue
        ratio = nominal/original_lots
        fee = original_fee*ratio
        cash -= fee
        opening_fees_total += fee
        active[sid]={"trader":trader,"risk":orig_risk*ratio,
                     "margin":orig_margin*ratio,"entry_at":at}
        assessments.append({"id":sid,"trader":trader,"entry_at":at.isoformat(),
                            "rolling_pf_predecision":str(pf),"prior_settled_n":n,
                            "weight":str(weight),"reason":reason,
                            "actual_lot":str(nominal),"admitted":True})
        if sid in deals:
            closed = deals[sid]
            exit_at = as_time(closed["exit_at"])
            if exit_at < at:
                raise ValueError("future outcome precedes entry")
            # Original settled PnL already includes original OPEN fee, so
            # reversing that fee recovers post-entry gross to be settled.
            gross = (D(closed["net_usd"])+original_fee)*ratio
            net = gross-fee
            heapq.heappush(pending,(exit_at,sid,net,gross))
        equity_peak_cash = max(equity_peak_cash,cash)
        max_cash_dd = max(max_cash_dd,(equity_peak_cash-cash)/equity_peak_cash)
    while pending:
        at,sid,pnl,gross=heapq.heappop(pending)
        pos=active.pop(sid)
        cash+=gross
        settled.append({"signal":sid,"trader":pos["trader"],
                        "entry_at":pos["entry_at"].isoformat(),
                        "exit_at":at.isoformat(),"pnl":pnl})
        rolling[pos["trader"]].update(pnl,at)
        equity_peak_cash = max(equity_peak_cash,cash)
        max_cash_dd=max(max_cash_dd,(equity_peak_cash-cash)/equity_peak_cash)
    summary=summarize(settled)
    summary.update({
        "scenario":mode,
        "frozen_candidate_signals":540,
        "paper_openings":sum(x["admitted"] for x in assessments),
        "paper_unresolved_open_positions":len(active),
        "opening_fees_total_usd":str(opening_fees_total),
        "paper_cash_after_events_usd":str(cash),
        "paper_cash_max_dd_pct":str(max_cash_dd*D(100)),
        "decisions_with_future_data":observed_future_outcomes_before_entry,
        "reason_counts":dict(reasons),
        "outcome_learning_policy":"ONLY_SETTLED_PREVIOUSLY_ADMITTED_TRADES",
        "no_unauthorized_new_lot":True,
    })
    return summary,assessments,settled


def run(manifest,replay):
    rows,deals,traders=frozen_inputs(manifest,replay)
    results={}
    decisions={}
    for mode in MODES:
        summary,assessed,closed=simulate_mode(rows,deals,traders,mode)
        results[mode]=summary
        decisions[mode]=assessed
    baseline=results["BASELINE"]
    assert baseline["paper_openings"]==540 and baseline["closed"]==538
    assert D(baseline["net_usd"]) == D(replay["shadow_projected_settled_net_pnl_usd"])
    assert baseline["paper_unresolved_open_positions"]==2
    assert all(v["decisions_with_future_data"]==0 for v in results.values())
    return {
        "schema":"qore.cibo.paper-rolling-pf-allocation-540.v1",
        "research_only":True,"certified":False,"broker_fills":0,
        "funded_population":"FROZEN_540_NO_NEW_TRADES",
        "temporal_order":"SETTLE_AT_OR_BEFORE_ENTRY_BEFORE_ROLLING_PF_CALC",
        "historical_bid_ask_verified":False,
        "lookback_settled_per_trader":WINDOW,"min_settled_for_pf":MIN_SETTLED,
        "prior_gain_usd":str(PRIOR_GAIN_USD),"prior_loss_usd":str(PRIOR_LOSS_USD),
        "pause_below_pf":str(PAUSE_BELOW_PF),
        "cooldown_eligible_signals":COOLDOWN_OPPORTUNITIES,
        "policies":results,
        "decisions":decisions,
        "limitations":[
            "Selected, reused, burned frozen cohort (NO fresh OOS and no certified edge)",
            "Scenario uses original entrant outcomes as counterfactual conditional on frozen entry and exit geometry",
            "Cash and live reservations change under allocation; other 2808 originally unfinanced signals are not reevaluated",
            "Never an MT5 broker account, no true historical spread/swap/execution/portfolio MTM",
            "Skip means NO observed outcome for later learning; cooldown recovery uses a probation signal",
            "Physical downscaling rounds to 0.01 lot, some policies suppress originally 0.01-volume trades",
            "Stop-protector ablation is a separate experiment; do not sum its post-hoc +$16.43 benefit here",
            "Rolling PF over previously *selected* traders has estimation and survivorship biases",
        ],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--replay",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    report=run(json.loads(args.manifest.read_text()),json.loads(args.replay.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("CIBO_P0_ROLLING_PF_ALLOCATION_540",json.dumps(report["policies"],sort_keys=True),flush=True)


if __name__=="__main__":
    main()
