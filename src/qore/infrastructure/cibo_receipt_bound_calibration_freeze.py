"""Receipt-bound T01..T20 calibration freeze for CIBO.

The underlying B manifest remains the canonical value object, but this adapter
constructs it only from canonical source-bound PASS receipts tied to one exact
integrated HEAD and policy identity. It cannot manufacture certification-ready
tool rows from booleans or arbitrary evidence refs.
"""

from __future__ import annotations

import json

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_calibration_freeze_manifest import (
    CiboCalibrationFreezeManifest,
    FrozenToolCalibration,
    FrozenToolCalibrationDisposition,
    build_calibration_freeze_manifest,
)
from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    CiboCrossBoundaryEvidenceReceipt,
    require_cross_boundary_receipts,
)

_TOOL_IDS = tuple(f"T{index:02d}" for index in range(1, 21))
_FORWARD_RECEIPT_ID = "PHASE20D_FORWARD_MANIFEST"
_PROVIDER_RECEIPT_ID = "PROVIDER_ECONOMICS_FREEZE"
_REQUIRED_RECEIPT_IDS = _TOOL_IDS + (
    _FORWARD_RECEIPT_ID,
    _PROVIDER_RECEIPT_ID,
)


def required_calibration_freeze_receipt_ids() -> tuple[str, ...]:
    return _REQUIRED_RECEIPT_IDS


def build_receipt_bound_calibration_freeze(
    *,
    receipts: tuple[CiboCrossBoundaryEvidenceReceipt, ...],
    integrated_git_sha: str,
    policy_identity_sha256: str,
) -> CiboCalibrationFreezeManifest:
    by_id = require_cross_boundary_receipts(
        receipts=receipts,
        required_receipt_ids=_REQUIRED_RECEIPT_IDS,
        integrated_git_sha=integrated_git_sha,
        policy_identity_sha256=policy_identity_sha256,
    )

    forward = by_id[_FORWARD_RECEIPT_ID]
    provider = by_id[_PROVIDER_RECEIPT_ID]
    if forward.evidence_kind != "PHASE20D_FORWARD_MANIFEST":
        raise CiboCapitalManagementError(
            "calibration freeze forward receipt kind invalid"
        )
    if provider.evidence_kind != "PROVIDER_ECONOMICS_FREEZE":
        raise CiboCapitalManagementError(
            "calibration freeze provider receipt kind invalid"
        )

    provider_required = {
        row.tool_code
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
        if row.provider_economics_required
    }
    tools: list[FrozenToolCalibration] = []
    for tool_code in _TOOL_IDS:
        receipt = by_id[tool_code]
        if receipt.evidence_kind != "CE2I_TOOL_CALIBRATION":
            raise CiboCapitalManagementError(
                f"calibration freeze tool receipt kind invalid: {tool_code}"
            )
        payload = json.loads(receipt.source_artifact_json)
        if payload.get("tool_code") != tool_code:
            raise CiboCapitalManagementError(
                f"calibration freeze tool identity drift: {tool_code}"
            )
        disposition_raw = payload.get("disposition")
        try:
            disposition = FrozenToolCalibrationDisposition(disposition_raw)
        except (TypeError, ValueError) as error:
            raise CiboCapitalManagementError(
                f"calibration freeze disposition invalid: {tool_code}"
            ) from error

        bool_fields = (
            "oos_ready",
            "certification_ready",
            "structurally_disabled",
            "provider_economics_bound",
        )
        for field in bool_fields:
            if type(payload.get(field)) is not bool:
                raise CiboCapitalManagementError(
                    f"calibration freeze tool boolean invalid: {tool_code}:{field}"
                )

        if disposition is FrozenToolCalibrationDisposition.CERTIFICATION_READY:
            if not (
                payload["oos_ready"]
                and payload["certification_ready"]
                and not payload["structurally_disabled"]
            ):
                raise CiboCapitalManagementError(
                    f"calibration freeze active tool state invalid: {tool_code}"
                )
        else:
            if tool_code not in {"T16", "T17"}:
                raise CiboCapitalManagementError(
                    f"calibration freeze illegal structural disablement: {tool_code}"
                )
            if (
                payload["oos_ready"]
                or payload["certification_ready"]
                or not payload["structurally_disabled"]
                or payload.get("provider_capability_verified") is not True
                or not isinstance(payload.get("structural_disable_reason"), str)
                or not payload["structural_disable_reason"]
            ):
                raise CiboCapitalManagementError(
                    f"calibration freeze structural disablement evidence invalid: {tool_code}"
                )

        if (
            tool_code in provider_required
            and payload["provider_economics_bound"] is not True
        ):
            raise CiboCapitalManagementError(
                f"calibration freeze provider binding missing: {tool_code}"
            )

        tools.append(
            FrozenToolCalibration(
                tool_code=tool_code,
                disposition=disposition,
                evidence_refs=(
                    receipt.source_artifact_sha256,
                    receipt.fingerprint(),
                ),
                oos_ready=payload["oos_ready"],
                certification_ready=payload["certification_ready"],
                structurally_disabled=payload["structurally_disabled"],
                provider_economics_bound=payload["provider_economics_bound"],
                holdout_outcomes_used=False,
                target_aware=False,
            )
        )

    frozen_at = max(item.observed_at for item in receipts)
    return build_calibration_freeze_manifest(
        frozen_at=frozen_at,
        phase20d_forward_manifest_sha256=forward.source_artifact_sha256,
        provider_economics_freeze_sha256=provider.source_artifact_sha256,
        tools=tuple(tools),
    )
