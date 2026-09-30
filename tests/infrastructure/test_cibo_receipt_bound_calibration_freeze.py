from __future__ import annotations

import json
from datetime import UTC, datetime

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
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    bind_cross_boundary_pass_artifact,
)
from qore.infrastructure.cibo_receipt_bound_calibration_freeze import (
    build_receipt_bound_calibration_freeze,
    required_calibration_freeze_receipt_ids,
)

T0 = datetime(2026, 9, 30, 21, 30, tzinfo=UTC)
HEAD = "a" * 40
POLICY = "sha256:" + "b" * 64
FORWARD_SHA = "sha256:" + "c" * 64
PROVIDER_FREEZE_SHA = "sha256:" + "d" * 64


def _base(
    receipt_id: str,
    *,
    evidence_kind: str,
    head: str = HEAD,
) -> dict:
    return {
        "schema": "qore.cibo.calibration-freeze-test.v1",
        "evidence_binding_id": receipt_id,
        "evidence_kind": evidence_kind,
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
    }


def _receipt(receipt_id: str, *, head: str = HEAD):
    if receipt_id == "PHASE20D_FORWARD_MANIFEST":
        kind = "PHASE20D_FORWARD_MANIFEST"
        payload = _base(receipt_id, evidence_kind=kind, head=head)
        payload["phase20d_forward_manifest_sha256"] = FORWARD_SHA
    elif receipt_id == "PROVIDER_ECONOMICS_FREEZE":
        kind = "PROVIDER_ECONOMICS_FREEZE"
        payload = _base(receipt_id, evidence_kind=kind, head=head)
        payload["provider_economics_freeze_sha256"] = PROVIDER_FREEZE_SHA
    else:
        kind = "CE2I_TOOL_CALIBRATION"
        payload = _base(receipt_id, evidence_kind=kind, head=head)
        provider_required = {
            row.tool_code
            for row in CIBO_T01_T20_CALIBRATION_MATRIX
            if row.provider_economics_required
        }
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
    artifact = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return bind_cross_boundary_pass_artifact(
        receipt_id=receipt_id,
        evidence_kind=kind,
        source_artifact_json=artifact,
    )


def _receipts(*, head: str = HEAD):
    return tuple(
        _receipt(receipt_id, head=head)
        for receipt_id in required_calibration_freeze_receipt_ids()
    )


def test_receipt_bound_calibration_freeze_seals_exact_t01_t20() -> None:
    manifest = build_receipt_bound_calibration_freeze(
        receipts=_receipts(),
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
    )

    assert len(manifest.tools) == 20
    assert manifest.structurally_disabled_tools == ("T16", "T17")
    assert len(manifest.active_certification_ready_tools) == 18
    assert manifest.sealed is True
    assert manifest.phase20d_forward_manifest_sha256 == FORWARD_SHA
    assert manifest.provider_economics_freeze_sha256 == PROVIDER_FREEZE_SHA
    assert manifest.holdout_outcomes_used is False
    assert manifest.holdout_market_data_read is False
    assert manifest.productive_authority is False


def test_missing_tool_receipt_fails_closed() -> None:
    receipts = tuple(
        item for item in _receipts() if item.receipt_id != "T11"
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="required receipts missing",
    ):
        build_receipt_bound_calibration_freeze(
            receipts=receipts,
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )


def test_cross_head_calibration_receipt_fails_closed() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="integrated-head drift",
    ):
        build_receipt_bound_calibration_freeze(
            receipts=_receipts(head="c" * 40),
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )


def test_non_t16_t17_structural_disablement_is_rejected() -> None:
    receipts = list(_receipts())
    index = required_calibration_freeze_receipt_ids().index("T03")
    payload = json.loads(receipts[index].source_artifact_json)
    payload.update(
        {
            "disposition": FrozenToolCalibrationDisposition.STRUCTURALLY_DISABLED.value,
            "oos_ready": False,
            "certification_ready": False,
            "structurally_disabled": True,
            "provider_capability_verified": True,
            "structural_disable_reason": "INVALID_TEST_DISABLEMENT",
        }
    )
    receipts[index] = bind_cross_boundary_pass_artifact(
        receipt_id="T03",
        evidence_kind="CE2I_TOOL_CALIBRATION",
        source_artifact_json=json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="illegal structural disablement",
    ):
        build_receipt_bound_calibration_freeze(
            receipts=tuple(receipts),
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )


def test_t16_structural_disablement_requires_provider_capability_proof() -> None:
    receipts = list(_receipts())
    index = required_calibration_freeze_receipt_ids().index("T16")
    payload = json.loads(receipts[index].source_artifact_json)
    payload["provider_capability_verified"] = False
    receipts[index] = bind_cross_boundary_pass_artifact(
        receipt_id="T16",
        evidence_kind="CE2I_TOOL_CALIBRATION",
        source_artifact_json=json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="structural disablement evidence invalid",
    ):
        build_receipt_bound_calibration_freeze(
            receipts=tuple(receipts),
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )
