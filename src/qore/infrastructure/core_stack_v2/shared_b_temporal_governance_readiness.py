"""Architect-B temporal governance readiness gate.

Combines sealed source-clock integrity with the exact 177-sensor calendar
qualification worklist. It uses Shared's existing temporal-governance contract
and refuses to freeze cadence, liquidity, skew or comparability policy
registries without empirical evidence.
"""

from __future__ import annotations

import hashlib
import json

from qore.infrastructure.core_stack_v2.global_temporal_comparability import (
    assess_temporal_governance_closure,
)

IDENTITY = "SHARED_B_TEMPORAL_GOVERNANCE_READINESS_001"
EXPECTED_CALENDAR_IDENTITY = (
    "SHARED_B_CANONICAL_CALENDAR_QUALIFICATION_WORKLIST_001"
)
EXPECTED_CLOCK_IDENTITY = "SHARED_B_TEMPORAL_SOURCE_CLOCK_INTEGRITY_001"


class SharedBTemporalGovernanceReadinessError(ValueError):
    """B-08 readiness evidence failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_temporal_governance_readiness(
    *,
    calendar_worklist: dict[str, object],
    source_clock_audit: dict[str, object],
) -> dict[str, object]:
    if calendar_worklist.get("identity") != EXPECTED_CALENDAR_IDENTITY:
        raise SharedBTemporalGovernanceReadinessError(
            "unexpected calendar worklist identity"
        )
    if source_clock_audit.get("identity") != EXPECTED_CLOCK_IDENTITY:
        raise SharedBTemporalGovernanceReadinessError(
            "unexpected source-clock identity"
        )

    if calendar_worklist.get("sensor_count") != 177:
        raise SharedBTemporalGovernanceReadinessError(
            "calendar worklist is not exact 177"
        )
    if calendar_worklist.get("qualification_record_count") != 177:
        raise SharedBTemporalGovernanceReadinessError(
            "calendar qualification population drift"
        )
    if calendar_worklist.get("canonical_calendar_verified_count") != 0:
        raise SharedBTemporalGovernanceReadinessError(
            "calendar worklist unexpectedly promoted canonical calendars"
        )
    if calendar_worklist.get("calendar_binding_verified_count") != 0:
        raise SharedBTemporalGovernanceReadinessError(
            "calendar worklist unexpectedly promoted bindings"
        )
    if calendar_worklist.get("provider_schedule_is_canonical_calendar") is not False:
        raise SharedBTemporalGovernanceReadinessError(
            "provider schedule was promoted to canonical calendar"
        )

    required_clock = {
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
    for key, expected in required_clock.items():
        if source_clock_audit.get(key) != expected:
            raise SharedBTemporalGovernanceReadinessError(
                f"source-clock invariant mismatch: {key}"
            )

    closure = assess_temporal_governance_closure(
        sensor_count=177,
        canonical_mapping_verified_count=0,
        calendar_count=0,
        binding_count=0,
        cadence_policy_registry_frozen=False,
        liquidity_policy_registry_frozen=False,
        temporal_skew_policy_registry_frozen=False,
        comparability_policy_registry_frozen=False,
        anti_leakage_pass=True,
        deterministic_validation_pass=True,
    )
    expected_blockers = {
        "CANONICAL_MAPPING_INCOMPLETE",
        "CANONICAL_CALENDAR_REGISTRY_EMPTY",
        "CALENDAR_BINDING_INCOMPLETE",
        "CADENCE_POLICY_REGISTRY_NOT_FROZEN",
        "LIQUIDITY_POLICY_REGISTRY_NOT_FROZEN",
        "TEMPORAL_SKEW_POLICY_REGISTRY_NOT_FROZEN",
        "COMPARABILITY_POLICY_REGISTRY_NOT_FROZEN",
    }
    if set(closure.blockers) != expected_blockers:
        raise SharedBTemporalGovernanceReadinessError(
            f"temporal blocker drift: {closure.blockers}"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "B08_TEMPORAL_GOVERNANCE_NOT_READY_EXACT_BLOCKERS_FROZEN",
        "sensor_universe_count": 177,
        "calendar_qualification_record_count": 177,
        "canonical_calendar_verified_count": 0,
        "calendar_binding_verified_count": 0,
        "source_clock_sensor_count": 3,
        "source_clock_sealed_shard_count": 41,
        "source_clock_tick_count": 203185,
        "source_clock_integrity_pass": True,
        "anti_leakage_pass": True,
        "deterministic_validation_pass": True,
        "cadence_policy_registry_frozen": False,
        "liquidity_policy_registry_frozen": False,
        "temporal_skew_policy_registry_frozen": False,
        "comparability_policy_registry_frozen": False,
        "policy_thresholds_invented": False,
        "global_threshold_extrapolation_from_three_sensors": False,
        "temporal_governance_status": closure.status.value,
        "temporal_governance_blockers": list(closure.blockers),
        "temporal_governance_fingerprint_sha256": closure.fingerprint(),
        "relational_comparability_authorized": False,
        "stale_relation_empirical_isolation_authorized": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b08_complete": False,
    }
    payload["readiness_fingerprint_sha256"] = _fingerprint(payload)
    return payload
