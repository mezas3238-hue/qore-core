"""Fail-closed CIBO pre-holdout readiness checkpoint.

This checkpoint never reads 2017H1 and never unseals it. It summarizes the
canonical T01..T20 calibration registry and identifies what still prevents the
CIBO PRE-HOLDOUT FREEZE.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)
from qore.infrastructure.cibo_ce2i_calibration_registry import (
    CiboCalibrationState,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_freeze import (
    ACTIVE_PRE_HOLDOUT_FREEZE,
    CURRENT_HOLDOUT_SEAL_STATE,
    CiboHoldoutSealState,
)


@dataclass(frozen=True, slots=True)
class CiboPreHoldoutCheckpoint:
    matrix_sha256: str
    calibrated_tools: tuple[str, ...]
    oos_ready_tools: tuple[str, ...]
    certification_ready_tools: tuple[str, ...]
    provider_economics_pending_tools: tuple[str, ...]
    calibration_pending_tools: tuple[str, ...]
    fail_closed_tools: tuple[str, ...]
    structurally_disabled_tools: tuple[str, ...]
    holdout_state: CiboHoldoutSealState
    holdout_2017h1_read: bool
    phase20d_causal_gate_passed: bool
    phase21_policy_freeze_sealed: bool
    pre_holdout_freeze_active: bool

    def __post_init__(self) -> None:
        if not self.matrix_sha256:
            raise CiboCapitalManagementError(
                "pre-holdout checkpoint matrix hash is required"
            )
        if self.holdout_state is not CiboHoldoutSealState.SEALED_UNTOUCHED:
            raise CiboCapitalManagementError(
                "pre-freeze checkpoint requires 2017H1 SEALED_UNTOUCHED"
            )
        if self.holdout_2017h1_read:
            raise CiboCapitalManagementError(
                "pre-freeze checkpoint cannot claim 2017H1 was read"
            )
        for name in (
            "phase20d_causal_gate_passed",
            "phase21_policy_freeze_sealed",
            "pre_holdout_freeze_active",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"pre-freeze checkpoint {name} must be bool"
                )
        if self.pre_holdout_freeze_active:
            raise CiboCapitalManagementError(
                "readiness checkpoint cannot activate pre-holdout freeze"
            )

    @property
    def ready_to_freeze(self) -> bool:
        active_tool_count = 20 - len(self.structurally_disabled_tools)
        return (
            self.phase20d_causal_gate_passed
            and self.phase21_policy_freeze_sealed
            and not self.provider_economics_pending_tools
            and not self.calibration_pending_tools
            and len(self.oos_ready_tools) == active_tool_count
            and len(self.certification_ready_tools) == active_tool_count
        )


def build_pre_holdout_checkpoint(
    *,
    phase20d_causal_gate_passed: bool = False,
    phase21_policy_freeze_sealed: bool = False,
) -> CiboPreHoldoutCheckpoint:
    rows = CIBO_T01_T20_CALIBRATION_MATRIX
    structurally_disabled = tuple(
        row.tool_code
        for row in rows
        if row.classification is CiboCalibrationState.FAIL_CLOSED
    )
    canonical = [
        {
            "tool": row.tool_code,
            "implemented": row.implemented,
            "calibrated": row.calibrated,
            "calibration_source": list(row.calibration_source),
            "calibration_type": row.calibration_type.value,
            "provider_economics_required": row.provider_economics_required,
            "fail_closed": row.fail_closed,
            "oos_ready": row.oos_ready,
            "certification_ready": row.certification_ready,
            "classification": row.classification.value,
            "blocker": list(row.blocker),
            "calibration_artifact_sha256": row.calibration_artifact_sha256,
        }
        for row in rows
    ]
    matrix_hash = hashlib.sha256(
        json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return CiboPreHoldoutCheckpoint(
        matrix_sha256=matrix_hash,
        calibrated_tools=tuple(row.tool_code for row in rows if row.calibrated),
        oos_ready_tools=tuple(row.tool_code for row in rows if row.oos_ready),
        certification_ready_tools=tuple(
            row.tool_code for row in rows if row.certification_ready
        ),
        provider_economics_pending_tools=tuple(
            row.tool_code
            for row in rows
            if row.tool_code not in structurally_disabled
            and row.provider_economics_required
            and not row.certification_ready
        ),
        calibration_pending_tools=tuple(
            row.tool_code
            for row in rows
            if row.tool_code not in structurally_disabled
            and not row.calibrated
        ),
        fail_closed_tools=tuple(
            row.tool_code for row in rows if row.fail_closed
        ),
        structurally_disabled_tools=structurally_disabled,
        holdout_state=CURRENT_HOLDOUT_SEAL_STATE,
        holdout_2017h1_read=False,
        phase20d_causal_gate_passed=phase20d_causal_gate_passed,
        phase21_policy_freeze_sealed=phase21_policy_freeze_sealed,
        pre_holdout_freeze_active=ACTIVE_PRE_HOLDOUT_FREEZE is not None,
    )
