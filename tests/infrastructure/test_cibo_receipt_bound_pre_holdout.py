from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_calibration_freeze_manifest import (
    FrozenToolCalibrationDisposition,
)
from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_gate import (
    CiboPreHoldoutStatus,
)
from qore.infrastructure.cibo_ce2i_provider_economics_component_freeze import (
    PROVIDER_ECONOMICS_COMPONENT_FREEZE_ID,
    CiboProviderEconomicsComponentFreeze,
)
from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
    provider_economics_evidence_ref,
)
from qore.infrastructure.cibo_ce2i_provider_economics_provenance import (
    provider_economics_provenance_sha256,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    bind_cross_boundary_pass_artifact,
)
from qore.infrastructure.cibo_receipt_bound_calibration_freeze import (
    build_receipt_bound_calibration_freeze,
    required_calibration_freeze_receipt_ids,
)
from qore.infrastructure.cibo_receipt_bound_pre_holdout import (
    evaluate_receipt_bound_pre_holdout_readiness,
    required_pre_holdout_receipt_ids,
)

T0 = datetime(2026, 9, 30, 22, 0, tzinfo=UTC)
HEAD = "a" * 40
POLICY = "sha256:" + "b" * 64
FORWARD_SHA = "sha256:" + "c" * 64
PHASE21_SHA = "sha256:" + "d" * 64


def _base(receipt_id: str, *, kind: str, head: str = HEAD) -> dict:
    return {
        "schema": "qore.cibo.pre-holdout-receipt-test.v1",
        "producer_gate_id": f"gate:{receipt_id}",
        "integrated_git_sha": head,
        "policy_identity_sha256": POLICY,
        "observed_at": T0.isoformat(),
        "status": "PASS",
        "failures": [],
        "holdout_outcomes_inspected": False,
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "holdout_mining_used": False,
        "outcome_aware_refit": False,
        "operational_authority_claimed": False,
        "kind_marker": kind,
    }


def _bind(receipt_id: str, kind: str, payload: dict):
    return bind_cross_boundary_pass_artifact(
        receipt_id=receipt_id,
        evidence_kind=kind,
        source_artifact_json=json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )


def _provider_freeze() -> CiboProviderEconomicsComponentFreeze:
    evidence = CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS
    observed_at = datetime.fromisoformat(evidence.observed_at)
    return CiboProviderEconomicsComponentFreeze(
        freeze_id=PROVIDER_ECONOMICS_COMPONENT_FREEZE_ID,
        provider_key=evidence.provider_key,
        environment="demo",
        source_evidence_ref=provider_economics_evidence_ref(),
        source_provenance_sha256=provider_economics_provenance_sha256(),
        source_observed_at=observed_at,
        frozen_at=T0 - timedelta(minutes=1),
        point_in_time_terms_frozen=True,
        spread_terms_frozen=True,
        commission_terms_frozen=True,
        expected_margin_terms_frozen=True,
        volume_contract_terms_frozen=True,
        empirical_slippage_frozen=True,
        execution_model_frozen=True,
        historical_2017_exact_claimed=evidence.historical_exact_claimed,
        holdout_outcomes_used=evidence.holdout_outcomes_used,
        target_aware=evidence.target_aware,
        broker_mutation_performed=evidence.broker_mutation_performed,
        pre_holdout_provider_economics_ready=True,
        blockers=(),
        execution_calibration_sha256="sha256:" + "e" * 64,
        productive_authority=False,
    )


def _calibration_receipts(provider_sha: str, *, head: str = HEAD):
    provider_required = {
        row.tool_code
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
        if row.provider_economics_required
    }
    result = []
    for receipt_id in required_calibration_freeze_receipt_ids():
        if receipt_id == "PHASE20D_FORWARD_MANIFEST":
            kind = "PHASE20D_FORWARD_MANIFEST"
            payload = _base(receipt_id, kind=kind, head=head)
            payload["phase20d_forward_manifest_sha256"] = FORWARD_SHA
        elif receipt_id == "PROVIDER_ECONOMICS_FREEZE":
            kind = "PROVIDER_ECONOMICS_FREEZE"
            payload = _base(receipt_id, kind=kind, head=head)
            payload["provider_economics_freeze_sha256"] = provider_sha
        else:
            kind = "CE2I_TOOL_CALIBRATION"
            payload = _base(receipt_id, kind=kind, head=head)
            disabled = receipt_id in {"T16", "T17"}
            payload.update(
                {
                    "tool_code": receipt_id,
                    "disposition": (
                        FrozenToolCalibrationDisposition.STRUCTURALLY_DISABLED.value
                        if disabled
                        else FrozenToolCalibrationDisposition.CERTIFICATION_READY.value
                    ),
                    "oos_ready": not disabled,
                    "certification_ready": not disabled,
                    "structurally_disabled": disabled,
                    "provider_economics_bound": receipt_id in provider_required,
                }
            )
            if disabled:
                payload["provider_capability_verified"] = True
                payload["structural_disable_reason"] = (
                    "PROVIDER_CAPABILITY_CANONICALLY_UNAVAILABLE"
                )
        result.append(_bind(receipt_id, kind, payload))
    return tuple(result)


def _pre_holdout_receipts(
    *,
    provider_sha: str,
    calibration_sha: str,
    phase21_sealed: bool = True,
):
    result = []
    for receipt_id in required_pre_holdout_receipt_ids():
        kind = receipt_id
        payload = _base(receipt_id, kind=kind)
        if receipt_id == "PHASE20D_CAUSAL_GATE":
            payload["phase20d_causal_gate_passed"] = True
            payload["phase20d_forward_manifest_sha256"] = FORWARD_SHA
        elif receipt_id == "PHASE21_POLICY_FREEZE":
            payload["phase21_policy_freeze_sealed"] = phase21_sealed
            payload["phase21_policy_freeze_sha256"] = PHASE21_SHA
        elif receipt_id == "PROVIDER_ECONOMICS_FREEZE":
            payload["provider_economics_freeze_sha256"] = provider_sha
            payload["pre_holdout_provider_economics_ready"] = True
        elif receipt_id == "CALIBRATION_FREEZE_MANIFEST":
            payload["calibration_freeze_manifest_sha256"] = calibration_sha
            payload["sealed"] = True
        result.append(_bind(receipt_id, kind, payload))
    return tuple(result)


def _valid_inputs():
    provider = _provider_freeze()
    provider_sha = provider.fingerprint()
    calibration_receipts = _calibration_receipts(provider_sha)
    manifest = build_receipt_bound_calibration_freeze(
        receipts=calibration_receipts,
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
    )
    pre_receipts = _pre_holdout_receipts(
        provider_sha=provider_sha,
        calibration_sha=manifest.fingerprint(),
    )
    return provider, calibration_receipts, pre_receipts


def test_receipt_bound_pre_holdout_can_reach_ready_without_reading_holdout() -> None:
    provider, calibration_receipts, pre_receipts = _valid_inputs()

    readiness = evaluate_receipt_bound_pre_holdout_readiness(
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
        receipts=pre_receipts,
        calibration_receipts=calibration_receipts,
        provider_economics_freeze=provider,
    )

    assert readiness.status is CiboPreHoldoutStatus.READY_TO_UNSEAL_2017H1
    assert readiness.blockers == ()
    assert readiness.holdout_outcomes_inspected is False
    assert readiness.holdout_market_data_read is False


def test_phase21_false_cannot_be_laundered_by_pass_envelope() -> None:
    provider, calibration_receipts, _ = _valid_inputs()
    manifest = build_receipt_bound_calibration_freeze(
        receipts=calibration_receipts,
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
    )
    pre_receipts = _pre_holdout_receipts(
        provider_sha=provider.fingerprint(),
        calibration_sha=manifest.fingerprint(),
        phase21_sealed=False,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="Phase21 policy freeze not sealed",
    ):
        evaluate_receipt_bound_pre_holdout_readiness(
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
            receipts=pre_receipts,
            calibration_receipts=calibration_receipts,
            provider_economics_freeze=provider,
        )


def test_provider_fingerprint_mismatch_fails_closed() -> None:
    provider, calibration_receipts, _ = _valid_inputs()
    manifest = build_receipt_bound_calibration_freeze(
        receipts=calibration_receipts,
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
    )
    pre_receipts = _pre_holdout_receipts(
        provider_sha="sha256:" + "f" * 64,
        calibration_sha=manifest.fingerprint(),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="provider freeze binding mismatch",
    ):
        evaluate_receipt_bound_pre_holdout_readiness(
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
            receipts=pre_receipts,
            calibration_receipts=calibration_receipts,
            provider_economics_freeze=provider,
        )


def test_missing_calibration_tool_receipt_fails_before_holdout() -> None:
    provider, calibration_receipts, pre_receipts = _valid_inputs()
    calibration_receipts = tuple(
        item for item in calibration_receipts if item.receipt_id != "T07"
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="required receipts missing",
    ):
        evaluate_receipt_bound_pre_holdout_readiness(
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
            receipts=pre_receipts,
            calibration_receipts=calibration_receipts,
            provider_economics_freeze=provider,
        )
