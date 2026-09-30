from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2.shared_data_health_intelligence import (
    SharedDataChangeInterpretation,
    SharedDataHealthObservation,
    SharedDataHealthState,
    SharedFreshnessState,
    assess_shared_data_health,
)

T0 = datetime(2026, 9, 30, 14, 0, tzinfo=UTC)


def _obs(**overrides: object) -> SharedDataHealthObservation:
    values: dict[str, object] = {
        "instrument_key": "USTEC",
        "observed_at": T0,
        "available_at": T0,
        "decision_time": T0,
        "previous_observed_at": T0 - timedelta(minutes=1),
        "expected_cadence_ms": 60_000,
        "validity_horizon_ms": 120_000,
        "decay_horizon_ms": 300_000,
        "market_open": True,
        "missing": False,
        "duplicate": False,
        "sequence_monotonic": True,
        "canonical_identity_verified": True,
        "roll_identity_unambiguous": True,
        "provider_healthy": True,
        "provenance_refs": ("real-provider-source",),
    }
    values.update(overrides)
    return SharedDataHealthObservation(**values)  # type: ignore[arg-type]


def test_healthy_fresh_data_allows_new_market_inference() -> None:
    a = assess_shared_data_health(_obs())
    assert a.state is SharedDataHealthState.HEALTHY
    assert a.freshness is SharedFreshnessState.FRESH
    assert a.interpretation is SharedDataChangeInterpretation.MARKET_OBSERVABLE
    assert a.new_market_change_inference_allowed is True
    assert a.historical_context_usable is True


def test_closed_market_staleness_is_not_market_change() -> None:
    a = assess_shared_data_health(
        _obs(
            market_open=False,
            decision_time=T0 + timedelta(minutes=3),
        )
    )
    assert a.state is SharedDataHealthState.MARKET_CLOSED
    assert a.interpretation is (
        SharedDataChangeInterpretation.EXPECTED_MARKET_CLOSED_ABSENCE
    )
    assert a.new_market_change_inference_allowed is False
    assert a.historical_context_usable is True


def test_open_market_staleness_is_data_feed_change() -> None:
    a = assess_shared_data_health(
        _obs(decision_time=T0 + timedelta(minutes=3))
    )
    assert a.state is SharedDataHealthState.STALE_UNEXPECTED
    assert a.freshness is SharedFreshnessState.STALE
    assert a.interpretation is SharedDataChangeInterpretation.DATA_FEED_CHANGE
    assert a.new_market_change_inference_allowed is False


def test_future_evidence_fails_closed() -> None:
    a = assess_shared_data_health(
        _obs(
            observed_at=T0 + timedelta(seconds=1),
            available_at=T0 + timedelta(seconds=1),
        )
    )
    assert a.state is SharedDataHealthState.FUTURE_EVIDENCE
    assert a.new_market_change_inference_allowed is False
    assert a.uncertainty_floor_bps == 10_000


def test_duplicate_and_out_of_order_fail_closed() -> None:
    duplicate = assess_shared_data_health(_obs(duplicate=True))
    assert duplicate.state is SharedDataHealthState.DUPLICATE

    out_of_order = assess_shared_data_health(
        _obs(
            observed_at=T0 - timedelta(minutes=2),
            available_at=T0 - timedelta(minutes=2),
            previous_observed_at=T0 - timedelta(minutes=1),
        )
    )
    assert out_of_order.state is SharedDataHealthState.OUT_OF_ORDER


def test_identity_roll_and_provider_anomalies_are_not_market_events() -> None:
    identity = assess_shared_data_health(
        _obs(canonical_identity_verified=False)
    )
    roll = assess_shared_data_health(_obs(roll_identity_unambiguous=False))
    provider = assess_shared_data_health(_obs(provider_healthy=False))

    assert identity.state is SharedDataHealthState.IDENTITY_AMBIGUITY
    assert roll.state is SharedDataHealthState.ROLL_AMBIGUITY
    assert provider.state is SharedDataHealthState.PROVIDER_ANOMALY
    assert all(
        item.new_market_change_inference_allowed is False
        for item in (identity, roll, provider)
    )


def test_missing_data_depends_on_market_clock() -> None:
    missing_open = assess_shared_data_health(
        _obs(observed_at=None, available_at=None, missing=True)
    )
    missing_closed = assess_shared_data_health(
        _obs(
            observed_at=None,
            available_at=None,
            missing=True,
            market_open=False,
        )
    )

    assert missing_open.state is SharedDataHealthState.MISSING
    assert missing_closed.state is SharedDataHealthState.MARKET_CLOSED
    assert missing_closed.interpretation is (
        SharedDataChangeInterpretation.EXPECTED_MARKET_CLOSED_ABSENCE
    )


def test_expired_closed_market_context_is_not_usable() -> None:
    a = assess_shared_data_health(
        _obs(
            market_open=False,
            decision_time=T0 + timedelta(minutes=10),
        )
    )
    assert a.freshness is SharedFreshnessState.EXPIRED
    assert a.historical_context_usable is False


def test_no_downstream_authority() -> None:
    a = assess_shared_data_health(_obs())
    assert a.execution_authority is False
    assert a.risk_authority is False
    assert a.sizing_authority is False
    assert a.capital_authority is False
