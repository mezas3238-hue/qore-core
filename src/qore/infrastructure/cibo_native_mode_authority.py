"""CIBO Native MAX sovereign BANK/MEDIUM/ATTACK directions into QDLE.

CIBO -- not the post-hoc replay mapper -- emits this per-opportunity PAPER
economic management instruction as part of its native decision. This is not a
broker order or LIVE signing. CIBO selects its mode and management intent;
ONLY QDLE decides physically financeable lots, stop+fees and broker margin.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from qore.infrastructure.cibo_native_max_cognitive_episode import CiboNativeMaxCognitiveEpisode

SOURCE = "CIBO_NATIVE_MAX_SOVEREIGN_MODE_QDLE_PAPER"
SHA = re.compile(r"^sha256:[a-f0-9]{64}$")
FRACTIONS = {"BANK": Decimal("0.0125"), "MEDIUM": Decimal("0.0250"), "ATTACK": Decimal("0.0500")}
EXIT_POLICIES = {
    "BANK": ("0.75", "0.75", "1.1", "0.5", "-0.35"),
    "MEDIUM": ("1", "1", "1.5", "0.75", "-0.5"),
    "ATTACK": ("1.5", "1.5", "2", "1", "-0.75"),
}
EXIT_FIELDS = (
    "partial_at_r", "breakeven_at_r", "trailing_activate_at_r",
    "trailing_distance_r", "defensive_close_at_r",
)


class CiboNativeModeError(ValueError):
    pass


def _sha(payload: dict) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _time(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CiboNativeModeError("native mode requires causal aware decision timestamp")
    return value.isoformat()


@dataclass(frozen=True, slots=True)
class NativeSovereignModeInstruction:
    signal_fingerprint: str
    trader_id: str
    decided_at: datetime
    semantic_digest: str
    mode: str
    requested_risk_fraction_of_nav: Decimal
    exit_policy: tuple[tuple[str, str], ...]
    calibration_confidence: int
    abstention_required: bool
    scenario_count: int
    decision_digest: str
    producer: str = SOURCE
    qdle_lot_authority_only: bool = True
    broker_execution_authorized: bool = False

    def __post_init__(self):
        if not self.signal_fingerprint or not self.trader_id:
            raise CiboNativeModeError("native mode signal/trader identity missing")
        _time(self.decided_at)
        if not isinstance(self.semantic_digest, str) or not SHA.fullmatch(self.semantic_digest):
            raise CiboNativeModeError("native mode semantic source digest invalid")
        if self.mode not in FRACTIONS:
            raise CiboNativeModeError("native mode must be BANK/MEDIUM/ATTACK")
        if self.requested_risk_fraction_of_nav != FRACTIONS[self.mode]:
            raise CiboNativeModeError("mode risk fraction drift")
        if self.exit_policy != tuple(zip(EXIT_FIELDS, EXIT_POLICIES[self.mode])):
            raise CiboNativeModeError("mode exit management plan drift")
        if (type(self.calibration_confidence) is not int
            or not 0 <= self.calibration_confidence <= 100
            or type(self.abstention_required) is not bool
            or type(self.scenario_count) is not int or self.scenario_count != 4):
            raise CiboNativeModeError("native cognition evidence invalid")
        if self.producer != SOURCE or not self.qdle_lot_authority_only or self.broker_execution_authorized:
            raise CiboNativeModeError("Native mode cannot claim LIVE broker/lot authority")
        if self.mode == "ATTACK" and (self.abstention_required or self.calibration_confidence < 67):
            raise CiboNativeModeError("uncalibrated ATTACK mode")
        if self.mode == "MEDIUM" and (self.abstention_required or not 34 <= self.calibration_confidence < 67):
            raise CiboNativeModeError("uncalibrated MEDIUM mode")
        if self.mode == "BANK" and not (self.abstention_required or self.calibration_confidence < 34):
            raise CiboNativeModeError("uncalibrated BANK mode")
        if self.decision_digest != _sha(self._content()):
            raise CiboNativeModeError("native instruction canonical seal mismatch")

    def _content(self):
        return {
            "signal_fingerprint": self.signal_fingerprint,
            "trader_id": self.trader_id,
            "decided_at": _time(self.decided_at),
            "semantic_digest": self.semantic_digest,
            "mode": self.mode,
            "requested_risk_fraction_of_nav": str(self.requested_risk_fraction_of_nav),
            "exit_policy": self.exit_policy,
            "calibration_confidence": self.calibration_confidence,
            "abstention_required": self.abstention_required,
            "scenario_count": self.scenario_count,
            "producer": self.producer,
            "qdle_lot_authority_only": self.qdle_lot_authority_only,
            "broker_execution_authorized": self.broker_execution_authorized,
        }

    def as_json(self):
        return {**self._content(), "exit_policy": [[k, v] for k, v in self.exit_policy], "decision_digest": self.decision_digest}


def issue_native_sovereign_mode_instruction(
    *, episode: CiboNativeMaxCognitiveEpisode, signal_fingerprint: str,
    trader_id: str, decided_at: datetime, semantic_digest: str,
) -> NativeSovereignModeInstruction:
    """Called directly by Native MAX runtime, never from historical outcomes."""
    if not isinstance(episode, CiboNativeMaxCognitiveEpisode):
        raise CiboNativeModeError("typed Native MAX cognitive episode required")
    episode.__post_init__()
    confidence = episode.calibration.confidence_band
    abstain = episode.abstention_required or (
        episode.metacognitive_audit.evidence_sufficiency.value != "sufficient"
    )
    mode = (
        "BANK" if abstain or confidence < 34 else
        "MEDIUM" if confidence < 67 else "ATTACK"
    )
    draft = dict(
        signal_fingerprint=signal_fingerprint,
        trader_id=trader_id,
        decided_at=decided_at,
        semantic_digest=semantic_digest,
        mode=mode,
        requested_risk_fraction_of_nav=FRACTIONS[mode],
        exit_policy=tuple(zip(EXIT_FIELDS, EXIT_POLICIES[mode])),
        calibration_confidence=confidence,
        abstention_required=bool(abstain),
        scenario_count=len(episode.scenarios),
    )
    # Derive digest from the eventual canonical content, not external labeling.
    provisional = NativeSovereignModeInstruction.__new__(NativeSovereignModeInstruction)
    for key, value in draft.items():
        object.__setattr__(provisional, key, value)
    object.__setattr__(provisional, "producer", SOURCE)
    object.__setattr__(provisional, "qdle_lot_authority_only", True)
    object.__setattr__(provisional, "broker_execution_authorized", False)
    return NativeSovereignModeInstruction(
        **draft, decision_digest=_sha(provisional._content())
    )


def native_mode_from_json(raw: object) -> NativeSovereignModeInstruction:
    if not isinstance(raw, dict):
        raise CiboNativeModeError("Native CIBO mode instruction missing")
    try:
        value = NativeSovereignModeInstruction(
            signal_fingerprint=raw["signal_fingerprint"],
            trader_id=raw["trader_id"],
            decided_at=datetime.fromisoformat(raw["decided_at"]),
            semantic_digest=raw["semantic_digest"],
            mode=raw["mode"],
            requested_risk_fraction_of_nav=Decimal(raw["requested_risk_fraction_of_nav"]),
            exit_policy=tuple((k, v) for k,v in raw["exit_policy"]),
            calibration_confidence=raw["calibration_confidence"],
            abstention_required=raw["abstention_required"],
            scenario_count=raw["scenario_count"],
            decision_digest=raw["decision_digest"],
            producer=raw["producer"],
            qdle_lot_authority_only=raw["qdle_lot_authority_only"],
            broker_execution_authorized=raw["broker_execution_authorized"],
        )
    except (TypeError, KeyError, ValueError, InvalidOperation) as exc:
        raise CiboNativeModeError("malformed sovereign mode instruction") from exc
    if value.as_json() != raw:
        raise CiboNativeModeError("native mode instruction noncanonical")
    return value
