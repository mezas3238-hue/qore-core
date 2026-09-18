"""VT31_NAS100 working memory.

Ephemeral causal state for the market *now*.  It is rebuilt from information
known no later than the decision timestamp. It contains no historical outcome
labels and no CIBO/laboratory statistics.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Nas100WorkingMemory:
    decision_minute_ny: int
    last_structure_event_family: str
    last_structure_event_age_minutes: int | None
    reference_reclaim_age_minutes: int | None
    current_path_vs_previous: Decimal | None
    reference_width_vs_prior5: Decimal | None

    def __post_init__(self) -> None:
        if not 0 <= self.decision_minute_ny < 24 * 60:
            raise ValueError("decision_minute_ny out of range")
        if (
            self.last_structure_event_age_minutes is not None
            and self.last_structure_event_age_minutes < 0
        ):
            raise ValueError("structure-event age cannot be negative")
        if (
            self.reference_reclaim_age_minutes is not None
            and self.reference_reclaim_age_minutes < 0
        ):
            raise ValueError("reference-reclaim age cannot be negative")
        for value in (
            self.current_path_vs_previous,
            self.reference_width_vs_prior5,
        ):
            if value is not None and (not value.is_finite() or value < 0):
                raise ValueError("working-memory ratios must be finite >= 0")

    def payload(self) -> dict[str, object]:
        raw = asdict(self)
        return {
            "schema": "qore.vt31.nas100.working_memory.v1",
            "memory_class": "WORKING_CAUSAL_RUNTIME",
            "causal_timestamp_state_only": True,
            "historical_outcome_labels_present": False,
            **{
                key: (
                    format(value, "f")
                    if isinstance(value, Decimal)
                    else value
                )
                for key, value in raw.items()
            },
        }

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
