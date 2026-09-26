"""Frozen consumed-evidence hypothesis for Capitalizer/CIBO departure alignment.

This contract freezes the structural statement discovered during consumed research before any
candidate construction or fresh-holdout work. It is not an entry rule, candidate, certificate,
or promotion authority.
"""

from __future__ import annotations

from dataclasses import dataclass

HYPOTHESIS_ID = "QORE_CAPITALIZER_HYPOTHESIS_CIBO_DEPARTURE_ALIGNMENT_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerDepartureAlignmentHypothesis:
    hypothesis_id: str
    capitalizer_event_family: tuple[str, ...]
    cibo_detector: str
    cibo_event: str
    cibo_source_timeframe: str
    direction_relation: str
    temporal_join: str
    diagnostic_horizon_minutes: int
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    lookback_tolerance_minutes: int = 0
    economic_candidate: bool = False
    rule_promotion_allowed: bool = False
    fresh_holdout_claimed: bool = False

    def __post_init__(self) -> None:
        if self.hypothesis_id != HYPOTHESIS_ID:
            raise ValueError("departure-alignment hypothesis identity is frozen")
        if self.capitalizer_event_family != (
            "HIGH_ACCEPTANCE",
            "HIGH_RAID_REJECTION",
            "LOW_ACCEPTANCE",
            "LOW_RAID_REJECTION",
        ):
            raise ValueError("Capitalizer event family is frozen")
        if self.cibo_detector != "CAUSAL_CISD_V1":
            raise ValueError("CIBO detector must remain CAUSAL_CISD_V1")
        if self.cibo_event != "DEPARTURE":
            raise ValueError("CIBO event must remain DEPARTURE")
        if self.cibo_source_timeframe != "H1":
            raise ValueError("source timeframe must remain H1")
        if self.direction_relation != "ALIGNED":
            raise ValueError("direction relation must remain ALIGNED")
        if self.temporal_join != "DEPARTURE_AT_EQUALS_M5_DECISION_AT":
            raise ValueError("temporal join semantics are frozen")
        if self.diagnostic_horizon_minutes != 15:
            raise ValueError("diagnostic horizon is frozen at 15 minutes")
        if self.evidence_status != "CONSUMED_RESEARCH_EVIDENCE":
            raise ValueError("hypothesis evidence must remain consumed")
        if self.lookback_tolerance_minutes != 0:
            raise ValueError("no temporal tolerance/lookback tuning is allowed")
        if self.economic_candidate or self.rule_promotion_allowed or self.fresh_holdout_claimed:
            raise ValueError("research hypothesis cannot claim candidate/promotion/freshness")


FROZEN_DEPARTURE_ALIGNMENT_HYPOTHESIS = CapitalizerDepartureAlignmentHypothesis(
    hypothesis_id=HYPOTHESIS_ID,
    capitalizer_event_family=(
        "HIGH_ACCEPTANCE",
        "HIGH_RAID_REJECTION",
        "LOW_ACCEPTANCE",
        "LOW_RAID_REJECTION",
    ),
    cibo_detector="CAUSAL_CISD_V1",
    cibo_event="DEPARTURE",
    cibo_source_timeframe="H1",
    direction_relation="ALIGNED",
    temporal_join="DEPARTURE_AT_EQUALS_M5_DECISION_AT",
    diagnostic_horizon_minutes=15,
)
