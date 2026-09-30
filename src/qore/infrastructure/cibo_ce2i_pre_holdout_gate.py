"""Fail-closed pre-holdout gate for the CIBO USD60 six-month examination.

The preregistered 2017H1 dataset must remain unread until this gate becomes
READY_TO_UNSEAL_2017H1. The gate inspects only code/config/calibration metadata;
it never reads holdout market data or Trader outcomes.

The historical calibration matrix remains immutable provenance. Once A+B have
terminalized the active tool surface, a sealed dynamic calibration manifest may
supersede historical matrix blockers for readiness evaluation only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_ce2i_calibration_freeze_manifest import (
    CiboCalibrationFreezeManifest,
)
from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
    CiboToolCalibrationMatrixRow,
)
from qore.infrastructure.cibo_ce2i_calibration_registry import (
    CiboCalibrationState,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    PREREGISTERED_USD60_HOLDOUT,
)
from qore.infrastructure.cibo_ce2i_provider_economics_component_freeze import (
    CiboProviderEconomicsComponentFreeze,
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
    phase20d_causal_gate_passed: bool
    phase21_policy_freeze_sealed: bool
    holdout_outcomes_inspected: bool
    holdout_market_data_read: bool

    def __post_init__(self) -> None:
        if type(self.status) is not CiboPreHoldoutStatus:
            raise TypeError("pre-holdout status must use canonical enum")
        if self.status is CiboPreHoldoutStatus.READY_TO_UNSEAL_2017H1:
            if self.blockers:
                raise ValueError("ready-to-unseal status cannot retain blockers")
        if type(self.phase20d_causal_gate_passed) is not bool:
            raise TypeError("phase20d causal gate flag must be bool")
        if type(self.phase21_policy_freeze_sealed) is not bool:
            raise TypeError("phase21 freeze flag must be bool")
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
    phase20d_causal_gate_passed: bool = False,
    phase21_policy_freeze_sealed: bool = False,
    provider_economics_component_freeze: (
        CiboProviderEconomicsComponentFreeze | None
    ) = None,
    calibration_freeze_manifest: CiboCalibrationFreezeManifest | None = None,
    phase20d_forward_manifest_sha256: str | None = None,
) -> CiboPreHoldoutReadiness:
    """Evaluate readiness without reading any holdout source or outcome."""

    blockers: list[str] = []
    canonical = tuple(f"T{index:02d}" for index in range(1, 21))
    if tuple(tool.code for tool in CE2I_TOOL_REGISTRY) != canonical:
        blockers.append("T01_T20_REGISTRY_INCOMPLETE")

    rows = {row.tool_code: row for row in CIBO_T01_T20_CALIBRATION_MATRIX}
    if tuple(rows) != canonical:
        blockers.append("T01_T20_CALIBRATION_MATRIX_INCOMPLETE")

    effective_provider_frozen = provider_economics_frozen
    effective_calibration_sealed = calibration_freeze_manifest_sealed

    if calibration_freeze_manifest is None:
        blockers.extend(_historical_matrix_blockers(rows))
    else:
        if not isinstance(
            calibration_freeze_manifest,
            CiboCalibrationFreezeManifest,
        ):
            raise TypeError(
                "calibration_freeze_manifest must use canonical manifest"
            )
        effective_calibration_sealed = calibration_freeze_manifest.sealed

        if phase20d_forward_manifest_sha256 is None:
            blockers.append("PHASE20D_FORWARD_MANIFEST_SHA_NOT_BOUND")
        elif (
            phase20d_forward_manifest_sha256
            != calibration_freeze_manifest.phase20d_forward_manifest_sha256
        ):
            blockers.append("PHASE20D_FORWARD_MANIFEST_SHA_MISMATCH")

        if provider_economics_component_freeze is None:
            blockers.append("PROVIDER_ECONOMICS_COMPONENT_FREEZE_MISSING")
            effective_provider_frozen = False
        else:
            if not isinstance(
                provider_economics_component_freeze,
                CiboProviderEconomicsComponentFreeze,
            ):
                raise TypeError(
                    "provider_economics_component_freeze must be canonical"
                )
            provider_ready = (
                provider_economics_component_freeze
                .pre_holdout_provider_economics_ready
            )
            effective_provider_frozen = provider_ready
            if (
                provider_economics_component_freeze.fingerprint()
                != calibration_freeze_manifest.provider_economics_freeze_sha256
            ):
                blockers.append("PROVIDER_ECONOMICS_FREEZE_SHA_MISMATCH")
            if (
                calibration_freeze_manifest.frozen_at
                < provider_economics_component_freeze.frozen_at
            ):
                blockers.append(
                    "CALIBRATION_FREEZE_PREDATES_PROVIDER_ECONOMICS_FREEZE"
                )

    if not phase20d_causal_gate_passed:
        blockers.append("PHASE20D_CAUSAL_TOOL_GATE_NOT_PASSED")
    if not phase21_policy_freeze_sealed:
        blockers.append("PHASE21_POLICY_FREEZE_NOT_SEALED")
    if not effective_provider_frozen:
        blockers.append("PROVIDER_ECONOMICS_NOT_FROZEN")
    if not effective_calibration_sealed:
        blockers.append("CALIBRATION_FREEZE_MANIFEST_NOT_SEALED")

    candidate = PREREGISTERED_USD60_HOLDOUT
    if candidate.outcome_data_inspected_at_selection:
        blockers.append("HOLDOUT_ALREADY_CONTAMINATED")

    blockers = list(dict.fromkeys(blockers))
    return CiboPreHoldoutReadiness(
        status=(
            CiboPreHoldoutStatus.READY_TO_UNSEAL_2017H1
            if not blockers
            else CiboPreHoldoutStatus.NOT_READY
        ),
        blockers=tuple(blockers),
        tool_matrix_sha256=calibration_matrix_sha256(),
        holdout_candidate_id=candidate.candidate_id,
        phase20d_causal_gate_passed=phase20d_causal_gate_passed,
        phase21_policy_freeze_sealed=phase21_policy_freeze_sealed,
        holdout_outcomes_inspected=False,
        holdout_market_data_read=False,
    )


def _historical_matrix_blockers(
    rows: dict[str, CiboToolCalibrationMatrixRow],
) -> list[str]:
    typed_rows = {
        row.tool_code: row
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
    }
    if tuple(typed_rows) != tuple(rows):
        raise ValueError("pre-holdout calibration row identity drift")

    blockers: list[str] = []
    unresolved_non_provider = tuple(
        code
        for code, row in typed_rows.items()
        if row.classification is CiboCalibrationState.CALIBRATION_UNAVAILABLE
    )
    if unresolved_non_provider:
        blockers.append(
            "UNRESOLVED_CAUSAL_CALIBRATIONS:"
            + ",".join(unresolved_non_provider)
        )

    provider_pending = tuple(
        code
        for code, row in typed_rows.items()
        if row.classification
        is CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED
    )
    if provider_pending:
        blockers.append(
            "PROVIDER_ECONOMICS_REQUIRED:" + ",".join(provider_pending)
        )

    illegal_fail_closed = tuple(
        code
        for code, row in typed_rows.items()
        if row.classification is CiboCalibrationState.FAIL_CLOSED
        and code not in {"T16", "T17"}
    )
    if illegal_fail_closed:
        blockers.append(
            "UNRESOLVED_FAIL_CLOSED_TOOLS:" + ",".join(illegal_fail_closed)
        )
    return blockers
