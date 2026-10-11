"""DCVC preregistered exploratory A/B; C is fail-closed without real Master Frame.

All economic results are frozen V49 source-anchored GROSS M1 replay outcomes,
not fresh BID/ASK fills. The B classifier itself NEVER receives trade outcomes.
Only settled B-selected fills update it once exit_at < next decision_at.
"""
from __future__ import annotations

import argparse
import heapq
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEFAULT_LOOKBACK,
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_causal_features_v1 import (
    DCVCPredecision,
    observe,
    safe_record,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
    _portfolio_select,
)

IDENTITY = "QORE_SCALPER_DCVC_PREQUENTIAL_SOURCE_ANCHORED_EXPLORATORY_V01"
COSTS = (Decimal("0"),Decimal("0.025"),Decimal("0.05"),Decimal("0.10"))
SPLIT_A = datetime.fromisoformat("2026-04-24T00:00:00+00:00")
SPLIT_B = datetime.fromisoformat("2026-07-06T00:00:00+00:00")


def read_jsonl(file: Path) -> tuple[dict[str, Any], ...]:
    return tuple(json.loads(line) for line in file.read_text(encoding="utf-8").splitlines()
                 if line.strip())


def market(
    original_root: Path, native_root: Path, output: Path,
) -> dict[str, Any]:
    op_files=tuple(original_root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    trade_files=tuple(original_root.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    if len(op_files)!=1 or len(trade_files)!=1:
        raise ValueError("one original source and economic ledger per market mandatory")
    sources=tuple(V49Opportunity(**row) for row in read_jsonl(op_files[0]))
    trades=tuple(V49EconomicTrade(**row) for row in read_jsonl(trade_files[0]))
    if not sources or len(sources)!=len(trades):
        raise ValueError("source/economic population mismatch")
    symbol=sources[0].symbol
    if any(x.symbol!=symbol for x in sources) or any(x.symbol!=symbol for x in trades):
        raise ValueError("mixed native symbol")
    by_key={(t.entry_at,t.trigger_family,t.h1_state_basis):t for t in trades}
    if len(by_key)!=len(trades):
        raise ValueError("duplicate frozen V49 economic identity")
    native=tuple(
        bar for bar in iter_cibo_m1(native_root)
        if DEV_WINDOW_START-DEFAULT_LOOKBACK<=bar.opened_at<DEV_WINDOW_END
    )
    if not native or any(x.symbol!=symbol for x in native):
        raise ValueError("native M1 is absent or wrong symbol")
    clocks=tuple(bar.closed_at for bar in native)
    if any(clocks[i]>=clocks[i+1] for i in range(len(clocks)-1)):
        raise ValueError("native M1 chronology invalid")
    features=[]
    labels=[]
    for source in sources:
        key=(source.m1_trigger_confirmed_at,source.m1_trigger_family,source.h1_state_basis)
        trade=by_key.get(key)
        if trade is None:
            raise ValueError("frozen V49 opportunity lacks exact economic identity")
        feature=observe(source,native,clocks)
        if feature.source_opportunity_id!=source_id(source):
            raise ValueError("source hash changed")
        features.append(feature)
        labels.append({"source_opportunity_id":source_id(source),**asdict(trade)})
    output.mkdir(parents=True,exist_ok=True)
    with (output/"dcvc-predecision.jsonl").open("w",encoding="utf-8") as f:
        for feature in features:
            f.write(json.dumps(safe_record(feature),sort_keys=True)+"\n")
    with (output/"dcvc-outcomes-after-settlement.jsonl").open(
        "w",encoding="utf-8"
    ) as f:
        for item in labels:
            f.write(json.dumps(item,sort_keys=True)+"\n")
    report={
        "identity":IDENTITY,"symbol":symbol,"n":len(features),
        "unknown_regimes":sum(x.regime=="UNKNOWN" for x in features),
        "confirmed_real_bid_ask":False,"ttrades_m30_m3_is_not_h1_m15_m1_gate":True,
        "master_frame_invoked":False,"live_authorized":False,
    }
    (output/"dcvc-market.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    return report


@dataclass(slots=True)
class DCVCState:
    total: int = 0
    gross_r: Decimal = Decimal(0)
    count: dict[str,int] | None = None
    realized: dict[str,Decimal] | None = None

    def __post_init__(self) -> None:
        if self.count is None:
            self.count = {}
        if self.realized is None:
            self.realized = {}

    def admit(self, item: DCVCPredecision) -> tuple[bool,str,Decimal|None]:
        """Only features + previously settled B trades: no trade/exit arguments."""
        if self.total<60:
            return True,"COLD_START_PASS",None
        if item.regime=="UNKNOWN":
            return True,"UNKNOWN_INFORMATIONAL_PASS",None
        assert self.count is not None and self.realized is not None
        n=self.count.get(item.regime,0)
        if n<20:
            return True,"UNDERPOWERED_INFORMATIONAL_PASS",None
        prior=self.gross_r/Decimal(self.total)
        mean=(self.realized.get(item.regime,Decimal(0))+Decimal(40)*prior)/Decimal(n+40)
        return mean>Decimal("0.025"),"FROZEN_POSTERIOR_EXPECTANCY",mean

    def settle(self, regime:str, result:Decimal) -> None:
        self.total+=1
        self.gross_r+=result
        assert self.count is not None and self.realized is not None
        self.count[regime]=self.count.get(regime,0)+1
        self.realized[regime]=self.realized.get(regime,Decimal(0))+result


def split(at:str)->str:
    dt=datetime.fromisoformat(at)
    return "TRAIN" if dt<SPLIT_A else "VALIDATION" if dt<SPLIT_B else "PSEUDO_TEST_CONSUMED"


def summarize(trades:tuple[V49EconomicTrade,...],cost:Decimal=Decimal(0))->dict[str,Any]:
    if not trades:
        return {"n":0,"gross_pf":None,"max_dd_r":None,"net_expectancy_r":None}
    stats=_metrics(trades,cost_r=cost)
    return {
        "n":stats.trades,"wins":stats.wins,"win_rate":stats.win_rate,
        "gross_profit_after_assumed_cost_r":stats.gross_profit_r,
        "gross_loss_after_assumed_cost_r":stats.gross_loss_r,
        "profit_factor_after_assumed_cost":stats.profit_factor,
        "total_r_after_assumed_cost":stats.total_r,
        "net_expectancy_r":stats.expectancy_r,
        "max_dd_r":stats.max_drawdown_r,
        "max_losing_streak":stats.max_losing_streak,
    }


def equity_curve(trades:tuple[V49EconomicTrade,...],cost:Decimal)->tuple[dict[str,Any],...]:
    ordered=sorted(trades,key=lambda x:(x.exit_at,x.entry_at,x.symbol))
    cumulative=peak=Decimal(0)
    capital=Decimal(100)
    capital_peak=Decimal(100)
    result=[]
    for x in ordered:
        r=Decimal(x.realized_gross_r)-cost
        cumulative+=r
        peak=max(cumulative,peak)
        # Experimental normalized risk: 1% of CURRENT equity per unit R.
        capital*=Decimal(1)+r*Decimal("0.01")
        capital_peak=max(capital_peak,capital)
        result.append({
            "closed_at":x.exit_at,"symbol":x.symbol,"entry_at":x.entry_at,
            "equity_r":str(cumulative),"drawdown_r":str(peak-cumulative),
            "capital_1pct_risk_hypothetical":str(capital),
            "capital_drawdown_pct_hypothetical":str(
                Decimal(100)*(capital_peak-capital)/capital_peak
            ),
        })
    return tuple(result)


def extras(trades:tuple[V49EconomicTrade,...],cost:Decimal)->dict[str,Any]:
    curve=equity_curve(trades,cost)
    maximum=max((Decimal(z["capital_drawdown_pct_hypothetical"]) for z in curve),
                default=Decimal(0))
    series=sorted(trades,key=lambda t:(t.exit_at,t.entry_at,t.symbol))
    underwater=longest=0
    streaks=[]
    streak=0
    for x,point in zip(series,curve,strict=True):
        if Decimal(x.realized_gross_r)-cost<0:
            streak+=1
        elif streak:
            streaks.append(streak)
            streak=0
        if Decimal(point["drawdown_r"])>0:
            underwater+=1
            longest=max(longest,underwater)
        else:
            underwater=0
    if streak:
        streaks.append(streak)
    monthly=Counter(x.entry_at[:7] for x in trades)
    return {
        "max_drawdown_pct_actual_capital":None,
        "max_drawdown_pct_1pct_risk_hypothetical":str(maximum),
        "longest_underwater_exits":longest,
        "losing_streak_lengths":streaks,
        "monthly_trades":dict(sorted(monthly.items())),
        "annual_trades":dict(sorted(Counter(x.entry_at[:4] for x in trades).items())),
    }


def aggregate(root:Path,output:Path)->dict[str,Any]:
    paths=sorted(root.rglob("dcvc-market.json"))
    feature_files=sorted(root.rglob("dcvc-predecision.jsonl"))
    label_files=sorted(root.rglob("dcvc-outcomes-after-settlement.jsonl"))
    if any(len(files)!=9 for files in (paths,feature_files,label_files)):
        raise ValueError("nine V49 frozen symbol artifacts mandatory")
    reports=[json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if len({s["symbol"] for s in reports})!=9:
        raise ValueError("market identity duplicated")
    features=tuple(DCVCPredecision(**x) for p in feature_files for x in read_jsonl(p))
    labels=tuple(x for p in label_files for x in read_jsonl(p))
    if len(features)!=2876 or len(labels)!=2876:
        raise ValueError("historical source census not 2876")
    feature_by_id={f.source_opportunity_id:f for f in features}
    label_by_id={t["source_opportunity_id"]:t for t in labels}
    if len(feature_by_id)!=2876 or set(feature_by_id)!=set(label_by_id):
        raise ValueError("frozen source ID reconciliation failed")
    trade_by_id={sid:V49EconomicTrade(**{k:v for k,v in row.items()
                                      if k!="source_opportunity_id"})
                 for sid,row in label_by_id.items()}
    baseline=tuple(t for _,t in _portfolio_select(tuple(trade_by_id.values())))
    baseline_m=_metrics(baseline)
    if (len(baseline)!=2020 or baseline_m.wins!=1167
        or abs(Decimal(baseline_m.total_r)-Decimal("-233.2693270763665099166092077"))
            >Decimal("0.000000001")
        or abs(Decimal(baseline_m.max_drawdown_r)-Decimal("236.134284"))
            >Decimal("0.00001")):
        raise ValueError("V49 2020 / PF / baseline drawdown is not reproducible")
    if abs(Decimal(baseline_m.profit_factor or "0")-
           Decimal("0.6644630742"))>Decimal("0.000001"):
        raise ValueError("frozen original PF diverges")

    state=DCVCState()
    selected=[]
    decisions=[]
    capacity:Counter[tuple[str,str]]=Counter()
    waiting:list[tuple[datetime,str,str,Decimal]]=[]
    ordered=sorted(feature_by_id.values(),key=lambda f:
                   (f.decision_at,f.symbol,trade_by_id[f.source_opportunity_id].trigger_family,
                    f.source_opportunity_id))
    for f in ordered:
        now=datetime.fromisoformat(f.decision_at)
        while waiting and waiting[0][0]<now:
            _,sid,regime,pnl=heapq.heappop(waiting)
            state.settle(regime,pnl)
        allowed,why,estimate=state.admit(f)
        slot=(f.session,f.operating_date)
        chosen=allowed and capacity[slot]<3
        if chosen:
            capacity[slot]+=1
            t=trade_by_id[f.source_opportunity_id]
            selected.append((f.source_opportunity_id,t))
            heapq.heappush(waiting,(datetime.fromisoformat(t.exit_at),
                                    f.source_opportunity_id,f.regime,
                                    Decimal(t.realized_gross_r)))
        decisions.append({
            "source_opportunity_id":f.source_opportunity_id,
            "decision_at":f.decision_at,"symbol":f.symbol,"regime":f.regime,
            "selected":chosen,"reason":why if not allowed else
                "MAX3_CAPACITY" if not chosen else why,
            "expected_prior_r":str(estimate) if estimate is not None else None,
            "settled_selected_b_before_decision":state.total,
            "outcome_available_to_classifier":False,
            "sample":split(f.decision_at),
        })
    b=tuple(x[1] for x in selected)
    if len(decisions)!=2876 or any(n>3 for n in capacity.values()):
        raise ValueError("A/B source universe or session MAX3 changed")
    # Original winner preservation uses source identity, never new payoffs.
    baseline_keys={
        (t.symbol,t.session,t.operating_date,t.entry_at,t.trigger_family):t
        for t in baseline if Decimal(t.realized_gross_r)>0
    }
    chosen_keys={
        (t.symbol,t.session,t.operating_date,t.entry_at,t.trigger_family) for t in b
    }
    retained=set(baseline_keys)&chosen_keys
    original_winner_r=sum((Decimal(baseline_keys[k].realized_gross_r)
                           for k in retained),Decimal(0))
    by_phase={}
    for label in ("TRAIN","VALIDATION","PSEUDO_TEST_CONSUMED"):
        a_rows=tuple(t for t in baseline if split(t.entry_at)==label)
        b_rows=tuple(t for t in b if split(t.entry_at)==label)
        by_phase[label]={"A_original":summarize(a_rows),
                         "B_dcvc":summarize(b_rows)}
    by_regime={}
    for regime in sorted({f.regime for f in features}):
        rows=tuple(t for sid,t in selected if feature_by_id[sid].regime==regime)
        by_regime[regime]=summarize(rows)
    quarter={}
    for name,rows in (("A",baseline),("B",b)):
        quarter[name]={}
        for q in sorted({t.entry_at[:4]+"Q"+str((int(t.entry_at[5:7])-1)//3+1)
                         for t in rows}):
            subset=tuple(t for t in rows
                if t.entry_at[:4]+"Q"+str((int(t.entry_at[5:7])-1)//3+1)==q)
            quarter[name][q]=summarize(subset)
    stress={
        str(cost):{
            "A_original":summarize(baseline,cost),
            "B_dcvc":summarize(b,cost),
            "A_drawdown_extras":extras(baseline,cost),
            "B_drawdown_extras":extras(b,cost),
        }
        for cost in COSTS
    }
    # Exposure-only placebo: scaling A risk per trade to B/A trade count.
    ratio=Decimal(len(b))/Decimal(len(baseline))
    exposure_dd=Decimal(baseline_m.max_drawdown_r)*ratio
    # Outcome-blind matched random: sample exact B session/date capacities,
    # then read outcomes only for OFFLINE diagnostic (not deployable policy).
    group:dict[tuple[str,str],list[str]]=defaultdict(list)
    for f in features:
        group[(f.session,f.operating_date)].append(f.source_opportunity_id)
    b_by_group=Counter((t.session,t.operating_date) for t in b)
    random_dd=[];random_pf=[]
    for seed in range(100):
        rng=random.Random(20261010+seed)
        placebo=[]
        for key,n in sorted(b_by_group.items()):
            draws=rng.sample(group[key],n)
            placebo.extend(trade_by_id[sid] for sid in draws)
        sample_metrics=summarize(tuple(placebo),Decimal("0.025"))
        random_dd.append(sample_metrics["max_dd_r"])
        random_pf.append(sample_metrics["profit_factor_after_assumed_cost"])
    result={
        "identity":IDENTITY,"source_opportunities":2876,
        "markets":9,"baseline_n":len(baseline),"dcvc_n":len(b),
        "baseline_control_verified":True,
        "predecision_feature_rows":len(features),
        "regimes_unknown":sum(f.regime=="UNKNOWN" for f in features),
        "B_model_trained_only_on_selected_settled":True,
        "method":"SOURCE_ANCHORED_V49_GROSS_BROKER_COSTS_MISSING",
        "A_original_gross":summarize(baseline),
        "B_dcvc_gross":summarize(b),
        "cost_stress_assumed_r":stress,
        "by_phase":by_phase,"by_regime_B":by_regime,"by_quarter":quarter,
        "preserved_original_winner_ids":len(retained),
        "preserved_original_winner_r":str(original_winner_r),
        "risk_exposure_matched_A_scaled_to_B_fraction":{
            "scaling_factor":str(ratio),"scaled_max_dd_r":str(exposure_dd),
            "not_a_new_executable_strategy":True,
        },
        "random_matched_100_seeds":{
            "cost_assumption_r":"0.025",
            "drawdown_r":random_dd,"profit_factor":random_pf,
            "uses_posthoc_B_group_counts":True,
            "confirmatory_evidence":False,
        },
        "physical_bid_ask_and_broker_costs_verified":False,
        "OOS_independent":False,
        "C_full_existing_master_frame":{
            "status":"BLOCKED_MISSING_REAL_ASOF_NINE_MARKET_A1_INPUT_AND_PHYSICAL_EXECUTION",
            "trades":None,"profit_factor":None,"drawdown_r":None,
            "not_replaced_by_proxy":True,
        },
        "certified":False,
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"dcvc-abc-scientific-exploratory.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    for label,rows in (("A_original",baseline),("B_dcvc",b)):
        for cost in COSTS:
            suffix=str(cost).replace(".","p")
            p=output/f"dcvc-{label}-equity-cost{suffix}.jsonl"
            with p.open("w",encoding="utf-8") as handle:
                for x in equity_curve(rows,cost):
                    handle.write(json.dumps(x,sort_keys=True)+"\n")
    with (output/"dcvc-decisions-outcome-blind.jsonl").open(
        "w",encoding="utf-8"
    ) as handle:
        for row in decisions:
            handle.write(json.dumps(row,sort_keys=True)+"\n")
    return result


def main()->None:
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="mode",required=True)
    mk=sub.add_parser("market")
    mk.add_argument("original",type=Path)
    mk.add_argument("native",type=Path)
    mk.add_argument("output",type=Path)
    ag=sub.add_parser("aggregate")
    ag.add_argument("root",type=Path)
    ag.add_argument("output",type=Path)
    args=parser.parse_args()
    report=(market(args.original,args.native,args.output)
            if args.mode=="market" else aggregate(args.root,args.output))
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
