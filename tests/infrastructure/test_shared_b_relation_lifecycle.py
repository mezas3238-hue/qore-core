from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_b_relation_lifecycle import (
    SharedBLeadLagState,
    SharedBRelationComparability,
    SharedBRelationLifecycleState,
    SharedBRelationObservation,
    append_relation_observation,
)

T0 = datetime(2026, 9, 30, 17, 0, tzinfo=UTC)


def _obs(**overrides: object) -> SharedBRelationObservation:
    values: dict[str, object] = {
        "relation_id": "REL:US2000:XAUUSD:M1",
        "source_instrument_key": "CTRADER_DEMO:US2000:10012",
        "target_instrument_key": "CTRADER_DEMO:XAUUSD:41",
        "horizon": "M1",
        "observed_at": T0,
        "evidence_cutoff_at": T0,
        "comparability": SharedBRelationComparability.COMPARABLE,
        "strength_bps": 5_000,
        "confidence_bps": 8_000,
        "stability_bps": 8_000,
        "lag_ms": 1_000,
        "leader_instrument_key": "CTRADER_DEMO:US2000:10012",
        "relationship_half_life_ms": 60_000,
        "provenance_refs": ("sealed-source",),
    }
    values.update(overrides)
    return SharedBRelationObservation(**values)  # type: ignore[arg-type]


def test_first_comparable_observation_is_emerging() -> None:
    track = append_relation_observation(observation=_obs())
    point = track.points[-1]

    assert point.state is SharedBRelationLifecycleState.EMERGING
    assert point.lead_lag_state is SharedBLeadLagState.SOURCE_LEADS
    assert point.relation_age_ms == 0
    assert len(track.fingerprint()) == 64


def test_strengthening_weakening_break_and_decoupling_are_descriptive() -> None:
    track = append_relation_observation(observation=_obs())
    track = append_relation_observation(
        observation=_obs(
            observed_at=T0 + timedelta(minutes=1),
            evidence_cutoff_at=T0 + timedelta(minutes=1),
            strength_bps=6_500,
        ),
        previous_track=track,
    )
    assert track.points[-1].state is SharedBRelationLifecycleState.STRENGTHENING

    track = append_relation_observation(
        observation=_obs(
            observed_at=T0 + timedelta(minutes=2),
            evidence_cutoff_at=T0 + timedelta(minutes=2),
            strength_bps=4_000,
        ),
        previous_track=track,
    )
    assert track.points[-1].state is SharedBRelationLifecycleState.WEAKENING

    track = append_relation_observation(
        observation=_obs(
            observed_at=T0 + timedelta(minutes=3),
            evidence_cutoff_at=T0 + timedelta(minutes=3),
            strength_bps=4_000,
            stability_bps=2_000,
        ),
        previous_track=track,
    )
    assert track.points[-1].state is SharedBRelationLifecycleState.BREAKING

    track = append_relation_observation(
        observation=_obs(
            observed_at=T0 + timedelta(minutes=4),
            evidence_cutoff_at=T0 + timedelta(minutes=4),
            strength_bps=1_000,
            stability_bps=8_000,
        ),
        previous_track=track,
    )
    assert track.points[-1].state is SharedBRelationLifecycleState.DECOUPLED


def test_leader_reversal_is_recorded_without_causal_claim() -> None:
    track = append_relation_observation(observation=_obs())
    track = append_relation_observation(
        observation=_obs(
            observed_at=T0 + timedelta(minutes=1),
            evidence_cutoff_at=T0 + timedelta(minutes=1),
            leader_instrument_key="CTRADER_DEMO:XAUUSD:41",
            lag_ms=2_000,
        ),
        previous_track=track,
    )

    point = track.points[-1]
    assert point.lead_lag_state is SharedBLeadLagState.LEADER_REVERSAL
    assert "LEADER_IDENTITY_CHANGED" in point.transition_reason_codes


def test_non_comparable_observation_cannot_carry_relation_metrics() -> None:
    with pytest.raises(ValueError, match="non-comparable relation"):
        _obs(comparability=SharedBRelationComparability.NOT_COMPARABLE)

    track = append_relation_observation(
        observation=_obs(
            comparability=SharedBRelationComparability.NOT_COMPARABLE,
            strength_bps=None,
            stability_bps=None,
            lag_ms=None,
            leader_instrument_key=None,
            relationship_half_life_ms=None,
        )
    )
    point = track.points[-1]
    assert point.state is SharedBRelationLifecycleState.INSUFFICIENT
    assert point.lead_lag_state is SharedBLeadLagState.INSUFFICIENT


def test_lifecycle_rejects_future_evidence_and_hindsight_append() -> None:
    with pytest.raises(ValueError, match="future relation evidence"):
        _obs(evidence_cutoff_at=T0 + timedelta(seconds=1))

    track = append_relation_observation(observation=_obs())
    with pytest.raises(ValueError, match="cannot append"):
        append_relation_observation(
            observation=_obs(
                observed_at=T0,
                evidence_cutoff_at=T0,
            ),
            previous_track=track,
        )


def test_lifecycle_identity_drift_fails_closed() -> None:
    track = append_relation_observation(observation=_obs())
    with pytest.raises(ValueError, match="identity drift"):
        append_relation_observation(
            observation=_obs(
                relation_id="REL:OTHER",
                observed_at=T0 + timedelta(minutes=1),
                evidence_cutoff_at=T0 + timedelta(minutes=1),
            ),
            previous_track=track,
        )


def test_relation_observation_rejects_forbidden_authority_and_outcome() -> None:
    for field in (
        "target_or_outcome_used",
        "future_market_used",
        "execution_authority",
        "risk_authority",
        "sizing_authority",
        "capital_authority",
    ):
        with pytest.raises(ValueError, match="forbidden authority"):
            _obs(**{field: True})
