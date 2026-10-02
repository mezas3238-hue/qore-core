from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capability_exam_cognitive_coverage import (
    EXPECTED_FACULTIES,
    EXPECTED_TOOLS,
    CiboCapabilityCognitiveCoverageReceipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    CiboEconomicCertificationStatus,
)
from qore.infrastructure.cibo_reused_holdout_capability_exam import (
    InfrastructureCapabilityExamReport,
    PerformanceMetrics,
    ToolAuditRow,
    ToolRuntimeStatus,
)
from qore.infrastructure.cibo_usd60_capability_certification import (
    CAPABILITY_CERTIFICATION_SCOPE,
    CAPABILITY_EVIDENCE_CLASS,
    assess_cibo_capability_economic_certification,
    build_cibo_usd60_capability_certification_receipt,
)

NOW = datetime(2026, 10, 2, 21, 45, tzinfo=UTC)
HEAD = "6b8a74b5170d687e56110302b5bf7ac4e7a13e8d"


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


def _metrics(lane: str, *, executed: int, ending: str) -> PerformanceMetrics:
    ending_decimal = Decimal(ending)
    return PerformanceMetrics(
        lane=lane,
        opportunity_count=10,
        executed_count=executed,
        rejected_or_unexpressible_count=10 - executed,
        initial_capital_usd=Decimal("60"),
        ending_capital_usd=ending_decimal,
        net_realized_pnl_usd=ending_decimal - Decimal("60"),
        peak_capital_usd=max(Decimal("60"), ending_decimal),
        minimum_capital_usd=Decimal("54"),
        max_realized_drawdown_usd=Decimal("6"),
        gross_profit_usd=Decimal("12"),
        gross_loss_usd=Decimal("7"),
        profit_factor=Decimal("1.714285714285714285714285714"),
        trading_days=4,
        trader_pnl_usd=(("VT31_NAS100", ending_decimal - Decimal("60")),),
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
            reason="runtime-applied" if code in core else "evaluated-fail-closed",
        )
        for code in EXPECTED_TOOLS
    )


def _report(*, executed: int = 2) -> InfrastructureCapabilityExamReport:
    gates = (
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
        ("T01_T20_RUNTIME_INTEGRATION_COMPLETE", True),
    )
    return InfrastructureCapabilityExamReport(
        exam_id="CIBO_REUSED_HOLDOUT_INFRASTRUCTURE_CAPABILITY_EXAM_V1",
        validation_mode=CAPABILITY_EVIDENCE_CLASS,
        candidate_id="CIBO_USD60_6M_HOLDOUT_2014-10-19_2015-04-19_V4",
        source_batch_sha256="sha256:" + "a" * 64,
        replay_started_at=NOW,
        cognitive_functional_coverage=_coverage(),
        minimal_seed_baseline=_metrics("MINIMAL_SEED_ONLY", executed=1, ending="61"),
        full_cibo=_metrics("FULL_CIBO_CORE", executed=executed, ending="65"),
        ending_capital_delta_usd=Decimal("4"),
        net_pnl_delta_usd=Decimal("4"),
        drawdown_improvement_usd=Decimal("0"),
        profit_factor_delta=Decimal("0"),
        tool_audit=_audit(),
        gates=gates,
        infrastructure_certified=True,
    )


def test_reused_dual_pass_builds_nonfresh_capability_certification() -> None:
    receipt = build_cibo_usd60_capability_certification_receipt(
        report=_report(),
        integrated_git_sha=HEAD,
        workflow_run_id=37067905657,
        qualified_at=NOW,
    )
    decision = assess_cibo_capability_economic_certification(receipt)

    assert receipt.evidence_class == "NON_CERTIFYING_REUSED_HOLDOUT"
    assert receipt.certification_scope == CAPABILITY_CERTIFICATION_SCOPE
    assert receipt.usd60_survival_passed is True
    assert receipt.maximum_capability_passed is True
    assert receipt.scientific_freshness_claimed is False
    assert receipt.fresh_oos_generalization_claimed is False
    assert decision.status is CiboEconomicCertificationStatus.CERTIFIED
    assert decision.evidence_class == CAPABILITY_EVIDENCE_CLASS
    assert decision.fresh_oos_generalization_claimed is False


def test_passive_survival_cannot_emit_capability_certification() -> None:
    report = _report(executed=0)
    report = replace(
        report,
        full_cibo=replace(
            report.full_cibo,
            executed_count=0,
            rejected_or_unexpressible_count=10,
        ),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="strict dual-objective PASS",
    ):
        build_cibo_usd60_capability_certification_receipt(
            report=report,
            integrated_git_sha=HEAD,
            workflow_run_id=37067905657,
            qualified_at=NOW,
        )


def test_capability_policy_identity_is_exact_head_bound() -> None:
    first = build_cibo_usd60_capability_certification_receipt(
        report=_report(),
        integrated_git_sha=HEAD,
        workflow_run_id=37067905657,
        qualified_at=NOW,
    )
    second = build_cibo_usd60_capability_certification_receipt(
        report=_report(),
        integrated_git_sha="f" * 40,
        workflow_run_id=37067905658,
        qualified_at=NOW,
    )

    assert (
        first.capability_policy_identity_sha256
        != second.capability_policy_identity_sha256
    )
    assert first.fingerprint() != second.fingerprint()
