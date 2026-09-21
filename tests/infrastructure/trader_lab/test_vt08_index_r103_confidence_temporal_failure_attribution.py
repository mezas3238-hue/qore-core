from __future__ import annotations

from datetime import date

from qore.infrastructure.trader_lab import (
    vt08_index_r103_confidence_temporal_failure_attribution as r103,
)


def test_r103_policy_under_attribution_is_frozen() -> None:
    assert r103.POLICY_ID == "EXPLICIT_FULL_R58_STANDARD_BASE"


def test_r103_source_r102_evidence_is_pinned() -> None:
    assert r103.SOURCE_R102_RUN_ID == 35554460252
    assert r103.SOURCE_R102_ARTIFACT_ID == 10619927443
    assert r103.SOURCE_R102_ARTIFACT_DIGEST == (
        "sha256:cb9c87bca14b6ab00cb910bf5dde8e380dd3453ecc833f3402c545ae197106a4"
    )


def test_r103_five_year_has_six_boundaries() -> None:
    boundaries = r103._block_boundaries("5Y")
    assert len(boundaries) == 6
    assert boundaries[0] == date(2018, 9, 15)
    assert boundaries[-1] == date(2023, 9, 15)


def test_r103_r66_uses_two_consumed_blocks() -> None:
    boundaries = r103._block_boundaries("R66")
    assert len(boundaries) == 3
    assert r103._block_name("R66", 0) == "B1"
    assert r103._block_name("R66", 1) == "B2"


def test_r103_identity_is_forensic_only() -> None:
    assert r103.IDENTITY == (
        "VT08_INDEX_R103_SOURCE_CONFIDENCE_TEMPORAL_FAILURE_ATTRIBUTION_001"
    )
