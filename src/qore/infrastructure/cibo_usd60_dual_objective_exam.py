"""Non-compensatory dual-objective gate for the CIBO USD60 capability exam.

Owner-defined certification intent for the reused-holdout capability exam:

1. USD60_SURVIVAL:
   CIBO must keep the exact USD60 account economically alive across the six-month
   replay under QORE Risk, with reconciled accounting and no productive authority.

2. MAXIMUM_CAPABILITY:
   CIBO must actually manage capital (not merely abstain), traverse Cognitive
   Executive + CF01..CF19, account for CE2I T01..T20, preserve sole CIBO sizing
   authority, and demonstrate measured behavior versus the control lane.

The two objectives are a strict AND gate. Strong maximum-capability behavior
cannot compensate for ruin, and passive survival cannot compensate for failure
to exercise/integrate CIBO's capability surface.

This gate deliberately accepts a reused/burned historical holdout for this
infrastructure/capability purpose. It makes no fresh-OOS generalization claim and
grants no broker, LIVE, real-capital, production, Risk-bypass, or merge authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import CiboCapitalManagementError
from qore.infrastructure.cibo_reused_holdout_capability_exam import (
    InfrastructureCapabilityExamReport,
    ToolRuntimeStatus,
)


DUAL_OBJECTIVE_EXAM_ID = "CIBO_USD60_DUAL_OBJECTIVE_CAPABILITY_EXAM_V1"


class CiboUsd60DualObjectiveStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class CiboUsd60ObjectiveResult:
    objective_id: str
    passed: bool
    gates: tuple[tuple[str, bool], ...]
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.objective_id:
            raise CiboCapitalManagementError(
                "USD60 objective id is required"
            )
        if type(self.passed) is not bool:
            raise CiboCapitalManagementError(
                "USD60 objective passed must be bool"
            )
        if not self.gates:
            raise CiboCapitalManagementError(
                "USD60 objective requires gates"
            )
        if len(dict(self.gates)) != len(self.gates):
            raise CiboCapitalManagementError(
                "USD60 objective gates must be unique"
            )
        if any(type(value) is not bool for _, value in self.gates):
            raise CiboCapitalManagementError(
                "USD60 objective gate values must be bool"
            )
        expected_blockers = tuple(
            name for name, value in self.gates if not value
        )
        if self.blockers != expected_blockers:
            raise CiboCapitalManagementError(
                "USD60 objective blockers/gates drift"
            )
        if self.passed != (not self.blockers):
            raise CiboCapitalManagementError(
                "USD60 objective pass/blocker drift"
            )


@dataclass(frozen=True, slots=True)
class CiboUsd60DualObjectiveReport:
    exam_id: str
    survival: CiboUsd60ObjectiveResult
    maximum_capability: CiboUsd60ObjectiveResult
    status: CiboUsd60DualObjectiveStatus
    reused_holdout_allowed: bool
    scientific_freshness_required: bool
    fresh_oos_generalization_claimed: bool
    broker_mutation_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if self.exam_id != DUAL_OBJECTIVE_EXAM_ID:
            raise CiboCapitalManagementError(
                "USD60 dual-objective exam identity drift"
            )
        if not isinstance(self.survival, CiboUsd60ObjectiveResult):
            raise CiboCapitalManagementError(
                "USD60 survival result must be canonical"
            )
        if not isinstance(
            self.maximum_capability,
            CiboUsd60ObjectiveResult,
        ):
            raise CiboCapitalManagementError(
                "USD60 maximum-capability result must be canonical"
            )
        expected = (
            CiboUsd60DualObjectiveStatus.PASS
            if self.survival.passed and self.maximum_capability.passed
            else CiboUsd60DualObjectiveStatus.BLOCKED
        )
        if self.status is not expected:
            raise CiboCapitalManagementError(
                "USD60 dual-objective status is not strict AND"
            )
        if self.reused_holdout_allowed is not True:
            raise CiboCapitalManagementError(
                "USD60 capability exam must permit reused holdout"
            )
        if self.scientific_freshness_required is not False:
            raise CiboCapitalManagementError(
                "USD60 capability exam must not require fresh holdout"
            )
        if self.fresh_oos_generalization_claimed is not False:
            raise CiboCapitalManagementError(
                "USD60 reused-holdout exam cannot claim fresh generalization"
            )
        if any(
            (
                self.broker_mutation_authorized,
                self.live_authorized,
                self.real_capital_authorized,
                self.production_authorized,
                self.merge_authorized,
            )
        ):
            raise CiboCapitalManagementError(
                "USD60 dual-objective exam cannot grant productive authority"
            )


def assess_cibo_usd60_dual_objective_exam(
    report: InfrastructureCapabilityExamReport,
) -> CiboUsd60DualObjectiveReport:
    """Assess survival and maximum capability as independent non-compensatory gates."""

    if not isinstance(report, InfrastructureCapabilityExamReport):
        raise CiboCapitalManagementError(
            "USD60 dual-objective gate requires canonical capability report"
        )

    gate_map = dict(report.gates)
    survival_gates = (
        (
            "EXACT_USD60_INITIAL_CAPITAL",
            report.full_cibo.initial_capital_usd == Decimal("60"),
        ),
        (
            "SIX_MONTH_PROTOCOL_SURFACE",
            gate_map.get("SIX_MONTH_PROTOCOL_SURFACE") is True,
        ),
        (
            "ACCOUNT_SURVIVED_ENDING_CAPITAL_POSITIVE",
            report.full_cibo.ending_capital_usd > 0,
        ),
        (
            "NO_INTRAPERIOD_RUIN",
            report.full_cibo.minimum_capital_usd > 0,
        ),
        (
            "ACCOUNTING_RESIDUAL_ZERO",
            gate_map.get("ACCOUNTING_RESIDUAL_ZERO") is True,
        ),
        (
            "QORE_RISK_SOVEREIGN",
            gate_map.get("RISK_SOVEREIGNTY") is True,
        ),
        (
            "FLOATING_PNL_NOT_FUNDING",
            gate_map.get("FLOATING_PNL_NOT_FUNDING") is True,
        ),
        (
            "BROKER_MUTATION_ZERO",
            gate_map.get("BROKER_MUTATION_ZERO") is True,
        ),
    )
    survival = _objective("USD60_SURVIVAL", survival_gates)

    by_tool = {item.tool_code: item for item in report.tool_audit}
    exact_tools = tuple(by_tool) == tuple(
        f"T{index:02d}" for index in range(1, 21)
    )
    no_missing_runtime = (
        exact_tools
        and all(
            item.status is not ToolRuntimeStatus.NOT_INTEGRATED
            for item in report.tool_audit
        )
    )
    all_tools_accounted = (
        exact_tools
        and all(bool(item.reason.strip()) for item in report.tool_audit)
    )
    core_lifecycle_applied = exact_tools and all(
        by_tool[code].status is ToolRuntimeStatus.APPLIED
        for code in ("T01", "T12", "T19", "T20")
    )

    coverage = report.cognitive_functional_coverage
    maximum_gates = (
        ("COGNITIVE_EXECUTIVE_USED", coverage.cognitive_used),
        (
            "CF01_CF19_CONSULTED",
            coverage.all_functional_faculties_consulted,
        ),
        (
            "CE2I_T01_T20_REGISTERED",
            coverage.all_ce2i_tools_registered,
        ),
        (
            "CIBO_SOLE_SIZING_AUTHORITY",
            coverage.trader_sizing_authority == "NONE"
            and coverage.cibo_sizing_authority == "CIBO_CMA",
        ),
        (
            "QORE_RISK_REMAINS_SOVEREIGN",
            coverage.qore_risk_sovereign,
        ),
        (
            "CIBO_ACTUALLY_MANAGED_CAPITAL",
            report.full_cibo.executed_count > 0,
        ),
        (
            "T01_T20_ACCOUNTED_WITH_REASON",
            all_tools_accounted,
        ),
        (
            "T01_T20_RUNTIME_INTEGRATION_COMPLETE",
            no_missing_runtime,
        ),
        (
            "CORE_CAPITAL_LIFECYCLE_APPLIED",
            core_lifecycle_applied,
        ),
        (
            "BASELINE_COMPARISON_COMPLETE",
            gate_map.get("BASELINE_COMPARISON_COMPLETE") is True,
        ),
        (
            "PERFORMANCE_DIFFERENCE_MEASURED",
            gate_map.get("PERFORMANCE_DIFFERENCE_MEASURED") is True,
        ),
        (
            "SETTLEMENT_RELEASE_RECONCILED",
            gate_map.get("SETTLEMENT_RELEASE_RECONCILED") is True,
        ),
    )
    maximum = _objective("MAXIMUM_CAPABILITY", maximum_gates)

    status = (
        CiboUsd60DualObjectiveStatus.PASS
        if survival.passed and maximum.passed
        else CiboUsd60DualObjectiveStatus.BLOCKED
    )
    return CiboUsd60DualObjectiveReport(
        exam_id=DUAL_OBJECTIVE_EXAM_ID,
        survival=survival,
        maximum_capability=maximum,
        status=status,
        reused_holdout_allowed=True,
        scientific_freshness_required=False,
        fresh_oos_generalization_claimed=False,
    )


def _objective(
    objective_id: str,
    gates: tuple[tuple[str, bool], ...],
) -> CiboUsd60ObjectiveResult:
    blockers = tuple(name for name, value in gates if not value)
    return CiboUsd60ObjectiveResult(
        objective_id=objective_id,
        passed=not blockers,
        gates=gates,
        blockers=blockers,
    )
