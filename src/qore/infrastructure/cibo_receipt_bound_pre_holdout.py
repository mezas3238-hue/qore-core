"""Receipt-bound pre-holdout readiness for CIBO USD60.

This wrapper removes caller-controlled readiness booleans and pre-built
provider-readiness objects from the final pre-holdout decision path.

Phase20D forward evidence, exact executed-risk fills, Phase21, Provider
Economics and the T01..T20 Calibration Freeze must converge on the same frozen
candidate/policy identity and source-bound receipts.

No holdout data is read here and no productive authority is granted.
"""

from __future__ import annotations

import json
import re

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_gate import (
    CiboPreHoldoutReadiness,
    CiboPreHoldoutStatus,
    evaluate_pre_holdout_readiness,
)
from qore.infrastructure.cibo_ce2i_provider_economics_component_freeze import (
    freeze_current_ctrader_demo_provider_economics,
)
from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
    calibrate_ctrader_demo_forward_execution,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    CiboCrossBoundaryEvidenceReceipt,
    require_cross_boundary_receipts,
)
from qore.infrastructure.cibo_instrument_capability_registry import (
    ProviderInstrumentCapabilityRegistry,
)
from qore.infrastructure.cibo_receipt_bound_calibration_freeze import (
    build_receipt_bound_calibration_freeze,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUIRED_IDS = (
    "PHASE20D_CAUSAL_GATE",
    "PHASE21_POLICY_FREEZE",
    "PROVIDER_ECONOMICS_FREEZE",
    "CALIBRATION_FREEZE_MANIFEST",
)


def required_pre_holdout_receipt_ids() -> tuple[str, ...]:
    return _REQUIRED_IDS


def evaluate_receipt_bound_pre_holdout_readiness(
    *,
    integrated_git_sha: str,
    policy_identity_sha256: str,
    receipts: tuple[CiboCrossBoundaryEvidenceReceipt, ...],
    calibration_receipts: tuple[CiboCrossBoundaryEvidenceReceipt, ...],
    forward_manifest: ArchBForwardEconomicManifest,
    executed_risk_book: VersionedPhase20ExecutedRiskBook,
    provider_capability_registry: ProviderInstrumentCapabilityRegistry,
) -> CiboPreHoldoutReadiness:
    """Rebuild every readiness-critical provider object before evaluating."""

    if not isinstance(forward_manifest, ArchBForwardEconomicManifest):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout forward manifest is invalid"
        )
    if not isinstance(executed_risk_book, VersionedPhase20ExecutedRiskBook):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout executed-risk book is invalid"
        )
    if not isinstance(
        provider_capability_registry,
        ProviderInstrumentCapabilityRegistry,
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout capability registry is invalid"
        )

    by_id = require_cross_boundary_receipts(
        receipts=receipts,
        required_receipt_ids=_REQUIRED_IDS,
        integrated_git_sha=integrated_git_sha,
        policy_identity_sha256=policy_identity_sha256,
    )
    expected_kinds = {
        "PHASE20D_CAUSAL_GATE": "PHASE20D_CAUSAL_GATE",
        "PHASE21_POLICY_FREEZE": "PHASE21_POLICY_FREEZE",
        "PROVIDER_ECONOMICS_FREEZE": "PROVIDER_ECONOMICS_FREEZE",
        "CALIBRATION_FREEZE_MANIFEST": "CALIBRATION_FREEZE_MANIFEST",
    }
    for receipt_id, expected_kind in expected_kinds.items():
        if by_id[receipt_id].evidence_kind != expected_kind:
            raise CiboCapitalManagementError(
                f"receipt-bound pre-holdout evidence kind invalid: {receipt_id}"
            )

    phase20 = by_id["PHASE20D_CAUSAL_GATE"]
    phase21 = by_id["PHASE21_POLICY_FREEZE"]
    provider_receipt = by_id["PROVIDER_ECONOMICS_FREEZE"]
    calibration_receipt = by_id["CALIBRATION_FREEZE_MANIFEST"]

    p20 = json.loads(phase20.source_artifact_json)
    p21 = json.loads(phase21.source_artifact_json)
    provider_payload = json.loads(provider_receipt.source_artifact_json)
    calibration_payload = json.loads(calibration_receipt.source_artifact_json)

    forward_sha = p20.get("phase20d_forward_manifest_sha256")
    if (
        not isinstance(forward_sha, str)
        or _SHA256_RE.fullmatch(forward_sha) is None
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout Phase20D forward SHA invalid"
        )
    if p20.get("phase20d_causal_gate_passed") is not True:
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout Phase20D causal gate not passed"
        )
    if forward_manifest.fingerprint() != forward_sha:
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout Phase20D forward manifest mismatch"
        )
    if not forward_manifest.ready_for_scientific_consumption:
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout forward manifest not scientifically ready"
        )

    if p21.get("phase21_policy_freeze_sealed") is not True:
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout Phase21 policy freeze not sealed"
        )
    phase21_sha = p21.get("phase21_policy_freeze_sha256")
    if (
        not isinstance(phase21_sha, str)
        or _SHA256_RE.fullmatch(phase21_sha) is None
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout Phase21 freeze SHA invalid"
        )

    execution_calibration = calibrate_ctrader_demo_forward_execution(
        manifest=forward_manifest,
        executed_risk_book=executed_risk_book,
        frozen_at=provider_receipt.observed_at,
    )
    if (
        not execution_calibration.empirical_slippage_calibrated
        or not execution_calibration.execution_model_ready
        or execution_calibration.blockers
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout provider execution calibration not ready"
        )

    provider_economics_freeze = (
        freeze_current_ctrader_demo_provider_economics(
            frozen_at=provider_receipt.observed_at,
            execution_calibration=execution_calibration,
        )
    )
    if provider_capability_registry.captured_at > provider_receipt.observed_at:
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout capability registry postdates provider freeze"
        )
    provider_fingerprint = provider_economics_freeze.fingerprint()
    if (
        provider_payload.get("provider_economics_freeze_sha256")
        != provider_fingerprint
        or provider_payload.get("execution_calibration_sha256")
        != execution_calibration.fingerprint()
        or provider_payload.get("pre_holdout_provider_economics_ready")
        is not True
        or not provider_economics_freeze.pre_holdout_provider_economics_ready
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout provider freeze binding mismatch"
        )

    calibration_freeze_manifest = build_receipt_bound_calibration_freeze(
        receipts=calibration_receipts,
        integrated_git_sha=integrated_git_sha,
        policy_identity_sha256=policy_identity_sha256,
        provider_capability_registry=provider_capability_registry,
        capability_at=provider_capability_registry.captured_at,
    )
    if any(
        len(tool.evidence_refs) != 2
        or any(
            _SHA256_RE.fullmatch(ref) is None
            for ref in tool.evidence_refs
        )
        for tool in calibration_freeze_manifest.tools
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout calibration tools are not receipt-bound"
        )

    calibration_fingerprint = calibration_freeze_manifest.fingerprint()
    if (
        calibration_payload.get("calibration_freeze_manifest_sha256")
        != calibration_fingerprint
        or calibration_payload.get("sealed") is not True
        or not calibration_freeze_manifest.sealed
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout calibration freeze binding mismatch"
        )
    if (
        calibration_freeze_manifest.phase20d_forward_manifest_sha256
        != forward_sha
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout Phase20D/calibration binding mismatch"
        )
    if (
        calibration_freeze_manifest.provider_economics_freeze_sha256
        != provider_fingerprint
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout provider/calibration binding mismatch"
        )

    readiness = evaluate_pre_holdout_readiness(
        phase20d_causal_gate_passed=True,
        phase21_policy_freeze_sealed=True,
        provider_economics_component_freeze=provider_economics_freeze,
        calibration_freeze_manifest=calibration_freeze_manifest,
        phase20d_forward_manifest_sha256=forward_sha,
    )
    if readiness.status is not CiboPreHoldoutStatus.READY_TO_UNSEAL_2017H1:
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout receipts are PASS but canonical gate is not ready"
        )
    if readiness.holdout_outcomes_inspected or readiness.holdout_market_data_read:
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout readiness consumed sealed holdout"
        )
    return readiness
