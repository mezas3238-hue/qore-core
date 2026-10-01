"""Sealed T01..T20 calibration-freeze manifest for CIBO pre-holdout governance.

This manifest is a cross-boundary integration artifact. Architect A/B may
produce evidence, but the final manifest is sealed only after every active tool
has terminal OOS/certification evidence. T16/T17 may be structurally disabled
when provider capability is explicitly unavailable.

It never reads or unseals 2017H1 and grants no productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)

CALIBRATION_FREEZE_MANIFEST_ID = "CIBO_T01_T20_CALIBRATION_FREEZE_MANIFEST_V1"


class FrozenToolCalibrationDisposition(StrEnum):
    CERTIFICATION_READY = "CERTIFICATION_READY"
    QUALIFICATION_FAILED_AND_DISABLED = "QUALIFICATION_FAILED_AND_DISABLED"
    STRUCTURALLY_DISABLED = "STRUCTURALLY_DISABLED"


@dataclass(frozen=True, slots=True)
class FrozenToolCalibration:
    tool_code: str
    disposition: FrozenToolCalibrationDisposition
    evidence_refs: tuple[str, ...]
    oos_ready: bool
    certification_ready: bool
    structurally_disabled: bool
    provider_economics_bound: bool
    holdout_outcomes_used: bool = False
    target_aware: bool = False

    def __post_init__(self) -> None:
        canonical = {f"T{index:02d}" for index in range(1, 21)}
        if self.tool_code not in canonical:
            raise CiboCapitalManagementError(
                "calibration freeze tool code is not canonical"
            )
        if type(self.disposition) is not FrozenToolCalibrationDisposition:
            raise CiboCapitalManagementError(
                "calibration freeze tool disposition invalid"
            )
        if (
            not self.evidence_refs
            or len(self.evidence_refs) != len(set(self.evidence_refs))
            or any(not isinstance(item, str) or not item for item in self.evidence_refs)
        ):
            raise CiboCapitalManagementError(
                "calibration freeze tool evidence refs invalid"
            )
        for name in (
            "oos_ready",
            "certification_ready",
            "structurally_disabled",
            "provider_economics_bound",
            "holdout_outcomes_used",
            "target_aware",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"calibration freeze tool {name} must be bool"
                )
        if self.holdout_outcomes_used or self.target_aware:
            raise CiboCapitalManagementError(
                "calibration freeze tool cannot consume holdout/target state"
            )
        if (
            self.disposition
            is FrozenToolCalibrationDisposition.CERTIFICATION_READY
        ):
            if (
                not self.oos_ready
                or not self.certification_ready
                or self.structurally_disabled
            ):
                raise CiboCapitalManagementError(
                    "certification-ready frozen tool state is inconsistent"
                )
        elif (
            self.disposition
            is FrozenToolCalibrationDisposition.STRUCTURALLY_DISABLED
        ):
            if self.tool_code not in {"T16", "T17"}:
                raise CiboCapitalManagementError(
                    "only T16/T17 may be structurally disabled"
                )
            if (
                self.oos_ready
                or self.certification_ready
                or not self.structurally_disabled
            ):
                raise CiboCapitalManagementError(
                    "structurally-disabled frozen tool state is inconsistent"
                )
        else:
            if (
                not self.oos_ready
                or self.certification_ready
                or not self.structurally_disabled
            ):
                raise CiboCapitalManagementError(
                    "qualification-failed frozen tool state is inconsistent"
                )


@dataclass(frozen=True, slots=True)
class CiboCalibrationFreezeManifest:
    manifest_id: str
    frozen_at: datetime
    phase20d_forward_manifest_sha256: str
    provider_economics_freeze_sha256: str
    tools: tuple[FrozenToolCalibration, ...]
    sealed: bool
    holdout_outcomes_used: bool = False
    holdout_market_data_read: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.manifest_id != CALIBRATION_FREEZE_MANIFEST_ID:
            raise CiboCapitalManagementError(
                "calibration freeze manifest identity drift"
            )
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "calibration freeze manifest timestamp must be timezone-aware"
            )
        _sha(
            self.phase20d_forward_manifest_sha256,
            "phase20d_forward_manifest_sha256",
        )
        _sha(
            self.provider_economics_freeze_sha256,
            "provider_economics_freeze_sha256",
        )
        canonical = tuple(f"T{index:02d}" for index in range(1, 21))
        observed = tuple(item.tool_code for item in self.tools)
        if observed != canonical:
            raise CiboCapitalManagementError(
                "calibration freeze manifest requires ordered T01..T20"
            )
        if any(not isinstance(item, FrozenToolCalibration) for item in self.tools):
            raise CiboCapitalManagementError(
                "calibration freeze manifest tool row invalid"
            )
        for name in (
            "sealed",
            "holdout_outcomes_used",
            "holdout_market_data_read",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"calibration freeze manifest {name} must be bool"
                )
        if not self.sealed:
            raise CiboCapitalManagementError(
                "calibration freeze manifest must be sealed"
            )
        if self.holdout_outcomes_used or self.holdout_market_data_read:
            raise CiboCapitalManagementError(
                "calibration freeze manifest cannot consume 2017H1"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "calibration freeze manifest has no productive authority"
            )
        provider_required = {
            item.tool_code
            for item in CIBO_T01_T20_CALIBRATION_MATRIX
            if item.provider_economics_required
        }
        if any(
            item.tool_code in provider_required
            and not item.provider_economics_bound
            for item in self.tools
        ):
            raise CiboCapitalManagementError(
                "calibration freeze provider-dependent tool is not bound"
            )
        active = tuple(
            item
            for item in self.tools
            if not item.structurally_disabled
        )
        if any(
            item.disposition
            is not FrozenToolCalibrationDisposition.CERTIFICATION_READY
            or not item.oos_ready
            or not item.certification_ready
            for item in active
        ):
            raise CiboCapitalManagementError(
                "calibration freeze manifest active tools are not terminal"
            )

    @property
    def structurally_disabled_tools(self) -> tuple[str, ...]:
        return tuple(
            item.tool_code for item in self.tools if item.structurally_disabled
        )

    @property
    def active_certification_ready_tools(self) -> tuple[str, ...]:
        return tuple(
            item.tool_code
            for item in self.tools
            if item.certification_ready and not item.structurally_disabled
        )

    def fingerprint(self) -> str:
        raw = json.dumps(
            _canonical(asdict(self)),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_calibration_freeze_manifest(
    *,
    frozen_at: datetime,
    phase20d_forward_manifest_sha256: str,
    provider_economics_freeze_sha256: str,
    tools: tuple[FrozenToolCalibration, ...],
) -> CiboCalibrationFreezeManifest:
    return CiboCalibrationFreezeManifest(
        manifest_id=CALIBRATION_FREEZE_MANIFEST_ID,
        frozen_at=frozen_at,
        phase20d_forward_manifest_sha256=phase20d_forward_manifest_sha256,
        provider_economics_freeze_sha256=provider_economics_freeze_sha256,
        tools=tools,
        sealed=True,
        holdout_outcomes_used=False,
        holdout_market_data_read=False,
        productive_authority=False,
    )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"calibration freeze manifest {name} must be canonical SHA-256"
        )


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value
