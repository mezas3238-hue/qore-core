from dataclasses import replace

from qore.infrastructure.core_stack_v2.shared_lab_data_pipeline import (
    ContinuityEvent,
    ObservationDisposition,
    bind_next_consumer,
    build_validated_sensor_receipt,
    classify_continuity,
    deterministic_replay_equal,
    uncertainty_after_degradation,
)
from qore.infrastructure.core_stack_v2.shared_lab_data_reality import (
    CanonicalIdentity,
    DataQualityMetrics,
    DataQualityThresholds,
    ProviderDatum,
    ProviderProvenance,
)


def _datum() -> ProviderDatum:
    ident = CanonicalIdentity("FX:EURUSD", "FX", "EUR", quote_currency="USD")
    prov = ProviderProvenance("p1", "source", "a" * 64, "decoder-v1", "map-v1")
    return ProviderDatum("d1", "EUR/USD", "p1", 1, 1_000, 1_010, 1.1, 1.1002, "FX", prov, ident, True, "LONDON")


def _metrics() -> DataQualityMetrics:
    return DataQualityMetrics(1, 1, 0, 0, 0, 0, 0, 0, (), (10,), 1)


def test_end_to_end_provider_to_validated_sensor_receipt() -> None:
    datum = _datum()
    aliases = {"EURUSD": (datum.canonical_identity,)}
    observation, receipt = build_validated_sensor_receipt(
        datum=datum,
        sensor_id="sensor.fx.microstructure",
        sensor_output=0.75,
        alias_map=aliases,
        expected_market_open=True,
        decision_at_ns=1_020,
        consumed_at_ns=1_030,
        now_ns=1_020,
        freshness_limit_ns=100,
        quality_metrics=_metrics(),
        quality_thresholds=DataQualityThresholds(),
    )
    assert observation is not None
    assert receipt.passed
    assert receipt.disposition is ObservationDisposition.VALIDATED
    assert observation.parent_fingerprint == receipt.raw_parent_fingerprint
    assert len(receipt.sensor_output_fingerprint or "") == 64


def test_future_leakage_blocks_output_not_merely_warns() -> None:
    datum = replace(_datum(), available_at_ns=1_100)
    observation, receipt = build_validated_sensor_receipt(
        datum=datum, sensor_id="s", sensor_output=1.0,
        alias_map={"EURUSD": (datum.canonical_identity,)}, expected_market_open=True,
        decision_at_ns=1_050, consumed_at_ns=1_200, now_ns=1_100, freshness_limit_ns=1_000,
        quality_metrics=_metrics(), quality_thresholds=DataQualityThresholds(),
    )
    assert observation is None
    assert receipt.disposition is ObservationDisposition.BLOCKED
    assert not receipt.chronology_pass


def test_uncertainty_rises_under_noncritical_degradation() -> None:
    assert uncertainty_after_degradation(base_uncertainty=0.1, missing_required_fraction=0.4, provider_conflict=False, stale=False) > 0.1
    assert uncertainty_after_degradation(base_uncertainty=0.1, missing_required_fraction=0.4, provider_conflict=True, stale=True) == 0.8


def test_continuity_classification_detects_duplicate_gap_and_reconnect() -> None:
    assert classify_continuity((1, 2, 3)) is ContinuityEvent.NORMAL
    assert classify_continuity((1, 2, 2)) is ContinuityEvent.DUPLICATE_EVENT
    assert classify_continuity((1, 3)) is ContinuityEvent.SEQUENCE_GAP
    assert classify_continuity((1, 2), reconnected=True) is ContinuityEvent.RECONNECT


def test_deterministic_replay_and_exact_next_consumer_lineage() -> None:
    datum = _datum()
    kwargs = dict(
        datum=datum,
        sensor_id="sensor.fx.microstructure",
        sensor_output=0.75,
        alias_map={"EURUSD": (datum.canonical_identity,)},
        expected_market_open=True,
        decision_at_ns=1_020,
        consumed_at_ns=1_030,
        now_ns=1_020,
        freshness_limit_ns=100,
        quality_metrics=_metrics(),
        quality_thresholds=DataQualityThresholds(),
    )
    observation_1, receipt_1 = build_validated_sensor_receipt(**kwargs)
    observation_2, receipt_2 = build_validated_sensor_receipt(**kwargs)
    assert deterministic_replay_equal(observation_1, receipt_1, observation_2, receipt_2)
    assert receipt_1.sensor_output_fingerprint is not None
    bound = bind_next_consumer(receipt_1, receipt_1.sensor_output_fingerprint)
    assert bound.lineage_exact_to_next_consumer


def test_wrong_next_consumer_parent_is_detected() -> None:
    datum = _datum()
    _, receipt = build_validated_sensor_receipt(
        datum=datum,
        sensor_id="s",
        sensor_output=0.5,
        alias_map={"EURUSD": (datum.canonical_identity,)},
        expected_market_open=True,
        decision_at_ns=1_020,
        consumed_at_ns=1_030,
        now_ns=1_020,
        freshness_limit_ns=100,
        quality_metrics=_metrics(),
        quality_thresholds=DataQualityThresholds(),
    )
    bound = bind_next_consumer(receipt, "0" * 64)
    assert not bound.lineage_exact_to_next_consumer
