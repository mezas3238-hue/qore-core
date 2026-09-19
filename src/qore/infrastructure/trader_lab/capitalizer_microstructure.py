"""Causal microstructure trace for the QORE Capitalizer.

The trace preserves *how* the market reached the current state without encoding economic
promotion rules. All events must be observable no later than the decision timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CapitalizerMicroEventKind(StrEnum):
    BALANCE_DETECTED = "BALANCE_DETECTED"
    COMPRESSION_DETECTED = "COMPRESSION_DETECTED"
    BREAK_ATTEMPT = "BREAK_ATTEMPT"
    LIQUIDITY_TAKEN = "LIQUIDITY_TAKEN"
    REJECTION_CONFIRMED = "REJECTION_CONFIRMED"
    ACCEPTANCE_CONFIRMED = "ACCEPTANCE_CONFIRMED"
    DISPLACEMENT_CONFIRMED = "DISPLACEMENT_CONFIRMED"
    PULLBACK_DETECTED = "PULLBACK_DETECTED"
    CONTINUATION_CONFIRMED = "CONTINUATION_CONFIRMED"
    REVERSAL_CONFIRMED = "REVERSAL_CONFIRMED"
    EXHAUSTION_DETECTED = "EXHAUSTION_DETECTED"


@dataclass(frozen=True, slots=True)
class CapitalizerMicroEvent:
    event_id: str
    kind: CapitalizerMicroEventKind
    observed_at: datetime
    value_token: str

    def __post_init__(self) -> None:
        if not self.event_id or not self.value_token:
            raise ValueError("microstructure event identity/value must be non-empty")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("microstructure event timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CapitalizerMicrostructureTrace:
    """Ordered, immutable decision-time event trace."""

    decision_at: datetime
    events: tuple[CapitalizerMicroEvent, ...]

    def __post_init__(self) -> None:
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise ValueError("decision_at must be timezone-aware")
        ids: set[str] = set()
        previous: datetime | None = None
        for event in self.events:
            if event.event_id in ids:
                raise ValueError("microstructure event ids must be unique")
            ids.add(event.event_id)
            if event.observed_at > self.decision_at:
                raise ValueError("future microstructure event cannot enter the trace")
            if previous is not None and event.observed_at < previous:
                raise ValueError("microstructure trace must be chronological")
            previous = event.observed_at

    @property
    def path(self) -> tuple[CapitalizerMicroEventKind, ...]:
        return tuple(event.kind for event in self.events)
