from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.active_perception_v12_source_anchors import (
    EXPECTED_ACQUISITION_MANIFEST_SHA256,
    EXPECTED_SOURCE_COUNT,
    SOURCE_ANCHOR_IDENTITY,
    build_v12_source_anchor_manifest,
)


def _times() -> tuple[datetime, ...]:
    start = datetime(2016, 4, 20, 14, 0, tzinfo=UTC)
    return tuple(start + timedelta(minutes=30 * index) for index in range(EXPECTED_SOURCE_COUNT))


def test_source_anchor_manifest_freezes_complete_ordered_population() -> None:
    manifest = build_v12_source_anchor_manifest(
        _times(),
        acquisition_manifest_sha256=EXPECTED_ACQUISITION_MANIFEST_SHA256,
    )
    payload = manifest.logical_payload()

    assert payload["identity"] == SOURCE_ANCHOR_IDENTITY
    assert payload["partition"] == "r8"
    assert payload["source_count"] == EXPECTED_SOURCE_COUNT
    assert len(payload["source_times"]) == EXPECTED_SOURCE_COUNT
    assert len(manifest.digest_sha256) == 64
    assert payload["target_or_outcome_used"] is False
    assert payload["r6_r5_read"] is False
    assert payload["fresh_holdout_opened"] is False


def test_source_anchor_manifest_rejects_population_drift() -> None:
    with pytest.raises(ValueError, match="population drift"):
        build_v12_source_anchor_manifest(
            _times()[:-1],
            acquisition_manifest_sha256=EXPECTED_ACQUISITION_MANIFEST_SHA256,
        )


def test_source_anchor_manifest_rejects_manifest_drift() -> None:
    with pytest.raises(ValueError, match="frozen acquisition manifest"):
        build_v12_source_anchor_manifest(
            _times(),
            acquisition_manifest_sha256="f" * 64,
        )
