from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

import pytest

from qore.infrastructure.cibo_arch2_fresh_oos_terminal_intake import (
    Architect2FreshOOSTerminalIntake,
)
from qore.infrastructure.cibo_arch2_t02_terminal_disposition import (
    T02TerminalDispositionAssessment,
)
from qore.infrastructure.cibo_arch2_t11_experiment_plan import (
    T11_MARKET_IMPACT_EXPERIMENT_PLAN,
)
from qore.infrastructure.cibo_arch2_t11_market_impact_terminal_receipt import (
    T11MarketImpactTerminalReceipt,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    REQUIRED_SYMBOLS,
    T11_NONLINEAR_INPUT_FREEZE,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_usd60_six_month_certification import (
    CiboMaximumCapabilityGateSet,
)
from qore.infrastructure.cibo_scientific_closure_41 import (
    CANONICAL_POLICY_IDENTITY,
    CANONICAL_PROVIDER_IDENTITY,
    CANONICAL_QUALIFICATION_PLAN_IDENTITY,
    COMPLETED,
    CONSUMED_INVALID_V4_HOLDOUT_ID,
    FALSIFIED,
    SOURCE_UNAVAILABLE_V5_HOLDOUT_ID,
)
from qore.infrastructure.cibo_scientific_closure_41_adapters import (
    ARCHITECT_A_35_IDS,
    ARCHITECT_A_GROUP2_11_IDS,
    GROUP1_28_IDS,
    GROUP2_CAPITAL_13_IDS,
    SPECIAL_6_IDS,
    CanonicalScientificBinding,
    Group1V4TerminalEvidenceHandoff,
    Group2CapitalTerminalEvidenceHandoff,
    adapt_fresh_oos_terminal_intake,
    adapt_group1_fresh_oos_handoff,
    adapt_group2_capital_terminal_batch,
    adapt_group2_capital_terminal_handoff,
    adapt_t02_terminal_assessment,
    adapt_t11_terminal_receipts,
    adapt_usd60_capability_classification,
    scientific_closure_41_dependency_manifest,
)


SUCCESSOR_HOLDOUT_ID = "CIBO_USD60_6M_HOLDOUT_2013-10-19_2014-04-19_V6"


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _binding(
    *,
    integrity: str = "PASS",
    holdout_id: str = SUCCESSOR_HOLDOUT_ID,
    population_identity: str = "phase22-v6:canonical",
) -> CanonicalScientificBinding:
    return CanonicalScientificBinding(
        scientific_hypothesis="Frozen preregistered hypothesis",
        evidence_refs=("artifact://immutable",),
        evidence_sha256s=(_sha("artifact"),),
        population_identity=population_identity,
        causal_lineage=_sha("lineage"),
        economic_result="PASS",
        stress_result="PASS",
        temporal_replication_result="PASS",
        integrity_result=integrity,
        evaluated_at=datetime(2026, 10, 2, 12, 0, tzinfo=UTC),
        holdout_id=holdout_id,
    )



def _v4_handoff(
    *,
    candidate_id: str = SUCCESSOR_HOLDOUT_ID,
    population_identity: str = "phase22-v6:canonical",
    trader_ids: tuple[str, ...] = (
        "VT08_FOREX",
        "R34_XAUUSD",
        "R38_EURUSD",
        "R43_GBPUSD",
        "R38_GBPJPY",
        "R42_AUDJPY",
        "VT31_NAS100",
    ),
) -> Group1V4TerminalEvidenceHandoff:
    return Group1V4TerminalEvidenceHandoff(
        candidate_id=candidate_id,
        phase22_manifest_sha256=_sha("successor-manifest"),
        outcome_bundle_sha256=_sha("successor-outcomes"),
        qualification_artifact_sha256=_sha("successor-qualification"),
        population_identity=population_identity,
        policy_identity=CANONICAL_POLICY_IDENTITY,
        qualification_plan_identity=CANONICAL_QUALIFICATION_PLAN_IDENTITY,
        provider_identity=CANONICAL_PROVIDER_IDENTITY,
        causal_lineage=_sha("lineage"),
        source_head_sha="a" * 40,
        trader_ids=trader_ids,
        qualification_status="PASS",
        terminal_recommendation=COMPLETED,
        observed_at=datetime(2026, 10, 2, 11, 59, tzinfo=UTC),
    )




def _group2_handoff(
    workstream_id: str,
    *,
    status: str = "PASS",
    manifest: str | None = None,
    population: str = "phase22-v6:canonical",
) -> Group2CapitalTerminalEvidenceHandoff:
    passed = status == "PASS"
    return Group2CapitalTerminalEvidenceHandoff(
        workstream_id=workstream_id,
        candidate_id=SUCCESSOR_HOLDOUT_ID,
        phase22_manifest_sha256=manifest or _sha("successor-manifest"),
        source_gate_id=f"gate:{workstream_id}",
        source_gate_evidence_sha256=_sha(f"evidence:{workstream_id}"),
        source_gate_status=status,
        terminal_recommendation=COMPLETED if passed else FALSIFIED,
        failed_dimensions=() if passed else ("NONCOMPENSATORY_GATE",),
        population_identity=population,
        policy_identity=CANONICAL_POLICY_IDENTITY,
        qualification_plan_identity=CANONICAL_QUALIFICATION_PLAN_IDENTITY,
        provider_identity=CANONICAL_PROVIDER_IDENTITY,
        causal_lineage=_sha("lineage"),
        source_head_sha="b" * 40,
        observed_at=datetime(2026, 10, 2, 11, 59, tzinfo=UTC),
    )


def _all_pass_gates() -> CiboMaximumCapabilityGateSet:
    return CiboMaximumCapabilityGateSet(
        six_complete_months=True,
        exact_initial_capital=True,
        survival=True,
        robust_economic_maximization=True,
        full_t01_t20_integration=True,
        capital_source_integrity=True,
        zero_double_spend=True,
        zero_outcome_awareness=True,
        zero_future_leakage=True,
        zero_martingale=True,
        zero_loss_recovery_sizing=True,
        risk_sovereignty=True,
        provider_constraint_integrity=True,
        fresh_oos_generalization=True,
        failure_resilience=True,
        baseline_comparison_complete=True,
        ablation_complete=True,
        stress_complete=True,
        monte_carlo_complete=True,
        trajectory_complete=True,
        all_tool_empirical_status_complete=True,
    )


def test_current_ownership_partition_is_exact_28_plus_13() -> None:
    assert len(GROUP1_28_IDS) == 28
    assert len(GROUP2_CAPITAL_13_IDS) == 13
    assert len(ARCHITECT_A_GROUP2_11_IDS) == 11
    assert not set(GROUP1_28_IDS) & set(GROUP2_CAPITAL_13_IDS)

    # Legacy producer surfaces stay known only as source compatibility.
    assert len(ARCHITECT_A_35_IDS) == 35
    assert len(SPECIAL_6_IDS) == 6


def test_dependency_manifest_names_all_41_without_fabricating_future_digests() -> None:
    manifest = scientific_closure_41_dependency_manifest()

    assert manifest["workstream_count"] == 41
    assert manifest["group1_successor_fresh_ce2i_genc_count"] == 28
    assert manifest["group2_capital_compound_count"] == 13
    assert (
        manifest["group2_evidence_state"]
        == "WAITING_FOR_GROUP1_IMMUTABLE_EVIDENCE"
    )
    assert manifest["unknown_future_digests_fabricated"] is False
    rows = manifest["workstreams"]
    assert isinstance(rows, list)
    assert len(rows) == 41
    t11 = next(row for row in rows if row["workstream_id"] == "T11")
    assert str(t11["already_sealed_provider_artifact_sha256"]).startswith(
        "sha256:"
    )
    assert all(
        row["future_artifact_digest_policy"] == "REQUIRED_AT_INTAKE"
        for row in rows
    )


def test_t02_waiting_assessment_cannot_be_promoted() -> None:
    waiting = T02TerminalDispositionAssessment(
        structural_population_sufficient=False,
        structural_precision_passed=False,
        economic_ablation_present=False,
        economic_ablation_passed=None,
        terminal_ready=False,
        recommendation=None,
        waiting_reason="WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="remains non-terminal",
    ):
        adapt_t02_terminal_assessment(
            assessment=waiting,
            phase22_manifest_sha256=_sha("manifest"),
            binding=_binding(),
        )


def test_t02_legitimate_falsification_is_preserved() -> None:
    failed = T02TerminalDispositionAssessment(
        structural_population_sufficient=True,
        structural_precision_passed=False,
        economic_ablation_present=False,
        economic_ablation_passed=None,
        terminal_ready=True,
        recommendation=FALSIFIED,
        waiting_reason=None,
    )

    evidence = adapt_t02_terminal_assessment(
        assessment=failed,
        phase22_manifest_sha256=_sha("manifest"),
        binding=_binding(),
    )

    assert evidence.terminal_disposition == FALSIFIED
    assert evidence.productive_authority is False


def test_usd60_all_pass_is_completed_without_profit_target() -> None:
    evidence = adapt_usd60_capability_classification(
        gates=_all_pass_gates(),
        hard_integrity_breach=False,
        architecture_or_calibration_intervention_possible=False,
        phase22_manifest_sha256=_sha("manifest"),
        binding=_binding(),
    )

    assert evidence.terminal_disposition == COMPLETED
    assert evidence.certification_authorized is False


def test_usd60_intervention_state_remains_nonterminal() -> None:
    gates = _all_pass_gates()
    object.__setattr__(gates, "survival", False)

    with pytest.raises(
        CiboCapitalManagementError,
        match="remains non-terminal",
    ):
        adapt_usd60_capability_classification(
            gates=gates,
            hard_integrity_breach=False,
            architecture_or_calibration_intervention_possible=True,
            phase22_manifest_sha256=_sha("manifest"),
            binding=_binding(),
        )


def test_usd60_hard_integrity_failure_is_explicit_terminal_falsification() -> None:
    gates = _all_pass_gates()

    evidence = adapt_usd60_capability_classification(
        gates=gates,
        hard_integrity_breach=True,
        architecture_or_calibration_intervention_possible=False,
        phase22_manifest_sha256=_sha("manifest"),
        binding=_binding(integrity="FAIL"),
    )

    assert evidence.terminal_disposition == FALSIFIED
    assert evidence.integrity_result == "FAIL"


def test_usd60_hard_integrity_failure_cannot_be_hidden_as_integrity_pass() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="must remain explicit",
    ):
        adapt_usd60_capability_classification(
            gates=_all_pass_gates(),
            hard_integrity_breach=True,
            architecture_or_calibration_intervention_possible=False,
            phase22_manifest_sha256=_sha("manifest"),
            binding=_binding(integrity="PASS"),
        )


def _t11_market_receipt(*, passed: bool) -> T11MarketImpactTerminalReceipt:
    rows = tuple(
        (
            symbol,
            passed if index > 0 else passed,
        )
        for index, symbol in enumerate(REQUIRED_SYMBOLS)
    )
    return T11MarketImpactTerminalReceipt(
        report_sha256=_sha("t11-report"),
        protocol_sha256=T11_NONLINEAR_INPUT_FREEZE.fingerprint(),
        experiment_plan_sha256=T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint(),
        symbol_count=len(REQUIRED_SYMBOLS),
        episode_count=144,
        child_entry_count=216,
        four_of_four_by_symbol=rows,
        market_impact_model_ready=passed,
        terminal_recommendation=COMPLETED if passed else FALSIFIED,
        broker_mutation_performed=True,
        all_created_positions_closed=True,
        phase22_v2_consumed=False,
        canonical_ledger_modified=False,
        productive_authority=False,
    )


def test_t11_falsified_market_impact_closes_without_new_broker_action() -> None:
    evidence = adapt_t11_terminal_receipts(
        market_impact=_t11_market_receipt(passed=False),
        gross_edge=None,
        phase22_manifest_sha256=_sha("manifest"),
        binding=_binding(),
    )

    assert evidence.terminal_disposition == FALSIFIED
    assert evidence.productive_authority is False


def test_t11_passed_market_impact_still_requires_fresh_gross_edge() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="fresh gross edge required",
    ):
        adapt_t11_terminal_receipts(
            market_impact=_t11_market_receipt(passed=True),
            gross_edge=None,
            phase22_manifest_sha256=_sha("manifest"),
            binding=_binding(),
        )


def test_legacy_v2_fresh_intake_cannot_be_relabelled_as_successor() -> None:
    intake = Architect2FreshOOSTerminalIntake(
        candidate_id="CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        execution_manifest_sha256=_sha("legacy-v2-manifest"),
        outcome_bundle_sha256=_sha("legacy-v2-outcomes"),
        qualification_plan_sha256=CANONICAL_QUALIFICATION_PLAN_IDENTITY,
        qualification_status="PASS",
        lineage_valid=True,
        fresh_oos_terminal_ready=True,
        terminal_recommendation=COMPLETED,
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="explicitly non-certifiable",
    ):
        adapt_fresh_oos_terminal_intake(
            intake=intake,
            phase22_manifest_sha256=_sha("successor-manifest"),
            binding=_binding(),
        )


@pytest.mark.parametrize(
    "holdout_id",
    [CONSUMED_INVALID_V4_HOLDOUT_ID, SOURCE_UNAVAILABLE_V5_HOLDOUT_ID],
)
def test_noncertifiable_fresh_handoff_is_rejected(holdout_id: str) -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="explicitly non-certifiable",
    ):
        _v4_handoff(candidate_id=holdout_id)


def test_successor_fresh_handoff_accepts_exact_v6_identity() -> None:
    successor = "CIBO_USD60_6M_HOLDOUT_2013-10-19_2014-04-19_V6"
    population = "phase22-v6:canonical"
    handoff = _v4_handoff(
        candidate_id=successor,
        population_identity=population,
    )
    evidence = adapt_group1_fresh_oos_handoff(
        handoff=handoff,
        binding=_binding(
            holdout_id=successor,
            population_identity=population,
        ),
    )
    assert evidence.holdout_id == successor
    assert evidence.terminal_disposition == COMPLETED


def test_successor_fresh_handoff_rejects_cross_holdout_binding() -> None:
    successor = "CIBO_USD60_6M_HOLDOUT_2013-10-19_2014-04-19_V6"
    handoff = _v4_handoff(candidate_id=successor)
    with pytest.raises(
        CiboCapitalManagementError,
        match="holdout identity drift",
    ):
        adapt_group1_fresh_oos_handoff(
            handoff=handoff,
            binding=_binding(),
        )


def test_v4_fresh_handoff_rejects_incomplete_trader_surface() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="exact ordered 7/7 Traders",
    ):
        _v4_handoff(
            trader_ids=(
                "VT08_FOREX",
                "R34_XAUUSD",
                "R38_EURUSD",
                "R43_GBPUSD",
                "R38_GBPJPY",
                "R42_AUDJPY",
            )
        )


def test_group2_capital_terminal_handoff_preserves_scientific_falsification() -> None:
    evidence = adapt_group2_capital_terminal_handoff(
        handoff=_group2_handoff("ADVERSARIAL_STRESS", status="FAIL"),
        binding=_binding(),
    )
    assert evidence.workstream_id == "ADVERSARIAL_STRESS"
    assert evidence.previous_disposition == "EXTERNAL_DEPENDENCY_BLOCKED"
    assert evidence.terminal_disposition == FALSIFIED
    assert evidence.failed_dimensions == ("NONCOMPENSATORY_GATE",)


def test_group2_capital_terminal_batch_requires_exact_13_of_13() -> None:
    handoffs = tuple(
        _group2_handoff(workstream_id)
        for workstream_id in GROUP2_CAPITAL_13_IDS
    )
    bindings = {
        workstream_id: _binding()
        for workstream_id in GROUP2_CAPITAL_13_IDS
    }
    evidence = adapt_group2_capital_terminal_batch(
        handoffs=handoffs,
        bindings=bindings,
    )
    assert tuple(item.workstream_id for item in evidence) == (
        GROUP2_CAPITAL_13_IDS
    )
    assert len(evidence) == 13
    assert all(
        item.previous_disposition == "EXTERNAL_DEPENDENCY_BLOCKED"
        for item in evidence
    )
    assert all(item.terminal_disposition == COMPLETED for item in evidence)


def test_group2_capital_terminal_batch_rejects_missing_workstream() -> None:
    handoffs = tuple(
        _group2_handoff(workstream_id)
        for workstream_id in GROUP2_CAPITAL_13_IDS[:-1]
    )
    bindings = {
        workstream_id: _binding()
        for workstream_id in GROUP2_CAPITAL_13_IDS
    }
    with pytest.raises(
        CiboCapitalManagementError,
        match="handoff coverage mismatch",
    ):
        adapt_group2_capital_terminal_batch(
            handoffs=handoffs,
            bindings=bindings,
        )


def test_group2_capital_pass_cannot_hide_failed_dimension() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="PASS cannot retain failed dimensions",
    ):
        Group2CapitalTerminalEvidenceHandoff(
            workstream_id="TEMPORAL_REPLICATION",
            candidate_id=SUCCESSOR_HOLDOUT_ID,
            phase22_manifest_sha256=_sha("successor-manifest"),
            source_gate_id="gate:TEMPORAL_REPLICATION",
            source_gate_evidence_sha256=_sha("temporal"),
            source_gate_status="PASS",
            terminal_recommendation=COMPLETED,
            failed_dimensions=("WF4_FAILED",),
            population_identity="phase22-v4:canonical",
            policy_identity=CANONICAL_POLICY_IDENTITY,
            qualification_plan_identity=(
                CANONICAL_QUALIFICATION_PLAN_IDENTITY
            ),
            provider_identity=CANONICAL_PROVIDER_IDENTITY,
            causal_lineage=_sha("lineage"),
            source_head_sha="b" * 40,
            observed_at=datetime(2026, 10, 2, 11, 59, tzinfo=UTC),
        )
