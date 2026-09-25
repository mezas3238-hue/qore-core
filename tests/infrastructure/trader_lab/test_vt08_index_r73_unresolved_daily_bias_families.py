from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r73_unresolved_daily_bias_families as r73,
)


def test_r73_family_classification_contract_is_stable() -> None:
    assert r73.R72_AMBIGUOUS_COUNTS == {
        "5Y": 2410,
        "2Y": 1050,
        "R66": 968,
    }


def test_r73_is_bound_to_official_r72_evidence() -> None:
    assert r73.SOURCE_R72_RUN_ID == 35506163421
    assert r73.SOURCE_R72_ARTIFACT_ID == 10604260215
    assert r73.SOURCE_R72_ARTIFACT_DIGEST.startswith("sha256:")


def test_r73_remains_forensics_identity() -> None:
    assert r73.IDENTITY == (
        "VT08_INDEX_R73_UNRESOLVED_DAILY_BIAS_FAMILIES_001"
    )
