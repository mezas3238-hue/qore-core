from qore.infrastructure.core_stack_v2.shared_lab_native_completion import (
    MultiuserNativeAcceptance,
    SharedLabAbsoluteCompletion,
)


def receipt(*, github_required: bool = False) -> MultiuserNativeAcceptance:
    return MultiuserNativeAcceptance(
        commit_sha="a" * 40,
        direct_cli_validate_pass=True,
        nine_concurrent_clients_pass=True,
        queue_32_pass=True,
        dynamic_worker_pool_pass=True,
        run_isolation_pass=True,
        run_id_unification_pass=True,
        deduplication_pass=True,
        causal_cache_pass=True,
        granular_lock_pass=True,
        failure_isolation_pass=True,
        evidence_ownership_pass=True,
        cancellation_pass=True,
        status_observability_pass=True,
        native_replay_pass=True,
        reproduce_pass=True,
        exact_sha_pass=True,
        persistent_dataset_pass=True,
        github_actions_required=github_required,
        github_publication_available=True,
    )


def test_native_completion_requires_actions_independence() -> None:
    assert receipt().passed
    assert not receipt(github_required=True).passed


def test_absolute_completion_requires_all_planes() -> None:
    result = SharedLabAbsoluteCompletion(
        previous_global_exam_pass=True,
        previous_data_reality_pass=True,
        previous_core_integrity_pass=True,
        native_multiuser_acceptance=receipt(),
    )
    assert result.laboratory_finished
