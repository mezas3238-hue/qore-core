from qore.infrastructure.cibo_arch2_t11_provider_containment_state import (
    AUDIT_ARTIFACT_DIGEST,
    AUDIT_ARTIFACT_ID,
    AUDIT_RUN_ID,
    BLOCK_REASON,
    CONTAMINATED_REPLACEMENT_RUN_ID,
    OPEN_CANCELLED_RUN_LABELS,
    T11_PROVIDER_CONTAINMENT_STATE,
)


def test_t11_provider_containment_fails_closed_on_orphan_exposure() -> None:
    state = T11_PROVIDER_CONTAINMENT_STATE

    assert state.audit_run_id == AUDIT_RUN_ID == 36947334465
    assert state.audit_artifact_id == AUDIT_ARTIFACT_ID == 11202212072
    assert state.audit_artifact_digest == AUDIT_ARTIFACT_DIGEST
    assert state.contaminated_replacement_run_id == (
        CONTAMINATED_REPLACEMENT_RUN_ID == 36946792349
    )
    assert state.open_position_count == 2
    assert state.open_order_count == 0
    assert state.open_labels == OPEN_CANCELLED_RUN_LABELS
    assert state.containment_clean is False
    assert state.replacement_evidence_admissible is False
    assert state.further_provider_experiment_allowed is False
    assert state.block_reason == BLOCK_REASON
    assert state.broker_mutation_performed_by_receipt is False
    assert state.phase22_v2_consumed is False
    assert state.canonical_ledger_modified is False
    assert state.productive_authority is False
