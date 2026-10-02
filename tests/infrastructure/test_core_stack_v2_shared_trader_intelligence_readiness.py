from __future__ import annotations

from qore.infrastructure.core_stack_v2.shared_trader_intelligence_readiness import (
    SharedTraderIntelligenceReadinessStatus,
    assess_shared_trader_intelligence_readiness,
)


def _assessment(**overrides: bool):
    values = {
        "contracts_frozen": False,
        "sovereignty_tests_pass": False,
        "anti_leakage_tests_pass": False,
        "alert_lifecycle_tests_pass": False,
        "position_lineage_tests_pass": False,
        "historical_causal_replay_pass": False,
        "opportunity_discovery_oos_pass": False,
        "regime_transition_oos_pass": False,
        "continuation_positive_tail_oos_pass": False,
        "position_threat_oos_pass": False,
        "control_treatment_attribution_pass": False,
        "false_alert_gate_pass": False,
        "missed_alert_gate_pass": False,
        "winner_preservation_gate_pass": False,
        "stress_validation_pass": False,
        "temporal_replication_pass": False,
        "runtime_sla_pass": False,
        "trader_integration_certified_separately": False,
        "cibo_read_only_contract_certified": False,
        "governed_productive_promotion": False,
    }
    values.update(overrides)
    return assess_shared_trader_intelligence_readiness(**values)


def test_current_contract_foundation_is_research_ready_not_certified() -> None:
    assessment = _assessment(
        contracts_frozen=True,
        sovereignty_tests_pass=True,
        anti_leakage_tests_pass=True,
        alert_lifecycle_tests_pass=True,
        position_lineage_tests_pass=True,
    )

    assert assessment.status is (
        SharedTraderIntelligenceReadinessStatus.RESEARCH_READY
    )
    assert "HISTORICAL_CAUSAL_REPLAY_NOT_PASS" in assessment.blockers
    assert "OPPORTUNITY_DISCOVERY_OOS_NOT_PASS" in assessment.blockers
    assert "REGIME_TRANSITION_OOS_NOT_PASS" in assessment.blockers
    assert "CONTINUATION_POSITIVE_TAIL_OOS_NOT_PASS" in assessment.blockers
    assert "POSITION_THREAT_OOS_NOT_PASS" in assessment.blockers
    assert "CONTROL_TREATMENT_ATTRIBUTION_NOT_PASS" in assessment.blockers
    assert "GOVERNED_PRODUCTIVE_PROMOTION_MISSING" in assessment.blockers
    assert assessment.productive_trader_behavior_change_authorized is False
    assert assessment.productive_cibo_behavior_change_authorized is False
    assert assessment.productive_risk_behavior_change_authorized is False
    assert assessment.execution_behavior_change_authorized is False
    assert len(assessment.fingerprint()) == 64


def test_missing_contract_foundation_is_not_ready() -> None:
    assessment = _assessment()

    assert assessment.status is SharedTraderIntelligenceReadinessStatus.NOT_READY
    assert "TYPED_CONTRACTS_NOT_FROZEN" in assessment.blockers
    assert "SOVEREIGNTY_TESTS_NOT_PASS" in assessment.blockers
    assert "POSITION_LINEAGE_TESTS_NOT_PASS" in assessment.blockers


def test_every_scientific_gate_is_required_for_pre_admission_ready() -> None:
    assessment = _assessment(
        contracts_frozen=True,
        sovereignty_tests_pass=True,
        anti_leakage_tests_pass=True,
        alert_lifecycle_tests_pass=True,
        position_lineage_tests_pass=True,
        historical_causal_replay_pass=True,
        opportunity_discovery_oos_pass=True,
        regime_transition_oos_pass=True,
        continuation_positive_tail_oos_pass=True,
        position_threat_oos_pass=True,
        control_treatment_attribution_pass=True,
        false_alert_gate_pass=True,
        missed_alert_gate_pass=True,
        winner_preservation_gate_pass=True,
        stress_validation_pass=True,
        temporal_replication_pass=True,
        runtime_sla_pass=True,
        trader_integration_certified_separately=True,
        cibo_read_only_contract_certified=True,
        governed_productive_promotion=True,
    )

    assert assessment.status is (
        SharedTraderIntelligenceReadinessStatus.PRE_ADMISSION_READY
    )
    assert assessment.blockers == ()
    assert assessment.productive_trader_behavior_change_authorized is False
    assert assessment.execution_behavior_change_authorized is False


def test_single_missing_scientific_gate_blocks_pre_admission() -> None:
    assessment = _assessment(
        contracts_frozen=True,
        sovereignty_tests_pass=True,
        anti_leakage_tests_pass=True,
        alert_lifecycle_tests_pass=True,
        position_lineage_tests_pass=True,
        historical_causal_replay_pass=True,
        opportunity_discovery_oos_pass=True,
        regime_transition_oos_pass=True,
        continuation_positive_tail_oos_pass=True,
        position_threat_oos_pass=True,
        control_treatment_attribution_pass=True,
        false_alert_gate_pass=True,
        missed_alert_gate_pass=True,
        winner_preservation_gate_pass=False,
        stress_validation_pass=True,
        temporal_replication_pass=True,
        runtime_sla_pass=True,
        trader_integration_certified_separately=True,
        cibo_read_only_contract_certified=True,
        governed_productive_promotion=True,
    )

    assert assessment.status is (
        SharedTraderIntelligenceReadinessStatus.RESEARCH_READY
    )
    assert assessment.blockers == ("WINNER_PRESERVATION_GATE_NOT_PASS",)
