"""Fail-closed readiness assembler for the real CIBO calibration freeze.

This module does not read the 2017H1 holdout and cannot grant productive
authority. It combines only already-sealed provider Core evidence, a
scientifically-consumable provider-aware Phase20D forward manifest and explicit
T01..T20 terminal calibration evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_calibration_freeze_manifest import (
    CiboCalibrationFreezeManifest,
    FrozenToolCalibration,
    build_calibration_freeze_manifest,
)
from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_provider_core_freeze_receipt import (
    PROVIDER_COMPONENT_FREEZE_SHA256,
    PROVIDER_CORE_FREEZE_RECEIPT,
)

CALIBRATION_FREEZE_READINESS_ID = "CIBO_CALIBRATION_FREEZE_READINESS_V1"
_CANONICAL_TOOLS = tuple(f"T{index:02d}" for index in range(1, 21))


@dataclass(frozen=True, slots=True)
class CiboCalibrationFreezeReadiness:
    readiness_id: str
    ready_to_seal: bool
    blockers: tuple[str, ...]
    forward_manifest_sha256: str | None
    provider_component_freeze_sha256: str
    observed_tool_codes: tuple[str, ...]
    missing_tool_codes: tuple[str, ...]
    calibration_manifest: CiboCalibrationFreezeManifest | None
    holdout_market_data_read: bool = False
    holdout_outcomes_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.readiness_id != CALIBRATION_FREEZE_READINESS_ID:
            raise CiboCapitalManagementError(
                "calibration freeze readiness identity drift"
            )
        if type(self.ready_to_seal) is not bool:
            raise CiboCapitalManagementError(
                "calibration freeze readiness flag must be bool"
            )
        if (
            not isinstance(self.blockers, tuple)
            or any(not isinstance(item, str) or not item for item in self.blockers)
            or len(self.blockers) != len(set(self.blockers))
        ):
            raise CiboCapitalManagementError(
                "calibration freeze readiness blockers invalid"
            )
        _sha(
            self.provider_component_freeze_sha256,
            "provider_component_freeze_sha256",
        )
        if self.forward_manifest_sha256 is not None:
            _sha(self.forward_manifest_sha256, "forward_manifest_sha256")
        if (
            self.observed_tool_codes
            != tuple(sorted(self.observed_tool_codes))
            or len(self.observed_tool_codes) != len(set(self.observed_tool_codes))
            or any(item not in _CANONICAL_TOOLS for item in self.observed_tool_codes)
        ):
            raise CiboCapitalManagementError(
                "calibration freeze readiness observed tools invalid"
            )
        expected_missing = tuple(
            item for item in _CANONICAL_TOOLS if item not in self.observed_tool_codes
        )
        if self.missing_tool_codes != expected_missing:
            raise CiboCapitalManagementError(
                "calibration freeze readiness missing-tool drift"
            )
        expected_ready = not self.blockers
        if self.ready_to_seal != expected_ready:
            raise CiboCapitalManagementError(
                "calibration freeze readiness blocker drift"
            )
        if self.ready_to_seal != (self.calibration_manifest is not None):
            raise CiboCapitalManagementError(
                "calibration freeze readiness manifest drift"
            )
        if self.calibration_manifest is not None:
            if (
                self.calibration_manifest.phase20d_forward_manifest_sha256
                != self.forward_manifest_sha256
                or self.calibration_manifest.provider_economics_freeze_sha256
                != self.provider_component_freeze_sha256
            ):
                raise CiboCapitalManagementError(
                    "calibration freeze readiness lineage drift"
                )
        if (
            self.holdout_market_data_read
            or self.holdout_outcomes_used
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "calibration freeze readiness cannot consume holdout/grant authority"
            )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["calibration_manifest"] = (
            None
            if self.calibration_manifest is None
            else asdict(self.calibration_manifest)
        )
        return payload


def evaluate_calibration_freeze_readiness(
    *,
    forward_manifest: Mapping[str, object],
    tools: tuple[FrozenToolCalibration, ...],
    frozen_at: datetime,
) -> CiboCalibrationFreezeReadiness:
    """Evaluate and, only when complete, assemble the sealed manifest."""

    if frozen_at.tzinfo is None or frozen_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "calibration freeze readiness frozen_at must be timezone-aware"
        )
    if not isinstance(forward_manifest, Mapping):
        raise CiboCapitalManagementError(
            "calibration freeze readiness forward manifest must be mapping"
        )

    blockers: list[str] = []
    forward_sha = _optional_sha(
        forward_manifest.get("manifest_sha256"),
        "forward manifest SHA",
        blockers,
    )
    _validate_forward_identity(forward_manifest, blockers)
    if forward_manifest.get("ready_for_scientific_consumption") is not True:
        blockers.append("FORWARD_MANIFEST_NOT_SCIENTIFICALLY_CONSUMABLE")

    if not PROVIDER_CORE_FREEZE_RECEIPT.core_pre_holdout_ready:
        blockers.append("PROVIDER_CORE_FREEZE_NOT_READY")

    by_code: dict[str, FrozenToolCalibration] = {}
    duplicate_codes: set[str] = set()
    for item in tools:
        if not isinstance(item, FrozenToolCalibration):
            raise CiboCapitalManagementError(
                "calibration freeze readiness requires canonical tool evidence"
            )
        if item.tool_code in by_code:
            duplicate_codes.add(item.tool_code)
        by_code[item.tool_code] = item
    if duplicate_codes:
        blockers.append(
            "DUPLICATE_TOOL_EVIDENCE:" + ",".join(sorted(duplicate_codes))
        )

    observed = tuple(sorted(by_code))
    missing = tuple(item for item in _CANONICAL_TOOLS if item not in by_code)
    if missing:
        blockers.append("MISSING_TOOL_EVIDENCE:" + ",".join(missing))

    provider_required = {
        row.tool_code
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
        if row.provider_economics_required
    }
    unbound = tuple(
        code
        for code in _CANONICAL_TOOLS
        if code in by_code
        and code in provider_required
        and not by_code[code].provider_economics_bound
    )
    if unbound:
        blockers.append(
            "PROVIDER_ECONOMICS_UNBOUND:" + ",".join(unbound)
        )

    blockers = list(dict.fromkeys(blockers))
    manifest: CiboCalibrationFreezeManifest | None = None
    if not blockers:
        assert forward_sha is not None
        ordered = tuple(by_code[code] for code in _CANONICAL_TOOLS)
        manifest = build_calibration_freeze_manifest(
            frozen_at=frozen_at,
            phase20d_forward_manifest_sha256=forward_sha,
            provider_economics_freeze_sha256=PROVIDER_COMPONENT_FREEZE_SHA256,
            tools=ordered,
        )

    return CiboCalibrationFreezeReadiness(
        readiness_id=CALIBRATION_FREEZE_READINESS_ID,
        ready_to_seal=not blockers,
        blockers=tuple(blockers),
        forward_manifest_sha256=forward_sha,
        provider_component_freeze_sha256=PROVIDER_COMPONENT_FREEZE_SHA256,
        observed_tool_codes=observed,
        missing_tool_codes=missing,
        calibration_manifest=manifest,
    )


def _validate_forward_identity(
    payload: Mapping[str, object],
    blockers: list[str],
) -> None:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    expected = (
        ("frozen_candidate_id", frozen.candidate_id),
        ("frozen_code_sha", frozen.code_sha),
        ("frozen_parameter_sha256", frozen.parameter_sha256()),
        ("qualification_plan_id", plan.plan_id),
        ("qualification_plan_sha256", phase20d_qualification_plan_sha256()),
        ("baseline_policy_id", plan.baseline_policy_id),
    )
    drift = tuple(name for name, value in expected if payload.get(name) != value)
    if drift:
        blockers.append("FORWARD_MANIFEST_IDENTITY_DRIFT:" + ",".join(drift))


def _optional_sha(
    value: object,
    name: str,
    blockers: list[str],
) -> str | None:
    if not isinstance(value, str):
        blockers.append("FORWARD_MANIFEST_SHA_REQUIRED")
        return None
    try:
        _sha(value, name)
    except CiboCapitalManagementError:
        blockers.append("FORWARD_MANIFEST_SHA_INVALID")
        return None
    return value


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"calibration freeze readiness {name} must be canonical SHA-256"
        )
