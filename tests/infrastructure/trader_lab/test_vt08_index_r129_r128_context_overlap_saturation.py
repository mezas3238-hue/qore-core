from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r129_r128_context_overlap_saturation as r129,
)


def test_r129_source_and_contexts_are_pinned() -> None:
    assert r129.SOURCE_R128_RUN_ID == 36075966463
    assert r129.SOURCE_R128_ARTIFACT_ID == 10839358300
    assert r129.SOURCE_R128_ARTIFACT_DIGEST == (
        "sha256:d69448f6dc7fe3b4d49c9be54b18c315"
        "8238d38e0e0f1e953ef5a43705f103a9"
    )
    assert r129.FLOOR == Decimal("0.005")
    assert tuple(context.context_id for context in r129.CONTEXTS) == (
        "LOSS_DEFENSE",
        "LOW_CONCURRENT",
        "LOSS_CLUSTER_L2_3",
        "DAILY_COMPRESSED",
        "PREV_BODY_OPPOSED",
        "SP500",
    )


def test_r129_membership_is_exact() -> None:
    row = {
        "governor_state": "LOSS_DEFENSE",
        "concurrent_pressure": "LOW",
        "loss_cluster": "L0",
        "recent_daily_range_state": "compressed",
        "previous_source_day_body_alignment": "aligned",
        "symbol": "NAS100",
    }
    assert r129._memberships(row) == (
        "LOSS_DEFENSE",
        "LOW_CONCURRENT",
        "DAILY_COMPRESSED",
    )
