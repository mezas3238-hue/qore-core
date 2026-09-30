from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_b_active_perception_acquisition import (
    SharedBAcquisitionFeasibility,
    SharedBAcquisitionStatus,
    SharedBActivePerceptionAcquisitionResult,
    SharedBInformationGap,
    SharedBSensorAcquisitionCandidate,
    assess_acquisition_feasibility,
)

NOW=datetime(2026,9,30,18,30,tzinfo=UTC)


def _gap() -> SharedBInformationGap:
    return SharedBInformationGap(
        gap_id="GAP:WP05:CROSS_ASSET",
        sensor_family="EQUITY_BREADTH_PROXY",
        market_scope="US2000",
        horizon="M1",
        required_by_at=NOW,
        causal_cutoff_at=NOW,
        provenance_refs=("blindspot:wp05",),
    )


def _candidate(**overrides: object) -> SharedBSensorAcquisitionCandidate:
    values:dict[str,object]={
        "gap_id":"GAP:WP05:CROSS_ASSET",
        "sensor_id":"CTRADER_DEMO:US2000:10012",
        "provider_or_source_id":"CTRADER_DEMO",
        "canonical_observation_key":"QORE:OBS:US2000",
        "available":True,
        "causally_available_by_cutoff":True,
        "expected_latency_ms":100,
        "acquisition_cost_units":2,
        "redundancy_bps":2_000,
        "health_bps":10_000,
        "deterministic_replay_supported":True,
        "exact_provenance_supported":True,
        "raw_evidence_retention_supported":True,
        "provider_revision_policy_known":True,
        "status":SharedBAcquisitionStatus.AVAILABLE,
        "evidence_cutoff_at":NOW,
        "assessed_at":NOW,
        "provenance_refs":("provider:catalog","source:availability"),
    }
    values.update(overrides)
    return SharedBSensorAcquisitionCandidate(**values)  # type: ignore[arg-type]


def test_feasibility_is_sensor_side_not_value_decision() -> None:
    result=assess_acquisition_feasibility(
        gap=_gap(),
        candidate=_candidate(),
        maximum_latency_ms=500,
        maximum_acquisition_cost_units=5,
        minimum_health_bps=9_500,
    )
    assert result.feasibility is SharedBAcquisitionFeasibility.FEASIBLE
    assert result.cognitive_value_decided is False
    assert result.predictive_value_decided is False
    assert result.economic_value_decided is False
    assert result.trade_priority_authority is False
    assert result.capital_priority_authority is False


def test_unavailable_noncausal_and_governance_incomplete_fail_closed() -> None:
    for candidate in (
        _candidate(available=False,status=SharedBAcquisitionStatus.UNAVAILABLE),
        _candidate(causally_available_by_cutoff=False),
        _candidate(deterministic_replay_supported=False),
    ):
        result=assess_acquisition_feasibility(
            gap=_gap(),
            candidate=candidate,
            maximum_latency_ms=500,
            maximum_acquisition_cost_units=5,
            minimum_health_bps=9_500,
        )
        assert result.feasibility is SharedBAcquisitionFeasibility.NOT_FEASIBLE


def test_unknown_cost_latency_health_remains_unknown() -> None:
    result=assess_acquisition_feasibility(
        gap=_gap(),
        candidate=_candidate(
            expected_latency_ms=None,
            acquisition_cost_units=None,
            health_bps=None,
        ),
        maximum_latency_ms=500,
        maximum_acquisition_cost_units=5,
        minimum_health_bps=9_500,
    )
    assert result.feasibility is SharedBAcquisitionFeasibility.UNKNOWN


def test_degraded_health_is_explicit_not_silent_rejection() -> None:
    result=assess_acquisition_feasibility(
        gap=_gap(),
        candidate=_candidate(health_bps=8_000,status=SharedBAcquisitionStatus.DEGRADED),
        maximum_latency_ms=500,
        maximum_acquisition_cost_units=5,
        minimum_health_bps=9_500,
    )
    assert result.feasibility is SharedBAcquisitionFeasibility.FEASIBLE_DEGRADED
    assert "SENSOR_HEALTH_DEGRADED" in result.reason_codes


def test_acquired_result_requires_sealed_replayable_evidence() -> None:
    result=SharedBActivePerceptionAcquisitionResult(
        gap_id="GAP:WP05:CROSS_ASSET",
        sensor_id="CTRADER_DEMO:US2000:10012",
        status=SharedBAcquisitionStatus.ACQUIRED,
        provider_or_source_id="CTRADER_DEMO",
        canonical_observation_key="QORE:OBS:US2000",
        provider_event_min_at=NOW-timedelta(days=1),
        provider_event_max_at=NOW-timedelta(hours=1),
        retrieved_at=NOW,
        raw_evidence_sha256="a"*64,
        replay_manifest_sha256="b"*64,
        artifact_id=11113260581,
        record_count=100,
        missing_count=0,
        degraded_count=0,
        deterministic_replay_verified=True,
        exact_provenance_verified=True,
    )
    assert len(result.fingerprint())==64

    with pytest.raises(ValueError,match="ACQUIRED requires"):
        SharedBActivePerceptionAcquisitionResult(
            gap_id="G",
            sensor_id="S",
            status=SharedBAcquisitionStatus.ACQUIRED,
            provider_or_source_id="P",
            canonical_observation_key=None,
            provider_event_min_at=None,
            provider_event_max_at=None,
            retrieved_at=NOW,
            raw_evidence_sha256=None,
            replay_manifest_sha256=None,
            artifact_id=None,
            record_count=0,
            missing_count=0,
            degraded_count=0,
            deterministic_replay_verified=False,
            exact_provenance_verified=False,
        )


def test_sensor_side_candidate_rejects_outcome_and_priority_authority() -> None:
    for field in (
        "target_or_outcome_used",
        "pnl_used",
        "trade_priority_authority",
        "capital_priority_authority",
        "sensor_admission_authority",
        "execution_authority",
        "risk_authority",
    ):
        with pytest.raises(ValueError,match="forbidden evidence"):
            _candidate(**{field:True})


def test_gap_and_candidate_cannot_mismatch() -> None:
    with pytest.raises(ValueError,match="identity mismatch"):
        assess_acquisition_feasibility(
            gap=_gap(),
            candidate=_candidate(gap_id="OTHER"),
            maximum_latency_ms=500,
            maximum_acquisition_cost_units=5,
            minimum_health_bps=9_500,
        )
