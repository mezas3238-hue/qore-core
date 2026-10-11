"""Issue #770: no-authority symmetric-barrier research, frozen V49 source.

Preserves original V49 2876 IDs and selected A MAX3; STOP_FIRST, no trailing.
Pure no-time-stop censored on feed end or any unobserved contiguous M1 gap.
Session-capped exits on original _session_bars and observes source M1 OHLC.
Opposite-direction same-time placebo is NOT an independent random time entry.
"""
from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    V49TradeDirection,
    materialize_trade_intent,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _replay_one,
    _session_bars,
)

IDENTITY="QORE_SCALPER_ISSUE770_1TO1_CAUSAL_ENTRY_SHADOW_RESEARCH_V1"
RESOLVED=frozenset(("STOP","TARGET","SESSION_EXIT"))
CENSORED=frozenset((
    "RIGHT_CENSORED_PRICE_GAP",
    "RIGHT_CENSORED_END_OF_FEED",
    "GAP_CENSORED_SESSION",
))


def rows(path:Path)->tuple[dict[str,Any],...]:
    return tuple(
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def match_key(source:V49Opportunity)->tuple[str,str,str]:
    return (source.m1_trigger_confirmed_at,
            source.m1_trigger_family,source.h1_state_basis)


def economic_key(trade:V49EconomicTrade)->tuple[str,str,str]:
    return trade.entry_at,trade.trigger_family,trade.h1_state_basis


def barrier_prices(
    entry:Decimal,stop:Decimal,direction:str,
)->tuple[Decimal,Decimal]:
    if entry==stop:
        raise ValueError("zero risk is not 1-to-1")
    risk=abs(entry-stop)
    if direction=="LONG":
        if stop>=entry:
            raise ValueError("invalid long protected swing")
        return stop,entry+risk
    if direction=="SHORT":
        if stop<=entry:
            raise ValueError("invalid short protected swing")
        return stop,entry-risk
    raise ValueError("invalid source direction")


def scan(
    *,
    bars:tuple[CapitalizerM1Bar,...],
    entry_at:datetime,
    entry:Decimal,
    stop:Decimal,
    direction:str,
    capped:bool,
)->dict[str,Any]:
    """Only post-confirmation candles; no unobserved interval may win/lose."""
    _stop,target=barrier_prices(entry,stop,direction)
    if not bars or bars[0].opened_at!=entry_at:
        raise ValueError("no exact first native M1 opening after decision close")
    previous_close=entry_at
    held=0
    last=entry
    seen_close=entry_at
    for bar in bars:
        if bar.opened_at!=previous_close:
            return {
                "status":"GAP_CENSORED_SESSION" if capped
                else "RIGHT_CENSORED_PRICE_GAP",
                "exit_at":None,"last_observed_at":seen_close.isoformat(),
                "last_observed_price":str(last),"R":None,
                "m1_bars_held":held,"both_touched":False,
                "target_first_sensitivity_R":None,
                "gap_next_observed_at":bar.opened_at.isoformat(),
            }
        held+=1
        previous_close=bar.closed_at
        seen_close=bar.closed_at
        last=bar.close
        stop_hit=bar.low<=stop if direction=="LONG" else bar.high>=stop
        target_hit=bar.high>=target if direction=="LONG" else bar.low<=target
        if stop_hit or target_hit:
            both=stop_hit and target_hit
            return {
                "status":"STOP" if stop_hit else "TARGET",
                "exit_at":bar.closed_at.isoformat(),
                "last_observed_at":bar.closed_at.isoformat(),
                "last_observed_price":str(last),
                "R":"-1" if stop_hit else "1",
                "m1_bars_held":held,"both_touched":both,
                "target_first_sensitivity_R":"1" if both else
                ("-1" if stop_hit else "1"),
                "gap_next_observed_at":None,
            }
    if capped:
        risk=abs(entry-stop)
        pnl=(last-entry if direction=="LONG" else entry-last)/risk
        return {
            "status":"SESSION_EXIT","exit_at":seen_close.isoformat(),
            "last_observed_at":seen_close.isoformat(),
            "last_observed_price":str(last),"R":str(pnl),
            "m1_bars_held":held,"both_touched":False,
            "target_first_sensitivity_R":str(pnl),
            "gap_next_observed_at":None,
        }
    return {
        "status":"RIGHT_CENSORED_END_OF_FEED",
        "exit_at":None,"last_observed_at":seen_close.isoformat(),
        "last_observed_price":str(last),"R":None,
        "m1_bars_held":held,"both_touched":False,
        "target_first_sensitivity_R":None,
        "gap_next_observed_at":None,
    }


def market(frozen:Path,native_root:Path,output:Path)->dict[str,Any]:
    opportunity_paths=tuple(
        frozen.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl")
    )
    economic_paths=tuple(
        frozen.rglob("capitalizer-*-v49-development-economics-trades.jsonl")
    )
    if len(opportunity_paths)!=1 or len(economic_paths)!=1:
        raise ValueError("frozen V49 native market sources/economics missing")
    source=tuple(V49Opportunity(**x) for x in rows(opportunity_paths[0]))
    economics=tuple(V49EconomicTrade(**x) for x in rows(economic_paths[0]))
    if not source or len(source)!=len(economics):
        raise ValueError("frozen source economics not one-to-one")
    symbol=source[0].symbol
    if any(x.symbol!=symbol for x in source) or any(x.symbol!=symbol for x in economics):
        raise ValueError("mixed source symbols")
    by_key={economic_key(x):x for x in economics}
    if len(by_key)!=len(economics):
        raise ValueError("duplicate original V49 economic matching key")
    native=tuple(x for x in iter_cibo_m1(native_root)
                 if x.opened_at>=DEV_WINDOW_START)
    if not native or any(x.symbol!=symbol for x in native):
        raise ValueError("native provider M1 missing or mixed")
    # Source baseline was restricted through DEV_WINDOW_END, unlike pure
    # forward resolution for cases with a post-development native M1 tail.
    old_bars=tuple(x for x in native if x.opened_at<DEV_WINDOW_END)
    opened_old=tuple(x.opened_at for x in old_bars)
    opened_full=tuple(x.opened_at for x in native)
    if any(opened_full[i]>=opened_full[i+1] for i in range(len(native)-1)):
        raise ValueError("native provider open clocks not strictly increasing")
    details:list[dict[str,Any]]=[]
    seen:set[str]=set()
    stats:Counter[str]=Counter()
    for opportunity in source:
        sid=source_id(opportunity)
        if sid in seen:
            raise ValueError("duplicate frozen V49 source ID")
        seen.add(sid)
        original=by_key.get(match_key(opportunity))
        if original is None:
            raise ValueError("frozen source trade missing")
        intent=materialize_trade_intent(opportunity)
        original_bars=_session_bars(old_bars,opened_old,intent=intent)
        reproducer=_replay_one(original_bars,intent)
        if reproducer!=original:
            raise ValueError(f"original V49 settlement changed for {sid}")
        idx=bisect.bisect_left(opened_full,intent.entry_at)
        if idx>=len(native) or native[idx].opened_at!=intent.entry_at:
            raise ValueError("provider native postconfirmation first M1 absent")
        if idx==0 or native[idx-1].closed_at!=intent.entry_at:
            raise ValueError("entry candle closed at unverified timestamp")
        if native[idx-1].close!=intent.entry_price:
            raise ValueError("frozen entry not identical to real native M1 close")
        stop,target=barrier_prices(
            intent.entry_price,intent.stop_price,intent.direction.value
        )
        pure=scan(
            bars=native[idx:],entry_at=intent.entry_at,entry=intent.entry_price,
            stop=stop,direction=intent.direction.value,capped=False,
        )
        capped=scan(
            bars=original_bars,entry_at=intent.entry_at,entry=intent.entry_price,
            stop=stop,direction=intent.direction.value,capped=True,
        )
        inverse_direction=(
            V49TradeDirection.SHORT.value if intent.direction==V49TradeDirection.LONG
            else V49TradeDirection.LONG.value
        )
        # A direction-flip uses exactly the same two 1R price barriers
        # exchanged as stop/target, and a symmetric stop distance.
        opposite_stop=target
        inverse_pure=scan(
            bars=native[idx:],entry_at=intent.entry_at,entry=intent.entry_price,
            stop=opposite_stop,direction=inverse_direction,capped=False,
        )
        inverse_capped=scan(
            bars=original_bars,entry_at=intent.entry_at,entry=intent.entry_price,
            stop=opposite_stop,direction=inverse_direction,capped=True,
        )
        stats[original.exit_reason]+=1
        details.append({
            "source_opportunity_id":sid,"symbol":symbol,
            "session":opportunity.session,
            "operating_date":opportunity.operating_date,
            "direction":intent.direction.value,
            "entry_at":intent.entry_at.isoformat(),
            "entry_price":str(intent.entry_price),
            "stop_m15_price":str(stop),
            "original_h1_target_price":str(intent.target_price),
            "symmetric_target_price":str(target),
            "one_risk_absolute":str(abs(intent.entry_price-stop)),
            "original_v49":asdict(original),
            "pure_1to1":pure,"session_capped_1to1":capped,
            "reverse_direction_same_time_pure":inverse_pure,
            "reverse_direction_same_time_session_capped":inverse_capped,
            "provider_native_m1_feed_end":native[-1].closed_at.isoformat(),
            "original_v49_reconstructed_unchanged":True,
            "h1_m15_swing_original_source_attested_not_author_certified":True,
            "broker_bid_ask_and_slippage_available":False,
            "live_authority":False,
        })
    if len(details)!=len(source):
        raise ValueError("market source count changed")
    output.mkdir(parents=True,exist_ok=True)
    (output/"scalper-issue770-all-original-ids-two-scenarios.jsonl").write_text(
        "".join(json.dumps(row,sort_keys=True)+"\n" for row in details),
        encoding="utf-8",
    )
    report={
        "identity":IDENTITY,"symbol":symbol,
        "source_ids":len(details),"source_replayed_original_exact":len(details),
        "V49_original_exit_reasons_all_pre_max3":dict(sorted(stats.items())),
        "native_M1_bars_since_development":len(native),
        "native_m1_last_close":native[-1].closed_at.isoformat(),
        "non_trade_broker_execution":True,
        "source_parent_H1_M15_not_regenerated":True,
        "certified":False,
    }
    (output/"scalper-issue770-market.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",
    )
    return report


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("frozen",type=Path)
    parser.add_argument("native",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    print(json.dumps(market(args.frozen,args.native,args.output),sort_keys=True))


if __name__=="__main__":
    main()
