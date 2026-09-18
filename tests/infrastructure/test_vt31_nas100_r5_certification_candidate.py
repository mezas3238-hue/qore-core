from __future__ import annotations

import json
import subprocess
import sys


def _self_test() -> dict[str, object]:
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
    return json.loads(completed.stdout)


def test_vt31_nas100_r5_contract_is_frozen_exactly() -> None:
    payload = _self_test()
    assert payload["candidate_id"] == "VT31_NAS100_R5"
    assert payload["base_variant"] == "WAIT_1025_B060"
    assert payload["activity_profile"] == "ACTIVITY_L"
    assert payload["rearm_management"] == "SCORE_PROTECT"
    assert payload["global_risk_scalar"] == "0.60"
    assert payload["reference_variant"] == (
        "REARM_ADAPTIVE_ACTIVITY_L_SCORE_PROTECT_RISK_SCALAR_060"
    )


def test_vt31_nas100_r5_final_holdout_is_two_year_unseen_window() -> None:
    payload = _self_test()
    assert payload["final_holdout_id"] == (
        "VT31_NAS100_R5_FINAL_HOLDOUT_001"
    )
    assert payload["final_holdout_start"] == (
        "2022-07-18T00:00:00+00:00"
    )
    assert payload["final_holdout_end_exclusive"] == (
        "2024-07-18T00:00:00+00:00"
    )


def test_vt31_nas100_r5_self_test_emits_stable_fingerprint() -> None:
    payload = _self_test()
    assert len(str(payload["contract_fingerprint"])) == 64
