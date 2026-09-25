from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)


def test_r102_policy_grid_is_bounded_and_fixed() -> None:
    assert r102.POLICIES == (
        "EXACT_R58_CONTROL",
        "R47_BASE_CONTROL",
        "EXPLICIT_FULL_R58_STANDARD_BASE",
        "EXPLICIT_LATE_ONLY_STANDARD_BASE",
    )


def test_r102_reuses_only_existing_risk_constants() -> None:
    assert r102.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")
    assert r102.MAX_REQUESTED_WEIGHT == Decimal("0.25")
    assert r102.PORTFOLIO_BUDGET_R == Decimal("0.75")


def test_r102_base_request_never_invents_new_floor_or_cap() -> None:
    class Item:
        weight = Decimal("0.40")

    assert r102._base_request(Item()) == Decimal("0.25")  # type: ignore[arg-type]


def test_r102_source_r100_evidence_is_pinned() -> None:
    assert r102.SOURCE_R100_RUN_ID == 35553739444
    assert r102.SOURCE_R100_ARTIFACT_ID == 10619881275
    assert r102.SOURCE_R100_ARTIFACT_DIGEST == (
        "sha256:c58d8e8844c5b99e46ae94653ded118b0f6564d285afe8ecbcdff227d657bb4b"
    )


def test_r102_identity_is_forensic_ablation_not_candidate() -> None:
    assert r102.IDENTITY == (
        "VT08_INDEX_R102_SOURCE_CONFIDENCE_RISK_TRANSPORT_ABLATION_001"
    )
