"""Only independent as-of evidence can promote missing M15/M1/H1 sensor facts."""
from __future__ import annotations

from dataclasses import replace
import pytest
from test_capitalizer_a1_source_sensor_independent_attestation_v1 import (
    _fixtures,
    _source,
)

from qore.infrastructure.trader_lab.capitalizer_a1_source_sensor_independent_attestation_v1 import (
    ProofStatus,
    attest_source_sensors,
)
from qore.infrastructure.trader_lab.capitalizer_a1_validated_sensor_overlay_v1 import (
    apply_independent_source_sensor_witnesses,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_entry_timing_sensors_shadow_v1 import (
    IDENTITY,
    EntrySensorFrame,
    SensorEvidence,
    SensorStatus,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_sensor_master_frame_bridge_v1 import (
    bind_scalper_sensors_into_master_context,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
)


def _shadow_frame() -> EntrySensorFrame:
    source = _source()
    at = source.m1_trigger_confirmed_at
    return EntrySensorFrame(
        identity=IDENTITY,
        symbol=source.symbol,
        session=source.session,
        decision_at=at,
        h1_direction=source.h1_state_direction,
        sensors=tuple(
            SensorEvidence(
                sensor=name, status=status, observed_at=at,
                value=value, explanation="source-only shadow", provenance="A2_original",
            )
            for name, status, value in (
                ("H1_BIAS_DECLARED", SensorStatus.OBSERVED, "BULLISH"),
                ("H1_THESIS_AGE_MINUTES", SensorStatus.OBSERVED, "64"),
                ("M15_PROTECTED_STOP_DECLARED", SensorStatus.OBSERVED, "95"),
                ("ACTUAL_M15_STRUCTURE_REVALIDATION", SensorStatus.NOT_AVAILABLE, None),
                ("M1_PROTECTED_SWING_ATTESTATION", SensorStatus.NOT_AVAILABLE, None),
                ("H1_TARGET_ROOM_R", SensorStatus.NOT_AVAILABLE, None),
                ("FULL_COGNITIVE_MASTER_FRAME", SensorStatus.NOT_AVAILABLE, None),
                ("SOURCE_SIGNAL_OBSERVED", SensorStatus.OBSERVED, "FVG_RETRACE_CISD"),
            )
        ),
        first_source_cisd_family="FVG_RETRACE_CISD",
        first_source_cisd_confirmed_at=at,
        source_event_observed=True,
    )


def test_raw_source_witnesses_reach_master_context_without_fake_full_frame() -> None:
    source = _source()
    m1, m15, h1 = _fixtures()
    witness = attest_source_sensors(source, m1=m1, m15=m15, h1=h1)
    original = _shadow_frame()
    updated = apply_independent_source_sensor_witnesses(
        frame=original, source_opportunity_id=source_opportunity_id(source),
        witness=witness,
    )
    old = {x.sensor: x for x in original.sensors}
    now = {x.sensor: x for x in updated.sensors}
    assert all(old[name].status is SensorStatus.NOT_AVAILABLE for name in (
        "ACTUAL_M15_STRUCTURE_REVALIDATION",
        "M1_PROTECTED_SWING_ATTESTATION",
        "H1_TARGET_ROOM_R",
        "FULL_COGNITIVE_MASTER_FRAME",
    ))
    assert all(now[name].status is SensorStatus.OBSERVED for name in (
        "ACTUAL_M15_STRUCTURE_REVALIDATION",
        "M1_PROTECTED_SWING_ATTESTATION",
        "H1_TARGET_ROOM_R",
    ))
    assert now["ACTUAL_M15_STRUCTURE_REVALIDATION"].value == "95"
    assert now["M1_PROTECTED_SWING_ATTESTATION"].value == "97"
    assert now["H1_TARGET_ROOM_R"].value is not None
    assert now["FULL_COGNITIVE_MASTER_FRAME"].status is SensorStatus.NOT_AVAILABLE
    assert updated.first_source_cisd_family == original.first_source_cisd_family
    assert not updated.execution_authorized
    binding = bind_scalper_sensors_into_master_context(updated)
    assert binding.context.evidence_provenance_complete
    assert binding.context.destination_context_known
    assert binding.context.destination_available
    assert not binding.full_nine_market_master_frame_evaluated
    assert not binding.grants_entry_authority


def test_missing_h1_remains_unavailable_and_does_not_block_original_signal() -> None:
    source = _source()
    m1, m15, h1 = _fixtures()
    witness = attest_source_sensors(
        source, m1=m1, m15=m15,
        h1=(replace(h1[0], minute_count=59),),
    )
    updated = apply_independent_source_sensor_witnesses(
        frame=_shadow_frame(), source_opportunity_id=source_opportunity_id(source),
        witness=witness,
    )
    by = {x.sensor: x for x in updated.sensors}
    assert by["H1_TARGET_ROOM_R"].status is SensorStatus.NOT_AVAILABLE
    assert by["ACTUAL_M15_STRUCTURE_REVALIDATION"].status is SensorStatus.OBSERVED
    assert by["M1_PROTECTED_SWING_ATTESTATION"].status is SensorStatus.OBSERVED
    assert updated.source_event_observed
    binding = bind_scalper_sensors_into_master_context(updated)
    assert not binding.context.destination_context_known
    assert not binding.context.evidence_provenance_complete


def test_witness_overlay_rejects_future_forged_brain_and_wrong_source() -> None:
    source = _source()
    m1, m15, h1 = _fixtures()
    witness = attest_source_sensors(source, m1=m1, m15=m15, h1=h1)
    frame = _shadow_frame()
    with pytest.raises(ValueError, match="original source M1"):
        apply_independent_source_sensor_witnesses(
            frame=frame, source_opportunity_id="WRONG", witness=witness,
        )
    fake_brain = replace(witness, evidence=(
        *witness.evidence[:3],
        replace(witness.evidence[3], status=ProofStatus.OBSERVED),
    ))
    with pytest.raises(ValueError, match="cannot certify full Master"):
        apply_independent_source_sensor_witnesses(
            frame=frame, source_opportunity_id=source_opportunity_id(source),
            witness=fake_brain,
        )
    future = replace(witness, evidence=(
        replace(
            witness.evidence[0],
            observed_at="2026-01-05T01:05:00+00:00",
        ),
        *witness.evidence[1:],
    ))
    with pytest.raises(ValueError, match="future attestation"):
        apply_independent_source_sensor_witnesses(
            frame=frame, source_opportunity_id=source_opportunity_id(source),
            witness=future,
        )
    double = replace(frame, sensors=(*frame.sensors, frame.sensors[-1]))
    with pytest.raises(ValueError, match="duplicate shadow"):
        apply_independent_source_sensor_witnesses(
            frame=double, source_opportunity_id=source_opportunity_id(source),
            witness=witness,
        )
