from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_causal_tool_readiness import (
    Phase20ToolEvidenceState,
    assess_phase20_causal_tool_readiness,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_readiness import (
    Phase20QualificationReadiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_oos_ablation import (
    T08NettingOosAblationReport,
    T08NettingShadowEpoch,
    assess_t08_fresh_oos_netting_ablation,
)
from qore.infrastructure.cibo_ce2i_phase20_t09_t18_scarcity_readiness import (
    Phase20T09T18ScarcityReadiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t09_t18_scarcity_utility import (
    Phase20ScarcityUtilityScope,
    Phase20T09T18ScarcityUtilityReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_readiness import (
    Phase20T12OosReadiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_utility import (
    T12_UTILITY_CONTRACT_ID,
    Phase20T12UtilityReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_oos_readiness import (
    Phase20T13OosReadiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_reserve_population import (
    Phase20T13ReservePopulationAudit,
)
from qore.infrastructure.cibo_ce2i_phase20_t14_intervention_population import (
    Phase20T14NaturalInterventionPopulation,
)
from qore.infrastructure.cibo_ce2i_phase20_t15_reservation_binding import (
    Phase20T15ReservationBinding,
)

BASE = datetime(2026, 9, 28, 5, 0, tzinfo=UTC)


def _qualification(*, ready: bool) -> Phase20QualificationReadiness:
    return Phase20QualificationReadiness(
        ready=ready,
        reasons=() if ready else ("MINIMUM_DECISION_EPOCHS_NOT_MET",),
        decision_epochs=80 if ready else 1,
        candidate_instances=200 if ready else 2,
        candidate_outcomes=200 if ready else 0,
        selected_instances=60 if ready else 1,
        selected_outcomes=60 if ready else 0,
        candidate_outcome_coverage=Decimal("1") if ready else Decimal("0"),
        selected_outcome_coverage=Decimal("1") if ready else Decimal("0"),
        calendar_span_days=28 if ready else 1,
        distinct_trading_days=20 if ready else 1,
        represented_lineages=7 if ready else 2,
        minimum_outcomes_any_lineage=8 if ready else 0,
        minimum_fold_candidate_outcomes=40 if ready else 0,
        minimum_fold_lineages=7 if ready else 0,
        missing_policy_decisions=0,
        pre_freeze_decisions=0,
    )


def _payload(index: int, *, malformed: bool = False) -> dict[str, object]:
    candidates: list[object] = [
        {
            "candidate": {
                "signal_fingerprint": f"a-{index}",
                "trader_id": "R38_EURUSD",
                "stop_risk_usd": "5",
                "margin_usd": "10",
                "concentration_group": "USD",
                "concentration_risk_usd": "5",
            }
        },
        {
            "candidate": {
                "signal_fingerprint": f"b-{index}",
                "trader_id": "R43_GBPUSD",
                "stop_risk_usd": "5",
                "margin_usd": "10",
                "concentration_group": "USD",
                "concentration_risk_usd": "5",
            }
        },
    ]
    if malformed:
        candidates[0] = {"candidate": {"signal_fingerprint": "broken"}}
    return {
        "evidence_kind": "FORWARD_OBSERVED",
        "hard_risk_headroom_usd": "5",
        "margin_headroom_usd": "100",
        "concentration_limit_by_group": [["USD", "100"]],
        "regime_state": {
            "provider_condition": "HEALTHY",
            "evidence_stale": False,
            "drawdown_utilization": "0.10",
        },
        "candidates": candidates,
        "known_options": [],
        "advanced_evidence": {"portfolio_netting": None},
    }


def _seal(index: int, *, malformed: bool = False) -> Phase20ForwardDecisionSeal:
    decision_at = BASE + timedelta(minutes=index)
    return Phase20ForwardDecisionSeal(
        evidence_id=f"evidence-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256=f"sha256:{index:064x}",
        decision_at=decision_at,
        candidate_id="candidate",
        code_sha="code",
        parameter_sha256="params",
        signal_fingerprints=(f"a-{index}", f"b-{index}"),
        canonical_payload_json=json.dumps(
            _payload(index, malformed=malformed),
            sort_keys=True,
        ),
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )


def _outcome(
    decision: Phase20ForwardDecisionSeal,
) -> Phase20ForwardOutcomeSeal:
    return Phase20ForwardOutcomeSeal(
        evidence_id=f"outcome:{decision.evidence_id}",
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=decision.signal_fingerprints[0],
        position_id=1,
        execution_risk_evidence_id=f"risk:{decision.evidence_id}",
        settlement_deal_ids=(1,),
        fill_evidence_refs=(f"fill:{decision.evidence_id}",),
        observed_at=decision.decision_at + timedelta(seconds=30),
        realized_net_pnl_usd=Decimal("-5"),
        executed_initial_stop_risk_usd=Decimal("5"),
        realized_structural_outcome_r=Decimal("-1"),
    )


def _row(report: object, code: str) -> object:
    return next(item for item in report.tools if item.tool_code == code)


def test_forward_readiness_uses_frozen_exact_competition_threshold() -> None:
    book = VersionedPhase20ForwardEvidenceBook(
        generation=30,
        decisions=tuple(_seal(index) for index in range(30)),
    )
    report = assess_phase20_causal_tool_readiness(
        evidence_book=book,
        qualification_readiness=_qualification(ready=True),
    )

    assert report.exact_competition_epochs == 30
    assert report.scarce_competition_epochs == 30
    assert report.valid_regime_epochs == 30

    t09 = _row(report, "T09")
    t12 = _row(report, "T12")
    t18 = _row(report, "T18")
    assert t09.state is Phase20ToolEvidenceState.FORWARD_POPULATION_READY
    assert t12.state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert "T12_PREOUTCOME_SHADOW_ABLATION_REQUIRED" in t12.blockers
    assert t18.state is Phase20ToolEvidenceState.FORWARD_POPULATION_READY

    t08 = _row(report, "T08")
    assert t08.state is Phase20ToolEvidenceState.STREAM_BLOCKED
    assert "PORTFOLIO_NETTING_EVIDENCE_COVERAGE_INCOMPLETE" in t08.blockers


def test_forward_readiness_does_not_confuse_contract_stream_with_calibration() -> None:
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=(_seal(0),),
        ),
        qualification_readiness=_qualification(ready=False),
    )

    assert _row(report, "T09").state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert _row(report, "T12").state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert _row(report, "T13").state is Phase20ToolEvidenceState.STREAM_BLOCKED
    assert (
        _row(report, "T14").state
        is Phase20ToolEvidenceState.REQUIRES_DIFFERENT_EVIDENCE
    )
    assert _row(report, "T15").state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert report.global_forward_ready is False


def test_forward_readiness_fails_closed_on_malformed_scarcity_payload() -> None:
    with pytest.raises(CiboCapitalManagementError, match="monetary field"):
        assess_phase20_causal_tool_readiness(
            evidence_book=VersionedPhase20ForwardEvidenceBook(
                generation=1,
                decisions=(_seal(0, malformed=True),),
            ),
            qualification_readiness=_qualification(ready=False),
        )

def test_t13_becomes_collecting_when_prior_causal_history_is_reconstructible() -> None:
    first = _seal(0)
    second = _seal(1)
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=3,
            decisions=(first, second),
            outcomes=(_outcome(first),),
        ),
        qualification_readiness=_qualification(ready=False),
    )

    t13 = _row(report, "T13")
    assert report.causal_history_epochs == 1
    assert t13.state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert t13.stream_bound is True
    assert t13.qualifying_epochs == 1
    assert (
        "FRESH_OOS_DRAWDOWN_RESERVE_UTILITY_ANALYSIS_REQUIRED"
        in t13.blockers
    )

def _t08_oos_report(*, ready: bool) -> T08NettingOosAblationReport:
    epochs = tuple(
        T08NettingShadowEpoch(
            epoch_id=f"t08-readiness-{index}",
            decision_at=BASE + timedelta(minutes=5 * index),
            shadow_sealed_at=BASE + timedelta(minutes=5 * index, milliseconds=10),
            outcome_observed_at=BASE + timedelta(minutes=5 * index, hours=1),
            baseline_selected_count=1,
            treatment_selected_count=2 if ready else 1,
            baseline_realized_net_pnl_usd=Decimal("1"),
            treatment_realized_net_pnl_usd=(
                Decimal("1.2") if ready else Decimal("1")
            ),
            baseline_peak_loss_usd=Decimal("5"),
            treatment_peak_loss_usd=Decimal("4"),
            treatment_gross_stop_risk_usd=Decimal("10"),
            treatment_netted_risk_usd=Decimal("8"),
            netting_credit_usd=Decimal("2"),
            risk_mapping_evidence_id=f"risk-map:{index}",
            correlation_evidence_id=f"corr:{index}",
            outcome_evidence_ids=(f"outcome:{index}",),
        )
        for index in range(32)
    )
    return assess_t08_fresh_oos_netting_ablation(epochs)


def _t13_population() -> Phase20T13ReservePopulationAudit:
    return Phase20T13ReservePopulationAudit(
        usable_decision_epochs=80,
        candidate_epochs=60,
        candidate_instances=120,
        settled_history_epochs=50,
        loss_cluster_epochs=20,
        settlement_drawdown_epochs=25,
        reserve_pressure_epochs=18,
        scarce_risk_headroom_epochs=12,
        pressure_and_scarcity_epochs=8,
        maximum_loss_cluster=4,
        maximum_settlement_drawdown_usd=Decimal("15"),
        minimum_decision_epochs=80,
        decision_threshold_met=True,
        source_decision_sha256s=tuple(
            f"sha256:{index:064x}" for index in range(80)
        ),
        reserve_policy_identified=False,
        oos_utility_demonstrated=False,
        blockers=(
            "T13_RESERVE_POLICY_NOT_IDENTIFIED",
            "FRESH_OOS_T13_RESERVE_UTILITY_REQUIRED",
        ),
    )


def test_readiness_uses_explicit_t08_oos_ablation_when_available() -> None:
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        qualification_readiness=_qualification(ready=True),
        t08_oos_ablation=_t08_oos_report(ready=True),
    )

    t08 = _row(report, "T08")
    assert t08.state is Phase20ToolEvidenceState.FORWARD_POPULATION_READY
    assert t08.observed_epochs == 32
    assert t08.qualifying_epochs == 32
    assert t08.blockers == ()


def test_readiness_uses_t13_pressure_scarcity_population_when_available() -> None:
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        qualification_readiness=_qualification(ready=True),
        t13_reserve_population=_t13_population(),
    )

    t13 = _row(report, "T13")
    assert t13.state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert t13.stream_bound is True
    assert t13.observed_epochs == 80
    assert t13.qualifying_epochs == 8
    assert "T13_RESERVE_POLICY_NOT_IDENTIFIED" in t13.blockers




def _t14_natural_population() -> Phase20T14NaturalInterventionPopulation:
    return Phase20T14NaturalInterventionPopulation(
        forward_bound_positions=12,
        physical_management_positions=8,
        management_events=10,
        qualifying_interventions=7,
        pre_post_path_positions=7,
        protection_transition_positions=5,
        volume_transition_positions=3,
        terminally_settled_after_intervention_positions=6,
        eligible_natural_intervention_positions=6,
        represented_lineages=("R38_EURUSD", "VT31_NAS100"),
        trader_owned_management_preserved=True,
        cibo_derisk_policy_identified=False,
        fresh_oos_utility_demonstrated=False,
        blockers=(
            "NATURAL_TRADER_INTERVENTIONS_DO_NOT_IDENTIFY_CIBO_DERISK_POLICY",
            "FRESH_OOS_DERISK_UTILITY_ANALYSIS_REQUIRED",
        ),
    )


def _t15_binding() -> Phase20T15ReservationBinding:
    return Phase20T15ReservationBinding(
        origin_epochs_with_known_options=10,
        known_option_instances=12,
        in_horizon_option_instances=10,
        considered_option_instances=10,
        representative_option_instances=8,
        policy_bound_origin_epochs=10,
        geometry_verified_origin_epochs=10,
        nonzero_reserve_origin_epochs=8,
        completely_bound_origin_epochs=10,
        missing_policy_origin_epochs=0,
        considered_set_mismatch_epochs=0,
        reserve_geometry_mismatch_epochs=0,
        reservation_binding_complete=True,
        future_materialization_used=False,
        outcome_magnitudes_read=False,
        counterfactual_reservation_effect_identified=False,
        blockers=(
            "COUNTERFACTUAL_RESERVATION_CAUSAL_EFFECT_NOT_IDENTIFIED",
            "FRESH_OOS_OPTIONALITY_UTILITY_ANALYSIS_REQUIRED",
        ),
    )


def test_readiness_consumes_stronger_t14_and_t15_audits() -> None:
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        qualification_readiness=_qualification(ready=True),
        t14_intervention_population=_t14_natural_population(),
        t15_reservation_binding=_t15_binding(),
    )

    t14 = _row(report, "T14")
    assert t14.state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert t14.observed_epochs == 12
    assert t14.qualifying_epochs == 6
    assert (
        "NATURAL_TRADER_INTERVENTIONS_DO_NOT_IDENTIFY_CIBO_DERISK_POLICY"
        in t14.blockers
    )

    t15 = _row(report, "T15")
    assert t15.state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert t15.observed_epochs == 10
    assert t15.qualifying_epochs == 10
    assert (
        "COUNTERFACTUAL_RESERVATION_CAUSAL_EFFECT_NOT_IDENTIFIED"
        in t15.blockers
    )



def _t13_oos_population_ready() -> Phase20T13OosReadiness:
    decision_sha256s = tuple(
        f"sha256:{index + 1000:064x}" for index in range(80)
    )
    changed_sha256s = decision_sha256s[:20]
    return Phase20T13OosReadiness(
        ready_for_utility_analysis=True,
        blockers=(),
        post_freeze_decision_epochs=80,
        pre_t13_freeze_decisions_excluded=0,
        treatment_sealed_epochs=80,
        missing_treatment_decisions=0,
        missing_baseline_policy_decisions=0,
        selection_changed_epochs=20,
        candidate_instances=240,
        candidate_outcomes=240,
        candidate_outcome_coverage=Decimal("1"),
        baseline_selected_instances=80,
        baseline_selected_outcomes=80,
        baseline_selected_outcome_coverage=Decimal("1"),
        treatment_selected_instances=80,
        treatment_selected_outcomes=80,
        treatment_selected_outcome_coverage=Decimal("1"),
        baseline_only_instances=20,
        baseline_only_outcomes=20,
        treatment_only_instances=20,
        treatment_only_outcomes=20,
        calendar_span_days=28,
        distinct_trading_days=20,
        represented_lineages=7,
        minimum_outcomes_any_lineage=8,
        minimum_fold_candidate_outcomes=40,
        minimum_fold_lineages=4,
        minimum_decision_epochs=80,
        minimum_candidate_outcomes=200,
        minimum_selected_outcomes=60,
        required_candidate_coverage=Decimal("0.95"),
        required_selected_coverage=Decimal("1"),
        fold_count=4,
        decision_sha256s=decision_sha256s,
        changed_decision_sha256s=changed_sha256s,
        fresh_oos_utility_demonstrated=False,
    )


def _t12_oos_population_ready() -> Phase20T12OosReadiness:
    decision_sha256s = tuple(
        f"sha256:{index:064x}" for index in range(80)
    )
    changed_sha256s = decision_sha256s[:20]
    return Phase20T12OosReadiness(
        ready_for_utility_analysis=True,
        blockers=(),
        post_freeze_decision_epochs=80,
        pre_t12_freeze_decisions_excluded=0,
        shadow_sealed_epochs=80,
        missing_shadow_decisions=0,
        missing_treatment_policy_decisions=0,
        selection_changed_epochs=20,
        allocator_changed_epochs=20,
        candidate_instances=240,
        candidate_outcomes=240,
        candidate_outcome_coverage=Decimal("1"),
        treatment_selected_instances=80,
        treatment_selected_outcomes=80,
        treatment_selected_outcome_coverage=Decimal("1"),
        control_selected_instances=80,
        control_selected_outcomes=80,
        control_selected_outcome_coverage=Decimal("1"),
        treatment_only_instances=20,
        treatment_only_outcomes=20,
        control_only_instances=20,
        control_only_outcomes=20,
        calendar_span_days=28,
        distinct_trading_days=20,
        represented_lineages=7,
        minimum_outcomes_any_lineage=8,
        minimum_fold_candidate_outcomes=60,
        minimum_fold_lineages=4,
        minimum_fold_selection_changed_epochs=5,
        minimum_decision_epochs=80,
        minimum_candidate_outcomes=200,
        minimum_selected_outcomes=60,
        required_candidate_coverage=Decimal("0.95"),
        required_selected_coverage=Decimal("1"),
        fold_count=4,
        decision_sha256s=decision_sha256s,
        changed_decision_sha256s=changed_sha256s,
        fresh_oos_utility_demonstrated=False,
    )


def _t12_oos_utility_ready() -> Phase20T12UtilityReport:
    from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
        phase20d_qualification_plan_sha256,
    )
    from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_policy import (
        T12_SHADOW_POLICY_ID,
        t12_shadow_policy_sha256,
    )

    return Phase20T12UtilityReport(
        contract_id=T12_UTILITY_CONTRACT_ID,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        t12_policy_id=T12_SHADOW_POLICY_ID,
        t12_policy_sha256=t12_shadow_policy_sha256(),
        population_ready=True,
        decision_epochs=80,
        candidate_instances=240,
        treatment_selected_instances=80,
        control_selected_instances=80,
        candidate_outcome_coverage=Decimal("1"),
        treatment_selected_outcome_coverage=Decimal("1"),
        control_selected_outcome_coverage=Decimal("1"),
        treatment_net_delta_usd=Decimal("12"),
        control_net_delta_usd=Decimal("10"),
        treatment_settlement_cash_drawdown_usd=Decimal("4"),
        control_settlement_cash_drawdown_usd=Decimal("5"),
        treatment_capital_productivity=Decimal("0.20"),
        control_capital_productivity=Decimal("0.10"),
        fold_treatment_net_delta_usd=(
            Decimal("3"),
            Decimal("3"),
            Decimal("3"),
            Decimal("3"),
        ),
        fold_control_net_delta_usd=(
            Decimal("2"),
            Decimal("3"),
            Decimal("2"),
            Decimal("3"),
        ),
        fold_incremental_net_delta_usd=(
            Decimal("1"),
            Decimal("0"),
            Decimal("1"),
            Decimal("0"),
        ),
        fresh_oos_utility_demonstrated=True,
        outcome_refit_performed=False,
        runtime_authority=False,
        blockers=(),
    )


def test_readiness_distinguishes_t12_oos_population_from_utility() -> None:
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        qualification_readiness=_qualification(ready=True),
        t12_oos_readiness=_t12_oos_population_ready(),
    )

    t12 = _row(report, "T12")
    assert t12.state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert t12.stream_bound is True
    assert t12.forward_population_ready is False
    assert t12.observed_epochs == 80
    assert t12.qualifying_epochs == 20
    assert t12.blockers == (
        "T12_OOS_POPULATION_READY_UTILITY_ANALYSIS_NOT_EXECUTED",
    )


def test_t12_utility_promotes_only_with_global_readiness() -> None:
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        qualification_readiness=_qualification(ready=True),
        t12_oos_readiness=_t12_oos_population_ready(),
        t12_oos_utility=_t12_oos_utility_ready(),
    )

    t12 = _row(report, "T12")
    assert t12.state is Phase20ToolEvidenceState.FORWARD_POPULATION_READY
    assert t12.blockers == ()
    assert t12.observed_epochs == 80
    assert t12.qualifying_epochs == 20


def test_t12_utility_cannot_bypass_global_phase20d_readiness() -> None:
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        qualification_readiness=_qualification(ready=False),
        t12_oos_readiness=_t12_oos_population_ready(),
        t12_oos_utility=_t12_oos_utility_ready(),
    )

    t12 = _row(report, "T12")
    assert t12.state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert t12.forward_population_ready is False
    assert "GLOBAL_PHASE20D_POPULATION_NOT_READY" in t12.blockers


def test_readiness_distinguishes_t13_oos_population_from_utility() -> None:
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        qualification_readiness=_qualification(ready=True),
        t13_oos_readiness=_t13_oos_population_ready(),
    )

    t13 = _row(report, "T13")
    assert t13.state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert t13.stream_bound is True
    assert t13.forward_population_ready is False
    assert t13.observed_epochs == 80
    assert t13.qualifying_epochs == 20
    assert t13.blockers == (
        "T13_OOS_POPULATION_READY_UTILITY_ANALYSIS_NOT_EXECUTED",
    )



def _scarcity_ready() -> Phase20T09T18ScarcityReadiness:
    return Phase20T09T18ScarcityReadiness(
        usable_forward_epochs=80,
        exact_competition_epochs=32,
        scarce_competition_epochs=32,
        cross_trader_scarce_epochs=32,
        scarcity_candidate_instances=64,
        scarcity_candidate_outcomes=64,
        scarcity_selected_instances=32,
        scarcity_selected_outcomes=32,
        scarcity_candidate_outcome_coverage=Decimal("1"),
        scarcity_selected_outcome_coverage=Decimal("1"),
        represented_lineages=("R38_EURUSD", "R43_GBPUSD"),
        missing_policy_scarcity_epochs=0,
        t09_folds=(),
        t18_folds=(),
        t09_ready_for_utility_analysis=True,
        t18_ready_for_utility_analysis=True,
        fresh_oos_utility_demonstrated=False,
        t09_blockers=(),
        t18_blockers=(),
    )


def test_competition_population_ready_does_not_self_promote_t09_t18() -> None:
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        qualification_readiness=_qualification(ready=True),
        t09_t18_scarcity_readiness=_scarcity_ready(),
    )

    t09 = _row(report, "T09")
    t18 = _row(report, "T18")
    assert t09.state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert t18.state is Phase20ToolEvidenceState.COLLECTING_FORWARD
    assert t09.forward_population_ready is False
    assert t18.forward_population_ready is False
    assert (
        "T09_SCARCITY_POPULATION_READY_UTILITY_ANALYSIS_NOT_EXECUTED"
        in t09.blockers
    )
    assert (
        "T18_SCARCITY_POPULATION_READY_UTILITY_ANALYSIS_NOT_EXECUTED"
        in t18.blockers
    )



def _scarcity_utility_ready() -> Phase20T09T18ScarcityUtilityReport:
    from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
        FROZEN_PHASE20D_QUALIFICATION_PLAN,
        phase20d_qualification_plan_sha256,
    )

    def scope(code: str) -> Phase20ScarcityUtilityScope:
        return Phase20ScarcityUtilityScope(
            tool_code=code,
            population_ready=True,
            decision_epochs=32,
            candidate_instances=64,
            policy_selected_instances=32,
            baseline_selected_instances=32,
            candidate_outcome_coverage=Decimal("1"),
            policy_selected_outcome_coverage=Decimal("1"),
            baseline_selected_outcome_coverage=Decimal("1"),
            policy_net_delta_usd=Decimal("64"),
            baseline_net_delta_usd=Decimal("32"),
            policy_settlement_cash_drawdown_usd=Decimal("4"),
            baseline_settlement_cash_drawdown_usd=Decimal("5"),
            policy_capital_productivity=Decimal("0.04"),
            baseline_capital_productivity=Decimal("0.01"),
            fold_policy_net_delta_usd=(
                Decimal("16"),
                Decimal("16"),
                Decimal("16"),
                Decimal("16"),
            ),
            fresh_oos_utility_demonstrated=True,
            runtime_authority=False,
            blockers=(),
        )

    return Phase20T09T18ScarcityUtilityReport(
        contract_id="CIBO_T09_T18_SCARCITY_UTILITY_V1",
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=(
            FROZEN_PHASE20D_QUALIFICATION_PLAN.baseline_policy_id
        ),
        outcome_refit_performed=False,
        t09=scope("T09"),
        t18=scope("T18"),
    )


def test_scarcity_utility_promotes_t09_t18_only_with_global_readiness() -> None:
    report = assess_phase20_causal_tool_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        qualification_readiness=_qualification(ready=True),
        t09_t18_scarcity_readiness=_scarcity_ready(),
        t09_t18_scarcity_utility=_scarcity_utility_ready(),
    )

    t09 = _row(report, "T09")
    t18 = _row(report, "T18")
    assert t09.state is Phase20ToolEvidenceState.FORWARD_POPULATION_READY
    assert t18.state is Phase20ToolEvidenceState.FORWARD_POPULATION_READY
    assert t09.blockers == ()
    assert t18.blockers == ()
