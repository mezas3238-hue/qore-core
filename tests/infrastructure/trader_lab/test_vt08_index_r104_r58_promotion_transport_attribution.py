from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r104_r58_promotion_transport_attribution as r104,
)


def test_r104_policy_is_frozen_to_r102_explicit_full() -> None:
    assert r104.POLICY_ID == "EXPLICIT_FULL_R58_STANDARD_BASE"


def test_r104_source_r103_evidence_is_pinned() -> None:
    assert r104.SOURCE_R103_RUN_ID == 35554775759
    assert r104.SOURCE_R103_ARTIFACT_ID == 10620007573
    assert r104.SOURCE_R103_ARTIFACT_DIGEST == (
        "sha256:ee2a328624348d4fb6daf8a0f7da2cb97657f178ff72abf3ec4085abab26fb8d"
    )


def test_r104_identity_is_forensic_only() -> None:
    assert r104.IDENTITY == (
        "VT08_INDEX_R104_R58_PROMOTION_MECHANISM_TRANSPORT_ATTRIBUTION_001"
    )


def test_r104_label_key_is_deterministic() -> None:
    assert r104._label_key(
        ("A", "B")
    ) == "A+B"
