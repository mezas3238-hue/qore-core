#!/usr/bin/env python3
"""VT31 native G3 coordinator versus original G3/G3 adapter, REAL M1 parity.

Two independent chronological passes over the SAME immutable NAS100 source.
Neither pass consumes the sealed coverage ledger until BOTH have finished.
No orders, sizing, PnL or certification; native profile is research opt-in.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.vt31_ict_cleanroom_cog_real_3y_fast_v1 import _stream
from scripts.vt31_trisession_online_real_g3_cog_20261015 import (
    adjudicate_posthoc,
    replay_online_g3,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    hash_file,
)

PREREG = "09b285911087374282dd9b9d29e598b1821f589d"
REFERENCE_CASEBOOK_SHA = (
    "cae03ff5faaaebabef4c6f4eed736d802061bfc8598f311fb4a0e27129591de1"
)
MODEL = "VT31_M7A_NATIVE_G3_THREE_SESSION_COG_OPS_PARITY_NOT_CERTIFIED"


def compare_native_vs_reference(
    *, market: Path, coverage_ledger: Path,
) -> dict[str, Any]:
    if hash_file(market) != MARKET_SHA:
        raise ValueError("VT31_NATIVE_REAL_M1_SOURCE_SHA_MISMATCH")
    reference_witness, reference_runtime = replay_online_g3(
        _stream(market), expected_m1=M1_TOTAL,
    )
    native_witness, native_runtime = replay_online_g3(
        _stream(market), expected_m1=M1_TOTAL, native_trader_g3=True,
    )
    # Strictly post hoc. A future-known 60M1 coverage bit cannot
    # influence the native pre-COG gating in either pass.
    ledger = json.loads(coverage_ledger.read_text(encoding="utf-8"))
    reference = adjudicate_posthoc(reference_witness, ledger, reference_runtime)
    native = adjudicate_posthoc(native_witness, ledger, native_runtime)
    left = reference["full_2325_day_session_G3_casebook_sha256"]
    right = native["full_2325_day_session_G3_casebook_sha256"]
    if left != REFERENCE_CASEBOOK_SHA or right != REFERENCE_CASEBOOK_SHA:
        raise AssertionError(
            "NATIVE_G3_INTEGRATION_FULL_CASEBOOK_SHA_DIVERGED:"
            f"reference={left}:native={right}"
        )
    if (
        reference["full_2325_day_session_G3_casebook"]
        != native["full_2325_day_session_G3_casebook"]
        or reference["three_sessions_online_causal_G3_diagnostics"]
        != native["three_sessions_online_causal_G3_diagnostics"]
    ):
        raise AssertionError("NATIVE_G3_CASEBOOK_OR_DIAGNOSTICS_NOT_IDENTICAL")
    if (
        native_runtime["one_trader"] != "VT31"
        or native_runtime["source_bars_consumed"] != M1_TOTAL
        or not native_runtime["native_VT31Trader_G3_integration_complete"]
        or native_runtime["M7_blocker_native_coordinator_still_defaults_OPS_to_LEGACY"]
        or native_runtime["original_ops_G3_research_windows"] <= 0
    ):
        raise AssertionError("NATIVE_G3_NOT_ACTUALLY_INSTANTIATED_AND_CONNECTED")

    summary = native["three_sessions_online_causal_G3_diagnostics"]
    if set(summary) != {"VT31_LONDON", "VT31_NY_AM", "VT31_NY_PM"}:
        raise AssertionError("NATIVE_G3_NOT_THREE_SESSIONS")
    if summary["VT31_NY_AM"]["online_H1_veto_days"] != 2:
        raise AssertionError("TTRADES_NYAM_SOURCE_H1_WAIT_INVARIANT_CHANGED")
    if any(s["anchor_days"] != 775 for s in summary.values()):
        raise AssertionError("TRISESSION_COHORT_DRIFT")
    return {
        "model": MODEL,
        "preregistered_commit_before_code": PREREG,
        "source_hash": MARKET_SHA,
        "M1_exact_closed_bars": M1_TOTAL,
        "three_session_causal_casebook_exact_parity": True,
        "full_casebook_json_sha256": right,
        "original_reference_json_sha256": left,
        "native_VT31Trader_G3_research_optin_connected": True,
        "native_VT31Trader_one_original_G3_COG": True,
        "original_G3_OPS_real_instances": (
            native_runtime["original_ops_G3_research_windows"]
        ),
        "original_reference_research_OPS_real_instances": (
            reference_runtime["original_ops_G3_research_windows"]
        ),
        "session_G3_diagnostics_not_trades": summary,
        "native_framework_contract_engineering": "PASS_RESEARCH_ONLY",
        "native_source_M0_method_profile_signed": False,
        "native_M2_ICT_TTRADES_doctrine_certified": False,
        "native_M3_author_displacement_certified": False,
        "native_M4_four_entry_families_certified": False,
        "native_M5_causative_swing_certified": False,
        "two_independent_human_reviews_M6": False,
        "M7_integrated_full_3_sessions_certified": False,
        "london_certified": False,
        "ny_am_certified": False,
        "ny_pm_certified": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "VT31_trader_certified": False,
        "orders": 0,
        "broker_fills": 0,
        "sizing": 0,
        "live_demo_vps_authorized": False,
        "PnL_PF_DD_Sortino": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--coverage-ledger", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = compare_native_vs_reference(
        market=args.market, coverage_ledger=args.coverage_ledger,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "M1": report["M1_exact_closed_bars"],
        "casebook": report["full_casebook_json_sha256"],
        "session_diagnostics": report["session_G3_diagnostics_not_trades"],
        "native_research_connected": True,
        "trader_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
