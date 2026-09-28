"""Canonical empirical calibration matrix for CIBO T01..T20.

Engineering/contract maturity is deliberately separate from calibration and
economic certification.  Only burned evidence may move a tool through
calibration.  The preregistered 2017H1 holdout is forbidden as a calibration
source.
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


class CiboCalibrationState(StrEnum):
    CALIBRATED_CAUSAL = "CALIBRATED_CAUSAL"
    CALIBRATED_ECONOMIC = "CALIBRATED_ECONOMIC"
    PROVIDER_ECONOMICS_REQUIRED = "PROVIDER_ECONOMICS_REQUIRED"
    CALIBRATION_UNAVAILABLE = "CALIBRATION_UNAVAILABLE"
    OOS_READY = "OOS_READY"
    CERTIFICATION_READY = "CERTIFICATION_READY"
    FAIL_CLOSED = "FAIL_CLOSED"


class CiboCalibrationType(StrEnum):
    CAUSAL_NORMALIZED = "CAUSAL_NORMALIZED"
    ECONOMIC = "ECONOMIC"
    MIXED_CAUSAL_AND_ECONOMIC = "MIXED_CAUSAL_AND_ECONOMIC"
    CONTRACT_ONLY = "CONTRACT_ONLY"


@dataclass(frozen=True, slots=True)
class CiboToolCalibrationRecord:
    tool_code: str
    state: CiboCalibrationState
    calibration_type: CiboCalibrationType
    calibration_sources: tuple[str, ...]
    provider_economics_required: bool
    fail_closed: bool
    oos_ready: bool
    certification_ready: bool
    blockers: tuple[str, ...]
    calibration_artifact_sha256: str | None = None
    holdout_outcomes_used: bool = False
    target_aware: bool = False

    def __post_init__(self) -> None:
        canonical = {tool.code for tool in CE2I_TOOL_REGISTRY}
        if self.tool_code not in canonical:
            raise CiboCapitalManagementError("unknown CE2I calibration tool")
        if type(self.state) is not CiboCalibrationState:
            raise CiboCapitalManagementError("invalid calibration state")
        if type(self.calibration_type) is not CiboCalibrationType:
            raise CiboCapitalManagementError("invalid calibration type")
        if not self.calibration_sources:
            raise CiboCapitalManagementError(
                "calibration record requires evidence/source references"
            )
        if len(self.calibration_sources) != len(set(self.calibration_sources)):
            raise CiboCapitalManagementError(
                "calibration source references must be unique"
            )
        for name in (
            "provider_economics_required",
            "fail_closed",
            "oos_ready",
            "certification_ready",
            "holdout_outcomes_used",
            "target_aware",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")
        if self.holdout_outcomes_used:
            raise CiboCapitalManagementError(
                "2017H1/fresh holdout outcomes are forbidden in calibration"
            )
        if self.target_aware:
            raise CiboCapitalManagementError(
                "calibration cannot contain an economic target"
            )
        calibrated = self.state in {
            CiboCalibrationState.CALIBRATED_CAUSAL,
            CiboCalibrationState.CALIBRATED_ECONOMIC,
            CiboCalibrationState.OOS_READY,
            CiboCalibrationState.CERTIFICATION_READY,
        }
        if calibrated and not self.calibration_artifact_sha256:
            raise CiboCapitalManagementError(
                "calibrated state requires a sealed calibration artifact hash"
            )
        if self.certification_ready and self.state is not CiboCalibrationState.CERTIFICATION_READY:
            raise CiboCapitalManagementError(
                "certification_ready requires CERTIFICATION_READY state"
            )
        if self.oos_ready and self.state not in {
            CiboCalibrationState.OOS_READY,
            CiboCalibrationState.CERTIFICATION_READY,
        }:
            raise CiboCapitalManagementError(
                "oos_ready requires OOS_READY/CERTIFICATION_READY state"
            )
        if self.state in {
            CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED,
            CiboCalibrationState.CALIBRATION_UNAVAILABLE,
            CiboCalibrationState.FAIL_CLOSED,
        } and not self.blockers:
            raise CiboCapitalManagementError(
                "blocked/unavailable calibration must name blockers"
            )

    @property
    def implemented(self) -> bool:
        tool = next(tool for tool in CE2I_TOOL_REGISTRY if tool.code == self.tool_code)
        return tool.maturity is not ToolMaturity.ARCHITECTURE_ONLY

    @property
    def calibrated(self) -> bool:
        return self.state in {
            CiboCalibrationState.CALIBRATED_CAUSAL,
            CiboCalibrationState.CALIBRATED_ECONOMIC,
            CiboCalibrationState.OOS_READY,
            CiboCalibrationState.CERTIFICATION_READY,
        }


_PHASE18 = "burned:phase18:seven-lineage-chronological-replay"
_PHASE19 = "burned:phase19:integrated-common-window"
_PHASE19_WFO = "burned:phase19j:post-freeze-walk-forward"
_PROVIDER_GAP = "provider-economics:current-demo-terms-and-historical-gap"
_PHASE20_CONTRACT = "phase20:contract-and-failure-proof"


def _row(
    code: str,
    state: CiboCalibrationState,
    kind: CiboCalibrationType,
    sources: tuple[str, ...],
    blockers: tuple[str, ...],
    *,
    provider: bool = False,
    calibration_artifact_sha256: str | None = None,
) -> CiboToolCalibrationRecord:
    return CiboToolCalibrationRecord(
        tool_code=code,
        state=state,
        calibration_type=kind,
        calibration_sources=sources,
        provider_economics_required=provider,
        fail_closed=True,
        oos_ready=False,
        certification_ready=False,
        blockers=blockers,
        calibration_artifact_sha256=calibration_artifact_sha256,
    )


CIBO_TOOL_CALIBRATION_REGISTRY: tuple[CiboToolCalibrationRecord, ...] = (
    _row("T01", CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED, CiboCalibrationType.MIXED_CAUSAL_AND_ECONOMIC, (_PHASE18, _PROVIDER_GAP), ("CALIBRATED_EXECUTION_ECONOMICS_REQUIRED",), provider=True),
    _row("T02", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE18, _PHASE19_WFO), ("STRUCTURAL_LEVERAGE_CALIBRATION_NOT_FROZEN",)),
    _row("T03", CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED, CiboCalibrationType.ECONOMIC, (_PROVIDER_GAP, _PHASE20_CONTRACT), ("CALIBRATED_EXECUTION_ECONOMICS_REQUIRED", "EQUIVALENT_EXPRESSION_UNIVERSE_NOT_CERTIFIED"), provider=True),
    _row("T04", CiboCalibrationState.CALIBRATED_CAUSAL, CiboCalibrationType.MIXED_CAUSAL_AND_ECONOMIC, (_PHASE18, _PHASE19_WFO, _PROVIDER_GAP), ("USD_TRUE_STOP_RISK_REQUIRES_PROVIDER_ECONOMICS",), provider=True, calibration_artifact_sha256=burned_t04_t10_calibration_sha256()),
    _row("T05", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE20_CONTRACT), ("RECYCLE_UTILITY_CALIBRATION_NOT_FROZEN",)),
    _row("T06", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE20_CONTRACT), ("REALIZED_PROFIT_EXPANSION_CALIBRATION_NOT_FROZEN",)),
    _row("T07", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.MIXED_CAUSAL_AND_ECONOMIC, (_PHASE19, _PHASE20_CONTRACT), ("VERIFIED_PROTECTED_ECONOMIC_FLOOR_CALIBRATION_NOT_FROZEN",), provider=True),
    _row("T08", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, "burned:phase19:overlap-dependence"), ("FACTOR_NETTING_CALIBRATION_NOT_FROZEN",)),
    _row("T09", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE19_WFO), ("CAUSAL_COMPETITION_POLICY_NOT_FROZEN",)),
    _row("T10", CiboCalibrationState.CALIBRATED_CAUSAL, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE19_WFO), ("USD_OUTPUT_PER_CAPITAL_TIME_PENDING_PROVIDER_ECONOMICS",), provider=True, calibration_artifact_sha256=burned_t04_t10_calibration_sha256()),
    _row("T11", CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED, CiboCalibrationType.MIXED_CAUSAL_AND_ECONOMIC, (_PROVIDER_GAP, _PHASE20_CONTRACT), ("SPREAD_COMMISSION_SLIPPAGE_AND_LATENCY_CALIBRATION_REQUIRED",), provider=True),
    _row("T12", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, "burned:phase19:temporal-stability"), ("CAUSAL_REGIME_BOUNDARIES_NOT_FROZEN",)),
    _row("T13", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19_WFO, _PHASE20_CONTRACT), ("DRAWDOWN_RESERVE_CALIBRATION_NOT_FROZEN",)),
    _row("T14", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE18, _PHASE20_CONTRACT), ("DERISK_TRIGGER_CALIBRATION_NOT_FROZEN",)),
    _row("T15", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE20_CONTRACT), ("OPTIONALITY_VALUE_CALIBRATION_NOT_FROZEN",)),
    _row("T16", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.ECONOMIC, (_PROVIDER_GAP, _PHASE20_CONTRACT), ("CERTIFIED_HEDGE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE", "HEDGE_COST_AND_BASIS_ECONOMICS_NOT_CERTIFIED"), provider=True),
    _row("T17", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.ECONOMIC, (_PROVIDER_GAP, _PHASE20_CONTRACT), ("CERTIFIED_LIMITED_DOWNSIDE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE", "PRICING_SETTLEMENT_EXECUTION_NOT_CERTIFIED"), provider=True),
    _row("T18", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE19_WFO), ("CROSS_TRADER_ALLOCATION_POLICY_NOT_FROZEN",)),
    _row("T19", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CONTRACT_ONLY, (_PHASE19, _PHASE20_CONTRACT), ("RESERVATION_EMPIRICAL_CALIBRATION_NOT_FROZEN",)),
    _row("T20", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.CONTRACT_ONLY, (_PHASE19, _PHASE20_CONTRACT), ("RELEASE_EMPIRICAL_CALIBRATION_NOT_FROZEN",)),
)


def calibration_record(tool_code: str) -> CiboToolCalibrationRecord:
    matches = tuple(row for row in CIBO_TOOL_CALIBRATION_REGISTRY if row.tool_code == tool_code)
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "calibration registry must contain exactly one tool record"
        )
    return matches[0]


def calibration_registry_complete() -> bool:
    canonical = tuple(f"T{index:02d}" for index in range(1, 21))
    return tuple(row.tool_code for row in CIBO_TOOL_CALIBRATION_REGISTRY) == canonical


def all_tools_ready_for_fresh_oos() -> bool:
    return calibration_registry_complete() and all(
        row.oos_ready for row in CIBO_TOOL_CALIBRATION_REGISTRY
    )
