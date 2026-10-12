"""One preregistered FX28 cross-sectional monthly forward carry reference.

Frozen prereg f94fda3d. Spot OHLC cannot identify historical carry factors.
Synthetic-only tests do not count as carry outcomes. No orders or broker NET.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import mean

from qore.research.alpha2_intermarket import MARKETS

IDENTITY = "QORE_ALPHA2_FX28_CARRY_1M_FORWARDS_FIXED6X6_V1"
FACTOR_REQUIRED = "HISTORICAL_FX_1M_FORWARD_ASOF_SOURCE_PROVENANCE"
PREREG_COMMIT = "f94fda3d51602a39548d767b87e379ac5fd742b5"
FX28 = tuple(s for s in MARKETS if len(s) == 6)
CCYS = frozenset({"AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"})
ALL_PAIRS = {frozenset((x, y)) for x in CCYS for y in CCYS if x != y}
COST_PER_SIDE_BPS = 2.0
PAIRS_PER_SIDE = 6
SYNTHETIC_NOT_CERTIFIED = True


def validate_roster() -> None:
    if (len(FX28) != 28 or len(CCYS) != 8
        or len({frozenset((s[:3], s[3:])) for s in FX28}) != 28
        or {frozenset((s[:3], s[3:])) for s in FX28} != ALL_PAIRS
        or any(s[:3] not in CCYS or s[3:] not in CCYS for s in FX28)
    ):
        raise ValueError("CARRY28_FX_ROSTER_NOT_COMPLETE_GRAPH8")


validate_roster()


@dataclass(frozen=True)
class ForwardWitness:
    """A frozen as-of historical 1M forward, not one original spot M5 bar."""
    symbol: str
    observed_at: datetime
    available_at: datetime
    decision_at: datetime
    contractual_maturity: date
    spot_mid_asof: float
    forward_1m_mid_asof: float
    settlement_spot_mid: float
    evidence_source_uri: str
    evidence_sha256: str

    def __post_init__(self) -> None:
        stamps = (self.observed_at, self.available_at, self.decision_at)
        if any(x.tzinfo is None or x.utcoffset() != UTC.utcoffset(x) for x in stamps):
            raise ValueError("CARRY28_ASOF_UTC_REQUIRED")
        if not self.observed_at <= self.available_at <= self.decision_at:
            raise ValueError("CARRY28_INFORMATION_LEAK_FUTURE_FORWARD")
        if (self.decision_at - self.available_at).total_seconds() > 24 * 3600:
            raise ValueError("CARRY28_FORWARD_STALE_MORE_THAN_24H")
        if self.symbol not in FX28:
            raise ValueError("CARRY28_FORBID_UNREGISTERED_PAIR")
        maturity_days = (self.contractual_maturity - self.decision_at.date()).days
        if not 20 <= maturity_days <= 38:
            raise ValueError("CARRY28_EXACT_1M_MATURITY_OUTSIDE_FROZEN_WINDOW")
        if (self.decision_at.date() < date(2016, 9, 17)
            or self.contractual_maturity >= date(2024, 9, 17)
            or self.decision_at.date() < date(2022, 1, 1)
            <= self.contractual_maturity):
            raise ValueError("CARRY28_OUTSIDE_SOURCE_EMBARGO_OR_SPLIT")
        if any(not math.isfinite(x) or x <= 0
               for x in (self.spot_mid_asof,self.forward_1m_mid_asof,self.settlement_spot_mid)):
            raise ValueError("CARRY28_NONFINITE_QUOTE")
        if (not self.evidence_source_uri.startswith(("https://", "s3://", "gcs://"))
            or len(self.evidence_sha256) != 64
            or any(x not in "0123456789abcdef" for x in self.evidence_sha256)):
            raise ValueError("CARRY28_PIT_FORWARD_SOURCE_PROVENANCE_REQUIRED")


def _iso(stamp: str) -> datetime:
    x=datetime.fromisoformat(stamp.replace("Z","+00:00"))
    if x.tzinfo is None:
        raise ValueError("CARRY28_UTC_DATETIME_REQUIRED")
    return x.astimezone(UTC)


def parse_snapshot(data: dict) -> tuple[date, list[ForwardWitness]]:
    if data.get("futures_contract_source_type") != "HISTORICAL_1M_FORWARD_EXPLICIT":
        raise ValueError("CARRY28_SPOT_SERIES_CANNOT_SUBSTITUTE_FORWARD")
    if data.get("original_28_broker_pair_contracts_verified") is not True:
        raise ValueError("CARRY28_BROKER_PAIR_UNCERTIFIED_DO_NOT_ASSERT_NET")
    ym=data["month"]
    d=date.fromisoformat(ym + "-01")
    witnesses=[]
    for x in data.get("quotes",[]):
        witnesses.append(ForwardWitness(
            symbol=x["symbol"],observed_at=_iso(x["observed_at"]),
            available_at=_iso(x["available_at"]),decision_at=_iso(x["decision_at"]),
            contractual_maturity=date.fromisoformat(x["contractual_maturity"]),
            spot_mid_asof=float(x["spot_mid_asof"]),
            forward_1m_mid_asof=float(x["forward_1m_mid_asof"]),
            settlement_spot_mid=float(x["settlement_spot_mid"]),
            evidence_source_uri=x["evidence_source_uri"],
            evidence_sha256=x["evidence_sha256"],
        ))
    return d, witnesses


def one_month(month: date, quotes: list[ForwardWitness]) -> dict:
    """No incomplete 28 basket, no currency subsets or missing data fillings."""
    if len(quotes)!=28 or {q.symbol for q in quotes}!=set(FX28):
        raise ValueError("CARRY28_INCOMPLETE_28_MONTH_NOT_TRADABLE")
    if month.day != 1 or any(q.decision_at.year != month.year
                             or q.decision_at.month != month.month for q in quotes):
        raise ValueError("CARRY28_MONTH_DECISION_NOT_MATCHED")
    if len({q.decision_at for q in quotes}) != 1:
        raise ValueError("CARRY28_SYNC_DECISION_REQUIRED")
    # A synthetic gradient on eight rates still maps to 28 PAIR rankings.
    sorted_pairs=sorted(
        quotes, key=lambda q:(-math.log(q.spot_mid_asof/q.forward_1m_mid_asof),q.symbol)
    )
    longs=sorted_pairs[:PAIRS_PER_SIDE]
    shorts=sorted_pairs[-PAIRS_PER_SIDE:]
    if len({q.symbol for q in longs+shorts}) != 12:
        raise ValueError("CARRY28_OVERLAPPING_SELECTION")
    exposure=defaultdict(float)
    gross=0.0
    ranked=[]
    for q in longs+shorts:
        w=(1.0 / 12.0) if q in longs else (-1.0 / 12.0)
        exposure[q.symbol[:3]]+=w
        exposure[q.symbol[3:]]-=w
        bps=10000*w*(q.settlement_spot_mid/q.forward_1m_mid_asof-1)
        gross+=bps
        ranked.append({
            "symbol":q.symbol,
            "signed_gross_notional_weight":w,
            "reference_forward_to_maturity_contribution_bps":bps,
            "forward_discount_signal_log_S_over_F":math.log(
                q.spot_mid_asof/q.forward_1m_mid_asof
            ),
        })
    cost=COST_PER_SIDE_BPS * 2.0
    year=month.year
    era="DEVELOPMENT" if year<=2021 else "DIAGNOSTIC"
    return {
        "month":month.isoformat()[:7],"era":era,
        "ranked_selected_12":ranked,
        "long6":[q.symbol for q in longs],
        "short6":[q.symbol for q in shorts],
        "currency_net_exposure_signed":dict(sorted(exposure.items())),
        "maximum_absolute_currency_exposure":max(map(abs,exposure.values())),
        "gross_reference_bps":gross,
        "assumed_2bps_each_side_for_gross_notional1_bps":cost,
        "gross_minus_assumed_cost_proxy_bps":gross-cost,
        "broker_NET_not_proven":True,
    }


def _month_range(start: date, end: date) -> list[str]:
    d=start
    a=[]
    while d<end:
        a.append(d.strftime("%Y-%m"))
        d=date(d.year+1,1,1) if d.month==12 else date(d.year,d.month+1,1)
    return a


def _block3(weekly: list[float], *, seed:int, draws:int=2000) -> list[float]:
    if not weekly:
        raise ValueError("CARRY28_ZERO_CALENDAR")
    n=len(weekly)
    rand=random.Random(seed)
    arr=[]
    for _ in range(draws):
        idx=[]
        while len(idx)<n:
            start=rand.randrange(n)
            idx.extend((start+j)%n for j in range(3))
        arr.append(sum(weekly[k] for k in idx[:n])/n)
    arr.sort()
    return [arr[int(.025*draws)],arr[int(.975*draws)-1]]


def summarize(months: list[dict], invalid_months: dict[str,str] | None = None) -> dict:
    by_month={x["month"]:x for x in months}
    if len(by_month)!=len(months):
        raise ValueError("CARRY28_DUPLICATED_MONTH_OUTCOME")
    allowed=set(_month_range(date(2016,9,1),date(2024,9,1)))
    if not set(by_month)<=allowed:
        raise ValueError("CARRY28_MONTH_BEYOND_WINDOW")
    stats={}
    for era,start,end in (
        ("DEVELOPMENT",date(2016,9,1),date(2022,1,1)),
        ("DIAGNOSTIC",date(2022,1,1),date(2024,9,1)),
    ):
        all_months=_month_range(start,end)
        data=[by_month[m]["gross_minus_assumed_cost_proxy_bps"]
              if m in by_month else 0.0 for m in all_months]
        n=sum(m in by_month for m in all_months)
        lower,upper=_block3(data,seed=20261012+(era=="DIAGNOSTIC"))
        stats[era]={
            "calendar_months_including_flat":len(all_months),
            "executed_full28_months":n,
            "min_months":24 if era=="DEVELOPMENT" else 12,
            "sample_gate":n>=(24 if era=="DEVELOPMENT" else 12),
            "mean_monthly_gross_minus_2bps_per_side_proxy_bps":mean(data),
            "CI95_circular_3month_block_bps":[lower,upper],
            "broker_NET_not_computed":True,
        }
    if not months:
        state="CARRY_NOT_IDENTIFIABLE_SPOT_ONLY"
    elif not all(x["sample_gate"] for x in stats.values()):
        state="CARRY28_UNDERPOWERED"
    elif all(x["mean_monthly_gross_minus_2bps_per_side_proxy_bps"]>0
             and x["CI95_circular_3month_block_bps"][0]>0
             for x in stats.values()):
        state="CARRY28_EXPLORATORY_FORWARD_SIGNAL_REQUIRES_VIRGIN_OOS"
    else:
        state="CARRY28_PREDECLARED_GROSS_MINUS_ASSUMED_COST_FAILED"
    return {
        "identity":IDENTITY,"prereg":PREREG_COMMIT,"status":state,
        "exact_28_fx_complete_graph_of_eight_currencies":True,
        "no_forward_factor_no_edge_test":not bool(months),
        "historical_spot_only_does_not_contain_forward_carry":True,
        "months":months,"incomplete_or_censored_months":invalid_months or {},
        "eras":stats,"account_broker_NET_not_computed":True,
        "UTC001_certified":False,"orders":0,
        "source_2016_to_2024_previously_exposed":True,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    outcomes=[]
    rejects={}
    if a.input is None:
        # Pure source-readiness check, NO economic backtest if absent forward data.
        rejects["FX28_MONTHLY_HISTORICAL_1M_FORWARD_QUOTES"]="ABSENT_NO_PIT_SOURCE_GIVEN"
    else:
        x=json.loads(a.input.read_text(encoding="utf-8"))
        if x.get("source_class")!="HISTORICAL_1M_FORWARD_EXPLICIT":
            raise ValueError("CARRY28_REFUSE_SPOT_OR_SYNTHETIC_AS_REAL_FACTOR")
        for row in x.get("monthly_snapshots",[]):
            month,quotes=parse_snapshot(row)
            key=month.strftime("%Y-%m")
            try:
                outcomes.append(one_month(month,quotes))
            except ValueError as e:
                rejects[key]=str(e)
    data=summarize(outcomes,rejects)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":data["status"],"eligible_months":len(outcomes),
                      "net":"BLOCKED","orders":0},sort_keys=True))


if __name__=="__main__":
    main()
