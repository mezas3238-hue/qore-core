"""A2 audit 13: original V49 versus *detected-online* first M1 CISD.

An event with confirmed_at earlier than the bar where it first becomes
discoverable is NEVER backdated. Paired future labels are strictly forensic.
No candidate, portfolio admission, stop/target, or live execution is changed.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
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
from qore.infrastructure.trader_lab.capitalizer_scalper_a2_cisd_prefix_causality_v1 import (
    observe_route_pair,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)

IDENTITY = "QORE_SCALPER_A2_THIRTEENTH_CISD_STREAM_PAIRED_DIAGNOSTIC_V1"
HORIZONS = (15, 30, 60)


def dt(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError("timezone-aware source time required")
    return result


def stream_first(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    thesis_at: datetime,
    direction: CapitalizerSourceDirection,
) -> dict[str, str] | None:
    """Emit first route witness at first *discovery* close, never time-travel."""

    for i, bar in enumerate(bars):
        if bar.closed_at <= thesis_at:
            raise ValueError("online bars must close after M15 thesis")
        receipt = observe_route_pair(
            bars[:i+1], thesis_at=thesis_at,
            deadline_at=bar.closed_at, direction=direction,
        )
        if receipt.first_at is None or receipt.first_family is None:
            continue
        confirmed = dt(receipt.first_at)
        if confirmed > bar.closed_at:
            raise ValueError("observer confirmed in unseen future")
        return {
            "detected_at": bar.closed_at.isoformat(),
            "witness_confirmed_at": receipt.first_at,
            "family": receipt.first_family,
            "late_witness_discovery": str(confirmed < bar.closed_at).lower(),
        }
    return None


def post_entry_labels(
    bars: tuple[CapitalizerM1Bar, ...],
    closed: tuple[datetime, ...],
    *,
    at: datetime,
    direction: str,
    original_risk_price: Decimal,
    minutes: int,
) -> dict[str, Any]:
    """Observed closed-M1 future path, NEVER a trade or intrabar fill."""

    zero = bisect.bisect_left(closed, at)
    end = bisect.bisect_left(closed, at + timedelta(minutes=minutes))
    if (
        zero == len(bars) or end == len(bars)
        or bars[zero].closed_at != at
        or bars[end].closed_at != at + timedelta(minutes=minutes)
        or end - zero != minutes
    ):
        return {"covered": False}
    segment = bars[zero+1:end+1]
    if len(segment) != minutes or any(
        b.closed_at != at + timedelta(minutes=i+1)
        for i, b in enumerate(segment)
    ):
        return {"covered": False}
    price = bars[zero].close
    end_close = bars[end].close
    side = Decimal(1) if direction == "BULLISH" else Decimal(-1)
    if direction not in ("BULLISH", "BEARISH") or original_risk_price <= 0:
        raise ValueError("unusable side or original frozen risk reference")
    signed_r = (end_close-price)*side/original_risk_price
    mfe = max(
        Decimal(0), *((
            (b.high-price) if side == 1 else (price-b.low)
        ) / original_risk_price for b in segment)
    )
    mae = max(
        Decimal(0), *((
            (price-b.low) if side == 1 else (b.high-price)
        ) / original_risk_price for b in segment)
    )
    return {
        "covered": True, "signed_close_r": str(signed_r),
        "positive": signed_r > 0,
        "mfe_observed_r": str(mfe), "mae_observed_r": str(mae),
        "risk_reference_is_original_v49_not_new_trade": True,
        "whole_m1_high_low_intrabar_order_unknown": True,
    }


def market(
    original_root: Path,
    native_root: Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    files = sorted(original_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    if len(files) != 1:
        raise ValueError("require one immutable source opportunity book")
    sources = tuple(V49Opportunity(**x) for x in _jsonl(files[0]))
    if not sources:
        raise ValueError("no source opportunity")
    symbol = sources[0].symbol
    if any(s.symbol != symbol for s in sources):
        raise ValueError("mixed source symbols")
    native = tuple(
        b for b in iter_cibo_m1(native_root)
        if DEV_WINDOW_START - timedelta(days=15) <= b.opened_at < DEV_WINDOW_END
    )
    if not native or any(b.symbol != symbol for b in native):
        raise ValueError("provider M1 missing/mismatched")
    if any(native[i].opened_at >= native[i+1].opened_at
           for i in range(len(native)-1)):
        raise ValueError("unsorted native chronology")
    opened = tuple(b.opened_at for b in native)
    closed = tuple(b.closed_at for b in native)
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    for s in sources:
        sid = source_id(s)
        if sid in ids:
            raise ValueError("duplicate source ID")
        ids.add(sid)
        thesis = dt(s.m15_setup_confirmed_at)
        at = dt(s.m1_trigger_confirmed_at)
        if not thesis < at:
            raise ValueError("source entry does not follow thesis")
        left = bisect.bisect_left(opened, thesis)
        right = bisect.bisect_left(opened, at)
        prefix = native[left:right]
        if not prefix or prefix[-1].closed_at != at:
            raise ValueError("native M1 source entry close absent")
        stream = stream_first(
            prefix, thesis_at=thesis,
            direction=CapitalizerSourceDirection(s.h1_state_direction),
        )
        if stream is None:
            raise ValueError("no CISD candidate detected by original close")
        detected = dt(stream["detected_at"])
        if detected > at or dt(stream["witness_confirmed_at"]) > detected:
            raise ValueError("online detector viewed unseen M1")
        # No future M15 or H1.state_until is fed to the per-close observer.
        risk = abs(Decimal(s.decision_reference_price) -
                   Decimal(s.m15_protected_swing_price))
        if risk <= 0:
            raise ValueError("zero source risk for non-executable diagnostic")
        labels = {}
        for h in HORIZONS:
            labels[str(h)] = {
                "v49": post_entry_labels(
                    native,closed,at=at,direction=s.h1_state_direction,
                    original_risk_price=risk,minutes=h,
                ),
                "online": post_entry_labels(
                    native,closed,at=detected,direction=s.h1_state_direction,
                    original_risk_price=risk,minutes=h,
                ),
            }
        rows.append({
            "source_opportunity_id": sid, "symbol": symbol,
            "session": s.session, "operating_date": s.operating_date,
            "m15_confirmed_at": s.m15_setup_confirmed_at,
            "direction": s.h1_state_direction,
            "v49_entry_at": s.m1_trigger_confirmed_at,
            "v49_family": s.m1_trigger_family,
            "online_discovered_at": stream["detected_at"],
            "online_witness_confirmed_at": stream["witness_confirmed_at"],
            "online_family": stream["family"],
            "online_witness_backdated": stream["late_witness_discovery"] == "true",
            "family_changed": stream["family"] != s.m1_trigger_family,
            "close_changed": stream["detected_at"] != s.m1_trigger_confirmed_at,
            "paired": labels, "changes_original_admission": False,
            "live_execution_claimed": False, "outcome_used_for_selection": False,
            "requires_independent_poi_swing_author_audit": True,
        })
    counts = Counter(
        "MATCHED_ONLINE" if not (x["family_changed"] or x["close_changed"])
        else "DIFFERENT_ONLINE"
        for x in rows
    )
    return {
        "identity": IDENTITY, "symbol": symbol, "sources": len(rows),
        "classification": dict(sorted(counts.items())),
        "online_late_witness": sum(x["online_witness_backdated"] for x in rows),
        "admission_changes": 0,"trades_reexecuted": 0,
        "uses_forward_labels_for_selection": False, "paper_pf": None,
        "author_certified": False,
    }, tuple(rows)


def aggregate(root: Path) -> dict[str, Any]:
    markets = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(root.rglob("scalper-thirteenth-stream-market.json"))
    ]
    if len(markets) != 9 or len({x["symbol"] for x in markets}) != 9:
        raise ValueError("nine markets must complete")
    rows = [
        row
        for p in sorted(root.rglob("scalper-thirteenth-stream-ids.jsonl"))
        for row in _jsonl(p)
    ]
    if len(rows) != 2876 or len({x["source_opportunity_id"] for x in rows}) != 2876:
        raise ValueError("2876 frozen IDs must be retained")
    selected: dict[tuple[str,str],list[dict[str,Any]]] = defaultdict(list)
    for row in rows:
        selected[(row["session"],row["operating_date"])].append(row)
    original_max3 = {
        x["source_opportunity_id"]
        for key in sorted(selected)
        for x in sorted(selected[key],key=lambda y: (
            dt(y["v49_entry_at"]),y["symbol"],y["v49_family"]
        ))[:3]
    }
    online_max3 = {
        x["source_opportunity_id"]
        for key in sorted(selected)
        for x in sorted(selected[key],key=lambda y: (
            dt(y["online_discovered_at"]),y["symbol"],y["online_family"]
        ))[:3]
    }
    if len(original_max3)!=2020:
        raise ValueError("original global MAX3 source book changed")
    groupings = {
        "ALL_ORIGINAL":rows,
        "FIRST_ONLINE_IDENTICAL":[x for x in rows if
                                  not (x["close_changed"] or x["family_changed"])],
        "FIRST_ONLINE_DIFFERENT":[x for x in rows if
                                  x["close_changed"] or x["family_changed"]],
        "ORIGINAL_MAX3":[x for x in rows if x["source_opportunity_id"] in original_max3],
    }
    comparison: dict[str,Any] = {}
    for name,cohort in groupings.items():
        hrows: dict[str, Any] = {}
        for h in HORIZONS:
            observed=[(x["paired"][str(h)]["v49"],x["paired"][str(h)]["online"])
                      for x in cohort]
            paired=[(a,b) for a,b in observed if a["covered"] and b["covered"]]
            wins_v49=sum(a["positive"] for a,b in paired)
            wins_online=sum(b["positive"] for a,b in paired)
            n=len(paired)
            hrows[str(h)]={
                "paired_covered":n,"missing_pair":len(cohort)-n,
                "v49_favorable":wins_v49,"online_favorable":wins_online,
                "difference_online_minus_v49_pp":
                    round(100*(wins_online-wins_v49)/n,4) if n else None,
                "mean_delta_signed_r": str(
                    sum((Decimal(b["signed_close_r"])-Decimal(a["signed_close_r"])
                         for a,b in paired), Decimal(0))/Decimal(n)
                ) if n else None,
                "mean_delta_mfe_observed_r":str(
                    sum((Decimal(b["mfe_observed_r"])-Decimal(a["mfe_observed_r"])
                         for a,b in paired),Decimal(0))/Decimal(n)
                ) if n else None,
                "mean_delta_mae_observed_r":str(
                    sum((Decimal(b["mae_observed_r"])-Decimal(a["mae_observed_r"])
                         for a,b in paired),Decimal(0))/Decimal(n)
                ) if n else None,
            }
        comparison[name]={"source_opportunities":len(cohort),"by_horizon":hrows}
    return {
        "identity":IDENTITY,"markets":9,"sources":2876,
        "online_first_different":len(groupings["FIRST_ONLINE_DIFFERENT"]),
        "stream_first_equal":len(groupings["FIRST_ONLINE_IDENTICAL"]),
        "late_witness_discoveries":sum(x["online_witness_backdated"] for x in rows),
        "original_max3":len(original_max3),"online_max3_anchored":len(online_max3),
        "max3_id_intersection":len(online_max3 & original_max3),
        "max3_online_changed_ids":len(online_max3 - original_max3),
        "cohorts":comparison,
        "counterfactual_is_not_a_replayed_portfolio":True,
        "physical_costs_included":False,"admissions_changed":0,
        "paper_pf":None,"paper_dd":None,"author_certified":False,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    m=sub.add_parser("market")
    m.add_argument("original",type=Path)
    m.add_argument("native",type=Path)
    m.add_argument("output",type=Path)
    a=sub.add_parser("matrix")
    a.add_argument("inputs",type=Path)
    a.add_argument("output",type=Path)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    if args.mode=="market":
        report,rows=market(args.original,args.native)
        (args.output/"scalper-thirteenth-stream-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        with (args.output/"scalper-thirteenth-stream-ids.jsonl").open(
            "w",encoding="utf-8"
        ) as f:
            for row in rows:
                f.write(json.dumps(row,sort_keys=True)+"\n")
    else:
        report=aggregate(args.inputs)
        (args.output/"scalper-thirteenth-stream-nine-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
