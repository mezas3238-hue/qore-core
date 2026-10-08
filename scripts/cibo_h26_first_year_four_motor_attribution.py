"""H26 scientific attribution: first 12 months of FULL 3368-trade CIBO replays.

Compare native original CIBO with each single economic group off;
this is conditional marginal output, never gross independent revenue
attributable to a motor. All replays continue for 3 years; only their
first 12 months of realized receipts are compared.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal as D
import argparse,json
from pathlib import Path

BOUNDARY=datetime(2020,7,1,tzinfo=timezone.utc)
START=datetime(2019,7,1,tzinfo=timezone.utc)
FIELDS=["SIZING","CIBO_COMPOUND","COMPOUND_PORTFOLIO","ADAPTIVE_LEVERAGE"]


def dec(x): return str(x)


def replay_info(p):
    assert p["trade_count"] == p["decision_count"] == 3368,"trade list drift"
    assert p["economic_group_report"]["all_entries_preserved"] is True
    rs=p["trade_receipts"]
    assert len(rs)==3368
    early=[]
    for tr in rs:
        exit_at=datetime.fromisoformat(tr["realized_exit_at"])
        assert exit_at>=START
        if exit_at<BOUNDARY: early.append(tr)
    modes={}
    for mode in ("BANK","MEDIUM","ATTACK"):
        rows=[t for t in early if t["mode"]==mode]
        modes[mode]={
            "n":len(rows),
            "net_profit_usd":dec(sum((D(t["realized_net_pnl_usd"]) for t in rows),D(0))),
            "already_charged_provider_fees_usd":dec(sum((D(t["provider_cost_usd"]) for t in rows),D(0))),
            "sum_stop_risk_usd":dec(sum((D(t["stop_risk_usd"]) for t in rows),D(0))),
            "multiplier_hist":dict(sorted(Counter(str(t["multiplier"]) for t in rows).items(),key=lambda x:int(x[0])))
        }
    net=sum((D(t["realized_net_pnl_usd"]) for t in early),D(0))
    all_net=sum((D(t["realized_net_pnl_usd"]) for t in rs),D(0))
    full_cap=D(p["ending_total_capital_usd"])
    assert abs(D(60)+all_net-full_cap)<D(".00000001"),"full PnL mismatch"
    assert sum(v["n"] for v in modes.values())==len(early)
    assert abs(sum((D(v["net_profit_usd"]) for v in modes.values()),D(0))-net)<D(".00000001")
    eco=p["economic_group_report"]
    return {
        "first_year_realized_closed_trade_count":len(early),
        "first_year_net_profit_usd":dec(net),
        "first_year_settled_balance_usd":dec(D(60)+net),
        "first_year_mode_breakdown":modes,
        "full_3year_ending_capital_usd":dec(full_cap),
        "full_3year_max_drawdown_pct":dec(D(p["max_drawdown_fraction"])*D(100)),
        "full_3year_sovereign_floor_breach_usd":p["sovereign_floor_breach_usd"],
        "all_3368_accounted_for":True,
        "ablation":eco["ablation"],
        "total_sizing_intensity_hist":eco["sizing_intensity_cap_counts"],
        "total_MEDIUM_dd_force_1x_count":eco["medium_drawdown_intensity_cap_bind_count"],
        "total_ATTACK_risk_fraction_band_cap_count":eco["attack_risk_fraction_band_taper_bind_count"],
        "total_ATTACK_profit_to_portfolio_usd":eco["attack_profit_to_portfolio_cushion_usd"],
        "total_bank_seed_issued_usd":p["bank_seed_issued_total_usd"],
        "total_bank_seed_recycled_usd":p["bank_seed_recycled_total_usd"],
        "total_portfolio_credit_recycled_usd":p["portfolio_attack_credit_recycled_total_usd"],
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--results-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    paths={
        "FULL":"h26-full.json",
        "WITHOUT_SIZING":"h26-no-sizing.json",
        "WITHOUT_CIBO_COMPOUND":"h26-no-cibo-compound.json",
        "WITHOUT_PORTFOLIO_COMPOUND":"h26-no-portfolio-compound.json",
        "WITHOUT_ADAPTIVE_LEVERAGE":"h26-no-leverage.json",
    }
    results={k:replay_info(json.loads((args.results_dir/v).read_text())) for k,v in paths.items()}
    base=results["FULL"]
    expected={
        "WITHOUT_SIZING":"SIZING",
        "WITHOUT_CIBO_COMPOUND":"CIBO_COMPOUND",
        "WITHOUT_PORTFOLIO_COMPOUND":"COMPOUND_PORTFOLIO",
        "WITHOUT_ADAPTIVE_LEVERAGE":"ADAPTIVE_LEVERAGE",
    }
    assert results["FULL"]["ablation"] is None
    for k,v in expected.items():
        assert results[k]["ablation"]==v,(k,results[k]["ablation"])
    assert abs(D(base["first_year_net_profit_usd"])-D("408.14184887909376990669055668"))<D(".00000001"),"H25 first year baseline differs"
    assert abs(D(base["full_3year_ending_capital_usd"])-D("3589.260487255495141276366310"))<D(".00000001"),"H25 control differs"
    marginal={}
    for without, motor in expected.items():
        case=results[without]
        marginal[motor]={
            "first_year_marginal_usd":dec(D(base["first_year_net_profit_usd"])-D(case["first_year_net_profit_usd"])),
            "full_3year_marginal_usd":dec(D(base["full_3year_ending_capital_usd"])-D(case["full_3year_ending_capital_usd"])),
            "first_year_counterfactual_net_usd":case["first_year_net_profit_usd"],
            "counterfactual_all_3year_trades":3368,
            "counterfactual_bank_valid_full_3year":D(case["full_3year_sovereign_floor_breach_usd"])==0,
            "remark":"Conditional full-vs-no-motor change; not standalone or additive income. No-engine run changes downstream trading/capital allocation."
        }
    analysis={
        "engine":"canonical CIBO full method + validated 5pct micro nominal risk + H21 sovereign bank50 and adverse cut -0.20R",
        "time_horizon":"2019-07-01 through 2020-07-01 exclusive, UTC exit-time realized settlement profit",
        "original_3year_source":"3368 full original Trader entries, no rejection",
        "cases":results,
        "conditional_motor_marginals":marginal,
        "caution":"Do NOT sum motor attributions. This is original $60 research native provider model, NOT funded live, not $14/lot, includes no floating open positions at year boundary. Bank floor in counterfactual can fail. Baseline 3-year DD >25pct.",
        "status":"RESEARCH_ONLY",
    }
    args.output.write_text(json.dumps(analysis,indent=2,sort_keys=True))
    print("CIBO_H26_FIRST_YEAR_BASELINE="+json.dumps({k:base[k] for k in [
        "first_year_net_profit_usd","first_year_settled_balance_usd","first_year_mode_breakdown",
        "total_sizing_intensity_hist","total_MEDIUM_dd_force_1x_count",
        "total_ATTACK_risk_fraction_band_cap_count"]},sort_keys=True))
    print("CIBO_H26_FOUR_MOTOR_CAUSAL_MARGINALS="+json.dumps(marginal,sort_keys=True))
    print("CIBO_H26_CONTROL_3368_FULL_H25_PARITY=YES")


if __name__=="__main__":
    main()
