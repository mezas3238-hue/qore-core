from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_b_core_broker_observability import (
    SharedBObservedSystemKind,
    SharedBObservedSystemState,
    SharedBSystemObservation,
    assess_system_observation,
)

NOW=datetime(2026,9,30,18,0,tzinfo=UTC)


def _obs(**overrides: object) -> SharedBSystemObservation:
    values:dict[str,object]={
        "system_id":"CTRADER_DEMO",
        "system_kind":SharedBObservedSystemKind.PROVIDER,
        "observed_at":NOW,
        "evidence_cutoff_at":NOW,
        "availability_known":True,
        "available":True,
        "latency_ms":100,
        "data_integrity_bps":10_000,
        "freshness_age_ms":100,
        "error_count":0,
        "provenance_refs":("provider:health",),
    }
    values.update(overrides)
    return SharedBSystemObservation(**values)  # type: ignore[arg-type]


def _assess(observation: SharedBSystemObservation):
    return assess_system_observation(
        observation,
        latency_degraded_threshold_ms=500,
        integrity_degraded_threshold_bps=9_500,
        freshness_degraded_threshold_ms=1_000,
    )


def test_healthy_system_observation_is_descriptive_only() -> None:
    a=_assess(_obs())
    assert a.state is SharedBObservedSystemState.HEALTHY
    assert a.new_market_inference_allowed is True
    assert a.relation_support_allowed is True
    assert a.mutation_authority is False
    assert a.restart_authority is False
    assert a.order_authority is False
    assert a.risk_authority is False
    assert len(a.fingerprint())==64


def test_unknown_availability_never_defaults_to_healthy() -> None:
    a=_assess(_obs(availability_known=False,available=None))
    assert a.state is SharedBObservedSystemState.UNKNOWN
    assert a.new_market_inference_allowed is False
    assert a.relation_support_allowed is False


def test_unavailable_and_degraded_are_distinct() -> None:
    unavailable=_assess(_obs(available=False))
    degraded=_assess(_obs(latency_ms=700))
    assert unavailable.state is SharedBObservedSystemState.UNAVAILABLE
    assert degraded.state is SharedBObservedSystemState.DEGRADED
    assert unavailable.new_market_inference_allowed is False
    assert degraded.new_market_inference_allowed is False


def test_missing_health_dimensions_are_degraded_not_assumed() -> None:
    a=_assess(
        _obs(
            latency_ms=None,
            data_integrity_bps=None,
            freshness_age_ms=None,
            error_count=None,
        )
    )
    assert a.state is SharedBObservedSystemState.DEGRADED
    assert {
        "LATENCY_UNKNOWN",
        "DATA_INTEGRITY_UNKNOWN",
        "FRESHNESS_UNKNOWN",
        "ERROR_COUNT_UNKNOWN",
    }.issubset(set(a.reason_codes))


def test_future_system_evidence_fails_closed() -> None:
    with pytest.raises(ValueError,match="future system evidence"):
        _obs(evidence_cutoff_at=datetime(2026,9,30,18,1,tzinfo=UTC))


def test_observation_cannot_carry_mutation_or_order_authority() -> None:
    for field in (
        "broker_mutation_performed","restart_authority","order_authority",
        "risk_authority","sizing_authority","capital_authority",
    ):
        with pytest.raises(ValueError,match="forbidden authority"):
            _obs(**{field:True})
