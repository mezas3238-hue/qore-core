"""W3 CMTRL: independent causal eight-state Bayesian H1 transition researcher.

Third/final original exploration. All 33 original source M5 SHA audited first;
mature next-H1 labels only; no PnL in training and no broker execution.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, deque
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any

from qore.research.alpha2_g1a_native_m5_gross import arm
from qore.research.alpha2_intermarket import M5, MARKETS, sha256_file
from qore.research.alpha2_lab_h4_extract import source33_manifest, verify_source
from qore.research.alpha2_w2_pade_native_m5 import (
    DEVELOPMENT_END,
    H1,
    NativeM5,
    complete_hours,
    read_original_market_rows,
)
from qore.research.alpha2_w2_volume_full33 import CUTOFF

IDENTITY = "QORE_ALPHA2_W3_CMTRL_FIRST_GROSS_NATIVE_M5_V01"
SOURCE33_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
WINDOW_HOURS = timedelta(hours=72)
WINDOW_LABEL_DAYS = timedelta(days=90)
LABELS_N = 240
PREVIOUS_RANGES = 20
MIN_STATE_EXAMPLES = 20
MIN_POSTERIOR_UP = 0.65
MAX_POSTERIOR_UP = 0.35
MIN_BASE_EXCESS = 0.10
ENTRY_DELAY = M5
MAX_HOLD = timedelta(hours=4)


def classify_h1_state(current: Any, prior: list[Any]) -> tuple[int, int, int] | None:
    if len(prior) < PREVIOUS_RANGES or current.range_price <= 0:
        return None
    delta = current.close - current.open
    upper = current.high - max(current.open, current.close)
    lower = min(current.open, current.close) - current.low
    if delta == 0 or upper == lower:
        return None
    previous_range = float(median(x.range_price for x in prior[-PREVIOUS_RANGES:]))
    if previous_range <= 0:
        return None
    return (int(delta > 0), int(current.range_price >= previous_range),
            int(upper > lower))


def online_posterior(
    key: tuple[int, int, int],
    matured: deque[tuple[datetime, tuple[int, int, int], int]],
) -> tuple[int, float, float] | None:
    n = sum(row[1] == key for row in matured)
    if n < MIN_STATE_EXAMPLES:
        return None
    state_up = sum(row[1] == key and row[2] == 1 for row in matured)
    global_up = sum(row[2] == 1 for row in matured)
    state_prob = (state_up + 1) / (n + 2)
    base_prob = (global_up + 1) / (len(matured) + 2)
    if state_prob >= MIN_POSTERIOR_UP and state_prob-base_prob >= MIN_BASE_EXCESS:
        return 1, state_prob, base_prob
    if state_prob <= MAX_POSTERIOR_UP and base_prob-state_prob >= MIN_BASE_EXCESS:
        return -1, state_prob, base_prob
    return None


def evaluate_day(
    symbol: str, day: date, today: dict[datetime, NativeM5],
    known: dict[datetime, Any],
    labeled: deque,
    last_state: tuple[datetime, tuple[int, int, int]] | None,
) -> tuple[list[dict], Counter[str], dict[datetime, Any], Any]:
    hours = complete_hours(today)
    reason: Counter[str] = Counter()
    plan = None
    for h, cur in sorted(hours.items()):
        old = [x for stamp,x in sorted(known.items())
               if h-WINDOW_HOURS <= stamp < h]
        key = classify_h1_state(cur, old)
        # Maturation at the moment current H1 closes: label of PREVIOUS H1
        # is only known if its immediate next H1 (current) exists and closes.
        if (last_state is not None and last_state[0] + H1 == h
                and cur.close != cur.open):
            labeled.append((h + H1, last_state[1], int(cur.close > cur.open)))
        while labeled and labeled[0][0] < h + H1 - WINDOW_LABEL_DAYS:
            labeled.popleft()
        if (day.weekday() <= 4 and 8 <= h.hour <= 15
                and day >= date(2016, 9, 17) and day < CUTOFF.date()
                and plan is None):
            if key is None:
                reason["INCOMPLETE_PAST20_OR_AMBIGUOUS_H1_GEOMETRY"] += 1
            else:
                posterior = online_posterior(key, labeled)
                if posterior is None:
                    reason["STATE_POSTERIOR_HAS_NO_EDGE_OR_POWER"] += 1
                elif h-H1 not in known or h-3*H1 not in known:
                    reason["PRE_EVENT_BASELINE_2H_UNAVAILABLE"] += 1
                else:
                    baseline_delta = known[h-H1].close - known[h-3*H1].close
                    if baseline_delta == 0:
                        reason["BASELINE_ZERO_DIRECTION"] += 1
                    else:
                        d = float(median(x.range_price for x in old[-PREVIOUS_RANGES:]))
                        if not math.isfinite(d) or d <= 0:
                            reason["INVALID_PREDECISION_STOP"] += 1
                        else:
                            direction, p_up, base = posterior
                            plan = {
                                "model": "CMTRL_FIXED_8STATE_BETA_CAUSAL_V01",
                                "state":list(key),
                                "direction":direction,
                                "control_direction":1 if baseline_delta > 0 else -1,
                                "posterior_up":p_up,
                                "unconditional_up":base,
                                "n_state":sum(a[1]==key for a in labeled),
                                "matured_transition_count":len(labeled),
                                "decision_utc":(h+H1).isoformat(),
                                "entry_utc":(h+H1+ENTRY_DELAY).isoformat(),
                                "exit_deadline_utc":(h+H1+ENTRY_DELAY+MAX_HOLD).isoformat(),
                                "stop_distance_price":d,
                            }
                            reason["EVENT"] += 1
        # Reveal this hour AFTER decision, never future hours to classifier.
        known[h] = cur
        last_state = (h, key) if key is not None else None
    events = []
    if plan is not None:
        t = datetime.fromisoformat(plan["entry_utc"])
        expiry = datetime.fromisoformat(plan["exit_deadline_utc"])
        if expiry > CUTOFF:
            strat = ctrl = {"status": "EMBARGO_CROSS_CENSORED"}
        elif t < DEVELOPMENT_END <= expiry:
            strat = ctrl = {"status": "ERA_BOUNDARY_CENSORED"}
        else:
            ref = {when: item.bar for when,item in today.items()}
            strat = arm(m5=ref, entry_at=t, expire_at=expiry,
                        distance=plan["stop_distance_price"],
                        direction=plan["direction"])
            ctrl = arm(m5=ref, entry_at=t, expire_at=expiry,
                       distance=plan["stop_distance_price"],
                       direction=plan["control_direction"])
        paired = strat["status"] == ctrl["status"] == "COMPLETE_GROSS_PROXY"
        decision = datetime.fromisoformat(plan["decision_utc"])
        iso = decision.isocalendar()
        events = [{
            "symbol":symbol, "utc_day":day.isoformat(),
            "era":"DEVELOPMENT" if decision < DEVELOPMENT_END else "DIAGNOSTIC",
            "iso_week":f"{iso.year}-W{iso.week:02d}",
            "plan":plan, "strategy":strat, "control":ctrl,
            "paired":paired,
            "delta_gross_bps":strat["gross_bps"]-ctrl["gross_bps"] if paired else None,
            "delta_gross_R":strat["gross_R"]-ctrl["gross_R"] if paired else None,
            "bidask_net_not_measured":True,
        }]
    return events, reason, known, last_state


def replay(symbol: str, native: Path, signed33: Path, aggregate12: Path | None) -> dict:
    if symbol not in MARKETS:
        raise ValueError("outside G0 33")
    frozen = source33_manifest(signed33)
    source_proof = verify_source(symbol, native, frozen, aggregate12)
    known: dict[datetime, Any] = {}
    labels: deque = deque(maxlen=LABELS_N)
    last_state = None
    today: dict[datetime, NativeM5] = {}
    previous_day: date | None = None
    events = []
    reasons: Counter[str] = Counter()
    days = 0

    def commit_day(day: date) -> None:
        nonlocal last_state, known, days
        fresh, counts, known, last_state = evaluate_day(
            symbol, day, today, known, labels, last_state
        )
        events.extend(fresh)
        reasons.update(counts)
        # Only retain H1 metadata <=72h prior. Never interpolate broker closures.
        cutoff = datetime(day.year, day.month, day.day, tzinfo=UTC) - WINDOW_HOURS
        known = {t: hour for t,hour in known.items() if t >= cutoff}
        days += 1

    for record in read_original_market_rows(symbol, native):
        now_day = record.bar.at.date()
        if previous_day is not None and previous_day != now_day:
            commit_day(previous_day)
            today = {}
        today[record.bar.at] = record
        previous_day = now_day
    if previous_day is not None:
        commit_day(previous_day)
    if len({x["utc_day"] for x in events}) != len(events):
        raise ValueError("CMTRL duplicate same-market UTC day")
    return {
        "identity": IDENTITY, "symbol":symbol,
        "source_33_manifest_sha256":SOURCE33_SHA,
        "source_proof":source_proof,
        "full_native_source_SHA_verified_before_OHLC":True,
        "days_with_any_source_rows":days,
        "original_signal_count":len(events),
        "paired_observed":sum(e["paired"] for e in events),
        "opportunities":events,
        "predeclared_rule_exclusion_counts":dict(sorted(reasons.items())),
        "comparison":"CMTRL_VS_PRE_EVENT_LAG_2H",
        "broker_volume_semantics":"IGNORED_BY_PRICE_GEOMETRY_MODEL",
        "broker_costs_verified":False,"news_known_asof_verified":False,
        "ohlc_broker_fill_executable":False,
        "UTC001_certified":False,"production_untouched":True,
        "after_2024_09_17_price_unread":True,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("symbol",choices=MARKETS)
    p.add_argument("native",type=Path)
    p.add_argument("signed33",type=Path)
    p.add_argument("output",type=Path)
    p.add_argument("--aggregate12",type=Path)
    args=p.parse_args()
    result=replay(args.symbol,args.native,args.signed33,args.aggregate12)
    args.output.mkdir(parents=True,exist_ok=True)
    target=args.output/f"alpha2-w3-cmtrl-gross-{args.symbol}.json"
    target.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    target.with_name(target.name+".sha256").write_text(
        sha256_file(target)+"  "+target.name+"\n",encoding="utf-8"
    )
    print(json.dumps({"symbol":args.symbol,"signals":result["original_signal_count"],
                      "paired":result["paired_observed"],"NET":"NOT_COMPUTED",
                      "third_final_research_hypothesis":True},sort_keys=True))


if __name__=="__main__":
    main()
