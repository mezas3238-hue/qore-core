from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

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
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_gate import (
    CiboPreHoldoutStatus,
)
from qore.infrastructure.cibo_ce2i_provider_economics_component_freeze import (
    freeze_current_ctrader_demo_provider_economics,
)
from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
    calibrate_ctrader_demo_forward_execution,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    bind_cross_boundary_pass_artifact,
)
from qore.infrastructure.cibo_instrument_capability_registry import (
    CapabilityStatus,
    ProviderInstrumentCapabilityRegistry,
)
from qore.infrastructure.cibo_receipt_bound_calibration_freeze import (
    build_receipt_bound_calibration_freeze,
    required_calibration_freeze_receipt_ids,
)
from qore.infrastructure.cibo_receipt_bound_pre_holdout import (
    evaluate_receipt_bound_pre_holdout_readiness,
    required_pre_holdout_receipt_ids,
)

FREEZE_AT = datetime(2026, 10, 1, 1, 0, tzinfo=UTC)
HEAD = "a" * 40
POLICY = FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
PHASE21_SHA = "sha256:" + "d" * 64

_PROVIDER_TEST = Path(__file__).with_name(
    "test_cibo_ce2i_provider_execution_calibration.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "_cibo_provider_execution_fixture",
    _PROVIDER_TEST,
)
assert _SPEC is not None and _SPEC.loader is not None
_PROVIDER_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PROVIDER_FIXTURE)

_CALIBRATION_TEST = Path(__file__).with_name(
    "test_cibo_receipt_bound_calibration_freeze.py"
)
_CALIBRATION_SPEC = importlib.util.spec_from_file_location(
    "_cibo_calibration_freeze_fixture",
    _CALIBRATION_TEST,
)
assert _CALIBRATION_SPEC is not None and _CALIBRATION_SPEC.loader is not None
_CALIBRATION_FIXTURE = importlib.util.module_from_spec(_CALIBRATION_SPEC)
_CALIBRATION_SPEC.loader.exec_module(_CALIBRATION_FIXTURE)


def _base(receipt_id: str, *, kind: str, head: str = HEAD) -> dict:
    return {
        "schema": "qore.cibo.pre-holdout-receipt-test.v1",
        "evidence_binding_id": receipt_id,
        "evidence_kind": kind,
        "producer_gate_id": f"gate:{receipt_id}",
        "integrated_git_sha": head,
        "policy_identity_sha256": POLICY,
        "observed_at": FREEZE_AT.isoformat(),
        "status": "PASS",
        "failures": [],
        "holdout_outcomes_inspected": False,
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "holdout_mining_used": False,
        "outcome_aware_refit": False,
        "operational_authority_claimed": False,
    }


def _bind(receipt_id: str, kind: str, payload: dict):
    return bind_cross_boundary_pass_artifact(
        receipt_id=receipt_id,
        evidence_kind=kind,
        source_artifact_json=json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )


def _forward_inputs():
    return _PROVIDER_FIXTURE._population()


def _provider_state():
    manifest, risks = _forward_inputs()
    calibration = calibrate_ctrader_demo_forward_execution(
        manifest=manifest,
        executed_risk_book=risks,
        frozen_at=FREEZE_AT,
    )
    provider = freeze_current_ctrader_demo_provider_economics(
        frozen_at=FREEZE_AT,
        execution_calibration=calibration,
    )
    assert calibration.execution_model_ready is True
    assert provider.pre_holdout_provider_economics_ready is True
    return manifest, risks, calibration, provider


def _calibration_receipts(
    *,
    forward_sha: str,
    provider_sha: str,
    provider_capability_registry,
    head: str = HEAD,
):
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
            payload["phase20d_forward_manifest_sha256"] = forward_sha
            payload["provider_capability_registry_sha256"] = (
                provider_capability_registry.fingerprint()
            )
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
                payload["provider_capability_registry_sha256"] = (
                    provider_capability_registry.fingerprint()
                )
                payload["structural_disable_reason"] = (
                    "PROVIDER_CAPABILITY_CANONICALLY_UNAVAILABLE"
                )
        result.append(_bind(receipt_id, kind, payload))
    return tuple(result)


def _pre_holdout_receipts(
    *,
    forward_sha: str,
    provider_sha: str,
    execution_calibration_sha: str,
    calibration_sha: str,
    phase21_sealed: bool = True,
):
    result = []
    for receipt_id in required_pre_holdout_receipt_ids():
        kind = receipt_id
        payload = _base(receipt_id, kind=kind)
        if receipt_id == "PHASE20D_CAUSAL_GATE":
            payload["phase20d_causal_gate_passed"] = True
            payload["phase20d_forward_manifest_sha256"] = forward_sha
        elif receipt_id == "PHASE21_POLICY_FREEZE":
            payload["phase21_policy_freeze_sealed"] = phase21_sealed
            payload["phase21_policy_freeze_sha256"] = PHASE21_SHA
        elif receipt_id == "PROVIDER_ECONOMICS_FREEZE":
            payload["provider_economics_freeze_sha256"] = provider_sha
            payload["execution_calibration_sha256"] = execution_calibration_sha
            payload["pre_holdout_provider_economics_ready"] = True
        elif receipt_id == "CALIBRATION_FREEZE_MANIFEST":
            payload["calibration_freeze_manifest_sha256"] = calibration_sha
            payload["sealed"] = True
        result.append(_bind(receipt_id, kind, payload))
    return tuple(result)


def _valid_inputs(*, provider_capability_registry=None):
    manifest, risks, calibration, provider = _provider_state()
    registry = (
        _CALIBRATION_FIXTURE._registry()
        if provider_capability_registry is None
        else provider_capability_registry
    )
    forward_sha = manifest.fingerprint()
    provider_sha = provider.fingerprint()
    calibration_receipts = _calibration_receipts(
        forward_sha=forward_sha,
        provider_sha=provider_sha,
        provider_capability_registry=registry,
    )
    freeze = build_receipt_bound_calibration_freeze(
        receipts=calibration_receipts,
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
        provider_capability_registry=registry,
        capability_at=registry.captured_at,
    )
    pre_receipts = _pre_holdout_receipts(
        forward_sha=forward_sha,
        provider_sha=provider_sha,
        execution_calibration_sha=calibration.fingerprint(),
        calibration_sha=freeze.fingerprint(),
    )
    return manifest, risks, registry, calibration_receipts, pre_receipts


def test_receipt_bound_pre_holdout_can_reach_ready_without_reading_holdout() -> None:
    manifest, risks, registry, calibration_receipts, pre_receipts = _valid_inputs()

    readiness = evaluate_receipt_bound_pre_holdout_readiness(
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
        receipts=pre_receipts,
        calibration_receipts=calibration_receipts,
        forward_manifest=manifest,
        executed_risk_book=risks,
        provider_capability_registry=registry,
    )

    assert readiness.status is CiboPreHoldoutStatus.READY_TO_UNSEAL_2017H1
    assert readiness.blockers == ()
    assert readiness.holdout_outcomes_inspected is False
    assert readiness.holdout_market_data_read is False


def test_phase21_false_cannot_be_laundered_by_pass_envelope() -> None:
    manifest, risks, registry, calibration_receipts, _ = _valid_inputs()
    calibration = calibrate_ctrader_demo_forward_execution(
        manifest=manifest,
        executed_risk_book=risks,
        frozen_at=FREEZE_AT,
    )
    provider = freeze_current_ctrader_demo_provider_economics(
        frozen_at=FREEZE_AT,
        execution_calibration=calibration,
    )
    freeze = build_receipt_bound_calibration_freeze(
        receipts=calibration_receipts,
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
        provider_capability_registry=registry,
        capability_at=registry.captured_at,
    )
    pre_receipts = _pre_holdout_receipts(
        forward_sha=manifest.fingerprint(),
        provider_sha=provider.fingerprint(),
        execution_calibration_sha=calibration.fingerprint(),
        calibration_sha=freeze.fingerprint(),
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
            forward_manifest=manifest,
            executed_risk_book=risks,
            provider_capability_registry=registry,
        )


def test_provider_fingerprint_mismatch_fails_closed() -> None:
    manifest, risks, registry, calibration_receipts, _ = _valid_inputs()
    calibration = calibrate_ctrader_demo_forward_execution(
        manifest=manifest,
        executed_risk_book=risks,
        frozen_at=FREEZE_AT,
    )
    freeze = build_receipt_bound_calibration_freeze(
        receipts=calibration_receipts,
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
        provider_capability_registry=registry,
        capability_at=registry.captured_at,
    )
    pre_receipts = _pre_holdout_receipts(
        forward_sha=manifest.fingerprint(),
        provider_sha="sha256:" + "f" * 64,
        execution_calibration_sha=calibration.fingerprint(),
        calibration_sha=freeze.fingerprint(),
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
            forward_manifest=manifest,
            executed_risk_book=risks,
            provider_capability_registry=registry,
        )


def test_missing_calibration_tool_receipt_fails_before_holdout() -> None:
    manifest, risks, registry, calibration_receipts, pre_receipts = _valid_inputs()
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
            forward_manifest=manifest,
            executed_risk_book=risks,
            provider_capability_registry=registry,
        )


def test_unknown_t16_capability_blocks_pre_holdout() -> None:
    registry = _CALIBRATION_FIXTURE._registry(
        hedge=CapabilityStatus.UNKNOWN,
    )
    manifest, _risks, _calibration, provider = _provider_state()
    calibration_receipts = _calibration_receipts(
        forward_sha=manifest.fingerprint(),
        provider_sha=provider.fingerprint(),
        provider_capability_registry=registry,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="T16 structural disablement requires provider-verified HEDGE UNAVAILABLE",
    ):
        build_receipt_bound_calibration_freeze(
            receipts=calibration_receipts,
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
            provider_capability_registry=registry,
            capability_at=registry.captured_at,
        )


def test_capability_registry_from_another_account_is_rejected() -> None:
    base_registry = _CALIBRATION_FIXTURE._registry()
    other_identity = replace(
        base_registry.account_identity,
        account_ref="different-account",
    )
    other_registry = ProviderInstrumentCapabilityRegistry(
        account_identity=other_identity,
        entries=tuple(
            replace(item, account_identity=other_identity)
            for item in base_registry.entries
        ),
        captured_at=base_registry.captured_at,
    )
    manifest, risks, calibration, provider = _provider_state()
    calibration_receipts = _calibration_receipts(
        forward_sha=manifest.fingerprint(),
        provider_sha=provider.fingerprint(),
        provider_capability_registry=other_registry,
    )
    freeze = build_receipt_bound_calibration_freeze(
        receipts=calibration_receipts,
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
        provider_capability_registry=other_registry,
        capability_at=other_registry.captured_at,
    )
    pre_receipts = _pre_holdout_receipts(
        forward_sha=manifest.fingerprint(),
        provider_sha=provider.fingerprint(),
        execution_calibration_sha=calibration.fingerprint(),
        calibration_sha=freeze.fingerprint(),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="capability registry account/provider scope mismatch",
    ):
        evaluate_receipt_bound_pre_holdout_readiness(
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
            receipts=pre_receipts,
            calibration_receipts=calibration_receipts,
            forward_manifest=manifest,
            executed_risk_book=risks,
            provider_capability_registry=other_registry,
        )
