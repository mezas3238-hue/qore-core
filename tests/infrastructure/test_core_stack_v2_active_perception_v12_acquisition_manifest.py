from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.active_perception_v12_acquisition_manifest import (
    V12_TICK_POST_SOURCE_MINUTES,
    V12_TICK_PRE_SOURCE_MINUTES,
    build_v12_tick_acquisition_manifest,
)

_BASE = datetime(2017, 6, 1, 14, 0, tzinfo=UTC)
_EVIDENCE = {
    "NAS100": "a" * 64,
    "SP500": "b" * 64,
    "US30": "c" * 64,
}


def test_manifest_uses_frozen_causal_context_and_checkpoint_horizons() -> None:
    manifest = build_v12_tick_acquisition_manifest(
        source_times=(_BASE,),
        provider_symbol="USTEC",
        evidence_sha256=_EVIDENCE,
    )

    assert manifest.partition == "r8"
    assert manifest.pre_source_minutes == V12_TICK_PRE_SOURCE_MINUTES == 60
    assert manifest.post_source_minutes == V12_TICK_POST_SOURCE_MINUTES == 15
    assert manifest.windows[0].from_at == _BASE - timedelta(minutes=60)
    assert manifest.windows[0].to_at == _BASE + timedelta(minutes=15)
    assert manifest.logical_payload()["target_or_outcome_used_for_selection"] is False


def test_overlapping_source_windows_are_merged_without_changing_source_count() -> None:
    manifest = build_v12_tick_acquisition_manifest(
        source_times=(
            _BASE,
            _BASE + timedelta(minutes=30),
            _BASE + timedelta(minutes=120),
        ),
        provider_symbol="USTEC",
        evidence_sha256=_EVIDENCE,
    )

    assert manifest.source_count == 3
    assert len(manifest.windows) == 2
    assert manifest.windows[0].source_count == 2
    assert manifest.windows[1].source_count == 1


def test_manifest_digest_is_order_independent_for_identical_source_evidence() -> None:
    first = build_v12_tick_acquisition_manifest(
        source_times=(_BASE, _BASE + timedelta(minutes=30)),
        provider_symbol="USTEC",
        evidence_sha256=_EVIDENCE,
    )
    second = build_v12_tick_acquisition_manifest(
        source_times=(_BASE + timedelta(minutes=30), _BASE),
        provider_symbol="USTEC",
        evidence_sha256=dict(reversed(tuple(_EVIDENCE.items()))),
    )

    assert first.digest_sha256 == second.digest_sha256


def test_empty_or_naive_source_population_fails_closed() -> None:
    with pytest.raises(ValueError, match="at least one causal source"):
        build_v12_tick_acquisition_manifest(
            source_times=(),
            provider_symbol="USTEC",
            evidence_sha256=_EVIDENCE,
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        build_v12_tick_acquisition_manifest(
            source_times=(datetime(2017, 6, 1, 14, 0),),
            provider_symbol="USTEC",
            evidence_sha256=_EVIDENCE,
        )
