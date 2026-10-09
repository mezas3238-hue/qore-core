#!/usr/bin/env python3
"""Compare original 540 vs 246 PAPER opens on identical 3368 Trader fingerprints.

Research diagnostics, not an executable strategy. M5 price after an M1 decision
must NEVER be presented as a predecision price. No inferred M1 broker fills.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path

OPEN_STATES = frozenset(("PAPER_OPEN", "PAPER_OPEN_UNRESOLVED_NO_EXIT_PATH"))
SUPPORTED = frozenset(("R34_XAUUSD", "R38_EURUSD", "R38_GBPJPY",
                       "R42_AUDJPY", "R43_GBPUSD", "VT31_NAS100", "VT08_FOREX"))


def timestamp(raw):
    if not isinstance(raw, str):
        raise ValueError("timestamp must be ISO string")
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp must have timezone")
    return dt.astimezone(timezone.utc)


def indexed(rows, name, expected):
    if not isinstance(rows, list) or len(rows) != expected:
        raise ValueError(name + " count must be " + str(expected))
    results = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(name + ": rows must be objects")
        sid = row.get("signal_fingerprint")
        if not isinstance(sid, str) or not sid or sid in results:
            raise ValueError(name + ": missing or duplicate signal_fingerprint")
        results[sid] = row
    return results


def _summary(rows):
    wins = [D(r["net_usd"]) for r in rows if r["net_usd"] is not None and D(r["net_usd"]) > 0]
    losses = [-D(r["net_usd"]) for r in rows if r["net_usd"] is not None and D(r["net_usd"]) < 0]
    opened = [r for r in rows if r["opened"]]
    closed = [r for r in rows if r["net_usd"] is not None]
    gross_wins, gross_losses = sum(wins, D(0)), sum(losses, D(0))
    return {
        "signal_count": len(rows),
        "opened": len(opened),
        "settled": len(closed),
        "unresolved": len(opened) - len(closed),
        "net_pnl_usd": str(gross_wins - gross_losses),
        "win_rate_pct": str(D(len(wins)) * 100 / D(len(closed))) if closed else None,
        "profit_factor": str(gross_wins / gross_losses) if gross_losses else None,
        "rejected_by_status": dict(sorted(Counter(r["status"] for r in rows if not r["opened"]).items())),
        "rejected_by_binding": dict(sorted(Counter(
            b for r in rows if not r["opened"] for b in
            (r["binding_limits"] if r["binding_limits"] else ["NO_BINDING_RECEIPT"])
        ).items())),
    }


def _percentiles(values):
    if not values:
        return None
    a = sorted(D(str(v)) for v in values)
    def q(n):
        z = D(len(a) - 1) * D(n) / D(100)
        lo = int(z)
        w = z - D(lo)
        return str(a[lo]*(D(1)-w)+a[min(lo+1,len(a)-1)]*w)
    return {"n":len(a),"mean":str(sum(a,D(0))/D(len(a))),
            "min":str(a[0]),"median":q(50),"p90":q(90),"max":str(a[-1])}


def _next_calendar_m5(decided_at):
    """Pure calendar bound, NEVER claims market M5 bar/tick actually exists."""
    minute = (decided_at.minute // 5) * 5
    floor = decided_at.replace(minute=minute, second=0, microsecond=0)
    if floor == decided_at:
        return floor
    return floor + timedelta(minutes=5)


def _cohort(originals, decisions, closed, trader):
    out=[]
    for sid,src in originals.items():
        if src["trader_id"] != trader:
            continue
        decision=decisions[sid]
        was_open=decision.get("status") in OPEN_STATES
        if (not was_open and decision.get("paper_entry_at")):
            raise ValueError("entry timestamp on a no-fill decision")
        if was_open and not decision.get("paper_entry_at"):
            raise ValueError("PAPER_OPEN without physical modeled entry timestamp")
        if sid in closed and not was_open:
            raise ValueError("PAPER closed without opening")
        if decision.get("signal_at") and timestamp(decision["signal_at"])!=timestamp(src["market_decision_at"]):
            raise ValueError("signal timestamp differs from original Trader")
        if timestamp(decision["qdle_at"])!=timestamp(src["market_decision_at"]):
            raise ValueError("QDLE decision time differs from Trader predecision epoch")
        entry_delta = None
        if was_open:
            entry_delta = D(str((timestamp(decision["paper_entry_at"])-
                                 timestamp(src["market_decision_at"])).total_seconds()))
            if entry_delta<0 or entry_delta>300:
                raise ValueError("PAPER fill time is future-unknown or out of M5 tolerance")
            entry_dt=timestamp(decision["paper_entry_at"])
            if entry_dt.second or entry_dt.microsecond or entry_dt.minute%5:
                raise ValueError("PAPER fill not aligned to M5 bar opening")
        bindings=decision.get("qdle_binding_limits", [])
        if not isinstance(bindings,list):
            raise ValueError("QDLE binding limits must be a list")
        row={
            "signal_fingerprint":sid,
            "trader":trader,
            "symbol":src["qore_symbol"],
            "status":decision.get("status", "MISSING_STATUS"),
            "mode":decision.get("mode"),
            "opened":was_open,
            "closed":sid in closed,
            "binding_limits":bindings,
            "net_usd":closed[sid]["net_usd"] if sid in closed else None,
            "decision_at":timestamp(src["market_decision_at"]).isoformat(),
            "entry_at":decision.get("paper_entry_at"),
            "delay_seconds":str(entry_delta) if entry_delta is not None else None,
            "future_M5_entry_used_as_predecision_quote":bool(entry_delta and entry_delta>0),
            "calendar_bound_seconds":str(D(str((
                _next_calendar_m5(timestamp(src["market_decision_at"]))-
                timestamp(src["market_decision_at"])).total_seconds()))),
            "calendar_bound_is_not_broker_fill":True,
            "paper_entry_price":decision.get("paper_entry_price"),
        }
        if src["trader_id"]=="VT31_NAS100":
            frame=dict(src["trader_opportunity"]["decision_context"]).get("ctx_timeframe")
            if frame != "M1":
                raise ValueError("VT31 native source timeframe drift: expected M1")
            row["native_timeframe"]="M1"
        out.append(row)
    return out


def compare(manifest, replay540, replay246, *, expected_signals=3368,
            expected_old=540, expected_new=246, expected_vt31=484):
    if not isinstance(manifest,dict):
        raise ValueError("frozen Trader manifest required")
    sources=indexed(manifest.get("opportunities"),"original_manifest",expected_signals)
    ids=set(sources)
    traders={r["trader_id"] for r in sources.values()}
    if expected_signals==3368 and traders!=SUPPORTED:
        raise ValueError("frozen seven-Trader manifest changed")
    if sum(s["trader_id"]=="VT31_NAS100" for s in sources.values())!=expected_vt31:
        raise ValueError("VT31 frozen M1 population mismatch")
    for name,replay,expected_open in (
        ("540",replay540,expected_old),("246",replay246,expected_new)):
        if (replay.get("certified") is not False or replay.get("broker_fills")!=0
                or replay.get("signal_count")!=expected_signals
                or replay.get("counts",{}).get("paper_open")!=expected_open):
            raise ValueError(name+": replay authority/size drift or invalid broker claim")
        if replay.get("origin_manifest_sha256")!=replay540.get("origin_manifest_sha256"):
            raise ValueError(name+": different original manifest provenance")
        decis=indexed(replay.get("signal_decisions"),name+" decisions",expected_signals)
        if set(decis)!=ids:
            raise ValueError(name+": different Trader signal fingerprints")
        closed_rows=replay.get("closed_trades")
        if not isinstance(closed_rows,list):
            raise ValueError("missing PAPER settled receipts")
        closed=indexed(closed_rows,name+" closes",len(closed_rows))
        if not set(closed).issubset(ids):
            raise ValueError("settlement outside original population")
        if replay.get("counts",{}).get("settled")!=len(closed):
            raise ValueError("settled count mismatch")
        all_rows=[]
        for trader in sorted(traders):
            all_rows.extend(_cohort(sources,decis,closed,trader))
        if sum(x["opened"] for x in all_rows)!=expected_open:
            raise ValueError("PAPER openings not consistent with receipt statuses")
        if sum(x["closed"] for x in all_rows)!=len(closed):
            raise ValueError("PAPER closes not consistent with receipt statuses")
        if name=="540":
            old_rows=all_rows
        else:
            new_rows=all_rows
    old={r["signal_fingerprint"]:r for r in old_rows}
    new={r["signal_fingerprint"]:r for r in new_rows}
    cohort={}
    delay={}
    for trader in sorted(traders):
        matching=[(old[sid],new[sid]) for sid in sources
                  if sources[sid]["trader_id"]==trader]
        both=sum(a["opened"] and b["opened"] for a,b in matching)
        only_old=sum(a["opened"] and not b["opened"] for a,b in matching)
        only_new=sum(not a["opened"] and b["opened"] for a,b in matching)
        neither=sum(not a["opened"] and not b["opened"] for a,b in matching)
        cohort[trader]={
            "source_signals":len(matching),
            "opened_both":both,"opened_only_540":only_old,
            "opened_only_246":only_new,"opened_neither":neither,
            "original":_summary([p[0] for p in matching]),
            "revised":_summary([p[1] for p in matching]),
            "status_transition_counts":dict(sorted(Counter(
                p[0]["status"]+" => "+p[1]["status"] for p in matching
            ).items())),
        }
        if trader=="VT31_NAS100":
            for label,positions in (
                ("540",[p[0] for p in matching]),
                ("246",[p[1] for p in matching])):
                filled=[r for r in positions if r["opened"]]
                shift=[D(r["delay_seconds"]) for r in filled]
                delay[label]={
                    "native_source_signals":len(positions),
                    "paper_openings_with_observed_atlas_M5_time":len(filled),
                    "future_M5_open_quoted_at_earlier_decision_count":
                        sum(x>0 for x in shift),
                    "exact_M5_boundary_count":sum(x==0 for x in shift),
                    "measured_delay_seconds":_percentiles(shift),
                    "calendar_only_expected_delay_seconds":_percentiles(
                        D(r["calendar_bound_seconds"]) for r in positions),
                    "missing_M1_executable_price_count":len(positions),
                    "m1_broker_price_verified":False,
                }
    totals={k:sum(v[k] for v in cohort.values()) for k in (
        "source_signals","opened_both","opened_only_540",
        "opened_only_246","opened_neither")}
    if (totals["opened_both"]+totals["opened_only_540"]!=expected_old or
        totals["opened_both"]+totals["opened_only_246"]!=expected_new or
        totals["source_signals"]!=expected_signals):
        raise ValueError("two-cohort identity reconciliation failed")
    return {
        "schema":"qore.cibo.p0-vt31-m1-m5-selection-540-vs-246.v1",
        "classification":"RESEARCH_NOT_BROKER_CERTIFIED_NOT_OOS",
        "source_signal_count":expected_signals,
        "source_sha256":replay540["origin_manifest_sha256"],
        "comparison_not_same_policy_or_capital_path":True,
        "two_books_unified":False,
        "vt31_delays":delay,
        "opening_intersection":totals,
        "by_trader":cohort,
        "vt31_m1_native_source_count":expected_vt31,
        "no_live":True,
        "not_proven":[
            "historical M1 executable tick or spread",
            "that a timing change causes VT31 win-rate change",
            "that PAPER PF changes derive from signal quality alone",
            "same initial order fills, price and risk between studies",
            "single canonical #745/#746 PAPER reservation authority",
        ],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--replay-540",required=True,type=Path)
    p.add_argument("--replay-246",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    files=(args.manifest,args.replay_540,args.replay_246)
    content=[x.read_bytes() for x in files]
    payload=[json.loads(x) for x in content]
    result=compare(*payload)
    result["evidence_zip_internal_json_sha256"]={
        label:"sha256:"+sha256(data).hexdigest()
        for label,data in zip(("manifest","replay_540","replay_246"),content)
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("CIBO_P0_VT31_M1_M5_TIMING_AND_SELECTION",json.dumps({
        "opening_intersection":result["opening_intersection"],
        "vt31_openings_540":result["vt31_delays"]["540"]["paper_openings_with_observed_atlas_M5_time"],
        "vt31_openings_246":result["vt31_delays"]["246"]["paper_openings_with_observed_atlas_M5_time"],
        "vt31_future_M5_quoted_count_540":
            result["vt31_delays"]["540"]["future_M5_open_quoted_at_earlier_decision_count"],
        "vt31_future_M5_quoted_count_246":
            result["vt31_delays"]["246"]["future_M5_open_quoted_at_earlier_decision_count"],
    },sort_keys=True),flush=True)


if __name__=="__main__":
    main()
