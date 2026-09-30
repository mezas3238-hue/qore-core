"""Canonical T01..T20 calibration/certification matrix.

The empirical calibration registry is the single source of truth.  This module
projects it into the explicit matrix required by CIBO certification governance.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_calibration_registry import (
    CIBO_TOOL_CALIBRATION_REGISTRY,
    CiboCalibrationState,
    CiboCalibrationType,
)

CiboCalibrationClassification = CiboCalibrationState


@dataclass(frozen=True, slots=True)
class CiboToolCalibrationMatrixRow:
    tool_code: str
    implemented: bool
    calibrated: bool
    calibration_source: tuple[str, ...]
    calibration_type: CiboCalibrationType
    provider_economics_required: bool
    fail_closed: bool
    oos_ready: bool
    certification_ready: bool
    classification: CiboCalibrationState
    blocker: tuple[str, ...]
    calibration_artifact_sha256: str | None

    def __post_init__(self) -> None:
        if not self.tool_code:
            raise CiboCapitalManagementError("matrix tool code is required")
        if not self.calibration_source:
            raise CiboCapitalManagementError("matrix calibration source is required")
        if self.certification_ready and not self.oos_ready:
            raise CiboCapitalManagementError(
                "certification-ready tool must first be OOS-ready"
            )
        if self.oos_ready and not self.calibrated:
            raise CiboCapitalManagementError(
                "OOS-ready tool must already be calibrated"
            )


CIBO_T01_T20_CALIBRATION_MATRIX: tuple[CiboToolCalibrationMatrixRow, ...] = tuple(
    CiboToolCalibrationMatrixRow(
        tool_code=row.tool_code,
        implemented=row.implemented,
        calibrated=row.calibrated,
        calibration_source=row.calibration_sources,
        calibration_type=row.calibration_type,
        provider_economics_required=row.provider_economics_required,
        fail_closed=row.fail_closed,
        oos_ready=row.oos_ready,
        certification_ready=row.certification_ready,
        classification=row.state,
        blocker=row.blockers,
        calibration_artifact_sha256=row.calibration_artifact_sha256,
    )
    for row in CIBO_TOOL_CALIBRATION_REGISTRY
)


def validate_calibration_matrix() -> None:
    canonical = tuple(f"T{index:02d}" for index in range(1, 21))
    observed = tuple(row.tool_code for row in CIBO_T01_T20_CALIBRATION_MATRIX)
    if observed != canonical:
        raise CiboCapitalManagementError(
            "calibration matrix must contain exactly canonical T01..T20"
        )
    if any(
        row.certification_ready
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
    ):
        raise CiboCapitalManagementError(
            "pre-holdout matrix cannot claim certification readiness"
        )
