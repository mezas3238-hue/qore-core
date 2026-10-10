"""Causal Scalper M1 sensor facts into the real QORE Master Cognitive Frame API.

This adapter supplies PRE-DECISION contextual evidence to a
CapitalizerCandidateCognitiveContext. It does not build a 9-market world,
invent regime/portfolio facts, or claim any Master Frame has been evaluated.
A1 must supply actual world/perceptions/regimes/cross-market graph to
build_master_cognitive_frame and log ACCEPT/WAIT/ABSTAIN decisions.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_master_cognitive_frame import (
    CapitalizerCandidateCognitiveContext,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_entry_timing_sensors_shadow_v1 import (
    EntrySensorFrame,
    SensorStatus,
)

IDENTITY = "QORE_SCALPER_SENSOR_TO_MASTER_CONTEXT_ADAPTER_V1"


@dataclass(frozen=True, slots=True)
class ScalperMasterSensorBinding:
    identity: str
    input_frame_identity: str
    context: CapitalizerCandidateCognitiveContext
    source_event_is_new_now: bool
    raw_m15_protected_swing_verified: bool = False
    full_nine_market_master_frame_evaluated: bool = False
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False
    uses_future_prices: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or any((
            self.raw_m15_protected_swing_verified,
            self.full_nine_market_master_frame_evaluated,
            self.grants_entry_authority,
            self.grants_capital_authority,
            self.uses_future_prices,
        )):
            raise ValueError("sensor binding is input to full brain, never authority")


def bind_scalper_sensors_into_master_context(
    frame: EntrySensorFrame,
) -> ScalperMasterSensorBinding:
    """Feed all status-tagged *observed* facts without inferring confidence.

    Missing M15 structural attestation, causal liquidity witness or broker
    quotes do NOT become zeroes or synthetic feature values.
    """

    at = datetime.fromisoformat(frame.decision_at)
    if at.utcoffset() is None:
        raise ValueError("Master context needs an aware as-of timestamp")
    by_name = {s.sensor: s for s in frame.sensors}
    if len(by_name) != len(frame.sensors):
        raise ValueError("duplicate sensor evidence key")
    def state(name: str) -> SensorStatus:
        if name not in by_name:
            raise ValueError("missing required Master Frame sensor " + name)
        return by_name[name].status
    for name in (
        "H1_BIAS_DECLARED", "H1_THESIS_AGE_MINUTES",
        "M15_PROTECTED_STOP_DECLARED", "ACTUAL_M15_STRUCTURE_REVALIDATION",
        "SOURCE_SIGNAL_OBSERVED", "M1_PROTECTED_SWING_ATTESTATION",
        "H1_TARGET_ROOM_R", "FULL_COGNITIVE_MASTER_FRAME",
    ):
        state(name)
    for item in frame.sensors:
        if datetime.fromisoformat(item.observed_at) > at:
            raise ValueError("sensor reports future observation beyond decision")
        if item.sensor in ("ORIGINAL_REALIZED_R", "MFE", "MAE", "FUTURE_H1_EXPIRY"):
            raise ValueError("outcome knowledge in predecision sensor")
    first_confirmed_at = (
        datetime.fromisoformat(frame.first_source_cisd_confirmed_at)
        if frame.first_source_cisd_confirmed_at else None
    )
    if first_confirmed_at is not None and first_confirmed_at > at:
        raise ValueError("future CISD event cannot count at current decision")
    new_event = frame.source_event_observed and first_confirmed_at == at
    destination_known = state("H1_TARGET_ROOM_R") in (
        SensorStatus.OBSERVED, SensorStatus.CONTRADICTORY
    )
    room = by_name["H1_TARGET_ROOM_R"].value
    available = bool(destination_known and room is not None and Decimal(room) > 0)
    # Full evidence is NOT complete if native M15 source swing is not
    # independently proved, target missing, or no original source event.
    raw_m15 = state("ACTUAL_M15_STRUCTURE_REVALIDATION") is SensorStatus.OBSERVED
    provenance_complete = raw_m15 and new_event and destination_known
    tokens = tuple(
        f"SCALPER_SENSOR:{r.sensor}:{r.status.value}:{r.value if r.value is not None else 'NA'}"
        for r in frame.sensors
    )
    tokens += (
        "SCALPER_NATIVE_M1_ASOF=YES",
        f"SCALPER_SOURCE_CISD_FIRST={frame.first_source_cisd_family or 'NA'}",
        f"SCALPER_NEW_CISD_AT_DECISION={new_event}",
        f"SCALPER_PROVENANCE_COMPLETE={provenance_complete}",
        "SCALPER_MASTER_COGNITIVE_FRAME_UNEVALUATED=YES",
    )
    fingerprint = hashlib.sha256(
        "|".join((frame.symbol, frame.session, frame.h1_direction, *tokens)).encode()
    ).hexdigest()
    context = CapitalizerCandidateCognitiveContext(
        symbol=frame.symbol,
        observed_at=at,
        failure_state_fingerprint=fingerprint,
        evidence_provenance_complete=provenance_complete,
        destination_context_known=destination_known,
        destination_available=available,
        event_is_fresh=new_event,
        genuinely_new_causal_event=new_event,
        observation_tokens=tokens,
    )
    return ScalperMasterSensorBinding(
        identity=IDENTITY,
        input_frame_identity=frame.identity,
        context=context,
        source_event_is_new_now=new_event,
    )
