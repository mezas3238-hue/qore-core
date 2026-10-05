from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    ExecutionMode,
    LabScope,
    ResourcePolicy,
    RunRequest,
)


def request(dataset_version: str = "1") -> RunRequest:
    return RunRequest(
        repository="owner/repo",
        repo_path=".",
        commit_sha="a" * 40,
        branch="branch",
        dataset_id="dataset",
        dataset_version=dataset_version,
        mode=ExecutionMode.QUICK,
        scope=LabScope.SENSOR,
        workers=2,
        policy=ResourcePolicy(),
    )


def test_configuration_hash_is_deterministic() -> None:
    assert request().configuration_hash() == request().configuration_hash()


def test_configuration_hash_changes_when_execution_contract_changes() -> None:
    first = request()
    second = RunRequest(
        repository=first.repository,
        repo_path=first.repo_path,
        commit_sha=first.commit_sha,
        branch=first.branch,
        dataset_id=first.dataset_id,
        dataset_version=first.dataset_version,
        mode=ExecutionMode.DEEP,
        scope=first.scope,
        workers=first.workers,
        policy=first.policy,
    )
    assert first.configuration_hash() != second.configuration_hash()
