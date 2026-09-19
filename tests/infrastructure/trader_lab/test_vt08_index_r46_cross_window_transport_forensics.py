from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r46_cross_window_transport_forensics as r46,
)


def test_r46_identity_and_required_dimensions_are_frozen() -> None:
    assert r46.IDENTITY == "VT08_INDEX_R46_CROSS_WINDOW_TRANSPORT_FORENSICS_001"
    required = {
        "symbol",
        "side",
        "market_side",
        "poi",
        "market_poi",
        "side_poi",
        "market_side_poi",
        "anchor",
        "model_kind",
        "rearm",
        "formation_tier",
        "formation_health_state",
        "poi_health_state",
        "source_day_relationship",
        "previous_source_day_body_alignment",
        "current_source_day_body_alignment",
        "risk_fraction_bucket",
        "cisd_latency_bucket",
        "continuation_latency_bucket",
        "h4_entry_latency_bucket",
        "closure_reference_expansion_state",
        "recent_h4_range_state",
        "recent_daily_range_state",
        "cross_index_state",
        "concurrent_pressure",
        "loss_cluster",
        "governor_state",
    }
    assert required.issubset(set(r46.DIMENSIONS))


def test_r46_causal_state_buckets_are_bounded_and_interpretable() -> None:
    assert r46._loss_cluster(0) == "L0"
    assert r46._loss_cluster(1) == "L1"
    assert r46._loss_cluster(2) == "L2_3"
    assert r46._loss_cluster(7) == "L4_PLUS"

    assert r46._pressure_bucket(0, Decimal("0")) == "NONE"
    assert r46._pressure_bucket(1, Decimal("0.20")) == "LOW"
    assert r46._pressure_bucket(2, Decimal("0.40")) == "MEDIUM"
    assert r46._pressure_bucket(3, Decimal("0.60")) == "HIGH"

    assert r46._governor_state(warn=False, hard=False, loss=False) == "NORMAL"
    assert r46._governor_state(warn=True, hard=False, loss=False) == "WARN_DD"
    assert (
        r46._governor_state(warn=False, hard=True, loss=True)
        == "HARD_DD+LOSS_DEFENSE"
    )


def test_r46_range_state_has_fixed_non_calendar_thresholds() -> None:
    assert r46._range_state(Decimal("0.79")) == "compressed"
    assert r46._range_state(Decimal("0.80")) == "normal"
    assert r46._range_state(Decimal("1.20")) == "normal"
    assert r46._range_state(Decimal("1.21")) == "expanded"
