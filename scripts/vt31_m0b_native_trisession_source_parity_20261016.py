#!/usr/bin/env python3
"""All 3 Silver Bullet windows: strict native source gate vs sealed G3 reference.

No lookahead: independent REAL M1 chronological replays finish BEFORE
reading the prior independent source coverage ledger. Zero orders/sizing.
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

PREREG = "db60ccdc949bd04250680face8c27d5455b3555d"
CASEBOOK = "cae03ff5faaaebabef4c6f4eed736d802061bfc8598f311fb4a0e27129591de1"
VERSION = "VT31_M0B_NATIVE_PRECOG_TRISESSION_M1_ONLY_NOT_CERTIFIED"


def compare_native_strict_source(*, market: Path, coverage: Path) -> dict[str, Any]:
    if hash_file(market) != MARKET_SHA:
        raise ValueError("M0B_ORIGINAL_NAS100_M1_SHA_MISMATCH")
    baseline_traces, baseline_runtime = replay_online_g3(
        _stream(market), expected_m1=M1_TOTAL,
    )
    strict_traces, strict_runtime = replay_online_g3(
        _stream(market),
        expected_m1=M1_TOTAL,
        native_trader_g3=True,
        native_strict_source_admission=True,
    )
    # Entire market has ALREADY BEEN consumed twice at this point.
    # No post hoc 60-M1 knowledge is available to pre-COG source gates.
    ledger = json.loads(coverage.read_text(encoding="utf-8"))
    baseline = adjudicate_posthoc(baseline_traces, ledger, baseline_runtime)
    strict = adjudicate_posthoc(strict_traces, ledger, strict_runtime)
    before = baseline["full_2325_day_session_G3_casebook_sha256"]
    after = strict["full_2325_day_session_G3_casebook_sha256"]
    if before != CASEBOOK or after != CASEBOOK:
        raise AssertionError(
            "M0B_NATIVE_STRICT_PRECOG_FULL_CASEBOOK_DIVERGED:"
            f"reference={before}:native={after}"
        )
    if (
        baseline["full_2325_day_session_G3_casebook"]
        != strict["full_2325_day_session_G3_casebook"]
        or baseline["three_sessions_online_causal_G3_diagnostics"]
        != strict["three_sessions_online_causal_G3_diagnostics"]
    ):
        raise AssertionError("M0B_STRICT_GATE_CASEBOOK_NOT_EXACTLY_EQUAL")
    if not strict_runtime["native_strict_preCOG_M0_source_admission"]:
        raise AssertionError("M0B_STRICT_NATIVE_SOURCE_GATE_NOT_EXECUTED")
    if not strict_runtime["native_VT31Trader_G3_integration_complete"]:
        raise AssertionError("M0B_ORIGINAL_NATIVE_G3_TRADER_NOT_USED")
    if strict_runtime["source_bars_consumed"] != M1_TOTAL:
        raise AssertionError("M0B_ORIGINAL_M1_BARS_DRIFT")
    by_session = strict["three_sessions_online_causal_G3_diagnostics"]
    if set(by_session) != {
        "VT31_LONDON", "VT31_NY_AM", "VT31_NY_PM",
    } or any(v["anchor_days"] != 775 for v in by_session.values()):
        raise AssertionError("M0B_THREE_SESSION_HISTORIC_COHORT_DRIFT")
    if by_session["VT31_NY_AM"]["online_H1_veto_days"] != 2:
        raise AssertionError("M0B_TTRADES_INCOMPLETE_H1_NYAM_VETO_DRIFT")
    if any(
        by_session[s]["online_H1_veto_days"] != 0
        for s in ("VT31_LONDON", "VT31_NY_PM")
    ):
        raise AssertionError("M0B_TTRADES_H1_LEAK_TO_ICT_GENERAL")
    return {
        "version": VERSION,
        "preregistered_before_code_commit": PREREG,
        "canonical_market_sha256": MARKET_SHA,
        "canonical_real_M1": M1_TOTAL,
        "NY_days_per_session": 775,
        "day_session_records": 2325,
        "reference_casebook_sha256": before,
        "native_source_gate_casebook_sha256": after,
        "full_2325_json_casebook_exact_parity": True,
        "reference_G3_research_adapter": True,
        "native_VT31Trader_strict_preCOG_gate_engineering": "PASS_RESEARCH_ONLY",
        "native_G3_COG_original": True,
        "native_G3_OPS_original": True,
        "independent_prior_coverage_ledger_loaded_only_posthoc": True,
        "session_cognition_observations_not_trades": by_session,
        "london_ICT_general_09H_gate": False,
        "ny_am_TTrades_09H_gate": True,
        "ny_pm_ICT_general_09H_gate": False,
        "source_profile_owner_approved": False,
        "M2_author_liquidity_doctrine_certified": False,
        "M3_author_displacement_certified": False,
        "M4_four_source_entry_families_certified": False,
        "M5_protected_swing_certified": False,
        "M6_two_independent_human_signatures": False,
        "M7_three_sessions_integrated_method_certified": False,
        "london_certified": False,
        "ny_am_certified": False,
        "ny_pm_certified": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "trader_certified": False,
        "broker_orders": 0,
        "broker_fills": 0,
        "sizing": 0,
        "PnL_PF_DD_Sortino": None,
        "demo_live_vps_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--market", type=Path, required=True)
    p.add_argument("--coverage-ledger", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = compare_native_strict_source(
        market=args.market, coverage=args.coverage_ledger,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "casebook": report["native_source_gate_casebook_sha256"],
        "M1": report["canonical_real_M1"],
        "sessions": report["session_cognition_observations_not_trades"],
        "native_gate": report["native_VT31Trader_strict_preCOG_gate_engineering"],
        "trader_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
