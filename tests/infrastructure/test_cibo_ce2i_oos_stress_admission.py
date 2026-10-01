from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_oos_stress_admission import (
    Ce2iOosStressScenarioMeta,
    Ce2iOosStressVerdict,
    T08OosStressEvidence,
    T09T18OosStressEvidence,
    T12OosStressEvidence,
    T13OosStressEvidence,
    evaluate_t08_oos_stress,
    evaluate_t09_t18_oos_stress,
    evaluate_t12_oos_stress,
    evaluate_t13_oos_stress,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_oos_ablation import (
    T08NettingShadowEpoch,
    assess_t08_fresh_oos_netting_ablation,
)
from qore.infrastructure.cibo_ce2i_phase20_t09_t18_scarcity_utility import (
    SCARCITY_UTILITY_CONTRACT_ID,
    Phase20ScarcityUtilityScope,
    Phase20T09T18ScarcityUtilityReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_utility import (
    T12_UTILITY_CONTRACT_ID,
    Phase20T12UtilityReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_policy import (
    T12_SHADOW_POLICY_ID,
    t12_shadow_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_oos_utility import (
    T13_UTILITY_CONTRACT_ID,
    Phase20T13UtilityReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_ID,
    t13_shadow_policy_sha256,
)
from qore.infrastructure.cibo_compound_adversarial_stress import (
    CompoundStressKind,
    CompoundStressScenario,
)
from qore.infrastructure.cibo_t09_t18_scarcity_safety_gate import (
    GATE_FROZEN_AT,
    GATE_SHA256,
    T09T18ScarcityCandidateVerdict,
    T09T18ScarcityGateReport,
    T09T18ScarcityStatus,
    T09T18ScarcityTool,
)
from qore.infrastructure.cibo_t09_t18_scarcity_safety_gate import (
    GATE_ID as SCARCITY_SAFETY_GATE_ID,
)

BASE = datetime(2026, 9, 30, 10, tzinfo=UTC)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _meta(
    kind: CompoundStressKind,
    index: int,
) -> Ce2iOosStressScenarioMeta:
    return Ce2iOosStressScenarioMeta(
        scenario=CompoundStressScenario(
            scenario_id=f"{kind.value}-{index}",
            kind=kind,
            severity=Decimal("1"),
            evidence_sha256=_sha(hex(index + 1)[2:]),
        ),
        stressed_population_sha256=_sha(str(index + 1)),
        protocol_binding_sha256=_sha("a"),
        scenario_preregistered_before_outcomes=True,
        stress_transform_non_improving=True,
    )


def _t08_epoch(index: int) -> T08NettingShadowEpoch:
    decision_at = BASE + timedelta(minutes=5 * index)
    return T08NettingShadowEpoch(
        epoch_id=f"epoch-{index}",
        decision_at=decision_at,
        shadow_sealed_at=decision_at + timedelta(milliseconds=10),
        outcome_observed_at=decision_at + timedelta(hours=1),
        baseline_selected_count=1,
        treatment_selected_count=2,
        baseline_realized_net_pnl_usd=Decimal("1"),
        treatment_realized_net_pnl_usd=Decimal("1.2"),
        baseline_peak_loss_usd=Decimal("5"),
        treatment_peak_loss_usd=Decimal("4"),
        treatment_gross_stop_risk_usd=Decimal("10"),
        treatment_netted_risk_usd=Decimal("8"),
        netting_credit_usd=Decimal("2"),
        risk_mapping_evidence_id=f"risk:{index}",
        correlation_evidence_id=f"corr:{index}",
        outcome_evidence_ids=(f"outcome:{index}",),
    )


def _t08_report():
    return assess_t08_fresh_oos_netting_ablation(
        tuple(_t08_epoch(index) for index in range(32))
    )


def _t12_report() -> Phase20T12UtilityReport:
    folds = tuple(Decimal("1") for _ in range(4))
    return Phase20T12UtilityReport(
        contract_id=T12_UTILITY_CONTRACT_ID,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        t12_policy_id=T12_SHADOW_POLICY_ID,
        t12_policy_sha256=t12_shadow_policy_sha256(),
        population_ready=True,
        decision_epochs=80,
        candidate_instances=200,
        treatment_selected_instances=80,
        control_selected_instances=80,
        candidate_outcome_coverage=Decimal("1"),
        treatment_selected_outcome_coverage=Decimal("1"),
        control_selected_outcome_coverage=Decimal("1"),
        treatment_net_delta_usd=Decimal("8"),
        control_net_delta_usd=Decimal("4"),
        treatment_settlement_cash_drawdown_usd=Decimal("3"),
        control_settlement_cash_drawdown_usd=Decimal("3"),
        treatment_capital_productivity=Decimal("1.2"),
        control_capital_productivity=Decimal("1"),
        fold_treatment_net_delta_usd=folds,
        fold_control_net_delta_usd=tuple(Decimal("0.5") for _ in range(4)),
        fold_incremental_net_delta_usd=tuple(
            Decimal("0.5") for _ in range(4)
        ),
        fresh_oos_utility_demonstrated=True,
        outcome_refit_performed=False,
        runtime_authority=False,
        blockers=(),
    )


def _t13_report() -> Phase20T13UtilityReport:
    return Phase20T13UtilityReport(
        contract_id=T13_UTILITY_CONTRACT_ID,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        t13_policy_id=T13_SHADOW_POLICY_ID,
        t13_policy_sha256=t13_shadow_policy_sha256(),
        population_ready=True,
        decision_epochs=80,
        candidate_instances=200,
        baseline_selected_instances=80,
        treatment_selected_instances=80,
        selection_changed_epochs=10,
        total_shadow_reserved_risk_usd=Decimal("10"),
        candidate_outcome_coverage=Decimal("1"),
        baseline_selected_outcome_coverage=Decimal("1"),
        treatment_selected_outcome_coverage=Decimal("1"),
        baseline_net_delta_usd=Decimal("4"),
        treatment_net_delta_usd=Decimal("6"),
        baseline_settlement_cash_drawdown_usd=Decimal("4"),
        treatment_settlement_cash_drawdown_usd=Decimal("3"),
        baseline_capital_productivity=Decimal("1"),
        treatment_capital_productivity=Decimal("1.2"),
        fold_baseline_net_delta_usd=tuple(
            Decimal("0.5") for _ in range(4)
        ),
        fold_treatment_net_delta_usd=tuple(
            Decimal("1") for _ in range(4)
        ),
        fresh_oos_utility_demonstrated=True,
        outcome_refit_performed=False,
        runtime_authority=False,
        blockers=(),
    )


def test_t08_stress_requires_every_scenario_to_keep_oos_utility() -> None:
    report = _t08_report()
    evidence = tuple(
        T08OosStressEvidence(meta=_meta(kind, index), report=report)
        for index, kind in enumerate(CompoundStressKind)
    )

    result = evaluate_t08_oos_stress(evidence)

    assert result.verdict is Ce2iOosStressVerdict.STRESS_ROBUST


def test_one_failed_t08_stress_scenario_falsifies() -> None:
    good = _t08_report()
    bad = assess_t08_fresh_oos_netting_ablation(
        tuple(
            replace(
                _t08_epoch(index),
                treatment_realized_net_pnl_usd=Decimal("0"),
            )
            for index in range(32)
        )
    )
    evidence = [
        T08OosStressEvidence(meta=_meta(kind, index), report=good)
        for index, kind in enumerate(CompoundStressKind)
    ]
    evidence[2] = replace(evidence[2], report=bad)

    result = evaluate_t08_oos_stress(tuple(evidence))

    assert result.verdict is Ce2iOosStressVerdict.FALSIFIED


def test_t12_canonical_reports_can_be_stress_admitted() -> None:
    report = _t12_report()
    evidence = tuple(
        T12OosStressEvidence(meta=_meta(kind, index), report=report)
        for index, kind in enumerate(CompoundStressKind)
    )

    result = evaluate_t12_oos_stress(evidence)

    assert result.verdict is Ce2iOosStressVerdict.STRESS_ROBUST


def test_t13_canonical_reports_can_be_stress_admitted() -> None:
    report = _t13_report()
    evidence = tuple(
        T13OosStressEvidence(meta=_meta(kind, index), report=report)
        for index, kind in enumerate(CompoundStressKind)
    )

    result = evaluate_t13_oos_stress(evidence)

    assert result.verdict is Ce2iOosStressVerdict.STRESS_ROBUST


def _scarcity_scope(tool_code: str) -> Phase20ScarcityUtilityScope:
    return Phase20ScarcityUtilityScope(
        tool_code=tool_code,
        population_ready=True,
        decision_epochs=80,
        candidate_instances=200,
        policy_selected_instances=80,
        baseline_selected_instances=80,
        candidate_outcome_coverage=Decimal("1"),
        policy_selected_outcome_coverage=Decimal("1"),
        baseline_selected_outcome_coverage=Decimal("1"),
        policy_net_delta_usd=Decimal("8"),
        baseline_net_delta_usd=Decimal("4"),
        policy_settlement_cash_drawdown_usd=Decimal("3"),
        baseline_settlement_cash_drawdown_usd=Decimal("3"),
        policy_capital_productivity=Decimal("1.2"),
        baseline_capital_productivity=Decimal("1"),
        fold_policy_net_delta_usd=tuple(Decimal("1") for _ in range(4)),
        fresh_oos_utility_demonstrated=True,
        runtime_authority=False,
        blockers=(),
    )


def _scarcity_utility_report() -> Phase20T09T18ScarcityUtilityReport:
    return Phase20T09T18ScarcityUtilityReport(
        contract_id=SCARCITY_UTILITY_CONTRACT_ID,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.baseline_policy_id,
        outcome_refit_performed=False,
        t09=_scarcity_scope("T09"),
        t18=_scarcity_scope("T18"),
    )


def _scarcity_safety_report() -> T09T18ScarcityGateReport:
    return T09T18ScarcityGateReport(
        gate_id=SCARCITY_SAFETY_GATE_ID,
        gate_sha256=GATE_SHA256,
        gate_frozen_at=GATE_FROZEN_AT,
        verdicts=(
            T09T18ScarcityCandidateVerdict(
                tool=T09T18ScarcityTool.T09,
                candidate_id="treatment",
                status=T09T18ScarcityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH,
                passed_fold_ids=("WF1", "WF2", "WF3", "WF4"),
                failed_fold_ids=(),
                failed_dimensions=(),
            ),
        ),
    )


def test_t09_stress_requires_utility_and_safety_gate_together() -> None:
    utility = _scarcity_utility_report()
    safety = _scarcity_safety_report()
    evidence = tuple(
        T09T18OosStressEvidence(
            meta=_meta(kind, index),
            tool=T09T18ScarcityTool.T09,
            treatment_candidate_id="treatment",
            utility_report=utility,
            safety_report=safety,
        )
        for index, kind in enumerate(CompoundStressKind)
    )

    result = evaluate_t09_t18_oos_stress(evidence)

    assert result.verdict is Ce2iOosStressVerdict.STRESS_ROBUST

def test_t12_report_rejects_manual_pass_metric_drift() -> None:
    report = _t12_report()

    with pytest.raises(CiboCapitalManagementError, match="PASS metric drift"):
        replace(
            report,
            treatment_capital_productivity=Decimal("0.5"),
        )


def test_t13_report_rejects_manual_pass_metric_drift() -> None:
    report = _t13_report()

    with pytest.raises(CiboCapitalManagementError, match="PASS metric drift"):
        replace(
            report,
            total_shadow_reserved_risk_usd=Decimal("0"),
        )


def test_scarcity_report_rejects_manual_pass_metric_drift() -> None:
    scope = _scarcity_scope("T09")

    with pytest.raises(CiboCapitalManagementError, match="PASS metric drift"):
        replace(
            scope,
            policy_net_delta_usd=Decimal("3"),
        )


def test_scarcity_report_rejects_scope_identity_swap() -> None:
    report = _scarcity_utility_report()

    with pytest.raises(
        CiboCapitalManagementError,
        match="scope identity drift",
    ):
        replace(report, t09=report.t18, t18=report.t09)

