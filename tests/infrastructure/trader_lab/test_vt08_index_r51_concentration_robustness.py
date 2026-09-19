from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r48_candidate_freeze as freeze
from qore.infrastructure.trader_lab import (
    vt08_index_r51_concentration_robustness as r51,
)


def test_r51_is_frozen_stress_not_retune() -> None:
    assert freeze.CANDIDATE_ID == (
        "VT08_INDEX_R47_TRANSPORT_SAFE_STRUCTURAL_DEMOTION_001"
    )
    assert r51.SECONDARY_STRESS == Decimal("0.10")
    assert r51.PF_FLOOR == Decimal("1.30")
    assert r51.MAX_WEIGHT_NEIGHBORHOOD == Decimal("0.25")
    assert r51.ADDITIONAL_CAPS == (Decimal("0.10"), Decimal("0.05"))
    assert r51.TOP_WINNER_REMOVAL_COUNT == 3


def test_r51_metrics_are_fail_closed() -> None:
    assert r51.FLOOR_WEIGHT == Decimal("0.005")
