from __future__ import annotations

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_third_slot_cross_feature_atlas_2r_v1 as atlas,
)


def test_cell_map_requires_unique_feature_names() -> None:
    assert atlas._cell_map(
        (("A", "ONE"), ("B", "TWO"))
    ) == {"A": "ONE", "B": "TWO"}
    with pytest.raises(ValueError, match="duplicate causal feature"):
        atlas._cell_map((("A", "ONE"), ("A", "TWO")))


def test_cross_feature_contract_is_pairwise_only() -> None:
    assert len(atlas.JOURNEY_FEATURES) == 6
    assert len(atlas.PREENTRY_FEATURES) == 14
    assert "ACTIVE_POSITION_COUNT" in atlas.JOURNEY_FEATURES
    assert "ENTRY_MODE" in atlas.PREENTRY_FEATURES
