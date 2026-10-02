from qore.infrastructure.cibo_arch2_t11_post_containment_cycle_v3 import (
    CLEAN_AUDIT_ARTIFACT_DIGEST,
    CLEAN_AUDIT_ARTIFACT_ID,
    CLEAN_AUDIT_RUN_ID,
    CLEANUP_ARTIFACT_DIGEST,
    CLEANUP_ARTIFACT_ID,
    CLEANUP_RUN_ID,
    CYCLE_ID,
    T11_POST_CONTAINMENT_CYCLE_V3,
    V1_RUN_ID,
    V2_RUN_ID,
)


def test_t11_v3_is_ready_only_after_global_clean_containment_proof() -> None:
    cycle = T11_POST_CONTAINMENT_CYCLE_V3

    assert cycle.cycle_id == CYCLE_ID
    assert cycle.v1_run_id == V1_RUN_ID == 36945327912
    assert cycle.v2_run_id == V2_RUN_ID == 36946792349
    assert cycle.cleanup_run_id == CLEANUP_RUN_ID == 36947869835
    assert cycle.cleanup_artifact_id == CLEANUP_ARTIFACT_ID == 11203160759
    assert cycle.cleanup_artifact_digest == CLEANUP_ARTIFACT_DIGEST
    assert cycle.clean_audit_run_id == CLEAN_AUDIT_RUN_ID == 36947985223
    assert cycle.clean_audit_artifact_id == CLEAN_AUDIT_ARTIFACT_ID == 11202788608
    assert cycle.clean_audit_artifact_digest == CLEAN_AUDIT_ARTIFACT_DIGEST
    assert cycle.independent_clean_audit_required is True
    assert cycle.independent_clean_audit_bound is True
    assert cycle.ready_for_versioned_execution is True
    assert cycle.v1_outcomes_consumable is False
    assert cycle.v2_outcomes_consumable is False
    assert cycle.changed_scientific_model is False
    assert cycle.changed_thresholds is False
    assert cycle.outcome_aware_repair is False
    assert cycle.broker_execution_authorized is False
    assert cycle.phase22_v2_consumed is False
    assert cycle.canonical_ledger_modified is False
    assert cycle.productive_authority is False
