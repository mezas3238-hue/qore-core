from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.active_perception_v13_sequential_representation import (
    EXPECTED_V13_ROW_COUNT,
    V13_BASE_FEATURES,
    V13_CHECKPOINTS_MINUTES,
    V13_MIN_CHECKPOINT_COVERAGE_BPS,
    V13_REPRESENTATION_IDENTITY,
    v13_artifact_fingerprint,
    v13_flat_feature_names,
    v13_representation_contract_fingerprint,
    v13_representation_contract_payload,
)


def test_v13_contract_freezes_exact_5x46_trajectory() -> None:
    payload = v13_representation_contract_payload()

    assert payload["identity"] == V13_REPRESENTATION_IDENTITY
    assert payload["checkpoints_minutes"] == [0, 3, 5, 10, 15]
    assert payload["base_representation"] == "M3_FULL_CAUSAL_MICROSTRUCTURE"
    assert len(V13_BASE_FEATURES) == 46
    assert len(v13_flat_feature_names()) == 230
    assert payload["trajectory_feature_count"] == 230
    assert payload["staleness_limit_ms"] == 30000
    assert payload["microstructure_windows_ms"] == [1000, 5000, 15000, 60000]
    assert payload["minimum_checkpoint_coverage_bps"] == 9500
    assert payload["target_or_outcome_read"] is False
    assert payload["r6_r5_read"] is False
    assert payload["fresh_holdout_opened"] is False


def test_v13_flat_feature_names_are_checkpoint_prefixed_and_unique() -> None:
    names = v13_flat_feature_names()

    assert len(names) == len(V13_CHECKPOINTS_MINUTES) * len(V13_BASE_FEATURES)
    assert len(names) == len(set(names))
    assert names[0].startswith("t0_")
    assert any(name.startswith("t15_") for name in names)


def test_v13_contract_and_artifact_fingerprints_are_sha256() -> None:
    contract = v13_representation_contract_fingerprint()
    artifact = v13_artifact_fingerprint(
        contract_fingerprint=contract,
        rows_sha256="a" * 64,
        checkpoint_coverage_bps=(9860, 9800, 9790, 9780, 9770),
    )

    assert len(contract) == 64
    assert len(artifact) == 64


def test_v13_artifact_rejects_checkpoint_coverage_width_drift() -> None:
    with pytest.raises(ValueError, match="coverage width drift"):
        v13_artifact_fingerprint(
            contract_fingerprint="b" * 64,
            rows_sha256="c" * 64,
            checkpoint_coverage_bps=(V13_MIN_CHECKPOINT_COVERAGE_BPS,) * 4,
        )


def test_v13_expected_population_is_complete_source_anchor_population() -> None:
    assert EXPECTED_V13_ROW_COUNT == 6804
