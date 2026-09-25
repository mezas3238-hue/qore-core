from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r100_cisd_ps_semantics_correction as r100,
)


def test_r100_semantic_labels_are_frozen() -> None:
    assert r100.STANDARD == "STANDARD_CISD_CONFIRMED"
    assert r100.EXPLICIT == "EXPLICIT_PS_MECHANISM_EVIDENCE"
    assert (
        r100.STANDARD_WITHOUT_EXTRA
        == "STANDARD_WITHOUT_EXTRA_PS_MECHANISM"
    )


def test_r100_r98_evidence_is_pinned() -> None:
    assert r100.SOURCE_R98_RUN_ID == 35553502458
    assert r100.SOURCE_R98_ARTIFACT_ID == 10619516510
    assert r100.SOURCE_R98_ARTIFACT_DIGEST == (
        "sha256:7878ee790fe11f9e8a6965dee74406cad8f5409705c7b1905288bed68788e05e"
    )


def test_r100_primary_sources_are_ttrades() -> None:
    assert "ttrades.com" in r100.TTRADES_IC_CISD_URL
    assert "ttrades.com" in r100.TTRADES_WICK_URL
    assert "ttrades.com" in r100.TTRADES_LONDON_URL
    assert "ttrades.com" in r100.TTRADES_IDEAL_URL


def test_r100_identity_is_source_semantics_correction() -> None:
    assert r100.IDENTITY == (
        "VT08_INDEX_R100_CISD_PROTECTED_SWING_SEMANTICS_CORRECTION_001"
    )
