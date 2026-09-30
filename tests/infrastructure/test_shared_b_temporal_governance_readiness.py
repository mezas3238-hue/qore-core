from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_temporal_governance_readiness import (
    SharedBTemporalGovernanceReadinessError,
    build_temporal_governance_readiness,
)


def _calendar() -> dict[str, object]:
    return {
        "identity": "SHARED_B_CANONICAL_CALENDAR_QUALIFICATION_WORKLIST_001",
        "sensor_count": 177,
        "qualification_record_count": 177,
        "canonical_calendar_verified_count": 0,
        "calendar_binding_verified_count": 0,
        "provider_schedule_is_canonical_calendar": False,
    }


def _clock() -> dict[str, object]:
    return {
        "identity": "SHARED_B_TEMPORAL_SOURCE_CLOCK_INTEGRITY_001",
        "sensor_count": 3,
        "sealed_shard_count": 41,
        "tick_count": 203185,
        "provider_event_after_retrieval_count": 0,
        "provider_event_retrieval_clock_separation_pass": True,
        "raw_shard_monotonicity_pass": True,
        "future_provider_event_rejected": True,
        "historical_retrieval_can_reset_market_freshness": False,
        "historical_retrieval_proves_past_point_in_time_availability": False,
        "canonical_market_hours_resolved": False,
        "relational_comparability_authorized": False,
    }


def test_readiness_freezes_exact_blockers_without_inventing_policies() -> None:
    payload = build_temporal_governance_readiness(
        calendar_worklist=_calendar(),
        source_clock_audit=_clock(),
    )
    assert payload["sensor_universe_count"] == 177
    assert payload["source_clock_sensor_count"] == 3
    assert payload["source_clock_sealed_shard_count"] == 41
    assert payload["source_clock_tick_count"] == 203185
    assert payload["source_clock_integrity_pass"] is True
    assert payload["anti_leakage_pass"] is True
    assert payload["deterministic_validation_pass"] is True
    assert payload["temporal_governance_status"] == "NOT_READY"
    assert set(payload["temporal_governance_blockers"]) == {
        "CANONICAL_MAPPING_INCOMPLETE",
        "CANONICAL_CALENDAR_REGISTRY_EMPTY",
        "CALENDAR_BINDING_INCOMPLETE",
        "CADENCE_POLICY_REGISTRY_NOT_FROZEN",
        "LIQUIDITY_POLICY_REGISTRY_NOT_FROZEN",
        "TEMPORAL_SKEW_POLICY_REGISTRY_NOT_FROZEN",
        "COMPARABILITY_POLICY_REGISTRY_NOT_FROZEN",
    }
    assert payload["cadence_policy_registry_frozen"] is False
    assert payload["liquidity_policy_registry_frozen"] is False
    assert payload["temporal_skew_policy_registry_frozen"] is False
    assert payload["comparability_policy_registry_frozen"] is False
    assert payload["policy_thresholds_invented"] is False
    assert payload["global_threshold_extrapolation_from_three_sensors"] is False
    assert payload["relational_comparability_authorized"] is False
    assert payload["stale_relation_empirical_isolation_authorized"] is False
    assert payload["b08_complete"] is False
    assert len(payload["readiness_fingerprint_sha256"]) == 64


def test_rejects_provider_schedule_calendar_promotion() -> None:
    calendar = deepcopy(_calendar())
    calendar["provider_schedule_is_canonical_calendar"] = True
    with pytest.raises(
        SharedBTemporalGovernanceReadinessError,
        match="promoted to canonical calendar",
    ):
        build_temporal_governance_readiness(
            calendar_worklist=calendar,
            source_clock_audit=_clock(),
        )


def test_rejects_clock_integrity_drift() -> None:
    clock = deepcopy(_clock())
    clock["provider_event_after_retrieval_count"] = 1
    with pytest.raises(
        SharedBTemporalGovernanceReadinessError,
        match="provider_event_after_retrieval_count",
    ):
        build_temporal_governance_readiness(
            calendar_worklist=_calendar(),
            source_clock_audit=clock,
        )
