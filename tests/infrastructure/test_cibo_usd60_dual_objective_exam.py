from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_capability_exam_cognitive_coverage import (
    EXPECTED_FACULTIES,
    EXPECTED_TOOLS,
    CiboCapabilityCognitiveCoverageReceipt,
)
from qore.infrastructure.cibo_reused_holdout_capability_exam import (
    InfrastructureCapabilityExamReport,
    PerformanceMetrics,
    ToolAuditRow,
    ToolRuntimeStatus,
)
from qore.infrastructure.cibo_usd60_dual_objective_exam import (
    CiboUsd60DualObjectiveStatus,
    assess_cibo_usd60_dual_objective_exam,
)

NOW = datetime(2026, 10, 2, 20, 0, tzinfo=UTC)


def _coverage() -> CiboCapabilityCognitiveCoverageReceipt:
    faculties = tuple(item.value for item in EXPECTED_FACULTIES)
    return CiboCapabilityCognitiveCoverageReceipt(
        source_batch_sha256="sha256:" + "a" * 64,
        observed_at=NOW,
        reasoning_route_tier="sol-high",
        reasoning_mode="high",
        reasoning_route_reason="material-analysis-or-contradiction",
        mission_code="cibo-usd60-capability-exam",
        mission_faculties=faculties,
        coordinated_faculties=faculties,
        coordination_disposition="request",
        executive_directive="request-evidence",
        ce2i_tool_codes=EXPECTED_TOOLS,
        trader_sizing_authority="NONE",
        cibo_sizing_authority="CIBO_CMA",
        qore_risk_sovereign=True,
        cognitive_used=True,
        all_functional_faculties_consulted=True,
        all_ce2i_tools_registered=True,
    )


def _metrics(
    lane: str,
    *,
    executed: int,
    ending: str,
    minimum: str,
) -> PerformanceMetrics:
    return PerformanceMetrics(
        lane=lane,
        opportunity_count=10,
        executed_count=executed,
        rejected_or_unexpressible_count=10 - executed,
        initial_capital_usd=Decimal("60"),
        ending_capital_usd=Decimal(ending),
        net_realized_pnl_usd=Decimal(ending) - Decimal("60"),
        peak_capital_usd=max(Decimal("60"), Decimal(ending)),
        minimum_capital_usd=Decimal(minimum),
        max_realized_drawdown_usd=Decimal("5"),
        gross_profit_usd=Decimal("12"),
        gross_loss_usd=Decimal("7"),
        profit_factor=Decimal("1.714285714285714285714285714"),
        trading_days=4,
        trader_pnl_usd=(("VT31_NAS100", Decimal(ending) - Decimal("60")),),
    )


def _audit() -> tuple[ToolAuditRow, ...]:
    core = {"T01", "T12", "T19", "T20"}
    return tuple(
        ToolAuditRow(
            tool_code=code,
            tool_name=f"tool-{code}",
            status=(
                ToolRuntimeStatus.APPLIED
                if code in core
                else ToolRuntimeStatus.FAIL_CLOSED
            ),
            enabled_epochs=1,
            regime_blocked_epochs=0,
            applied_count=1 if code in core else 0,
            abstain_count=0,
            fail_closed_count=0 if code in core else 1,
            reason=(
                "runtime-applied"
                if code in core
                else "evaluated-fail-closed-by-precondition"
            ),
        )
        for code in EXPECTED_TOOLS
    )


def _gates(*, runtime_complete: bool = True) -> tuple[tuple[str, bool], ...]:
    return (
        ("EXACT_USD60_INITIAL_CAPITAL", True),
        ("COGNITIVE_EXECUTIVE_USED", True),
        ("CF01_CF19_FUNCTIONAL_COVERAGE_COMPLETE", True),
        ("CE2I_T01_T20_REGISTRY_COVERAGE_COMPLETE", True),
        ("CIBO_SOLE_SIZING_AUTHORITY", True),
        ("EXACT_SEVEN_TRADER_LANES", True),
        ("SIX_MONTH_PROTOCOL_SURFACE", True),
        ("SURVIVAL", True),
        ("ACCOUNTING_RESIDUAL_ZERO", True),
        ("RISK_SOVEREIGNTY", True),
        ("SETTLEMENT_RELEASE_RECONCILED", True),
        ("BROKER_MUTATION_ZERO", True),
        ("FLOATING_PNL_NOT_FUNDING", True),
        ("BASELINE_COMPARISON_COMPLETE", True),
        ("PERFORMANCE_DIFFERENCE_MEASURED", True),
        ("T01_T20_ACCOUNTABILITY_COMPLETE", True),
        ("T01_T20_RUNTIME_INTEGRATION_COMPLETE", runtime_complete),
    )


def _report() -> InfrastructureCapabilityExamReport:
    gates = _gates()
    return InfrastructureCapabilityExamReport(
        exam_id="CIBO_REUSED_HOLDOUT_INFRASTRUCTURE_CAPABILITY_EXAM_V1",
        validation_mode="NON_CERTIFYING_REUSED_HOLDOUT",
        candidate_id="CIBO_USD60_6M_HOLDOUT_2014-10-19_2015-04-19_V4",
        source_batch_sha256="sha256:" + "a" * 64,
        replay_started_at=NOW,
        cognitive_functional_coverage=_coverage(),
        minimal_seed_baseline=_metrics(
            "MINIMAL_SEED_ONLY",
            executed=1,
            ending="61",
            minimum="54",
        ),
        full_cibo=_metrics(
            "FULL_CIBO_CORE",
            executed=1,
            ending="65",
            minimum="55",
        ),
        ending_capital_delta_usd=Decimal("4"),
        net_pnl_delta_usd=Decimal("4"),
        drawdown_improvement_usd=Decimal("0"),
        profit_factor_delta=Decimal("0"),
        tool_audit=_audit(),
        gates=gates,
        infrastructure_certified=True,
    )


def test_dual_objective_requires_survival_and_maximum_capability() -> None:
    result = assess_cibo_usd60_dual_objective_exam(_report())

    assert result.status is CiboUsd60DualObjectiveStatus.PASS
    assert result.survival.passed is True
    assert result.maximum_capability.passed is True
    assert result.reused_holdout_allowed is True
    assert result.scientific_freshness_required is False
    assert result.fresh_oos_generalization_claimed is False


def test_ruin_blocks_exam_even_when_maximum_capability_is_complete() -> None:
    report = _report()
    report = replace(
        report,
        full_cibo=replace(
            report.full_cibo,
            minimum_capital_usd=Decimal("0"),
        ),
    )

    result = assess_cibo_usd60_dual_objective_exam(report)

    assert result.status is CiboUsd60DualObjectiveStatus.BLOCKED
    assert result.survival.passed is False
    assert "NO_INTRAPERIOD_RUIN" in result.survival.blockers
    assert result.maximum_capability.passed is True


def test_passive_survival_cannot_compensate_for_missing_tool_integration() -> None:
    report = _report()
    audit = list(report.tool_audit)
    index = next(
        idx for idx, item in enumerate(audit) if item.tool_code == "T11"
    )
    audit[index] = replace(
        audit[index],
        status=ToolRuntimeStatus.NOT_INTEGRATED,
        fail_closed_count=0,
        reason="runtime-path-missing",
    )
    report = replace(
        report,
        tool_audit=tuple(audit),
        gates=_gates(runtime_complete=False),
        infrastructure_certified=False,
    )

    result = assess_cibo_usd60_dual_objective_exam(report)

    assert result.survival.passed is True
    assert result.maximum_capability.passed is False
    assert result.status is CiboUsd60DualObjectiveStatus.BLOCKED
    assert (
        "T01_T20_RUNTIME_INTEGRATION_COMPLETE"
        in result.maximum_capability.blockers
    )


def test_zero_managed_entries_fails_maximum_capability_even_if_account_survives() -> None:
    report = _report()
    report = replace(
        report,
        full_cibo=replace(
            report.full_cibo,
            executed_count=0,
            rejected_or_unexpressible_count=10,
            ending_capital_usd=Decimal("60"),
            net_realized_pnl_usd=Decimal("0"),
            minimum_capital_usd=Decimal("60"),
        ),
    )

    result = assess_cibo_usd60_dual_objective_exam(report)

    assert result.survival.passed is True
    assert result.maximum_capability.passed is False
    assert "CIBO_ACTUALLY_MANAGED_CAPITAL" in result.maximum_capability.blockers
