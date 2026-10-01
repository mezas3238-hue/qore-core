from __future__ import annotations

import importlib.util
import json
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure import cibo_arch_a_internal_readiness as gate
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam_provider_truth_control import (
    build_e4_provider_truth_control,
)

_FIXTURE_PATH = Path(__file__).with_name("test_cibo_ce2i_final_certification.py")
_SPEC = importlib.util.spec_from_file_location("_provider_truth_fixture", _FIXTURE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)

_INTAKE_FIXTURE_PATH = Path(__file__).with_name(
    "test_cibo_arch_a_internal_readiness_gate.py"
)
_INTAKE_SPEC = importlib.util.spec_from_file_location(
    "_provider_truth_intake_fixture",
    _INTAKE_FIXTURE_PATH,
)
assert _INTAKE_SPEC is not None and _INTAKE_SPEC.loader is not None
_INTAKE_FIXTURE = importlib.util.module_from_spec(_INTAKE_SPEC)
_INTAKE_SPEC.loader.exec_module(_INTAKE_FIXTURE)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _artifact(*, ready: bool = True) -> str:
    payload = {
        "calibration_id": "CIBO_CTRADER_DEMO_FORWARD_EXECUTION_CALIBRATION_V1",
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "manifest_sha256": _sha("manifest"),
        "manifest_candidate_rows": 200,
        "manifest_complete_lineage_rows": 190,
        "frozen_at": "2026-10-01T18:00:00+00:00",
        "total_observations": 190,
        "observations": [{"i": index} for index in range(190)],
        "symbol_summaries": [{"qore_symbol": "X", "observation_count": 190}],
        "manifest_scientifically_ready": ready,
        "all_complete_rows_reconciled": ready,
        "required_symbol_coverage_met": ready,
        "minimum_symbol_observations_met": ready,
        "empirical_slippage_calibrated": ready,
        "execution_model_ready": ready,
        "historical_2017_exact_claimed": False,
        "holdout_outcomes_used": False,
        "target_aware": False,
        "productive_authority": False,
        "blockers": [] if ready else ["EMPIRICAL_EXECUTION_CALIBRATION_REQUIRED"],
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    payload["calibration_sha256"] = "sha256:" + sha256(raw).hexdigest()
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _chain(artifact: str):
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    payload = _INTAKE_FIXTURE._phase22_v2_manifest_payload()
    refs = dict(payload["receipts"])
    refs["provider_economics_sha256"] = (
        "sha256:" + sha256(artifact.encode("utf-8")).hexdigest()
    )
    payload["receipts"] = refs
    unsigned = dict(payload)
    unsigned.pop("manifest_sha256")
    payload["manifest_sha256"] = gate.forward_manifest_payload_sha256(unsigned)
    intake = gate.evaluate_architect_a_phase22_v2_scientific_intake(payload)
    return phase22, intake


def test_e4_provider_truth_accepts_ready_empirical_calibration() -> None:
    artifact = _artifact()
    phase22, intake = _chain(artifact)
    receipt = build_e4_provider_truth_control(
        integrated_git_sha="a" * 40,
        phase22_receipt=phase22,
        intake=intake,
        provider_calibration_artifact_json=artifact,
        observed_at=phase22.qualified_at + timedelta(minutes=1),
    )
    assert receipt.receipt_id == "E4_PROVIDER_TRUTH"
    assert receipt.producer_gate_id == "CIBO_ARCH_A_E4_PROVIDER_TRUTH_V1"


def test_e4_provider_truth_rejects_not_ready_calibration() -> None:
    artifact = _artifact(ready=False)
    phase22, intake = _chain(artifact)
    with pytest.raises(
        CiboCapitalManagementError,
        match="required provider gate failed",
    ):
        build_e4_provider_truth_control(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            intake=intake,
            provider_calibration_artifact_json=artifact,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )


def test_e4_provider_truth_rejects_artifact_digest_drift() -> None:
    artifact = _artifact()
    phase22, intake = _chain(artifact)
    with pytest.raises(
        CiboCapitalManagementError,
        match="artifact digest drift",
    ):
        build_e4_provider_truth_control(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            intake=intake,
            provider_calibration_artifact_json=artifact + " ",
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )
