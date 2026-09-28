"""Empirical calibration registry for CIBO T01..T20.

Contract maturity is deliberately separate from calibration readiness. This
registry records what burned evidence exists and what still blocks a tool from
being called empirically calibrated for the USD60 six-month examination.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_tool_registry import CE2I_TOOL_REGISTRY


class CiboCalibrationState(StrEnum):
    SOURCE_IDENTIFIED = "SOURCE_IDENTIFIED"
    CALIBRATION_BLOCKED = "CALIBRATION_BLOCKED"
    CALIBRATED_ON_BURNED_DATA = "CALIBRATED_ON_BURNED_DATA"
    FRESH_OOS_PENDING = "FRESH_OOS_PENDING"
    FRESH_OOS_VALIDATED = "FRESH_OOS_VALIDATED"


@dataclass(frozen=True, slots=True)
class CiboToolCalibrationRecord:
    tool_code: str
    state: CiboCalibrationState
    burned_evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    holdout_outcomes_used: bool = False
    target_aware: bool = False

    def __post_init__(self) -> None:
        if self.tool_code not in {tool.code for tool in CE2I_TOOL_REGISTRY}:
            raise CiboCapitalManagementError("unknown CE2I calibration tool")
        if type(self.state) is not CiboCalibrationState:
            raise CiboCapitalManagementError(
                "calibration state must use canonical enum"
            )
        if not self.burned_evidence_refs:
            raise CiboCapitalManagementError(
                "calibration record requires burned evidence references"
            )
        if len(self.burned_evidence_refs) != len(set(self.burned_evidence_refs)):
            raise CiboCapitalManagementError(
                "calibration evidence refs must be unique"
            )
        if self.holdout_outcomes_used or self.target_aware:
            raise CiboCapitalManagementError(
                "calibration cannot use holdout outcomes or economic target"
            )
        if (
            self.state is CiboCalibrationState.CALIBRATION_BLOCKED
            and not self.blockers
        ):
            raise CiboCapitalManagementError(
                "blocked calibration must name its blocker"
            )
        if (
            self.state
            in {
                CiboCalibrationState.CALIBRATED_ON_BURNED_DATA,
                CiboCalibrationState.FRESH_OOS_PENDING,
                CiboCalibrationState.FRESH_OOS_VALIDATED,
            }
            and self.blockers
        ):
            raise CiboCapitalManagementError(
                "calibrated record cannot retain blockers"
            )


_PHASE18 = "burned:phase18:seven-lineage-chronological-replay"
_PHASE19 = "burned:phase19:integrated-common-window"
_PHASE19_WFO = "burned:phase19j:post-freeze-walk-forward"
_PROVIDER_GAP = "phase19:provider-economics-inventory:BLOCKED_PROVIDER_ECONOMICS"
_PHASE20_CONTRACT = "phase20:contract-and-failure-proof"


CIBO_TOOL_CALIBRATION_REGISTRY: tuple[CiboToolCalibrationRecord, ...] = (
    CiboToolCalibrationRecord(
        "T01",
        CiboCalibrationState.CALIBRATION_BLOCKED,
        (_PHASE18, _PROVIDER_GAP),
        ("CALIBRATED_EXECUTION_ECONOMICS_REQUIRED",),
    ),
    CiboToolCalibrationRecord(
        "T02",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE18, _PHASE19_WFO),
        ("STRUCTURAL_LEVERAGE_CALIBRATION_NOT_FROZEN",),
    ),
    CiboToolCalibrationRecord(
        "T03",
        CiboCalibrationState.CALIBRATION_BLOCKED,
        (_PROVIDER_GAP, _PHASE20_CONTRACT),
        (
            "CALIBRATED_EXECUTION_ECONOMICS_REQUIRED",
            "EQUIVALENT_EXPRESSION_UNIVERSE_NOT_CERTIFIED",
        ),
    ),
    CiboToolCalibrationRecord(
        "T04",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE18, _PHASE19_WFO, _PROVIDER_GAP),
        ("USD_TRUE_STOP_RISK_CALIBRATION_NOT_FROZEN",),
    ),
    CiboToolCalibrationRecord(
        "T05",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19, _PHASE20_CONTRACT),
        ("RECYCLE_UTILITY_CALIBRATION_NOT_FROZEN",),
    ),
    CiboToolCalibrationRecord(
        "T06",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19, _PHASE20_CONTRACT),
        ("PROFIT_FUNDED_EXPANSION_CALIBRATION_NOT_FROZEN",),
    ),
    CiboToolCalibrationRecord(
        "T07",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19, _PHASE20_CONTRACT),
        ("PROTECTED_CAPACITY_EXPANSION_CALIBRATION_NOT_FROZEN",),
    ),
    CiboToolCalibrationRecord(
        "T08",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19, "burned:phase19:overlap-dependence"),
        ("FACTOR_NETTING_CALIBRATION_NOT_FROZEN",),
    ),
    CiboToolCalibrationRecord(
        "T09",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19, _PHASE19_WFO),
        ("COMPETITION_POLICY_REQUIRES_ROBUST_RECALIBRATION",),
    ),
    CiboToolCalibrationRecord(
        "T10",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19, _PHASE19_WFO),
        ("CAPITAL_VELOCITY_CALIBRATION_NOT_FROZEN",),
    ),
    CiboToolCalibrationRecord(
        "T11",
        CiboCalibrationState.CALIBRATION_BLOCKED,
        (_PROVIDER_GAP, _PHASE20_CONTRACT),
        ("CALIBRATED_EXECUTION_ECONOMICS_REQUIRED",),
    ),
    CiboToolCalibrationRecord(
        "T12",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19, "burned:phase19:temporal-stability"),
        ("REGIME_BOUNDARIES_REQUIRE_BURNED_DATA_CALIBRATION",),
    ),
    CiboToolCalibrationRecord(
        "T13",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19_WFO, _PHASE20_CONTRACT),
        ("DRAWDOWN_RESERVE_CALIBRATION_NOT_FROZEN",),
    ),
    CiboToolCalibrationRecord(
        "T14",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE18, _PHASE20_CONTRACT),
        ("DERISK_TRIGGER_CALIBRATION_NOT_FROZEN",),
    ),
    CiboToolCalibrationRecord(
        "T15",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19, _PHASE20_CONTRACT),
        ("OPTIONALITY_VALUE_CALIBRATION_NOT_FROZEN",),
    ),
    CiboToolCalibrationRecord(
        "T16",
        CiboCalibrationState.CALIBRATION_BLOCKED,
        (_PROVIDER_GAP, _PHASE20_CONTRACT),
        ("CERTIFIED_HEDGE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE",),
    ),
    CiboToolCalibrationRecord(
        "T17",
        CiboCalibrationState.CALIBRATION_BLOCKED,
        (_PROVIDER_GAP, _PHASE20_CONTRACT),
        ("CERTIFIED_LIMITED_DOWNSIDE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE",),
    ),
    CiboToolCalibrationRecord(
        "T18",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19, _PHASE19_WFO),
        ("CROSS_TRADER_ALLOCATION_REQUIRES_ROBUST_RECALIBRATION",),
    ),
    CiboToolCalibrationRecord(
        "T19",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19, _PHASE20_CONTRACT),
        ("RESERVATION_UTILITY_CALIBRATION_NOT_FROZEN",),
    ),
    CiboToolCalibrationRecord(
        "T20",
        CiboCalibrationState.SOURCE_IDENTIFIED,
        (_PHASE19, _PHASE20_CONTRACT),
        ("RELEASE_UTILITY_CALIBRATION_NOT_FROZEN",),
    ),
)


def calibration_record(tool_code: str) -> CiboToolCalibrationRecord:
    matches = tuple(
        row for row in CIBO_TOOL_CALIBRATION_REGISTRY
        if row.tool_code == tool_code
    )
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
        row.state
        in {
            CiboCalibrationState.CALIBRATED_ON_BURNED_DATA,
            CiboCalibrationState.FRESH_OOS_PENDING,
            CiboCalibrationState.FRESH_OOS_VALIDATED,
        }
        for row in CIBO_TOOL_CALIBRATION_REGISTRY
    )
