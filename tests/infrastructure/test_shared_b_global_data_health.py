from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2.shared_b_global_data_health import (
    SharedBGlobalDataObservation,
    SharedBGlobalDataState,
    SharedBGlobalInterpretation,
    assess_shared_b_global_data_health,
)

T0 = datetime(2026, 9, 30, 17, 0, tzinfo=UTC)


def _obs(**overrides: object) -> SharedBGlobalDataObservation:
    values: dict[str, object] = {
        "instrument_key": "CTRADER_DEMO:US2000:10012",
        "decision_time": T0,
        "provider_event_at": T0,
        "retrieved_at": T0,
        "previous_provider_event_at": T0 - timedelta(seconds=1),
        "expected_cadence_ms": 1_000,
        "validity_horizon_ms": 5_000,
        "decay_horizon_ms": 30_000,
        "canonical_market_open": True,
        "provider_available": True,
        "feed_available": True,
        "provider_degraded": False,
        "partial_degradation": False,
        "missing": False,
        "duplicate": False,
        "sequence_monotonic": True,
        "crossed_quote": False,
        "impossible_value": False,
        "canonical_identity_verified": True,
        "roll_identity_unambiguous": True,
        "relation_evidence_age_ms": 1_000,
        "relation_validity_horizon_ms": 5_000,
        "provenance_refs": ("sealed-source",),
        "relational_comparability_verified": True,
    }
    values.update(overrides)
    return SharedBGlobalDataObservation(**values)  # type: ignore[arg-type]


def test_healthy_global_data_allows_market_and_relation_cognition() -> None:
    assessment = assess_shared_b_global_data_health(_obs())
    assert assessment.state is SharedBGlobalDataState.HEALTHY
    assert assessment.interpretation is SharedBGlobalInterpretation.MARKET_OBSERVABLE
    assert assessment.new_market_change_inference_allowed is True
    assert assessment.relational_claim_allowed is True
    assert assessment.market_plane_known is True
    assert assessment.provider_plane_available is True
    assert assessment.feed_plane_available is True


def test_market_closed_is_distinct_from_provider_and_feed_failure() -> None:
    closed = assess_shared_b_global_data_health(
        _obs(
            canonical_market_open=False,
            provider_event_at=None,
            retrieved_at=None,
            missing=True,
        )
    )
    provider = assess_shared_b_global_data_health(
        _obs(
            canonical_market_open=None,
            provider_available=False,
            feed_available=False,
            missing=True,
        )
    )
    feed = assess_shared_b_global_data_health(
        _obs(
            canonical_market_open=True,
            feed_available=False,
            missing=True,
        )
    )

    assert closed.state is SharedBGlobalDataState.MARKET_CLOSED
    assert closed.interpretation is (
        SharedBGlobalInterpretation.EXPECTED_MARKET_CLOSED_ABSENCE
    )
    assert provider.state is SharedBGlobalDataState.PROVIDER_UNAVAILABLE
    assert provider.interpretation is SharedBGlobalInterpretation.DATA_PLANE_FAILURE
    assert feed.state is SharedBGlobalDataState.FEED_UNAVAILABLE
    assert feed.interpretation is SharedBGlobalInterpretation.DATA_PLANE_FAILURE


def test_unknown_market_state_never_becomes_closed_or_healthy() -> None:
    assessment = assess_shared_b_global_data_health(
        _obs(canonical_market_open=None)
    )
    assert assessment.state is SharedBGlobalDataState.MARKET_STATE_UNKNOWN
    assert assessment.market_plane_known is False
    assert assessment.new_market_change_inference_allowed is False
    assert assessment.relational_claim_allowed is False


def test_crossed_quote_and_impossible_value_fail_closed() -> None:
    crossed = assess_shared_b_global_data_health(_obs(crossed_quote=True))
    impossible = assess_shared_b_global_data_health(_obs(impossible_value=True))
    assert crossed.state is SharedBGlobalDataState.CROSSED_QUOTE
    assert impossible.state is SharedBGlobalDataState.IMPOSSIBLE_VALUE
    assert crossed.relational_claim_allowed is False
    assert impossible.relational_claim_allowed is False


def test_partial_and_provider_degradation_are_not_market_events() -> None:
    partial = assess_shared_b_global_data_health(_obs(partial_degradation=True))
    provider = assess_shared_b_global_data_health(_obs(provider_degraded=True))
    assert partial.state is SharedBGlobalDataState.PARTIAL_DEGRADATION
    assert provider.state is SharedBGlobalDataState.PROVIDER_DEGRADED
    assert partial.new_market_change_inference_allowed is False
    assert provider.new_market_change_inference_allowed is False


def test_unverified_comparability_cannot_emit_stale_relation() -> None:
    assessment = assess_shared_b_global_data_health(
        _obs(
            relational_comparability_verified=False,
            relation_evidence_age_ms=6_000,
            relation_validity_horizon_ms=5_000,
        )
    )
    assert assessment.state is SharedBGlobalDataState.HEALTHY
    assert assessment.interpretation is SharedBGlobalInterpretation.MARKET_OBSERVABLE
    assert assessment.reason_codes == ("RELATIONAL_COMPARABILITY_UNVERIFIED",)
    assert assessment.new_market_change_inference_allowed is True
    assert assessment.relational_claim_allowed is False
    assert assessment.historical_context_usable is True


def test_healthy_market_without_relational_evidence_cannot_claim_relation() -> None:
    assessment = assess_shared_b_global_data_health(
        _obs(
            relational_comparability_verified=False,
            relation_evidence_age_ms=None,
            relation_validity_horizon_ms=None,
        )
    )
    assert assessment.state is SharedBGlobalDataState.HEALTHY
    assert assessment.reason_codes == (
        "DATA_HEALTHY_RELATIONAL_EVIDENCE_INSUFFICIENT",
    )
    assert assessment.relational_claim_allowed is False


def test_stale_relation_blocks_relation_but_not_fresh_market_observation() -> None:
    assessment = assess_shared_b_global_data_health(
        _obs(
            relation_evidence_age_ms=6_000,
            relation_validity_horizon_ms=5_000,
        )
    )
    assert assessment.state is SharedBGlobalDataState.STALE_RELATION
    assert assessment.interpretation is (
        SharedBGlobalInterpretation.RELATIONAL_EVIDENCE_DEGRADED
    )
    assert assessment.new_market_change_inference_allowed is True
    assert assessment.relational_claim_allowed is False
    assert assessment.historical_context_usable is True


def test_future_duplicate_out_of_order_and_identity_fail_closed() -> None:
    future = assess_shared_b_global_data_health(
        _obs(
            provider_event_at=T0 + timedelta(seconds=1),
            retrieved_at=T0 + timedelta(seconds=1),
        )
    )
    duplicate = assess_shared_b_global_data_health(_obs(duplicate=True))
    out_of_order = assess_shared_b_global_data_health(
        _obs(
            provider_event_at=T0 - timedelta(seconds=2),
            retrieved_at=T0 - timedelta(seconds=2),
            previous_provider_event_at=T0 - timedelta(seconds=1),
        )
    )
    identity = assess_shared_b_global_data_health(
        _obs(canonical_identity_verified=False)
    )
    assert future.state is SharedBGlobalDataState.FUTURE_EVIDENCE
    assert duplicate.state is SharedBGlobalDataState.DUPLICATE
    assert out_of_order.state is SharedBGlobalDataState.OUT_OF_ORDER
    assert identity.state is SharedBGlobalDataState.IDENTITY_AMBIGUITY


def test_open_market_stale_data_fails_closed() -> None:
    assessment = assess_shared_b_global_data_health(
        _obs(decision_time=T0 + timedelta(seconds=10))
    )
    assert assessment.state is SharedBGlobalDataState.STALE_UNEXPECTED
    assert assessment.new_market_change_inference_allowed is False
    assert assessment.relational_claim_allowed is False


def test_global_data_health_has_no_downstream_authority() -> None:
    assessment = assess_shared_b_global_data_health(_obs())
    assert assessment.execution_authority is False
    assert assessment.risk_authority is False
    assert assessment.sizing_authority is False
    assert assessment.capital_authority is False


def test_fresh_download_does_not_make_old_market_event_fresh() -> None:
    historical_event = datetime(2017, 1, 3, 14, 0, tzinfo=UTC)
    retrieved_now = T0
    assessment = assess_shared_b_global_data_health(
        _obs(
            decision_time=retrieved_now,
            provider_event_at=historical_event,
            retrieved_at=retrieved_now,
            previous_provider_event_at=historical_event - timedelta(seconds=1),
        )
    )
    assert assessment.state is SharedBGlobalDataState.STALE_UNEXPECTED
    assert assessment.reason_codes == ("MARKET_EVENT_STALE",)
    assert assessment.transport_age_ms == 0
    assert assessment.provider_event_age_ms is not None
    assert assessment.provider_event_age_ms > assessment.transport_age_ms
    assert assessment.new_market_change_inference_allowed is False
    assert assessment.relational_claim_allowed is False
