from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
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
from qore.infrastructure.cibo_instrument_capability_registry import (
    CapabilityStatus,
    InstrumentCapability,
    ProviderCapabilityEvidence,
    ProviderInstrumentCapabilityRegistry,
)
from qore.infrastructure.cibo_receipt_bound_calibration_freeze import (
    build_receipt_bound_calibration_freeze,
    required_calibration_freeze_receipt_ids,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

T0 = datetime(2026, 9, 30, 21, 30, tzinfo=UTC)
HEAD = "a" * 40
POLICY = "sha256:" + "b" * 64
FORWARD_SHA = "sha256:" + "c" * 64
PROVIDER_FREEZE_SHA = "sha256:" + "d" * 64


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="12345",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _capability_entry(
    *,
    capability: InstrumentCapability,
    status: CapabilityStatus,
    index: int,
) -> ProviderCapabilityEvidence:
    provider_verified = status is not CapabilityStatus.UNKNOWN
    return ProviderCapabilityEvidence(
        evidence_id=f"capability-{capability.value.lower()}",
        account_identity=_identity(),
        capability=capability,
        status=status,
        observed_at=T0,
        produced_at=T0,
        source="CTRADER_DEMO_CAPABILITY_TEST",
        source_ref=f"provider-capability:{capability.value}",
        evidence_sha256="sha256:" + f"{index:064x}",
        policy_version="CIBO_TEST_CAPABILITY_V1",
        provider_verified=provider_verified,
    )


def _registry(
    *,
    hedge: CapabilityStatus = CapabilityStatus.UNAVAILABLE,
    option: CapabilityStatus = CapabilityStatus.UNAVAILABLE,
    spread: CapabilityStatus = CapabilityStatus.UNAVAILABLE,
) -> ProviderInstrumentCapabilityRegistry:
    return ProviderInstrumentCapabilityRegistry(
        account_identity=_identity(),
        entries=(
            _capability_entry(
                capability=InstrumentCapability.HEDGE,
                status=hedge,
                index=1,
            ),
            _capability_entry(
                capability=InstrumentCapability.OPTION,
                status=option,
                index=2,
            ),
            _capability_entry(
                capability=InstrumentCapability.DEFINED_RISK_SPREAD,
                status=spread,
                index=3,
            ),
        ),
        captured_at=T0,
    )


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


def _receipt(
    receipt_id: str,
    *,
    registry: ProviderInstrumentCapabilityRegistry,
    head: str = HEAD,
):
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
            payload["provider_capability_registry_sha256"] = registry.fingerprint()
            payload["structural_disable_reason"] = (
                "PROVIDER_CAPABILITY_CANONICALLY_UNAVAILABLE"
            )
    artifact = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return bind_cross_boundary_pass_artifact(
        receipt_id=receipt_id,
        evidence_kind=kind,
        source_artifact_json=artifact,
    )


def _receipts(
    *,
    registry: ProviderInstrumentCapabilityRegistry,
    head: str = HEAD,
):
    return tuple(
        _receipt(receipt_id, registry=registry, head=head)
        for receipt_id in required_calibration_freeze_receipt_ids()
    )


def _build(
    *,
    registry: ProviderInstrumentCapabilityRegistry,
    receipts=None,
):
    return build_receipt_bound_calibration_freeze(
        receipts=(
            _receipts(registry=registry)
            if receipts is None
            else receipts
        ),
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
        provider_capability_registry=registry,
        capability_at=T0,
    )


def test_receipt_bound_calibration_freeze_seals_exact_t01_t20() -> None:
    registry = _registry()

    manifest = _build(registry=registry)

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
    registry = _registry()
    receipts = tuple(
        item
        for item in _receipts(registry=registry)
        if item.receipt_id != "T11"
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="required receipts missing",
    ):
        _build(registry=registry, receipts=receipts)


def test_cross_head_calibration_receipt_fails_closed() -> None:
    registry = _registry()

    with pytest.raises(
        CiboCapitalManagementError,
        match="integrated-head drift",
    ):
        build_receipt_bound_calibration_freeze(
            receipts=_receipts(
                registry=registry,
                head="c" * 40,
            ),
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
            provider_capability_registry=registry,
            capability_at=T0,
        )


def test_non_t16_t17_structural_disablement_is_rejected() -> None:
    registry = _registry()
    receipts = list(_receipts(registry=registry))
    index = required_calibration_freeze_receipt_ids().index("T03")
    payload = json.loads(receipts[index].source_artifact_json)
    payload.update(
        {
            "disposition": FrozenToolCalibrationDisposition.STRUCTURALLY_DISABLED.value,
            "oos_ready": False,
            "certification_ready": False,
            "structurally_disabled": True,
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
        _build(registry=registry, receipts=tuple(receipts))


def test_t16_unknown_capability_cannot_be_structurally_disabled() -> None:
    registry = _registry(hedge=CapabilityStatus.UNKNOWN)

    with pytest.raises(
        CiboCapitalManagementError,
        match="T16 structural disablement requires provider-verified HEDGE UNAVAILABLE",
    ):
        _build(registry=registry)


def test_t17_requires_both_option_and_spread_unavailable() -> None:
    registry = _registry(
        option=CapabilityStatus.UNAVAILABLE,
        spread=CapabilityStatus.UNKNOWN,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="T17 structural disablement requires provider-verified OPTION and SPREAD UNAVAILABLE",
    ):
        _build(registry=registry)


def test_t16_registry_fingerprint_mismatch_fails_closed() -> None:
    registry = _registry()
    receipts = list(_receipts(registry=registry))
    index = required_calibration_freeze_receipt_ids().index("T16")
    payload = json.loads(receipts[index].source_artifact_json)
    payload["provider_capability_registry_sha256"] = "sha256:" + "f" * 64
    receipts[index] = bind_cross_boundary_pass_artifact(
        receipt_id="T16",
        evidence_kind="CE2I_TOOL_CALIBRATION",
        source_artifact_json=json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="provider registry binding mismatch",
    ):
        _build(registry=registry, receipts=tuple(receipts))
