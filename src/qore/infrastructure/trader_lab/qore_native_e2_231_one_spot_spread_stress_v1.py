"""Posthoc ONE screenshot spot-spread stress for frozen 231 gross E2 cells.

This is not an execution backtest: screenshot date, timezone, broker account,
index aliases, fees and historical spreads NOT VERIFIED. No new original M5 read.
Never compute 'net' performance or certified traders from this stress.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_e2_posthoc_bh_sensitivity_v1 as source_e2
from qore.infrastructure.trader_lab import qore_native_g1_screenshot_bidask_spot_audit_v1 as quote
from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as g0
from qore.infrastructure.trader_lab import qore_native_e2_33x7_holm_synchronized_weeks_v1 as parent

IDENTITY="QORE_NATIVE_E2_ONE_SCREENSHOT_SPREAD_STRESS_231_POSTHOC_V1"
NOT_EXECUTABLE="SPOT_QUOTE_NOT_HISTORICAL_E2_ENTRY_EXIT_CONTRACT"
BLOCKED={"GBPUSD","NAS100","SP500"}

def stress(e2:dict[str,Any], screenshot:dict[str,Any])->dict[str,Any]:
    source_e2.analyze(e2) # verifies source exact 231 signatures/inference and no net
    spots=quote.spread_stats(screenshot)
    spreads={row["canonical_symbol"]:row for row in spots["rows"]}
    periods=("development","temporal_diagnostic")
    joined=[]
    for cell_id in parent.CELLS:
        method,symbol=cell_id.split("__",1)
        base={"cell_id":cell_id,"method_id":method,"symbol":symbol}
        s=spreads[symbol]
        excluded=symbol in BLOCKED
        base.update({
            "bidask_screenshot_spread_bps_not_hist":s["spread_bps_approx"],
            "snapshot_source_quote_quality":s["quality_gate"],
            "broker_contract_compatible_with_historical_E2":False,
            "spot_cost_comparison_descriptive_only":not excluded,
            "historical_net_performance_measured":False,
            "screen_usable_as_trade_authorization":False,
        })
        for period in periods:
            original=next(x for x in e2[period]["cells"] if x["cell_id"]==cell_id)
            gross=original["gross_mean_bps"]
            baseline=original["control_gross_mean_bps"]
            delta=original["paired_delta_mean_bps"]
            if not original["net_broker_certification"] is False:
                raise ValueError("original E2 net data is not certified")
            base[period]={
                "historic_gross_reference_bps":gross,
                "historic_control_gross_reference_bps":baseline,
                "historic_paired_delta_bps_UNCHANGED":delta,
                "one_spot_spread_subtracted_from_gross_NOT_NET_bps":
                    (round(gross-s["spread_bps_approx"],6)
                     if not excluded and gross is not None else None),
                "gross_above_one_spot_spread_boolean_not_significance":
                    (gross > s["spread_bps_approx"]
                     if not excluded and gross is not None else None),
                "screenshot_quote_not_time_aligned":True,
            }
        base["above_one_spot_spread_in_both_periods_NOT_EDGE"]= (
            all(base[period]["gross_above_one_spot_spread_boolean_not_significance"]
                is True for period in periods) if not excluded else None
        )
        joined.append(base)
    if len(joined)!=231:
        raise ValueError("all 231 cannot be omitted when all 33 screenshot quotes provided")
    counts={
        "total":231,
        "blocked_contract_or_zero_spread_cells":sum(x["symbol"] in BLOCKED for x in joined),
        "eligible_only_for_nonhistorical_spot_comparison":sum(x["spot_cost_comparison_descriptive_only"] for x in joined),
        "dev_above_current_spot_spread":sum(x["development"]["gross_above_one_spot_spread_boolean_not_significance"] is True for x in joined),
        "diag_above_current_spot_spread":sum(x["temporal_diagnostic"]["gross_above_one_spot_spread_boolean_not_significance"] is True for x in joined),
        "both_above_current_spot_spread":sum(x["above_one_spot_spread_in_both_periods_NOT_EDGE"] is True for x in joined),
    }
    if counts["blocked_contract_or_zero_spread_cells"] != 21 or counts["eligible_only_for_nonhistorical_spot_comparison"] != 210:
        raise ValueError("zero spread + two unverified indices must never be promoted")
    return {
        "identity":IDENTITY,
        "status":"POSTHOC_ONE_SPOT_FRICTION_ILLUSTRATION_ONLY_NO_HISTORICAL_NET",
        "study_e2_parent_run":source_e2.PARENT_RUN,
        "study_e2_original_sha256":source_e2.PARENT_JSON_SHA256,
        "history_based_spread_calibration":False,
        "commission_slippage_swap_financing_latency_included":False,
        "screenshot_broker_equivalence_proven":False,
        "screenshot_quote_calendar_date_verified":False,
        "broker_tick_data_historical_time_alignment":False,
        "new_price_data_downloaded":False,
        "net_trade_or_live_approved":False,
        "real_net_PF_sharpe_sortino_DD_measured":False,
        "G1_certified":False,
        "traders_certified":0,
        "production_untouched":True,
        "WARNING":NOT_EXECUTABLE,
        "counts":counts,
        "rows":joined,
    }

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("original_e2_signed_artifact",type=Path)
    p.add_argument("user_quote_33_transcription",type=Path)
    p.add_argument("out_dir",type=Path)
    args=p.parse_args()
    r=stress(
        source_e2.load_signed(args.original_e2_signed_artifact),
        json.loads(args.user_quote_33_transcription.read_text(encoding="utf-8")),
    )
    args.out_dir.mkdir(parents=True,exist_ok=True)
    out=args.out_dir/"qore-native-e2-231-single-spread-spot-screen-NOT-NET.json"
    out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    out.with_name(out.name+".sha256").write_text(
        g0.sha256(out)+f"  {out.name}\n",encoding="utf-8",
    )
    print(json.dumps({
        "identity":r["identity"],
        "counts":r["counts"],
        "signed_e2_json_sha":r["study_e2_original_sha256"],
        "G1_certified":False,
        "traders_certified":0,
        "posthoc_single_spread_not_historical_cost":True,
    },sort_keys=True))

if __name__=="__main__":
    main()
