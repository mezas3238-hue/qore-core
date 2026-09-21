from __future__ import annotations

from datetime import date

from qore.infrastructure.trader_lab import (
    vt08_index_r105_standard_context_transport_atlas as r105,
)


def test_r105_identity_and_source_are_frozen() -> None:
    assert r105.IDENTITY == (
        "VT08_INDEX_R105_STANDARD_CAUSAL_CONTEXT_TRANSPORT_ATLAS_001"
    )
    assert r105.SOURCE_R104_RUN_ID == 35556281814
    assert r105.SOURCE_R104_ARTIFACT_ID == 10621165375
    assert r105.SOURCE_R104_ARTIFACT_DIGEST == (
        "sha256:1a05f768c25fdc872ccc46495c86b250258ed4c935f98f3fd2d893c9ea14e773"
    )


def test_r105_period_ids_are_evaluation_only() -> None:
    assert r105._period_id("5Y", date(2018, 9, 15)) == "Y1"
    assert r105._period_id("2Y", date(2025, 9, 15)) == "Y2"
    assert r105._period_id("R66", date(2017, 9, 16)) == "B2"


def test_r105_context_dimensions_include_source_day_and_range_state() -> None:
    assert "previous_source_day_body_alignment" in r105.DIMENSIONS
    assert "source_day_relationship" in r105.DIMENSIONS
    assert "recent_h4_range_state" in r105.DIMENSIONS
    assert "cross_index_state" in r105.DIMENSIONS


def test_r105_reporting_sample_is_descriptive_only() -> None:
    assert r105.MIN_REPORT_SAMPLE == 20
