from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r117_standard_late_revalidation_anatomy as r117,
)


def test_r117_frozen_standard_surface_is_pinned() -> None:
    assert r117.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }


def test_r117_r116_source_is_pinned() -> None:
    assert r117.SOURCE_R116_RUN_ID == 35666472208
    assert r117.SOURCE_R116_ARTIFACT_ID == 10669207820
    assert r117.SOURCE_R116_ARTIFACT_DIGEST == (
        "sha256:b3d6aa3e0af0cb9aeaf809fb54f40d2f3e1a7d0de9a98808b0a5227c9228e9f2"
    )
