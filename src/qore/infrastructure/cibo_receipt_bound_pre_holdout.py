"""Receipt-bound pre-holdout readiness for CIBO USD60.

This wrapper removes caller-controlled readiness booleans from the final
pre-holdout decision path. Phase20D, Phase21, Provider Economics and the T01..T20
Calibration Freeze must each arrive as canonical PASS receipts bound to the same
integrated HEAD and policy identity.

No holdout data is read here and no productive authority is granted.
"""

from __future__ import annotations

import json
import re

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_calibration_freeze_manifest import (
    CiboCalibrationFreezeManifest,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_gate import (
    CiboPreHoldoutReadiness,
    CiboPreHoldoutStatus,
    evaluate_pre_holdout_readiness,
)
from qore.infrastructure.cibo_ce2i_provider_economics_component_freeze import (
    CiboProviderEconomicsComponentFreeze,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    CiboCrossBoundaryEvidenceReceipt,
    require_cross_boundary_receipts,
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
    provider_economics_freeze: CiboProviderEconomicsComponentFreeze,
    calibration_freeze_manifest: CiboCalibrationFreezeManifest,
) -> CiboPreHoldoutReadiness:
    if not isinstance(
        provider_economics_freeze,
        CiboProviderEconomicsComponentFreeze,
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout provider freeze is invalid"
        )
    if not isinstance(
        calibration_freeze_manifest,
        CiboCalibrationFreezeManifest,
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout calibration manifest is invalid"
        )

    by_id = require_cross_boundary_receipts(
        receipts=receipts,
        required_receipt_ids=_REQUIRED_IDS,
        integrated_git_sha=integrated_git_sha,
        policy_identity_sha256=policy_identity_sha256,
    )

    phase20 = by_id["PHASE20D_CAUSAL_GATE"]
    phase21 = by_id["PHASE21_POLICY_FREEZE"]
    provider_receipt = by_id["PROVIDER_ECONOMICS_FREEZE"]
    calibration_receipt = by_id["CALIBRATION_FREEZE_MANIFEST"]

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

    p20 = json.loads(phase20.source_artifact_json)
    p21 = json.loads(phase21.source_artifact_json)
    provider_payload = json.loads(provider_receipt.source_artifact_json)
    calibration_payload = json.loads(calibration_receipt.source_artifact_json)

    forward_sha = p20.get("phase20d_forward_manifest_sha256")
    if not isinstance(forward_sha, str) or _SHA256_RE.fullmatch(forward_sha) is None:
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout Phase20D forward SHA invalid"
        )
    if p20.get("phase20d_causal_gate_passed") is not True:
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout Phase20D causal gate not passed"
        )
    if p21.get("phase21_policy_freeze_sealed") is not True:
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout Phase21 policy freeze not sealed"
        )
    phase21_sha = p21.get("phase21_policy_freeze_sha256")
    if not isinstance(phase21_sha, str) or _SHA256_RE.fullmatch(phase21_sha) is None:
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout Phase21 freeze SHA invalid"
        )

    provider_fingerprint = provider_economics_freeze.fingerprint()
    if (
        provider_payload.get("provider_economics_freeze_sha256")
        != provider_fingerprint
        or provider_payload.get("pre_holdout_provider_economics_ready")
        is not True
        or not provider_economics_freeze.pre_holdout_provider_economics_ready
    ):
        raise CiboCapitalManagementError(
            "receipt-bound pre-holdout provider freeze binding mismatch"
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

    if calibration_freeze_manifest.phase20d_forward_manifest_sha256 != forward_sha:
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
