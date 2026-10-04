"""Absolute completion gate for the multiuser native QORE Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MultiuserNativeAcceptance:
    commit_sha: str
    direct_cli_validate_pass: bool
    nine_concurrent_clients_pass: bool
    queue_32_pass: bool
    dynamic_worker_pool_pass: bool
    run_isolation_pass: bool
    deduplication_pass: bool
    causal_cache_pass: bool
    granular_lock_pass: bool
    failure_isolation_pass: bool
    evidence_ownership_pass: bool
    cancellation_pass: bool
    status_observability_pass: bool
    native_replay_pass: bool
    reproduce_pass: bool
    exact_sha_pass: bool
    persistent_dataset_pass: bool
    github_actions_required: bool
    github_publication_available: bool

    @property
    def passed(self) -> bool:
        return (
            len(self.commit_sha) == 40
            and self.direct_cli_validate_pass
            and self.nine_concurrent_clients_pass
            and self.queue_32_pass
            and self.dynamic_worker_pool_pass
            and self.run_isolation_pass
            and self.deduplication_pass
            and self.causal_cache_pass
            and self.granular_lock_pass
            and self.failure_isolation_pass
            and self.evidence_ownership_pass
            and self.cancellation_pass
            and self.status_observability_pass
            and self.native_replay_pass
            and self.reproduce_pass
            and self.exact_sha_pass
            and self.persistent_dataset_pass
            and not self.github_actions_required
            and self.github_publication_available
        )


@dataclass(frozen=True, slots=True)
class SharedLabAbsoluteCompletion:
    previous_global_exam_pass: bool
    previous_data_reality_pass: bool
    previous_core_integrity_pass: bool
    native_multiuser_acceptance: MultiuserNativeAcceptance

    @property
    def laboratory_finished(self) -> bool:
        return (
            self.previous_global_exam_pass
            and self.previous_data_reality_pass
            and self.previous_core_integrity_pass
            and self.native_multiuser_acceptance.passed
        )
