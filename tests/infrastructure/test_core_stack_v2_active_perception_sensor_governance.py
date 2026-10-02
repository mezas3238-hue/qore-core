from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.active_perception_sensor_governance import (
    ActivePerceptionSensorContract,
    ActivePerceptionSensorFamily,
    SensorAdmissionStatus,
    SensorMissingnessSemantics,
    SensorObservationKind,
    SensorTimestampSemantics,
    active_perception_sensor_fingerprint,
    admit_active_perception_sensor,
)


def _valid_contract(**overrides):
    values = {
        "sensor_key": "nas100.top_of_book",
        "family": ActivePerceptionSensorFamily.MARKET_MICROSTRUCTURE,
        "observation_kind": SensorObservationKind.DIRECT_OBSERVATION,
        "provider_or_source_id": "ctrader-demo",
        "economic_or_market_scope": "NAS100",
        "timestamp_semantics": SensorTimestampSemantics.SNAPSHOT_AS_OF,
        "missingness_semantics": SensorMissingnessSemantics.EXPLICIT_MISSING,
        "retained_evidence": True,
        "deterministic_replay": True,
        "exact_provenance": True,
        "timezone_aware": True,
        "causal_as_of_available": True,
        "future_backfill_visible_at_runtime": False,
        "provider_revision_policy_known": True,
        "runtime_equivalent_source_available": True,
    }
    values.update(overrides)
    return ActivePerceptionSensorContract(**values)


def test_active_perception_sensor_admits_only_causal_replayable_evidence() -> None:
    contract = _valid_contract()
    decision = admit_active_perception_sensor(contract)

    assert decision.status is SensorAdmissionStatus.ADMITTED_FOR_R8_RESEARCH
    assert decision.reasons == ("CAUSAL_SENSOR_CONTRACT_PASS",)
    assert decision.r8_research_only is True
    assert decision.r6_r5_consumed_for_selection is False
    assert decision.fresh_holdout_opened is False


def test_active_perception_sensor_rejects_future_backfill_and_missing_provenance() -> None:
    contract = _valid_contract(
        exact_provenance=False,
        future_backfill_visible_at_runtime=True,
    )
    decision = admit_active_perception_sensor(contract)

    assert decision.status is SensorAdmissionStatus.REJECTED
    assert "PROVENANCE_INCOMPLETE" in decision.reasons
    assert "FUTURE_BACKFILL_LEAKAGE_RISK" in decision.reasons


def test_active_perception_rejects_fabricated_microstructure_from_ohlc() -> None:
    contract = _valid_contract(
        observation_kind=SensorObservationKind.SHARED_DERIVED_FEATURE,
        inferred_from_same_closed_sensor_universe=True,
    )
    decision = admit_active_perception_sensor(contract)

    assert decision.status is SensorAdmissionStatus.REJECTED
    assert "NOT_A_GENUINELY_NEW_OBSERVATION" in decision.reasons
    assert "MICROSTRUCTURE_CANNOT_BE_FABRICATED_FROM_OHLC" in decision.reasons


def test_active_perception_sensor_fingerprint_is_deterministic() -> None:
    contract = _valid_contract()
    first = active_perception_sensor_fingerprint(contract)
    second = active_perception_sensor_fingerprint(contract)

    assert first == second
    assert len(first) == 64


def test_active_perception_sensor_contract_rejects_forbidden_authority() -> None:
    with pytest.raises(ValueError, match="forbidden evidence"):
        _valid_contract(execution_authority=True)

    with pytest.raises(ValueError, match="forbidden evidence"):
        _valid_contract(outcome_used=True)
