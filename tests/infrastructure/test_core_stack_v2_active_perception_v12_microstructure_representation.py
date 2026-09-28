from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_foundation import (
    V12CausalMicrostructureSnapshot,
    V12MicrostructureAvailability,
    V12MicrostructureWindowStats,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_representation import (
    FROZEN_STALENESS_LIMIT_MS,
    FROZEN_WINDOWS_MS,
    normalize_v12_microstructure_snapshot,
    v12_microstructure_candidate_fields,
    v12_microstructure_representation_contract_fingerprint,
)


def _windows() -> tuple[V12MicrostructureWindowStats, ...]:
    return tuple(
        V12MicrostructureWindowStats(
            window_ms=window_ms,
            bid_update_count=2,
            ask_update_count=1,
            update_imbalance_bps=3333,
            bid_path_variation=20_000,
            ask_path_variation=10_000,
            bid_displacement=10_000,
            ask_displacement=-10_000,
        )
        for window_ms in FROZEN_WINDOWS_MS
    )


def test_representation_normalizes_available_pair_deterministically() -> None:
    snapshot = V12CausalMicrostructureSnapshot(
        evaluation_at=datetime(2017, 6, 1, 14, 0, tzinfo=UTC),
        staleness_limit_ms=FROZEN_STALENESS_LIMIT_MS,
        availability=V12MicrostructureAvailability.AVAILABLE,
        bid_age_ms=1_500,
        ask_age_ms=500,
        bid_relative_price=2_000_000_000,
        ask_relative_price=2_000_100_000,
        spread_relative_price=100_000,
        crossed_quote=False,
        side_age_skew_ms=1_000,
        windows=_windows(),
    )

    row = normalize_v12_microstructure_snapshot(snapshot)

    assert row["causal_pair_available"] == 1
    assert row["crossed_causal_quote"] == 0
    assert row["bid_age_ratio_bps"] == 500
    assert row["ask_age_ratio_bps"] == 166
    assert row["age_skew_ratio_bps"] == 333
    assert row["spread_bps"] == 0
    assert row["w1000_bid_update_rate_x1000"] == 2000
    assert row["w1000_ask_update_rate_x1000"] == 1000
    assert row["w1000_total_update_rate_x1000"] == 3000
    assert row["w1000_update_imbalance_bps"] == 3333
    assert row["w1000_bid_displacement_bps"] == 0
    assert row["w1000_ask_displacement_bps"] == 0
    assert row["w1000_path_variation_asymmetry_bps"] == 3333


def test_representation_preserves_explicit_missingness_when_pair_stale() -> None:
    snapshot = V12CausalMicrostructureSnapshot(
        evaluation_at=datetime(2017, 6, 1, 14, 0, tzinfo=UTC),
        staleness_limit_ms=FROZEN_STALENESS_LIMIT_MS,
        availability=V12MicrostructureAvailability.INSUFFICIENT,
        bid_age_ms=31_000,
        ask_age_ms=500,
        bid_relative_price=2_000_000_000,
        ask_relative_price=2_000_100_000,
        spread_relative_price=None,
        crossed_quote=None,
        side_age_skew_ms=None,
        windows=_windows(),
    )

    row = normalize_v12_microstructure_snapshot(snapshot)

    assert row["bid_present"] == 1
    assert row["ask_present"] == 1
    assert row["bid_fresh"] == 0
    assert row["ask_fresh"] == 1
    assert row["causal_pair_available"] == 0
    assert row["bid_age_ratio_bps"] == 10_000
    assert row["spread_bps"] is None
    assert row["w1000_bid_displacement_bps"] is None
    assert row["w1000_bid_update_rate_x1000"] == 2000


def test_representation_rejects_staleness_drift() -> None:
    snapshot = V12CausalMicrostructureSnapshot(
        evaluation_at=datetime(2017, 6, 1, 14, 0, tzinfo=UTC),
        staleness_limit_ms=60_000,
        availability=V12MicrostructureAvailability.AVAILABLE,
        bid_age_ms=500,
        ask_age_ms=500,
        bid_relative_price=2_000_000_000,
        ask_relative_price=2_000_100_000,
        spread_relative_price=100_000,
        crossed_quote=False,
        side_age_skew_ms=0,
        windows=_windows(),
    )

    with pytest.raises(ValueError, match="staleness drift"):
        normalize_v12_microstructure_snapshot(snapshot)


def test_candidate_family_is_exactly_m0_through_m3() -> None:
    candidates = v12_microstructure_candidate_fields()

    assert tuple(candidates) == (
        "M0_QUOTE_STATE",
        "M1_QUOTE_STATE_UPDATE_INTENSITY",
        "M2_QUOTE_STATE_PATH_RESPONSE",
        "M3_FULL_CAUSAL_MICROSTRUCTURE",
    )
    assert len(candidates["M0_QUOTE_STATE"]) == 10
    assert len(candidates["M1_QUOTE_STATE_UPDATE_INTENSITY"]) == 26
    assert len(candidates["M2_QUOTE_STATE_PATH_RESPONSE"]) == 30
    assert len(candidates["M3_FULL_CAUSAL_MICROSTRUCTURE"]) == 46
    assert len(v12_microstructure_representation_contract_fingerprint()) == 64
