from qore.infrastructure.cibo_arch2_t11_execution_claim import (
    CANONICAL_HEAD_SHA,
    CANONICAL_RUN_ATTEMPT,
    CANONICAL_RUN_ID,
    INITIAL_HEAD_SHA,
    INITIAL_RUN_ATTEMPT,
    INITIAL_RUN_ID,
    REPLACEMENT_TRIGGER_SHA,
    T11_MARKET_IMPACT_EXECUTION_CLAIM,
)


def test_t11_execution_lineage_allows_only_one_non_outcome_aware_replacement() -> None:
    claim = T11_MARKET_IMPACT_EXECUTION_CLAIM

    assert claim.initial_run_id == INITIAL_RUN_ID == 36945327912
    assert claim.initial_run_attempt == INITIAL_RUN_ATTEMPT == 1
    assert claim.initial_head_sha == INITIAL_HEAD_SHA
    assert claim.initial_run_cancelled is True
    assert claim.initial_terminal_artifact_count == 0
    assert claim.initial_outcome_evidence_consumed is False

    assert claim.replacement_trigger_sha == REPLACEMENT_TRIGGER_SHA
    assert claim.replacement_changed_scientific_model is False
    assert claim.replacement_changed_thresholds is False
    assert claim.replacement_outcome_aware is False

    assert claim.canonical_run_id == CANONICAL_RUN_ID == 36946792349
    assert claim.canonical_run_attempt == CANONICAL_RUN_ATTEMPT == 1
    assert claim.canonical_head_sha == CANONICAL_HEAD_SHA == REPLACEMENT_TRIGGER_SHA

    assert claim.further_silent_rerun_allowed is False
    assert claim.further_replacement_requires_new_versioned_cycle is True
    assert claim.phase22_v2_consumed is False
    assert claim.canonical_ledger_modified is False
    assert claim.productive_authority is False
