"""Shared deterministic contracts for concrete QORE trader research signals.

This module owns the smallest explicit side/signal representation used by the
DEMO/research trader producers. It is intentionally separate from execution
authority: a trader signal is a falsifiable directional hypothesis, never an
``OrderIntent``, never a Risk authorization, and never a production decision.

The ``FunctionalDecision.outcome`` enum is closed to authorization/status
semantics (APPROVED / REJECTED / BLOCKED / DEGRADED) and therefore MUST NOT be
abused as a trade side. This module maps a directional signal as follows:

* BUY / SELL -> ``DecisionOutcome.APPROVED`` ("a determinate directional signal
  was emitted"): both directions are "approved" as emitted signals, never an
  approval of the buy direction itself.
* ABSTAIN -> ``DecisionOutcome.BLOCKED`` ("no determinate signal; fail closed").
* REJECTED / DEGRADED are never emitted by these producers.

The side is carried first-class in ``metadata.attributes["side"]`` (exactly
``"buy"`` / ``"sell"`` / ``"abstain"``) and is extractable through
:func:`extract_trader_signal_side`, so downstream consumers never have to guess.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType

from qore.domain.events import CorrelationId
from qore.functional.decisions import (
    DecisionId,
    DecisionMetadata,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionStatus,
    DecisionType,
    FunctionalDecision,
)
from qore.infrastructure.research_lineage_canonical import _cjson, _sha256
from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError

_SIGNAL_DECISION_TYPE = DecisionType("qore.trader.research-signal")
_DECISION_ID_DOMAIN = b"qore.trader.research-signal-decision-id.v1"
_CORRELATION_ID_DOMAIN = b"qore.trader.research-signal-correlation-id.v1"
_SIDE_ATTRIBUTE = "side"

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "secret=",
    "token=",
)


class TraderSignalSide(StrEnum):
    """Closed directional signal of a concrete trader methodology."""

    BUY = "buy"
    SELL = "sell"
    ABSTAIN = "abstain"


def _validate_public_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResearchLineageValidationError(f"{field_name} must be a non-empty str")
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise ResearchLineageValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def derive_trader_correlation_id(binding_fingerprint: str) -> CorrelationId:
    """Derive one stable correlation identity per research run binding."""
    if not isinstance(binding_fingerprint, str) or not binding_fingerprint:
        raise ResearchLineageValidationError(
            "binding fingerprint must be a non-empty str"
        )
    digest = hashlib.sha256(
        _CORRELATION_ID_DOMAIN + b"|" + binding_fingerprint.encode("ascii")
    ).digest()
    return CorrelationId(uuid.UUID(bytes=digest[:16]))


def _canonical_evidence(evidence: Mapping[str, str]) -> str:
    if not isinstance(evidence, Mapping):
        raise ResearchLineageValidationError("evidence must be a Mapping")
    for key, value in evidence.items():
        if not isinstance(key, str) or not key:
            raise ResearchLineageValidationError("evidence keys must be non-empty str")
        if not isinstance(value, str):
            raise ResearchLineageValidationError("evidence values must be str")
    return "|".join(f"{key}={value}" for key, value in sorted(evidence.items()))


def derive_trader_decision_id(
    *,
    binding_fingerprint: str,
    sequence_number: int,
    side: TraderSignalSide,
    evidence: Mapping[str, str],
) -> DecisionId:
    """Derive a deterministic, collision-resistant decision id for one signal."""
    if not isinstance(binding_fingerprint, str) or not binding_fingerprint:
        raise ResearchLineageValidationError(
            "binding fingerprint must be a non-empty str"
        )
    if (
        isinstance(sequence_number, bool)
        or type(sequence_number) is not int
        or sequence_number < 0
    ):
        raise ResearchLineageValidationError(
            "sequence_number must be a non-negative int; bool rejected"
        )
    if not isinstance(side, TraderSignalSide):
        raise ResearchLineageValidationError("side must be TraderSignalSide")
    digest = hashlib.sha256(
        _DECISION_ID_DOMAIN
        + b"|"
        + binding_fingerprint.encode("ascii")
        + b"|"
        + str(sequence_number).encode("ascii")
        + b"|"
        + side.value.encode("ascii")
        + b"|"
        + _canonical_evidence(evidence).encode("utf-8")
    ).digest()
    return DecisionId(uuid.UUID(bytes=digest[:16]))


def build_trader_signal_decision(
    *,
    decision_id: DecisionId,
    timestamp: datetime,
    correlation_id: CorrelationId,
    side: TraderSignalSide,
    reason_code: str,
    summary: str,
    evidence: Mapping[str, str],
) -> FunctionalDecision:
    """Project an explicit trader signal into a resolved FunctionalDecision."""
    if not isinstance(decision_id, DecisionId):
        raise ResearchLineageValidationError("decision_id must be DecisionId")
    if not isinstance(correlation_id, CorrelationId):
        raise ResearchLineageValidationError("correlation_id must be CorrelationId")
    if not isinstance(side, TraderSignalSide):
        raise ResearchLineageValidationError("side must be TraderSignalSide")
    reason_code = _validate_public_code(reason_code, field_name="reason code")
    summary = _validate_public_code(summary, field_name="summary")

    evidence_attributes: dict[str, str] = {}
    for key, value in evidence.items():
        if not isinstance(key, str) or not key:
            raise ResearchLineageValidationError("evidence keys must be non-empty str")
        if not isinstance(value, str):
            raise ResearchLineageValidationError("evidence values must be str")
        evidence_attributes[key] = value

    outcome = (
        DecisionOutcome.APPROVED
        if side in {TraderSignalSide.BUY, TraderSignalSide.SELL}
        else DecisionOutcome.BLOCKED
    )
    return FunctionalDecision(
        decision_id=decision_id,
        timestamp=timestamp,
        decision_type=_SIGNAL_DECISION_TYPE,
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(
            correlation_id=correlation_id,
            attributes=MappingProxyType({_SIDE_ATTRIBUTE: side.value}),
        ),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode(reason_code),
                summary=summary,
                attributes=MappingProxyType(evidence_attributes),
            ),
        ),
        outcome=outcome,
    )


def extract_trader_signal_side(decision: FunctionalDecision) -> TraderSignalSide | None:
    """Extract the explicit side carried by a trader signal decision, if any."""
    if not isinstance(decision, FunctionalDecision):
        raise ResearchLineageValidationError("decision must be FunctionalDecision")
    if decision.decision_type.value != _SIGNAL_DECISION_TYPE.value:
        return None
    side = decision.metadata.attributes.get(_SIDE_ATTRIBUTE)
    if isinstance(side, str):
        try:
            return TraderSignalSide(side)
        except ValueError:
            return None
    return None


@dataclass(frozen=True, slots=True)
class TraderSignalStateContent:
    """Bounded deterministic rolling-window state for OHLC signal producers.

    ``bars`` is a bounded tuple of ``(close, high, low)`` floats in canonical
    arrival order. ``last_closed_at`` retains the exact close boundary of the
    most recent appended bar for chronology fail-closed checks. It must be
    timezone-aware when present.
    """

    config_fingerprint: str
    bars: tuple[tuple[float, float, float], ...]
    last_closed_at: datetime | None

    def __post_init__(self) -> None:
        if not isinstance(self.config_fingerprint, str) or not self.config_fingerprint:
            raise ResearchLineageValidationError(
                "config_fingerprint must be a non-empty str"
            )
        if not isinstance(self.bars, tuple):
            raise ResearchLineageValidationError("bars must be a tuple")
        for bar in self.bars:
            if not isinstance(bar, tuple) or len(bar) != 3:
                raise ResearchLineageValidationError(
                    "every bar must be a 3-tuple of (close, high, low)"
                )
            for value in bar:
                if type(value) is not float:
                    raise ResearchLineageValidationError(
                        "bar prices must be float; bool rejected"
                    )
        if self.last_closed_at is not None and (
            not isinstance(self.last_closed_at, datetime)
            or self.last_closed_at.tzinfo is None
            or self.last_closed_at.utcoffset() is None
        ):
            raise ResearchLineageValidationError(
                "last_closed_at must be a timezone-aware datetime or None"
            )

    def logical_values(self) -> Mapping[str, object]:
        return {
            "config_fingerprint": self.config_fingerprint,
            "bars": self.bars,
            "last_closed_at": self.last_closed_at,
        }


def canonical_decimal_string(value: Decimal) -> str:
    """Canonical exact Decimal projection (never float)."""
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResearchLineageValidationError("Decimal value must be finite")
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


def market_decimal(value: float) -> Decimal:
    """Convert a canonical market float to exact Decimal at the boundary."""
    if type(value) is not float:
        raise ResearchLineageValidationError("market value must be float; bool rejected")
    return Decimal(str(value))


def validate_lookback(value: int, *, field_name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or type(value) is not int or value < minimum:
        raise ResearchLineageValidationError(
            f"{field_name} must be an int >= {minimum}; bool rejected"
        )
    return value


def validate_positive_decimal(value: Decimal, *, field_name: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ResearchLineageValidationError(
            f"{field_name} must be a finite positive Decimal"
        )
    return value


def compute_trader_config_fingerprint(
    *,
    schema: str,
    fields: Mapping[str, str],
) -> str:
    """Deterministic SHA-256 fingerprint over exact canonical config strings."""
    if not isinstance(schema, str) or not schema:
        raise ResearchLineageValidationError("schema must be a non-empty str")
    if not isinstance(fields, Mapping):
        raise ResearchLineageValidationError("fields must be a Mapping")
    ordered_fields: dict[str, str] = {}
    for key, value in fields.items():
        if not isinstance(key, str) or not key:
            raise ResearchLineageValidationError(
                "config field keys must be non-empty str"
            )
        if not isinstance(value, str):
            raise ResearchLineageValidationError("config field values must be str")
        ordered_fields[key] = value
    canonical: dict[str, object] = {
        "schema": "qore.trader.configuration.v1",
        "config_schema": schema,
        "fields": dict(sorted(ordered_fields.items())),
    }
    return _sha256(_cjson(canonical))
