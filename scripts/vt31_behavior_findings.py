"""Render descriptive findings from the immutable VT-31 behavior observatory.

This renderer does not select markets, rules or candidates. It summarizes
stability, uncertainty, coverage, cross-index synchronization and unsupervised
pre-entry regime behavior from consumed evidence only.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

MARKETS=("NAS100","SP500","US30")


def D(v: object)->Decimal:
    return Decimal(str(v))


def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument('--observatory',required=True,type=Path); ap.add_argument('--output',required=True,type=Path); ap.add_argument('--markdown',required=True,type=Path); a=ap.parse_args()
    p=json.loads(a.observatory.read_text())
    if p.get('research_only') is not True or p.get('opens_new_holdout') is not False or p.get('selection_prohibited') is not True:
        raise ValueError('observatory governance guard')
    if p.get('terminal_count')!=618 or p.get('coverage',{}).get('root_count')!=780:
        raise ValueError('observatory cardinality changed')

    coverage_market=p['coverage']['by_dimension']['market']
    bootstrap=p['block_bootstrap_uncertainty']
    temporal=p['temporal']['market_half_year']
    features=p['feature_distributions_by_market']
    failures=p['failure_modes']['by_market']
    regimes=p['unsupervised_pre_entry_regimes']['clusters']

    market_profiles:dict[str,Any]={}
    for market in MARKETS:
        mm=p['market_metrics'][market]
        bm=bootstrap[f'market:{market}']
        tm=temporal[market]
        market_profiles[market]={
            'terminal_metrics':mm,
            'coverage':coverage_market[market],
            'failure_modes':failures[market],
            'bootstrap_mean_stressed_r':bm,
            'half_year_stability':{
                'eligible_period_count_n_ge_10':tm['eligible_period_count_n_ge_10'],
                'positive_period_count':tm['positive_period_count'],
                'positive_period_fraction':tm['positive_period_fraction'],
                'periods':tm['periods'],
            },
            'feature_fingerprint':{
                name:{'median':dist['median'],'p25':dist['p25'],'p75':dist['p75']}
                for name,dist in features[market].items()
            },
        }

    regime_profiles={}
    for name,r in sorted(regimes.items()):
        outcome=r['outcome_metrics_label_only']
        stability=r['half_year_stability_label_only']
        regime_profiles[name]={
            'n':r['n'],
            'market_counts':r['market_counts'],
            'side_counts':r['side_counts'],
            'entry_family_counts':r['entry_family_counts'],
            'mean_stressed_r':outcome['mean_stressed_r'],
            'profit_factor_stressed':outcome['profit_factor_stressed'],
            'max_drawdown_stressed_r':outcome['max_drawdown_stressed_r'],
            'positive_half_year_fraction':stability['positive_period_fraction'],
            'feature_profile_pre_entry_only':r['feature_profile_pre_entry_only'],
        }

    payload={
        'schema':'qore.vt31.multi_index_behavior_findings.v1',
        'research_only':True,'opens_new_holdout':False,'selection_prohibited':True,'candidate_status':'NO_R9_NOT_CERTIFIED',
        'market_profiles':market_profiles,
        'cross_index':{
            'pairwise_same_day':p['cross_index']['pairwise_same_day'],
            'breadth_metrics':p['cross_index']['breadth_metrics'],
            'side_consensus_metrics':p['cross_index']['side_consensus_metrics'],
            'day_cohort_count':p['cross_index']['day_cohort_count'],
        },
        'regime_profiles':regime_profiles,
        'structural_observations':{
            'all_market_means_negative':all(D(p['market_metrics'][m]['mean_stressed_r'])<0 for m in MARKETS),
            'all_market_pf_below_one':all(D(p['market_metrics'][m]['profit_factor_stressed'])<1 for m in MARKETS),
            'overall_initial_stop_count':p['failure_modes']['overall'].get('initial_stop',0),
            'overall_protected_stop_count':p['failure_modes']['overall'].get('protected_stop',0),
            'overall_target_count':p['failure_modes']['overall'].get('target',0),
            'regime_count':len(regimes),
        },
        'interpretation_constraints':[
            'relative differences between indices are descriptive and do not authorize selecting or dropping a market',
            'bootstrap and regime outcomes are consumed-evidence diagnostics, not promotion gates',
            'no fresh holdout has been opened',
        ],
    }
    a.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n')

    lines=['# VT-31 Multi-Index Deep Behavior Findings','',
           'Consumed-only descriptive report. It does not select a candidate or authorize live trading.','',
           '## Asset profiles','',
           '| Market | Terminal n | Mean R | PF | Max DD | Streak | Terminalization | Bootstrap positive mean | Positive half-years |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for market in MARKETS:
        x=market_profiles[market]; m=x['terminal_metrics']; c=x['coverage']; b=x['bootstrap_mean_stressed_r']; t=x['half_year_stability']
        lines.append(f"| {market} | {m['n']} | {m['mean_stressed_r']} | {m['profit_factor_stressed']} | {m['max_drawdown_stressed_r']} | {m['max_losing_streak']} | {c['terminalization_fraction']} | {b['positive_mean_fraction']} | {t['positive_period_count']}/{t['eligible_period_count_n_ge_10']} |")
    lines += ['', '## Cross-index synchronization','', json.dumps(payload['cross_index']['pairwise_same_day'],sort_keys=True,indent=2),'',
              '## Unsupervised regimes','']
    for name,r in regime_profiles.items():
        lines.append(f"- {name}: n={r['n']}, mean={r['mean_stressed_r']}R, PF={r['profit_factor_stressed']}, DD={r['max_drawdown_stressed_r']}R, positive-half-year-fraction={r['positive_half_year_fraction']}")
    lines += ['', '## Governance','',
              'All relative differences remain descriptive. No market is selected or removed, no R9 rule is created, and fresh evidence remains sealed.']
    a.markdown.write_text('\n'.join(lines)+'\n')
    print(json.dumps({
        'market_profiles':{m:{
            'coverage':market_profiles[m]['coverage'],
            'bootstrap':market_profiles[m]['bootstrap_mean_stressed_r'],
            'half_year':{k:market_profiles[m]['half_year_stability'][k] for k in ('eligible_period_count_n_ge_10','positive_period_count','positive_period_fraction')},
            'failure_modes':market_profiles[m]['failure_modes'],
            'feature_fingerprint':market_profiles[m]['feature_fingerprint'],
        } for m in MARKETS},
        'cross_index':payload['cross_index'],
        'regimes':{k:{x:v[x] for x in ('n','market_counts','side_counts','mean_stressed_r','profit_factor_stressed','max_drawdown_stressed_r','positive_half_year_fraction')} for k,v in regime_profiles.items()},
    },sort_keys=True))

if __name__=='__main__': main()
