from __future__ import annotations

import json
import subprocess
import sys

import scripts.vt31_nas100_r5_certification_candidate as candidate


def test_vt31_nas100_r5_contract_is_frozen_exactly() -> None:
    payload = candidate.contract_payload()
    assert payload["candidate_id"] == "VT31_NAS100_R5"
    assert payload["base_variant"] == "WAIT_1025_B060"
    assert payload["global_risk_scalar"] == "0.60"
    assert payload["rearm"]["activity_profile"]["name"] == "ACTIVITY_L"
    assert payload["rearm"]["management"] == "SCORE_PROTECT"
    assert payload["candidate_frozen"] is True
    assert payload["live_authorized"] is False
    assert payload["real_capital_authorized"] is False
    assert payload["production_authorized"] is False


def test_vt31_nas100_r5_final_holdout_is_two_year_unseen_window() -> None:
    payload = candidate.contract_payload()
    holdout = payload["final_holdout"]
    assert holdout["id"] == "VT31_NAS100_R5_FINAL_HOLDOUT_001"
    assert holdout["start_at"] == "2022-07-18T00:00:00+00:00"
    assert holdout["end_exclusive"] == "2024-07-18T00:00:00+00:00"
    assert holdout["calendar_span"] == "2Y"
    assert holdout["canonical_m1_minimum_coverage_days"] == 730
    assert holdout["selected_before_open"] is True
    assert holdout["retuning_after_open_on_same_interval"] is False
    assert holdout["all_annual_blocks_must_be_positive"] is True


def test_vt31_nas100_r5_self_test_emits_stable_fingerprint() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/vt31_nas100_r5_certification_candidate.py",
            "--self-test",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["candidate_id"] == "VT31_NAS100_R5"
    assert len(payload["contract_fingerprint"]) == 64
    assert payload["reference_variant"] == (
        "REARM_ADAPTIVE_ACTIVITY_L_SCORE_PROTECT_RISK_SCALAR_060"
    )
