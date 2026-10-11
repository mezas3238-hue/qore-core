"""Audit14: research-only fully settled *source-anchored* causal-first replay.

Replays all 2876 frozen V49 opportunities on the same provider M1; compares
first M1 discovery against V49 under original M15 protected swing, *as-of*
V49 H1 objective selection, STOP-FIRST, session exit and portfolio MAX3.

IMPORTANT: original V49 H1/M15 parent opportunity universe is held fixed.
This does NOT regenerate every alternative H1/M15 setup in chronological
streaming, nor have synchronized physical BID/ASK/commissions. Consequently
metrics are GROSS-R sensitivity, not a certified physical/live replay.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    _aggregate,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
    _untouched_h1_target_fast,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    materialize_trade_intent,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
    _portfolio_select,
    _replay_one,
    _session_bars,
)

IDENTITY="QORE_SCALPER_A2_FOURTEENTH_SOURCE_ANCHORED_FIRST_ONLINE_GROSS_REPLAY_V1"


def aware(raw: str) -> datetime:
    value=datetime.fromisoformat(raw)
    if value.utcoffset() is None:
        raise ValueError("all source timestamps must be aware")
    return value


def replay_market(
    original:Path, online_root:Path,native_root:Path,
) -> tuple[dict[str,Any],tuple[dict[str,Any],...],tuple[V49EconomicTrade,...]]:
    paths=sorted(original.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    economics=sorted(original.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    online_paths=sorted(online_root.rglob("scalper-thirteenth-stream-ids.jsonl"))
    if len(paths)!=1 or len(economics)!=1 or len(online_paths)!=1:
        raise ValueError("require one frozen V49 source/economic + first online ledger")
    sources=tuple(V49Opportunity(**x) for x in _jsonl(paths[0]))
    baselines=tuple(V49EconomicTrade(**x) for x in _jsonl(economics[0]))
    online=tuple(_jsonl(online_paths[0]))
    if not sources or len(sources)!=len(baselines) or len(online)!=len(sources):
        raise ValueError("original source/economic and online populations unequal")
    symbol=sources[0].symbol
    if any(s.symbol!=symbol for s in sources):
        raise ValueError("mixed frozen source symbols")
    # Source economic ledger identity resolved by original time + route/basis.
    baseline_by_key={
        (x.entry_at,x.trigger_family,x.h1_state_basis):x for x in baselines
    }
    if len(baseline_by_key)!=len(baselines):
        raise ValueError("duplicate baseline economic key")
    online_by_id={x["source_opportunity_id"]:x for x in online}
    if len(online_by_id)!=len(online):
        raise ValueError("duplicate online source identity")
    m1=tuple(
        x for x in iter_cibo_m1(native_root)
        if DEV_WINDOW_START-timedelta(days=15)<=x.opened_at<DEV_WINDOW_END
    )
    if not m1 or any(x.symbol!=symbol for x in m1):
        raise ValueError("independent native M1 missing/mixed")
    if any(m1[i].opened_at>=m1[i+1].opened_at for i in range(len(m1)-1)):
        raise ValueError("provider M1 chronology is not sorted/unique")
    economic_bars=tuple(x for x in m1 if x.opened_at>=DEV_WINDOW_START)
    opened=tuple(x.opened_at for x in economic_bars)
    all_opened=tuple(x.opened_at for x in m1)
    h1=_aggregate(m1,minutes=60)
    rows:list[dict[str,Any]]=[]
    candidate_trades:list[V49EconomicTrade]=[]
    seen:set[str]=set()
    counts:Counter[str]=Counter()
    for s in sources:
        sid=source_id(s)
        if sid in seen or sid not in online_by_id:
            raise ValueError("source ID duplicate/unmatched")
        seen.add(sid)
        observation=online_by_id[sid]
        if (observation["symbol"]!=symbol
                or observation["v49_entry_at"]!=s.m1_trigger_confirmed_at
                or observation["v49_family"]!=s.m1_trigger_family):
            raise ValueError("online ledger not reconciled to frozen original")
        orig_intent=materialize_trade_intent(s)
        orig_base=baseline_by_key.get((
            s.m1_trigger_confirmed_at,s.m1_trigger_family,s.h1_state_basis
        ))
        if orig_base is None:
            raise ValueError("frozen economic source key missing")
        orig_bars=_session_bars(economic_bars,opened,intent=orig_intent)
        original_fill=_replay_one(orig_bars,orig_intent)
        if original_fill!=orig_base:
            raise ValueError("V49 native M1 gross economic source not reproduced")
        new_fill:V49EconomicTrade|None=None
        target:Decimal|None=None
        decision=aware(observation["online_discovered_at"])
        orig_at=aware(s.m1_trigger_confirmed_at)
        if decision>orig_at or decision<=aware(s.m15_setup_confirmed_at):
            raise ValueError("online event outside source-anchored M15 causal interval")
        if decision<aware(s.h1_state_from):
            raise ValueError("online event precedes established H1 state")
        if decision<aware(observation["online_witness_confirmed_at"]):
            raise ValueError("online witness confirmed in unseen future")
        if observation["online_witness_backdated"]:
            raise ValueError("this paired source book declares no late discovery")
        ix=bisect.bisect_left(all_opened,decision)
        if ix==0 or ix>=len(m1) or m1[ix-1].closed_at!=decision:
            raise ValueError("first-online discovery close absent from provider M1")
        price=m1[ix-1].close
        status="ELIGIBLE"
        if capitalizer_session_at(decision) is not CapitalizerSession(s.session):
            status="OUTSIDE_SOURCE_SESSION"
        elif decision<DEV_WINDOW_START:
            status="OUTSIDE_DEVELOPMENT_WINDOW"
        else:
            stop=Decimal(s.m15_protected_swing_price)
            direction=CapitalizerSourceDirection(s.h1_state_direction)
            valid_stop=(
                stop<price if direction is CapitalizerSourceDirection.BULLISH
                else price<stop
            )
            if not valid_stop:
                status="INVALID_M15_STOP_AT_ONLINE_CLOSE"
            else:
                target=_untouched_h1_target_fast(
                    h1,m1,all_opened,
                    decision_at=decision,decision_price=price,direction=direction,
                )
                if target is None:
                    status="NO_UNTOUCHED_H1_OBJECTIVE_AT_ONLINE_CLOSE"
                else:
                    # V49 target search policy is unchanged, only as-of timestamp.
                    # Do not use frozen original target, which may not be available.
                    alternative=replace(
                        orig_intent,entry_at=decision,entry_price=price,
                        target_price=target,
                        trigger_family=observation["online_family"],
                    )
                    new_bars=_session_bars(economic_bars,opened,intent=alternative)
                    if not new_bars or new_bars[0].opened_at!=decision:
                        status="NO_SESSION_M1_AFTER_ONLINE_ENTRY"
                    else:
                        new_fill=_replay_one(new_bars,alternative)
                        if new_fill is None:
                            status="ECONOMIC_REPLAY_UNAVAILABLE"
                        else:
                            candidate_trades.append(new_fill)
        counts[status]+=1
        rows.append({
            "source_opportunity_id":sid,"symbol":symbol,"session":s.session,
            "operating_date":s.operating_date,
            "v49_entry_at":s.m1_trigger_confirmed_at,
            "online_entry_at":observation["online_discovered_at"],
            "online_family":observation["online_family"],
            "source_family":s.m1_trigger_family,
            "frozen_381":observation["frozen_full_prefix_disagreement"],
            "first_online_differs":observation["close_changed"] or
                observation["family_changed"],
            "status":status,
            "rejection_is_diagnostic_not_a_hard_veto":status!="ELIGIBLE",
            "original_gross_r":original_fill.realized_gross_r,
            "candidate_gross_r":new_fill.realized_gross_r
                if status=="ELIGIBLE" and new_fill is not None else None,
            "candidate_entry_price":str(price),
            "candidate_stop_price":s.m15_protected_swing_price,
            "candidate_target_price":str(target)
                if status=="ELIGIBLE" and target is not None else None,
            "candidate_exit_reason":new_fill.exit_reason
                if status=="ELIGIBLE" and new_fill is not None else None,
            "session_at_online":capitalizer_session_at(decision).value
                if capitalizer_session_at(decision) else None,
            "source_anchored_H1_M15_not_regenerated":True,
            "source_author_POI_not_independently_certified":True,
            "physical_bid_ask_available":False,
        })
        # Sentinel to prevent stale alternative-fill leakage across IDs.
        if status=="ELIGIBLE":
            counts["CANDIDATE_LIFECYCLE_REPLAYED"]+=1
    if len(seen)!=len(sources):
        raise ValueError("source ledger conservation failed")
    if counts["CANDIDATE_LIFECYCLE_REPLAYED"]!=len(candidate_trades):
        raise ValueError("candidate trade count accounting diverged")
    return ({
        "identity":IDENTITY,"symbol":symbol,"sources":len(sources),
        "original_economics_reconciled":len(sources),
        "source_first_online_differs":sum(x["first_online_differs"] for x in rows),
        "frozen_381":sum(x["frozen_381"] for x in rows),
        "candidate_eligibility_status":dict(sorted(counts.items())),
        "candidate_gross_fills":len(candidate_trades),
        "physical_bid_ask_available":False,"real_broker_costs_applied":False,
        "full_source_generated_streaming":False,"new_trade_authority":False,
        "certification":"BLOCKED_PHYSICAL_PRICING_AND_SOURCE_AUTHENTICITY",
    },tuple(rows),tuple(candidate_trades))


def aggregate(root:Path)->dict[str,Any]:
    files=sorted(root.rglob("scalper-audit14-market.json"))
    summaries=[json.loads(f.read_text(encoding="utf-8")) for f in files]
    if len(summaries)!=9 or len({x["symbol"] for x in summaries})!=9:
        raise ValueError("nine market economic books required")
    rows=[x for f in sorted(root.rglob("scalper-audit14-ids.jsonl"))
          for x in _jsonl(f)]
    if len(rows)!=2876 or len({x["source_opportunity_id"] for x in rows})!=2876:
        raise ValueError("original 2876 source IDs missing or duplicated")
    trade_rows=[V49EconomicTrade(**x)
                for f in sorted(root.rglob("scalper-audit14-candidates.jsonl"))
                for x in _jsonl(f)]
    original_trade_files=sorted(
        root.rglob("capitalizer-*-v49-development-economics-trades.jsonl")
    )
    original_trades=tuple(V49EconomicTrade(**x)
                          for f in original_trade_files for x in _jsonl(f))
    if len(original_trades)!=2876:
        raise ValueError("baseline 2876 economic trades missing")
    baseline=tuple(t for _,t in _portfolio_select(original_trades))
    if len(baseline)!=2020:
        raise ValueError("frozen portfolio MAX3 cannot change")
    gross_orig=_metrics(baseline)
    if (gross_orig.wins!=1167 or
            abs(Decimal(gross_orig.total_r)-Decimal("-233.2693270763665099166092077"))>Decimal("1e-15")):
        raise ValueError("baseline gross outcomes changed")
    alternative=tuple(t for _,t in _portfolio_select(tuple(trade_rows)))
    if not alternative:
        raise ValueError("causal-first anchored portfolio has no eligible fills")
    candidate_metrics=_metrics(alternative)
    source_ids_original={
        (t.symbol,t.session,t.operating_date,t.entry_at,t.trigger_family)
        for t in baseline
    }
    by_status=Counter(x["status"] for x in rows)
    return {
        "identity":IDENTITY,"markets":9,"sources":2876,
        "frozen_381":sum(x["frozen_381"] for x in rows),
        "online_different":sum(x["first_online_differs"] for x in rows),
        "statuses":dict(sorted(by_status.items())),
        "baseline_v49_max3":len(baseline),
        "candidate_anchored_max3":len(alternative),
        "candidate_eligible_pre_max3":len(trade_rows),
        "v49_baseline_gross_metrics":asdict(gross_orig),
        "causal_first_anchored_gross_metrics":asdict(candidate_metrics),
        "net_R_difference_anchored_minus_original":str(
            Decimal(candidate_metrics.total_r)-Decimal(gross_orig.total_r)
        ),
        "baseline_trade_keys":len(source_ids_original),
        "costs_bid_ask_present":False,
        "spread_sensitivity_calibrated_to_broker":False,
        "complete_stream_generated_all_H1_M15_opportunities":False,
        "trader_certifiable":False,
    }


def main()->None:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    m=sub.add_parser("market")
    m.add_argument("original",type=Path)
    m.add_argument("online",type=Path)
    m.add_argument("native",type=Path)
    m.add_argument("output",type=Path)
    a=sub.add_parser("matrix")
    a.add_argument("inputs",type=Path)
    a.add_argument("output",type=Path)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    if args.mode=="market":
        rep,ids,trades=replay_market(args.original,args.online,args.native)
        (args.output/"scalper-audit14-market.json").write_text(
            json.dumps(rep,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        with (args.output/"scalper-audit14-ids.jsonl").open(
            "w",encoding="utf-8"
        ) as out:
            for row in ids:
                out.write(json.dumps(row,sort_keys=True)+"\n")
        with (args.output/"scalper-audit14-candidates.jsonl").open(
            "w",encoding="utf-8"
        ) as out:
            for row in trades:
                out.write(json.dumps(asdict(row),sort_keys=True)+"\n")
    else:
        rep=aggregate(args.inputs)
        (args.output/"scalper-audit14-nine-market.json").write_text(
            json.dumps(rep,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
    print(json.dumps(rep,sort_keys=True))


if __name__=="__main__":
    main()
