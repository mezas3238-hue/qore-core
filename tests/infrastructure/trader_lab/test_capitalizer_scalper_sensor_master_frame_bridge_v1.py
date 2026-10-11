"""The real QORE Master Cognitive candidate receives sensors, never future R."""

from __future__ import annotations

from dataclasses import replace

import pytest

from qore.infrastructure.trader_lab.capitalizer_master_cognitive_frame import (
    CapitalizerCandidateCognitiveContext,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_entry_timing_sensors_shadow_v1 import (
    IDENTITY as SENSOR_ID,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_entry_timing_sensors_shadow_v1 import (
    EntrySensorFrame,
    SensorEvidence,
    SensorStatus,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_sensor_master_frame_bridge_v1 import (
    IDENTITY,
    bind_scalper_sensors_into_master_context,
)

AT = "2026-04-02T10:30:00+00:00"


def _sensor(name: str, value: str | None, status: SensorStatus) -> SensorEvidence:
    return SensorEvidence(
        sensor=name, status=status, observed_at=AT, value=value,
        explanation="pretrade source",
        provenance="native M1 closed and upstream source",
    )


def _frame() -> EntrySensorFrame:
    return EntrySensorFrame(
        identity=SENSOR_ID,
        symbol="EURUSD", session="LONDON", decision_at=AT,
        h1_direction="BULLISH",
        sensors=(
            _sensor("H1_BIAS_DECLARED", "BULLISH", SensorStatus.OBSERVED),
            _sensor("H1_THESIS_AGE_MINUTES", "80", SensorStatus.OBSERVED),
            _sensor("M15_PROTECTED_STOP_DECLARED", "1.0910", SensorStatus.OBSERVED),
            _sensor("ACTUAL_M15_STRUCTURE_REVALIDATION",
                    None, SensorStatus.NOT_AVAILABLE),
            _sensor("SOURCE_SIGNAL_OBSERVED", "LIQUIDITY_SWEEP_CISD",
                    SensorStatus.OBSERVED),
            _sensor("M1_PROTECTED_SWING_ATTESTATION",
                    None, SensorStatus.NOT_AVAILABLE),
            _sensor("H1_TARGET_ROOM_R", None, SensorStatus.NOT_AVAILABLE),
            _sensor("FULL_COGNITIVE_MASTER_FRAME", None, SensorStatus.NOT_AVAILABLE),
        ),
        first_source_cisd_family="LIQUIDITY_SWEEP_CISD",
        first_source_cisd_confirmed_at=AT, source_event_observed=True,
    )


def test_real_master_frame_candidate_accepts_sensor_inputs_without_authority() -> None:
    bound = bind_scalper_sensors_into_master_context(_frame())
    assert bound.identity == IDENTITY
    assert isinstance(bound.context, CapitalizerCandidateCognitiveContext)
    assert bound.context.symbol == "EURUSD"
    assert bound.context.event_is_fresh is True
    assert bound.context.genuinely_new_causal_event is True
    assert not bound.context.evidence_provenance_complete
    assert not bound.context.destination_context_known
    assert not bound.context.destination_available
    assert not bound.full_nine_market_master_frame_evaluated
    assert not bound.grants_entry_authority
    assert not bound.grants_capital_authority
    assert any("H1_THESIS_AGE_MINUTES" in x for x in bound.context.observation_tokens)
    assert any("SCALPER_PROVENANCE_COMPLETE=False" in x
               for x in bound.context.observation_tokens)


def test_new_cisd_event_is_not_repeated_on_subsequent_m1_candles() -> None:
    f = _frame()
    later = replace(f, decision_at="2026-04-02T10:31:00+00:00")
    b = bind_scalper_sensors_into_master_context(later)
    assert not b.source_event_is_new_now
    assert not b.context.event_is_fresh
    assert not b.context.genuinely_new_causal_event


def test_asof_master_frame_rejects_future_sensor_and_future_cisd() -> None:
    f = _frame()
    with pytest.raises(ValueError, match="future observation"):
        bind_scalper_sensors_into_master_context(replace(
            f, sensors=(
                replace(f.sensors[0], observed_at="2026-04-02T10:31:00+00:00"),
                *f.sensors[1:],
            ),
        ))
    with pytest.raises(ValueError, match="future CISD"):
        bind_scalper_sensors_into_master_context(replace(
            f, first_source_cisd_confirmed_at="2026-04-02T10:31:00+00:00"
        ))


def test_no_fake_complete_world_model_from_partial_m15_or_target() -> None:
    f = _frame()
    sensors = tuple(
        replace(s, status=SensorStatus.OBSERVED, value="1.6")
        if s.sensor == "H1_TARGET_ROOM_R" else s
        for s in f.sensors
    )
    b = bind_scalper_sensors_into_master_context(replace(f,sensors=sensors))
    assert b.context.destination_context_known
    assert b.context.destination_available
    assert not b.context.evidence_provenance_complete
    assert not b.full_nine_market_master_frame_evaluated


def test_missing_sensor_cannot_be_silently_promoted_to_master_brain() -> None:
    f = _frame()
    with pytest.raises(ValueError, match="missing required"):
        bind_scalper_sensors_into_master_context(replace(
            f, sensors=f.sensors[:-1],
        ))
