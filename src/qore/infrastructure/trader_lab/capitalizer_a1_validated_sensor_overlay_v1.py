"""Research bridge: independently proven native-M1/M15/H1 evidence -> A1 sensor frame.

Only independent OBSERVED witnesses upgrade an A2 NOT_AVAILABLE market
sensor. This never upgrades FULL_COGNITIVE_MASTER_FRAME: executing a
nine-market Frame, not observing a market price, must attest that fact.

The frozen V49 signals and base A2 sensor book are never mutated, and no
new entry veto, source-author certificate, risk sizing or LIVE permission
is created by this representation.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_a1_source_sensor_independent_attestation_v1 import (
    A1SourceSensorAttestation,
    ProofStatus,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_entry_timing_sensors_shadow_v1 import (
    EntrySensorFrame,
    SensorEvidence,
    SensorStatus,
)

UPGRADABLE = frozenset((
    "ACTUAL_M15_STRUCTURE_REVALIDATION",
    "M1_PROTECTED_SWING_ATTESTATION",
    "H1_TARGET_ROOM_R",
))
FRAME_ID = "FULL_COGNITIVE_MASTER_FRAME"


def _kv(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for piece in value.split(";"):
        name, sep, payload = piece.partition("=")
        if not sep or not name or not payload or name in result:
            raise ValueError("independent witness has malformed causal attributes")
        result[name] = payload
    return result


def _aware(value: str) -> datetime:
    at = datetime.fromisoformat(value)
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("independent proof uses naive timestamp")
    return at


def _verified_value(
    name: str, proof_source: str, independent: str, *,
    frame: EntrySensorFrame,
) -> str:
    source = _kv(proof_source)
    observed = _kv(independent)
    at = _aware(frame.decision_at)
    if name == "ACTUAL_M15_STRUCTURE_REVALIDATION":
        if (
            _aware(source["confirmed"]) >= at
            or _aware(source["confirmed"]) != _aware(observed["confirmed"])
            or Decimal(source["stop"]) != Decimal(observed["swing"])
        ):
            raise ValueError("M15 independent price/timestamp mismatch")
        return source["stop"]
    if name == "M1_PROTECTED_SWING_ATTESTATION":
        if _aware(observed["confirmed"]) != at or Decimal(observed["swing"]) <= 0:
            raise ValueError("M1 protected swing not confirmed at source M1 close")
        return observed["swing"]
    if name == "H1_TARGET_ROOM_R":
        if (
            Decimal(source["target"]) != Decimal(observed["target"])
            or _aware(observed["confirmed"]) > at
        ):
            raise ValueError("H1 target lacks an as-of independent candle")
        value = Decimal(source["room_r"])
        if not value.is_finite() or value <= 0:
            raise ValueError("independent H1 target room must be positive")
        return str(value)
    raise ValueError("no direct market sensor can validate full cognition")


def apply_independent_source_sensor_witnesses(
    *,
    frame: EntrySensorFrame,
    source_opportunity_id: str,
    witness: A1SourceSensorAttestation,
) -> EntrySensorFrame:
    """Update research view only, preserving the source-CISD conflict unchanged."""
    at = _aware(frame.decision_at)
    if (
        not source_opportunity_id
        or witness.source_opportunity_id != source_opportunity_id
        or witness.symbol != frame.symbol
        or _aware(witness.decision_at) != at
    ):
        raise ValueError("independent witness does not match original source M1 identity")
    original_by_name = {row.sensor: row for row in frame.sensors}
    if len(original_by_name) != len(frame.sensors):
        raise ValueError("duplicate shadow sensor names")
    proofs = {row.sensor: row for row in witness.evidence}
    if len(proofs) != len(witness.evidence) or set(proofs) != UPGRADABLE | {FRAME_ID}:
        raise ValueError("incomplete or duplicated independent witness set")
    if proofs[FRAME_ID].status is not ProofStatus.NOT_AVAILABLE:
        raise ValueError("one-market OHLC cannot certify full Master Frame")
    replacements: dict[str, SensorEvidence] = {}
    for name in UPGRADABLE:
        prior = original_by_name.get(name)
        proof = proofs[name]
        if prior is None:
            raise ValueError("original A2 sensor field missing: " + name)
        if _aware(proof.observed_at) > at:
            raise ValueError("future attestation cannot enter M1 cognition")
        if proof.status is not ProofStatus.OBSERVED:
            continue
        if prior.status is not SensorStatus.NOT_AVAILABLE:
            raise ValueError("independent proof cannot overwrite existing A2 market fact")
        if proof.source_witness is None or proof.independent_witness is None:
            raise ValueError("OBSERVED status requires both source and raw-M1 witness")
        val = _verified_value(
            name, proof.source_witness, proof.independent_witness, frame=frame
        )
        replacements[name] = replace(
            prior, status=SensorStatus.OBSERVED, value=val,
            provenance="A1_INDEPENDENT_NATIVE_M1:" + proof.provenance,
            explanation=proof.reason + "; source A2 shadow left unchanged",
        )
    return replace(frame, sensors=tuple(
        replacements.get(row.sensor, row) for row in frame.sensors
    ))
