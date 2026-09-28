"""Canonical T01..T20 calibration / certification matrix.

Contract implementation, causal calibration and exact provider-economic
certification are deliberately separate axes. Fresh holdout outcomes are never
valid calibration inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
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
    PROVIDER_ECONOMIC = "PROVIDER_ECONOMIC"
    HYBRID = "HYBRID"
    CONTRACT_INVARIANT = "CONTRACT_INVARIANT"


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
    holdout_outcomes_used: bool = False
    target_aware: bool = False

    def __post_init__(self) -> None:
        if self.tool_code not in {tool.code for tool in CE2I_TOOL_REGISTRY}:
            raise CiboCapitalManagementError("unknown CE2I calibration tool")
        if type(self.state) is not CiboCalibrationState:
            raise CiboCapitalManagementError("non-canonical calibration state")
        if type(self.calibration_type) is not CiboCalibrationType:
            raise CiboCapitalManagementError("non-canonical calibration type")
        if not self.calibration_sources:
            raise CiboCapitalManagementError("calibration sources are required")
        if len(self.calibration_sources) != len(set(self.calibration_sources)):
            raise CiboCapitalManagementError("calibration sources must be unique")
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
        if self.holdout_outcomes_used or self.target_aware:
            raise CiboCapitalManagementError(
                "calibration cannot use fresh holdout outcomes or economic targets"
            )
        if self.certification_ready and not self.oos_ready:
            raise CiboCapitalManagementError(
                "certification-ready tool must also be OOS-ready"
            )
        if self.state is CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED:
            if not self.provider_economics_required or not self.blockers:
                raise CiboCapitalManagementError(
                    "provider-economic blocker must be explicit"
                )
        if self.state in {
            CiboCalibrationState.CALIBRATION_UNAVAILABLE,
            CiboCalibrationState.FAIL_CLOSED,
        } and not self.blockers:
            raise CiboCapitalManagementError(
                "unavailable/fail-closed calibration must name blocker"
            )
        if self.certification_ready and self.blockers:
            raise CiboCapitalManagementError(
                "certification-ready tool cannot retain blockers"
            )

    @property
    def implemented(self) -> bool:
        tool = next(item for item in CE2I_TOOL_REGISTRY if item.code == self.tool_code)
        return tool.maturity is not ToolMaturity.ARCHITECTURE_ONLY


_PHASE18 = "burned:phase18:seven-lineage-chronological-replay"
_PHASE19 = "burned:phase19:integrated-common-window"
_PHASE19_WFO = "burned:phase19j:post-freeze-walk-forward"
_PHASE19_DEP = "burned:phase19:overlap-dependence"
_PHASE19_TEMP = "burned:phase19:temporal-stability"
_PROVIDER_GAP = "phase19:provider-economics-inventory:BLOCKED_PROVIDER_ECONOMICS"
_PHASE20_CONTRACT = "phase20:contract-and-failure-proof"


def _row(
    code: str,
    state: CiboCalibrationState,
    kind: CiboCalibrationType,
    sources: tuple[str, ...],
    *,
    provider: bool = False,
    fail_closed: bool = True,
    oos_ready: bool = False,
    certification_ready: bool = False,
    blockers: tuple[str, ...] = (),
) -> CiboToolCalibrationRecord:
    return CiboToolCalibrationRecord(
        tool_code=code,
        state=state,
        calibration_type=kind,
        calibration_sources=sources,
        provider_economics_required=provider,
        fail_closed=fail_closed,
        oos_ready=oos_ready,
        certification_ready=certification_ready,
        blockers=blockers,
    )


# This matrix is intentionally conservative. SOURCE_IDENTIFIED is no longer a
# permitted status: a tool is either already causally/economically calibrated,
# explicitly waiting on provider economics, unavailable, OOS/certification
# ready, or fail-closed while burned-data calibration is still unfinished.
CIBO_TOOL_CALIBRATION_REGISTRY: tuple[CiboToolCalibrationRecord, ...] = (
    _row("T01", CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED, CiboCalibrationType.PROVIDER_ECONOMIC, (_PHASE18, _PROVIDER_GAP), provider=True, blockers=("CALIBRATED_EXECUTION_ECONOMICS_REQUIRED",)),
    _row("T02", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE18, _PHASE19_WFO), blockers=("STRUCTURAL_LEVERAGE_CALIBRATION_NOT_FROZEN",)),
    _row("T03", CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED, CiboCalibrationType.PROVIDER_ECONOMIC, (_PROVIDER_GAP, _PHASE20_CONTRACT), provider=True, blockers=("CALIBRATED_EXECUTION_ECONOMICS_REQUIRED", "EQUIVALENT_EXPRESSION_UNIVERSE_NOT_CERTIFIED")),
    _row("T04", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.HYBRID, (_PHASE18, _PHASE19_WFO, _PROVIDER_GAP), provider=True, blockers=("T04_R_NORMALIZED_CALIBRATION_NOT_FROZEN", "T04_USD_ECONOMIC_REQUIRES_PROVIDER_ECONOMICS")),
    _row("T05", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE20_CONTRACT), blockers=("RECYCLE_UTILITY_CALIBRATION_NOT_FROZEN",)),
    _row("T06", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE20_CONTRACT), blockers=("PROFIT_FUNDED_EXPANSION_CALIBRATION_NOT_FROZEN",)),
    _row("T07", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.HYBRID, (_PHASE19, _PHASE20_CONTRACT), provider=True, blockers=("PROTECTED_CAPACITY_EXPANSION_CALIBRATION_NOT_FROZEN",)),
    _row("T08", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE19_DEP), blockers=("FACTOR_NETTING_CALIBRATION_NOT_FROZEN",)),
    _row("T09", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE19_WFO), blockers=("COMPETITION_POLICY_REQUIRES_ROBUST_RECALIBRATION",)),
    _row("T10", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE19_WFO), blockers=("CAPITAL_VELOCITY_CALIBRATION_NOT_FROZEN",)),
    _row("T11", CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED, CiboCalibrationType.HYBRID, (_PROVIDER_GAP, _PHASE20_CONTRACT), provider=True, blockers=("CALIBRATED_EXECUTION_ECONOMICS_REQUIRED",)),
    _row("T12", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE19_TEMP), blockers=("REGIME_BOUNDARIES_REQUIRE_BURNED_DATA_CALIBRATION",)),
    _row("T13", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19_WFO, _PHASE20_CONTRACT), blockers=("DRAWDOWN_RESERVE_CALIBRATION_NOT_FROZEN",)),
    _row("T14", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.HYBRID, (_PHASE18, _PHASE20_CONTRACT), provider=True, blockers=("DERISK_TRIGGER_CALIBRATION_NOT_FROZEN",)),
    _row("T15", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE20_CONTRACT), blockers=("OPTIONALITY_VALUE_CALIBRATION_NOT_FROZEN",)),
    _row("T16", CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED, CiboCalibrationType.PROVIDER_ECONOMIC, (_PROVIDER_GAP, _PHASE20_CONTRACT), provider=True, blockers=("CERTIFIED_HEDGE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE", "HEDGE_COST_AND_MARGIN_ECONOMICS_REQUIRED")),
    _row("T17", CiboCalibrationState.CALIBRATION_UNAVAILABLE, CiboCalibrationType.PROVIDER_ECONOMIC, (_PROVIDER_GAP, _PHASE20_CONTRACT), provider=True, blockers=("CERTIFIED_LIMITED_DOWNSIDE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE",)),
    _row("T18", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CAUSAL_NORMALIZED, (_PHASE19, _PHASE19_WFO), blockers=("CROSS_TRADER_ALLOCATION_REQUIRES_ROBUST_RECALIBRATION",)),
    _row("T19", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CONTRACT_INVARIANT, (_PHASE19, _PHASE20_CONTRACT), blockers=("RESERVATION_EMPIRICAL_AUDIT_NOT_FROZEN",)),
    _row("T20", CiboCalibrationState.FAIL_CLOSED, CiboCalibrationType.CONTRACT_INVARIANT, (_PHASE19, _PHASE20_CONTRACT), blockers=("RELEASE_EMPIRICAL_AUDIT_NOT_FROZEN",)),
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


def all_tools_certification_ready() -> bool:
    return calibration_registry_complete() and all(
        row.certification_ready for row in CIBO_TOOL_CALIBRATION_REGISTRY
    )
