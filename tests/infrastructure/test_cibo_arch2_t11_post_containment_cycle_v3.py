from qore.infrastructure.cibo_arch2_t11_post_containment_cycle_v3 import (
    CLEANUP_ARTIFACT_DIGEST,
    CLEANUP_ARTIFACT_ID,
    CLEANUP_RUN_ID,
    CYCLE_ID,
    T11_POST_CONTAINMENT_CYCLE_V3,
    V1_RUN_ID,
    V2_RUN_ID,
)


def test_t11_v3_is_frozen_but_not_executable_before_independent_clean_audit() -> None:
    cycle = T11_POST_CONTAINMENT_CYCLE_V3

    assert cycle.cycle_id == CYCLE_ID
    assert cycle.v1_run_id == V1_RUN_ID == 36945327912
    assert cycle.v2_run_id == V2_RUN_ID == 36946792349
    assert cycle.cleanup_run_id == CLEANUP_RUN_ID == 36947697015
    assert cycle.cleanup_artifact_id == CLEANUP_ARTIFACT_ID == 11202798042
    assert cycle.cleanup_artifact_digest == CLEANUP_ARTIFACT_DIGEST
    assert cycle.independent_clean_audit_required is True
    assert cycle.independent_clean_audit_bound is False
    assert cycle.ready_for_versioned_execution is False
    assert cycle.v1_outcomes_consumable is False
    assert cycle.v2_outcomes_consumable is False
    assert cycle.changed_scientific_model is False
    assert cycle.changed_thresholds is False
    assert cycle.outcome_aware_repair is False
    assert cycle.broker_execution_authorized is False
    assert cycle.phase22_v2_consumed is False
    assert cycle.canonical_ledger_modified is False
    assert cycle.productive_authority is False
