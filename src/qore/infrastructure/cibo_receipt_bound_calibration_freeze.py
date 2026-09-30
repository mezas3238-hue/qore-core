"""Receipt-bound T01..T20 calibration freeze for CIBO.

The underlying B manifest remains the canonical value object, but this adapter
constructs it only from canonical source-bound PASS receipts tied to one exact
integrated HEAD and policy identity. It cannot manufacture certification-ready
tool rows from booleans or arbitrary evidence refs.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

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
from qore.infrastructure.cibo_instrument_capability_registry import (
    CapabilityStatus,
    InstrumentCapability,
    ProviderInstrumentCapabilityRegistry,
)

_TOOL_IDS = tuple(f"T{index:02d}" for index in range(1, 21))
_FORWARD_RECEIPT_ID = "PHASE20D_FORWARD_MANIFEST"
_PROVIDER_RECEIPT_ID = "PROVIDER_ECONOMICS_FREEZE"
_REQUIRED_RECEIPT_IDS = _TOOL_IDS + (
    _FORWARD_RECEIPT_ID,
    _PROVIDER_RECEIPT_ID,
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def required_calibration_freeze_receipt_ids() -> tuple[str, ...]:
    return _REQUIRED_RECEIPT_IDS


def build_receipt_bound_calibration_freeze(
    *,
    receipts: tuple[CiboCrossBoundaryEvidenceReceipt, ...],
    integrated_git_sha: str,
    policy_identity_sha256: str,
    provider_capability_registry: ProviderInstrumentCapabilityRegistry,
    capability_at: datetime,
) -> CiboCalibrationFreezeManifest:
    if not isinstance(
        provider_capability_registry,
        ProviderInstrumentCapabilityRegistry,
    ):
        raise CiboCapitalManagementError(
            "calibration freeze requires canonical provider capability registry"
        )
    if capability_at.tzinfo is None or capability_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "calibration freeze capability_at must be timezone-aware"
        )
    if capability_at > provider_capability_registry.captured_at:
        raise CiboCapitalManagementError(
            "calibration freeze capability time exceeds registry capture"
        )

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

    forward_payload = json.loads(forward.source_artifact_json)
    provider_payload = json.loads(provider.source_artifact_json)
    forward_manifest_sha256 = forward_payload.get(
        "phase20d_forward_manifest_sha256"
    )
    provider_freeze_sha256 = provider_payload.get(
        "provider_economics_freeze_sha256"
    )
    if (
        not isinstance(forward_manifest_sha256, str)
        or _SHA256_RE.fullmatch(forward_manifest_sha256) is None
    ):
        raise CiboCapitalManagementError(
            "calibration freeze forward manifest SHA invalid"
        )
    if (
        not isinstance(provider_freeze_sha256, str)
        or _SHA256_RE.fullmatch(provider_freeze_sha256) is None
    ):
        raise CiboCapitalManagementError(
            "calibration freeze provider freeze SHA invalid"
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
            _validate_t16_t17_active_capability(
                tool_code=tool_code,
                registry=provider_capability_registry,
                at=capability_at,
                payload=payload,
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
                or not isinstance(payload.get("structural_disable_reason"), str)
                or not payload["structural_disable_reason"]
            ):
                raise CiboCapitalManagementError(
                    f"calibration freeze structural disablement evidence invalid: {tool_code}"
                )
            _validate_t16_t17_disabled_capability(
                tool_code=tool_code,
                registry=provider_capability_registry,
                at=capability_at,
                payload=payload,
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
        phase20d_forward_manifest_sha256=forward_manifest_sha256,
        provider_economics_freeze_sha256=provider_freeze_sha256,
        tools=tuple(tools),
    )


def _registry_status(
    *,
    registry: ProviderInstrumentCapabilityRegistry,
    capability: InstrumentCapability,
    at: datetime,
) -> CapabilityStatus:
    return registry.status(
        capability=capability,
        at=at,
    )


def _require_registry_binding(
    *,
    payload: dict[str, object],
    registry: ProviderInstrumentCapabilityRegistry,
    tool_code: str,
) -> None:
    if payload.get("provider_capability_registry_sha256") != registry.fingerprint():
        raise CiboCapitalManagementError(
            f"calibration freeze provider registry binding mismatch: {tool_code}"
        )


def _validate_t16_t17_disabled_capability(
    *,
    tool_code: str,
    registry: ProviderInstrumentCapabilityRegistry,
    at: datetime,
    payload: dict[str, object],
) -> None:
    _require_registry_binding(
        payload=payload,
        registry=registry,
        tool_code=tool_code,
    )
    if tool_code == "T16":
        if _registry_status(
            registry=registry,
            capability=InstrumentCapability.HEDGE,
            at=at,
        ) is not CapabilityStatus.UNAVAILABLE:
            raise CiboCapitalManagementError(
                "T16 structural disablement requires provider-verified HEDGE UNAVAILABLE"
            )
        return

    option_status = _registry_status(
        registry=registry,
        capability=InstrumentCapability.OPTION,
        at=at,
    )
    spread_status = _registry_status(
        registry=registry,
        capability=InstrumentCapability.DEFINED_RISK_SPREAD,
        at=at,
    )
    if (
        option_status is not CapabilityStatus.UNAVAILABLE
        or spread_status is not CapabilityStatus.UNAVAILABLE
    ):
        raise CiboCapitalManagementError(
            "T17 structural disablement requires provider-verified OPTION and SPREAD UNAVAILABLE"
        )


def _validate_t16_t17_active_capability(
    *,
    tool_code: str,
    registry: ProviderInstrumentCapabilityRegistry,
    at: datetime,
    payload: dict[str, object],
) -> None:
    if tool_code not in {"T16", "T17"}:
        return
    _require_registry_binding(
        payload=payload,
        registry=registry,
        tool_code=tool_code,
    )
    supported = {
        CapabilityStatus.SUPPORTED,
        CapabilityStatus.CONDITIONALLY_SUPPORTED,
    }
    if tool_code == "T16":
        if _registry_status(
            registry=registry,
            capability=InstrumentCapability.HEDGE,
            at=at,
        ) not in supported:
            raise CiboCapitalManagementError(
                "T16 active calibration requires provider-supported HEDGE capability"
            )
        return

    option_status = _registry_status(
        registry=registry,
        capability=InstrumentCapability.OPTION,
        at=at,
    )
    spread_status = _registry_status(
        registry=registry,
        capability=InstrumentCapability.DEFINED_RISK_SPREAD,
        at=at,
    )
    if option_status not in supported and spread_status not in supported:
        raise CiboCapitalManagementError(
            "T17 active calibration requires provider-supported OPTION or SPREAD capability"
        )
