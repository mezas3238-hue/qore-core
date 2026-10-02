from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2.active_perception_v12_coverage_pilot import (
    V12CoveragePilotSample,
    V12CoveragePilotStatus,
    classify_v12_coverage_pilot,
    select_v12_temporal_coverage_pilot,
    v12_coverage_pilot_selection_digest,
)

_BASE = datetime(2016, 1, 1, tzinfo=UTC)


def _windows(count: int) -> list[list[object]]:
    return [
        [
            (_BASE + timedelta(days=index)).isoformat(timespec="microseconds"),
            (_BASE + timedelta(days=index, minutes=75)).isoformat(
                timespec="microseconds"
            ),
            index + 1,
        ]
        for index in range(count)
    ]


def test_pilot_selection_is_first_quartiles_mid_and_last() -> None:
    selected = select_v12_temporal_coverage_pilot(_windows(101))

    assert tuple(item.manifest_index for item in selected) == (0, 25, 50, 75, 100)


def test_pilot_selection_deduplicates_indices_for_small_manifest() -> None:
    selected = select_v12_temporal_coverage_pilot(_windows(2))

    assert tuple(item.manifest_index for item in selected) == (0, 1)


def test_selection_digest_is_deterministic_and_manifest_bound() -> None:
    selected = select_v12_temporal_coverage_pilot(_windows(9))
    first = v12_coverage_pilot_selection_digest(
        manifest_sha256="a" * 64,
        windows=selected,
    )
    second = v12_coverage_pilot_selection_digest(
        manifest_sha256="a" * 64,
        windows=selected,
    )
    other = v12_coverage_pilot_selection_digest(
        manifest_sha256="b" * 64,
        windows=selected,
    )

    assert first == second
    assert first != other


def test_coverage_classification_requires_both_sides_in_every_pilot_window() -> None:
    full = classify_v12_coverage_pilot(
        (
            V12CoveragePilotSample(0, 10, 11),
            V12CoveragePilotSample(1, 20, 21),
        )
    )
    partial = classify_v12_coverage_pilot(
        (
            V12CoveragePilotSample(0, 10, 11),
            V12CoveragePilotSample(1, 0, 0),
        )
    )
    none = classify_v12_coverage_pilot(
        (
            V12CoveragePilotSample(0, 0, 0),
            V12CoveragePilotSample(1, 0, 0),
        )
    )

    assert full is V12CoveragePilotStatus.FULL_BID_ASK_HISTORY
    assert partial is V12CoveragePilotStatus.PARTIAL_BID_ASK_HISTORY
    assert none is V12CoveragePilotStatus.NO_HISTORY
