import pytest

from qore.infrastructure.core_stack_v2.shared_lab_manifest import (
    LAB_CONTRACT_ID,
    LAB_VERSION,
    SharedLabBuildManifest,
    build_manifest,
)


def test_build_manifest_is_reproducibly_fingerprinted():
    first = build_manifest(
        code_sha="abc123",
        branch="agent/qore-shared-lab-001",
        tool_registry_fingerprint="f" * 64,
    )
    second = build_manifest(
        code_sha="abc123",
        branch="agent/qore-shared-lab-001",
        tool_registry_fingerprint="f" * 64,
    )
    assert first.lab_version == LAB_VERSION
    assert first.contract_id == LAB_CONTRACT_ID
    assert first.fingerprint() == second.fingerprint()


def test_manifest_rejects_holdout_opening():
    with pytest.raises(ValueError, match="protected holdout"):
        SharedLabBuildManifest(
            lab_version=LAB_VERSION,
            contract_id=LAB_CONTRACT_ID,
            code_sha="sha",
            branch="branch",
            tool_registry_fingerprint="f" * 64,
            core_lane_id="core",
            data_sensor_lane_id="data",
            authority_free=True,
            protected_holdout_opened=True,
            productive_runtime_mutated=False,
        )
