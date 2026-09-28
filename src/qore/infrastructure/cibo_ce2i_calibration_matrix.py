"""Canonical T01..T20 calibration/certification matrix.

This module separates contract implementation from causal calibration, provider
economics, fresh-OOS readiness and economic certification.  It must never infer
calibration from a GREEN engineering test suite.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_burned_calibration import (
    burned_t04_t10_calibration_sha256,
)
from qore.infrastructure.cibo_ce2i_tool_registry import (
    CE2I_TOOL_REGISTRY,
    ToolMaturity,
)


class CiboCalibrationClassification(StrEnum):
    CALIBRATED_CAUSAL = "CALIBRATED_CAUSAL"
    CALIBRATED_ECONOMIC = "CALIBRATED_ECONOMIC"
    PROVIDER_ECONOMICS_REQUIRED = "PROVIDER_ECONOMICS_REQUIRED"
    CALIBRATION_UNAVAILABLE = "CALIBRATION_UNAVAILABLE"
    OOS_READY = "OOS_READY"
    CERTIFICATION_READY = "CERTIFICATION_READY"
    FAIL_CLOSED = "FAIL_CLOSED"


class CiboCalibrationType(StrEnum):
    CAUSAL_NORMALIZED = "CAUSAL_NORMALIZED"
    ECONOMIC_PROVIDER_BOUND = "ECONOMIC_PROVIDER_BOUND"
    CONTRACT_INTEGRITY = "CONTRACT_INTEGRITY"
    INSTRUMENT_CAPABILITY = "INSTRUMENT_CAPABILITY"


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
    classification: CiboCalibrationClassification
    blocker: tuple[str, ...]
    calibration_artifact_sha256: str | None = None

    def __post_init__(self) -> None:
        canonical = {tool.code for tool in CE2I_TOOL_REGISTRY}
        if self.tool_code not in canonical:
            raise CiboCapitalManagementError("unknown CE2I tool in matrix")
        if not self.calibration_source:
            raise CiboCapitalManagementError(
                "calibration matrix requires provenance"
            )
        if self.certification_ready and not self.oos_ready:
            raise CiboCapitalManagementError(
                "certification-ready tool must first be OOS-ready"
            )
        if self.calibrated and self.classification in {
            CiboCalibrationClassification.PROVIDER_ECONOMICS_REQUIRED,
            CiboCalibrationClassification.CALIBRATION_UNAVAILABLE,
            CiboCalibrationClassification.FAIL_CLOSED,
        }:
            raise CiboCapitalManagementError(
                "uncalibrated classification cannot claim calibrated"
            )
        if self.certification_ready and self.blocker:
            raise CiboCapitalManagementError(
                "certification-ready tool cannot retain blockers"
            )
        if self.calibrated and not self.calibration_artifact_sha256:
            raise CiboCapitalManagementError(
                "calibrated tool requires sealed calibration artifact hash"
            )


_P18 = "burned:phase18:seven-lineage-chronological-replay"
_P18_ARTIFACTS = (
    "artifact:10972328824:sha256:63df308d8d395589aa8dd05149e82594e600c9f2b64e923ffa7e1a64d7981370",
    "artifact:10972179510:sha256:1a5b4460b6fbea98744478ddb5ab80067642f939afd5bacc73131b4e1e4ecc40",
    "artifact:10972612721:sha256:7c0913bf80060e681152ad835b777433e5c6491e3d2d7ebc959d3685b5f27fab",
    "artifact:10972877463:sha256:2b3e6157d60b7e6783eda76f961a6616ca6263589a41572de29792bd881c62d5",
    "artifact:10971784365:sha256:57a9cc194b689ed6b245497c38e805a42f4299924c576513616d6449ab4f9c19",
    "artifact:10972877395:sha256:d05327c77f48cf8fb4e01f87bcf43ee088ed860f575a5845ae07130d7b5f43ab",
    "artifact:10972014225:sha256:2af24819edd86568147167353a4a700c75419a30aa57bc9df084e2e4d6de5e41",
)
_P19 = (
    "burned:phase19:integrated-common-window:"
    "artifact:10972948493:"
    "sha256:e2fcf03ac78e278a22ec53f4f4d6b419ae4d9f5f7a9c674c23fd18c3a4e95527"
)
_P19_WFO = "burned:phase19j:post-freeze-walk-forward"
_P20 = "phase20:contract-and-failure-proof"
_PROVIDER = "phase19:provider-economics-inventory:BLOCKED_PROVIDER_ECONOMICS"


def _row(
    code: str,
    *,
    source: tuple[str, ...],
    kind: CiboCalibrationType,
    provider: bool = False,
    fail_closed: bool = False,
    calibrated: bool = False,
    classification: CiboCalibrationClassification | None = None,
    blocker: tuple[str, ...],
    calibration_artifact_sha256: str | None = None,
) -> CiboToolCalibrationMatrixRow:
    tool = next(item for item in CE2I_TOOL_REGISTRY if item.code == code)
    resolved_classification = classification or (
        CiboCalibrationClassification.PROVIDER_ECONOMICS_REQUIRED
        if provider
        else CiboCalibrationClassification.CALIBRATION_UNAVAILABLE
    )
    return CiboToolCalibrationMatrixRow(
        tool_code=code,
        implemented=tool.maturity is not ToolMaturity.ARCHITECTURE_ONLY,
        calibrated=calibrated,
        calibration_source=source,
        calibration_type=kind,
        provider_economics_required=provider,
        fail_closed=fail_closed,
        oos_ready=False,
        certification_ready=False,
        classification=resolved_classification,
        blocker=blocker,
        calibration_artifact_sha256=calibration_artifact_sha256,
    )


CIBO_T01_T20_CALIBRATION_MATRIX: tuple[CiboToolCalibrationMatrixRow, ...] = (
    _row("T01", source=(_P18, _PROVIDER), kind=CiboCalibrationType.ECONOMIC_PROVIDER_BOUND, provider=True, fail_closed=True, blocker=("CALIBRATED_EXECUTION_ECONOMICS_REQUIRED",)),
    _row("T02", source=(_P18, *_P18_ARTIFACTS, _P19_WFO), kind=CiboCalibrationType.CAUSAL_NORMALIZED, blocker=("STRUCTURAL_LEVERAGE_BURNED_CALIBRATION_PENDING",)),
    _row("T03", source=(_PROVIDER, _P20), kind=CiboCalibrationType.ECONOMIC_PROVIDER_BOUND, provider=True, fail_closed=True, blocker=("PROVIDER_MARGIN_ECONOMICS_REQUIRED", "EQUIVALENT_EXPRESSION_UNIVERSE_NOT_CERTIFIED")),
    _row(
        "T04",
        source=(_P18, _P19, _P19_WFO, "phase19:phase20-train-expectation-priors"),
        kind=CiboCalibrationType.CAUSAL_NORMALIZED,
        provider=True,
        calibrated=True,
        classification=CiboCalibrationClassification.CALIBRATED_CAUSAL,
        blocker=("T04_USD_ECONOMIC_PENDING_PROVIDER_ECONOMICS",),
        calibration_artifact_sha256=burned_t04_t10_calibration_sha256(),
    ),
    _row("T05", source=(_P19, _P20), kind=CiboCalibrationType.CAUSAL_NORMALIZED, blocker=("CAPITAL_LIFECYCLE_CALIBRATION_PENDING",)),
    _row("T06", source=(_P19, _P20), kind=CiboCalibrationType.CAUSAL_NORMALIZED, blocker=("REALIZED_PROFIT_EXPANSION_CALIBRATION_PENDING",)),
    _row("T07", source=(_P19, _P20), kind=CiboCalibrationType.CAUSAL_NORMALIZED, blocker=("PROTECTED_FLOOR_CALIBRATION_PENDING",)),
    _row("T08", source=(_P19, "burned:phase19:overlap-dependence"), kind=CiboCalibrationType.CAUSAL_NORMALIZED, blocker=("FACTOR_NETTING_CALIBRATION_PENDING",)),
    _row("T09", source=(_P19, _P19_WFO), kind=CiboCalibrationType.CAUSAL_NORMALIZED, blocker=("CAUSAL_COMPETITION_CALIBRATION_PENDING",)),
    _row(
        "T10",
        source=(_P19, _P19_WFO, "phase19:phase20-train-expectation-priors"),
        kind=CiboCalibrationType.CAUSAL_NORMALIZED,
        provider=True,
        calibrated=True,
        classification=CiboCalibrationClassification.CALIBRATED_CAUSAL,
        blocker=("USD_OUTPUT_PER_CAPITAL_TIME_PENDING_PROVIDER_ECONOMICS",),
        calibration_artifact_sha256=burned_t04_t10_calibration_sha256(),
    ),
    _row("T11", source=(_PROVIDER, _P20), kind=CiboCalibrationType.ECONOMIC_PROVIDER_BOUND, provider=True, fail_closed=True, blocker=("SPREAD_COMMISSION_SLIPPAGE_CALIBRATION_REQUIRED",)),
    _row("T12", source=(_P19, "burned:phase19:temporal-stability"), kind=CiboCalibrationType.CAUSAL_NORMALIZED, blocker=("CAUSAL_REGIME_BOUNDARIES_CALIBRATION_PENDING",)),
    _row("T13", source=(_P19_WFO, _P20), kind=CiboCalibrationType.CAUSAL_NORMALIZED, blocker=("DRAWDOWN_RESERVE_CALIBRATION_PENDING",)),
    _row("T14", source=(_P18, *_P18_ARTIFACTS, _P20), kind=CiboCalibrationType.CAUSAL_NORMALIZED, blocker=("DERISK_TRIGGER_CALIBRATION_PENDING",)),
    _row("T15", source=(_P19, _P20), kind=CiboCalibrationType.CAUSAL_NORMALIZED, blocker=("OPTIONALITY_VALUE_CALIBRATION_PENDING",)),
    _row("T16", source=(_PROVIDER, _P20), kind=CiboCalibrationType.INSTRUMENT_CAPABILITY, provider=True, fail_closed=True, blocker=("CERTIFIED_HEDGE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE", "HEDGE_COST_AND_BASIS_ECONOMICS_REQUIRED")),
    _row("T17", source=(_PROVIDER, _P20), kind=CiboCalibrationType.INSTRUMENT_CAPABILITY, provider=True, fail_closed=True, blocker=("CERTIFIED_LIMITED_DOWNSIDE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE",)),
    _row("T18", source=(_P19, _P19_WFO), kind=CiboCalibrationType.CAUSAL_NORMALIZED, blocker=("CROSS_TRADER_ALLOCATION_CALIBRATION_PENDING",)),
    _row("T19", source=(_P19, _P20), kind=CiboCalibrationType.CONTRACT_INTEGRITY, blocker=("RESERVATION_EMPIRICAL_CALIBRATION_PENDING",)),
    _row("T20", source=(_P19, _P20), kind=CiboCalibrationType.CONTRACT_INTEGRITY, blocker=("RELEASE_EMPIRICAL_CALIBRATION_PENDING",)),
)


def validate_calibration_matrix() -> None:
    canonical = tuple(f"T{index:02d}" for index in range(1, 21))
    observed = tuple(row.tool_code for row in CIBO_T01_T20_CALIBRATION_MATRIX)
    if observed != canonical:
        raise CiboCapitalManagementError(
            "calibration matrix must contain exactly canonical T01..T20"
        )
    if any(row.certification_ready for row in CIBO_T01_T20_CALIBRATION_MATRIX):
        raise CiboCapitalManagementError(
            "pre-calibration matrix cannot claim certification readiness"
        )
