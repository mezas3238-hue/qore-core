"""Source-defined session context for QORE Capitalizer Strategy Closure V2.

Important boundary:
- QORE broad surveillance buckets are portfolio/research infrastructure.
- ICT source kill-zones are narrower methodology contexts.
They must never be silently treated as the same clock definition.

London and New York windows below are frozen from the reviewed ICT lessons.
Asian exact fixed-clock boundaries remain unresolved in this closure because the reviewed
material is event/open-relative and reconstructed clocks can vary with seasonal time handling.
Fail closed instead of inventing precision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession

NEW_YORK = ZoneInfo("America/New_York")


class CapitalizerSourceSessionResolution(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    OUTSIDE = "OUTSIDE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class CapitalizerSourceSessionAssessment:
    session: CapitalizerSession
    resolution: CapitalizerSourceSessionResolution
    source_window_id: str
    local_time: time
    reasons: tuple[str, ...]
    qore_surveillance_bucket_equated_to_source_window: bool = False

    def __post_init__(self) -> None:
        if self.qore_surveillance_bucket_equated_to_source_window:
            raise ValueError("QORE surveillance bucket cannot masquerade as ICT kill-zone")
        if not self.source_window_id or not self.reasons:
            raise ValueError("source session assessment requires id and reasons")

    @property
    def resolved(self) -> bool:
        return self.resolution is not CapitalizerSourceSessionResolution.REVIEW_REQUIRED

    @property
    def eligible(self) -> bool:
        return self.resolution is CapitalizerSourceSessionResolution.ELIGIBLE


def _in_half_open_window(value: time, start: time, end: time) -> bool:
    return start <= value < end


def assess_source_session_context(
    *,
    session: CapitalizerSession,
    observed_at: datetime,
) -> CapitalizerSourceSessionAssessment:
    """Classify only reviewed author-time context, DST-aware in New York local time."""

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("source session observation must be timezone-aware")
    local = observed_at.astimezone(NEW_YORK).timetz().replace(tzinfo=None)

    if session is CapitalizerSession.LONDON:
        eligible = _in_half_open_window(local, time(2, 0), time(5, 0))
        return CapitalizerSourceSessionAssessment(
            session=session,
            resolution=(
                CapitalizerSourceSessionResolution.ELIGIBLE
                if eligible
                else CapitalizerSourceSessionResolution.OUTSIDE
            ),
            source_window_id="ICT_LONDON_KILLZONE_0200_0500_NY",
            local_time=local,
            reasons=(
                "ICT_LONDON_KILLZONE_WINDOW"
                if eligible
                else "OUTSIDE_ICT_LONDON_KILLZONE_WINDOW",
            ),
        )

    if session is CapitalizerSession.NEW_YORK:
        eligible = _in_half_open_window(local, time(7, 0), time(9, 0))
        return CapitalizerSourceSessionAssessment(
            session=session,
            resolution=(
                CapitalizerSourceSessionResolution.ELIGIBLE
                if eligible
                else CapitalizerSourceSessionResolution.OUTSIDE
            ),
            source_window_id="ICT_NEW_YORK_KILLZONE_0700_0900_NY",
            local_time=local,
            reasons=(
                "ICT_NEW_YORK_KILLZONE_WINDOW"
                if eligible
                else "OUTSIDE_ICT_NEW_YORK_KILLZONE_WINDOW",
            ),
        )

    return CapitalizerSourceSessionAssessment(
        session=session,
        resolution=CapitalizerSourceSessionResolution.REVIEW_REQUIRED,
        source_window_id="ICT_ASIAN_KILLZONE_EXACT_CLOCK_REVIEW_REQUIRED",
        local_time=local,
        reasons=(
            "ASIAN_OPEN_CONTEXT_REVIEWED",
            "EXACT_FIXED_CLOCK_NOT_FROZEN",
            "FAIL_CLOSED_PENDING_SOURCE_CLOCK_RESOLUTION",
        ),
    )
