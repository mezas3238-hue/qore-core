"""Fail-closed pre-holdout gate for the CIBO USD60 six-month examination.

The preregistered 2017H1 dataset must remain unread until this gate becomes
READY_TO_UNSEAL_2017H1. The gate inspects only code/config/calibration metadata;
it never reads holdout market data or Trader outcomes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)
from qore.infrastructure.cibo_ce2i_calibration_registry import (
    CiboCalibrationState,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    PREREGISTERED_USD60_HOLDOUT,
)
from qore.infrastructure.cibo_ce2i_tool_registry import CE2I_TOOL_REGISTRY


class CiboPreHoldoutStatus(StrEnum):
    NOT_READY = "NOT_READY"
    READY_TO_FREEZE = "READY_TO_FREEZE"
    READY_TO_UNSEAL_2017H1 = "READY_TO_UNSEAL_2017H1"


@dataclass(frozen=True, slots=True)
class CiboPreHoldoutReadiness:
    status: CiboPreHoldoutStatus
    blockers: tuple[str, ...]
    tool_matrix_sha256: str
    holdout_candidate_id: str
    holdout_outcomes_inspected: bool
    holdout_market_data_read: bool

    def __post_init__(self) -> None:
        if type(self.status) is not CiboPreHoldoutStatus:
            raise TypeError("pre-holdout status must use canonical enum")
        if self.status is CiboPreHoldoutStatus.READY_TO_UNSEAL_2017H1:
            if self.blockers:
                raise ValueError("ready-to-unseal status cannot retain blockers")
        if self.holdout_outcomes_inspected or self.holdout_market_data_read:
            raise ValueError("pre-holdout readiness cannot consume 2017H1")


def _matrix_payload() -> list[dict[str, object]]:
    return [
        {
            "tool_code": row.tool_code,
            "implemented": row.implemented,
            "calibrated": row.calibrated,
            "classification": row.classification.value,
            "calibration_type": row.calibration_type.value,
            "calibration_source": list(row.calibration_source),
            "provider_economics_required": row.provider_economics_required,
            "fail_closed": row.fail_closed,
            "oos_ready": row.oos_ready,
            "certification_ready": row.certification_ready,
            "blocker": list(row.blocker),
            "calibration_artifact_sha256": row.calibration_artifact_sha256,
        }
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
    ]


def calibration_matrix_sha256() -> str:
    raw = json.dumps(
        _matrix_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def evaluate_pre_holdout_readiness(
    *,
    provider_economics_frozen: bool = False,
    calibration_freeze_manifest_sealed: bool = False,
) -> CiboPreHoldoutReadiness:
    """Evaluate readiness without reading any holdout source or outcome."""

    blockers: list[str] = []
    canonical = tuple(f"T{index:02d}" for index in range(1, 21))
    if tuple(tool.code for tool in CE2I_TOOL_REGISTRY) != canonical:
        blockers.append("T01_T20_REGISTRY_INCOMPLETE")

    rows = {row.tool_code: row for row in CIBO_T01_T20_CALIBRATION_MATRIX}
    if tuple(rows) != canonical:
        blockers.append("T01_T20_CALIBRATION_MATRIX_INCOMPLETE")

    unresolved_non_provider = tuple(
        code
        for code, row in rows.items()
        if row.classification is CiboCalibrationState.CALIBRATION_UNAVAILABLE
    )
    if unresolved_non_provider:
        blockers.append(
            "UNRESOLVED_CAUSAL_CALIBRATIONS:"
            + ",".join(unresolved_non_provider)
        )

    provider_pending = tuple(
        code
        for code, row in rows.items()
        if row.classification is CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED
    )
    if provider_pending:
        blockers.append(
            "PROVIDER_ECONOMICS_REQUIRED:" + ",".join(provider_pending)
        )

    # T16/T17 may remain structurally fail-closed when no certified instrument
    # universe exists. This is explicit non-activation, never certification.
    illegal_fail_closed = tuple(
        code
        for code, row in rows.items()
        if row.classification is CiboCalibrationState.FAIL_CLOSED
        and code not in {"T16", "T17"}
    )
    if illegal_fail_closed:
        blockers.append(
            "UNRESOLVED_FAIL_CLOSED_TOOLS:" + ",".join(illegal_fail_closed)
        )

    if not provider_economics_frozen:
        blockers.append("PROVIDER_ECONOMICS_NOT_FROZEN")
    if not calibration_freeze_manifest_sealed:
        blockers.append("CALIBRATION_FREEZE_MANIFEST_NOT_SEALED")

    candidate = PREREGISTERED_USD60_HOLDOUT
    if candidate.outcome_data_inspected_at_selection:
        blockers.append("HOLDOUT_ALREADY_CONTAMINATED")

    return CiboPreHoldoutReadiness(
        status=(
            CiboPreHoldoutStatus.READY_TO_UNSEAL_2017H1
            if not blockers
            else CiboPreHoldoutStatus.NOT_READY
        ),
        blockers=tuple(blockers),
        tool_matrix_sha256=calibration_matrix_sha256(),
        holdout_candidate_id=candidate.candidate_id,
        holdout_outcomes_inspected=False,
        holdout_market_data_read=False,
    )
