from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_foundation import (
    V12CausalMicrostructureSnapshot,
    V12MicrostructureAvailability,
    V12MicrostructureWindowStats,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_representation import (
    FROZEN_WINDOWS_MS,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_representation import (
    V14_BASE_FEATURES,
    normalize_v14_peer_snapshot,
    v14_flat_feature_names,
)


def _snapshot() -> V12CausalMicrostructureSnapshot:
    return V12CausalMicrostructureSnapshot(
        evaluation_at=datetime(2017, 1, 1, tzinfo=UTC),
        staleness_limit_ms=30_000,
        availability=V12MicrostructureAvailability.AVAILABLE,
        bid_age_ms=1_000,
        ask_age_ms=2_000,
        bid_relative_price=100_000,
        ask_relative_price=100_010,
        spread_relative_price=10,
        crossed_quote=False,
        side_age_skew_ms=-1_000,
        windows=tuple(
            V12MicrostructureWindowStats(
                window_ms=value,
                bid_update_count=2,
                ask_update_count=3,
                update_imbalance_bps=-2_000,
                bid_path_variation=10,
                ask_path_variation=20,
                bid_displacement=5,
                ask_displacement=7,
            )
            for value in FROZEN_WINDOWS_MS
        ),
    )


def test_v14_representation_has_exact_460_raw_feature_cells() -> None:
    assert len(V14_BASE_FEATURES) == 46
    assert len(v14_flat_feature_names()) == 460
    assert len(set(v14_flat_feature_names())) == 460


def test_v14_normalization_reuses_exact_m3_feature_order() -> None:
    row = normalize_v14_peer_snapshot(
        _snapshot(),
        selected_staleness_limit_ms=30_000,
    )
    assert tuple(row) == V14_BASE_FEATURES
    assert row["causal_pair_available"] == 1
    assert row["crossed_causal_quote"] == 0
    assert row["spread_bps"] is not None
