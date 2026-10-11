"""DCVC Audit02 P0: diagnose 241-closed-native-M1 UNKNOWN windows only.

Forensic observations are as-of a frozen decision. No futures, outcomes or
selection-policy imports. Classifications of feed gaps are descriptive, not
claims that an exchange/provider definitely closed at a particular time.
"""
from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEFAULT_LOOKBACK,
    DEV_WINDOW_END,
    DEV_WINDOW_START,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_ab_experiment_v1 import (
    read_jsonl,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_causal_features_v1 import (
    DCVCPredecision,
)

IDENTITY = "QORE_SCALPER_DCVC_AUDIT02_UNKNOWN_241_BAR_FORENSICS_V1"
WINDOW=241
MINUTE=timedelta(minutes=1)


def availability_diagnostic(
    item: DCVCPredecision,
    bars: tuple[CapitalizerM1Bar, ...],
    clocks: tuple[datetime, ...],
) -> dict[str, Any]:
    """Never look at any bar whose close is later than this decision."""
    instant=datetime.fromisoformat(item.decision_at)
    position=bisect.bisect_right(clocks,instant)
    if position==0 or clocks[position-1]!=instant:
        raise ValueError("native last closed bar missing at frozen decision")
    history=bars[max(0,position-WINDOW):position]
    if history[-1].symbol!=item.symbol:
        raise ValueError("native symbol does not match original source")
    if history[-1].closed_at.isoformat()!=item.native_last_m1_closed_at:
        raise ValueError("native availability differs from frozen predecision")
    pairs=tuple(zip(history,history[1:]))
    gaps=tuple(
        (a,b) for a,b in pairs
        if b.opened_at!=a.closed_at or b.closed_at-a.closed_at!=MINUTE
    )
    consecutive=1
    for a,b in reversed(pairs):
        if b.opened_at!=a.closed_at or b.closed_at-a.closed_at!=MINUTE:
            break
        consecutive+=1
    observed_regime=item.regime
    if len(history)<WINDOW:
        cause="HISTORY_START_UNDER_241_CLOSES"
    elif gaps:
        largest=max(gaps,key=lambda pair: pair[1].opened_at-pair[0].closed_at)
        d=largest[1].opened_at-largest[0].closed_at
        if d>=timedelta(hours=48):
            cause="MULTIDAY_MARKET_CLOSURE_OR_FEED_GAP"
        elif d>=timedelta(hours=1):
            cause="SESSION_OR_OVERNIGHT_BREAK_OR_FEED_GAP"
        else:
            cause="SHORT_NATIVE_M1_FEED_GAP"
    else:
        prices=[x.close for x in history]
        changes=[prices[i+1]-prices[i] for i in range(240)]
        if all(x==0 for x in changes):
            cause="FLAT_LAST_240_NATIVE_RETURNS"
        elif all(x==0 for x in changes[-30:]):
            cause="FLAT_LAST_30_NATIVE_RETURNS"
        else:
            cause="VALID_FULL_WINDOW"
    if (cause=="VALID_FULL_WINDOW")!=(observed_regime!="UNKNOWN"):
        raise ValueError("reason for UNKNOWN conflicts with immutable v0.1 regime")
    last_gap=gaps[-1] if gaps else None
    return {
        "source_opportunity_id":item.source_opportunity_id,
        "symbol":item.symbol,
        "session":item.session,
        "operating_date":item.operating_date,
        "decision_at":item.decision_at,
        "regime":observed_regime,
        "diagnosis":cause,
        "native_history_bars_in_window":len(history),
        "native_last_contiguous_bars":consecutive,
        "native_window_gap_count":len(gaps),
        "nearest_native_gap_previous_close":(
            last_gap[0].closed_at.isoformat() if last_gap else None
        ),
        "nearest_native_gap_next_open":(
            last_gap[1].opened_at.isoformat() if last_gap else None
        ),
        "nearest_native_gap_minutes":(
            str((last_gap[1].opened_at-last_gap[0].closed_at).total_seconds()/60)
            if last_gap else None
        ),
        "native_candles_after_decision_used":0,
        "broker_open_hours_verified":False,
        "provider_gap_vs_calendar_cause_proven":False,
        "feature_v01_unchanged":True,
    }


def market(root:Path,native_root:Path,output:Path)->dict[str,Any]:
    paths=tuple(root.rglob("dcvc-predecision.jsonl"))
    if len(paths)!=1:
        raise ValueError("requires one frozen predecision ledger per symbol")
    features=tuple(DCVCPredecision(**row) for row in read_jsonl(paths[0]))
    if not features:
        raise ValueError("empty frozen source ledger")
    symbol=features[0].symbol
    if any(f.symbol!=symbol for f in features):
        raise ValueError("mixed symbol predecision")
    bars=tuple(
        bar for bar in iter_cibo_m1(native_root)
        if DEV_WINDOW_START-DEFAULT_LOOKBACK<=bar.opened_at<DEV_WINDOW_END
    )
    if not bars or any(b.symbol!=symbol for b in bars):
        raise ValueError("native M1 symbol missing/mixed")
    clocks=tuple(bar.closed_at for bar in bars)
    if any(clocks[i]>=clocks[i+1] for i in range(len(clocks)-1)):
        raise ValueError("out-of-order native bar")
    rows=tuple(availability_diagnostic(x,bars,clocks) for x in features)
    if len({row["source_opportunity_id"] for row in rows})!=len(rows):
        raise ValueError("duplicate original source id")
    stats=Counter(row["diagnosis"] for row in rows)
    report={
        "identity":IDENTITY,"symbol":symbol,"sources":len(rows),
        "unknown":sum(row["regime"]=="UNKNOWN" for row in rows),
        "reasons":dict(sorted(stats.items())),
        "future_candles_used":0,"v01_modified":False,
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"dcvc-audit02-unknown-native-reasons.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in rows),
        encoding="utf-8",
    )
    (output/"dcvc-audit02-market.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",
    )
    return report


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("frozen_market",type=Path)
    p.add_argument("native",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    print(json.dumps(market(args.frozen_market,args.native,args.output),sort_keys=True))


if __name__=="__main__":
    main()
