from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r116_anatomy_retest_execution_attribution as r116,
)


def test_r116_frozen_surfaces_are_pinned() -> None:
    assert r116.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }
    assert r116.EXPECTED_RETEST == {
        "5Y": 1049,
        "2Y": 452,
        "R66": 318,
    }


def test_r116_r115_source_is_pinned() -> None:
    assert r116.SOURCE_R115_RUN_ID == 35666028472
    assert r116.SOURCE_R115_ARTIFACT_ID == 10669327043
    assert r116.SOURCE_R115_ARTIFACT_DIGEST == (
        "sha256:86c7b0851e39f78fa6d5bc3c8d8c961d53cde79acb5011570c9753e6a3ddbbc4"
    )
