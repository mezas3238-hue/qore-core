"""V48 session-window differential audit.

Current V2 source-session code hard-vetoes observations outside ICT killzones. V48
separates an ICT route's time context from TTrades route validity so one author's
window cannot silently veto another author's source-supported setup.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_SESSION_WINDOW_DIFFERENTIAL"


class V48SessionWindowStatus(StrEnum):
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    CROSS_SOURCE_OVERCONSTRAINT = "CROSS_SOURCE_OVERCONSTRAINT"
    CROSS_SOURCE_UNRESOLVED = "CROSS_SOURCE_UNRESOLVED"


@dataclass(frozen=True, slots=True)
class V48SessionWindowFinding:
    finding_id: str
    session: str
    current_qore_behavior: str
    source_evidence: str
    source_url: str
    status: V48SessionWindowStatus
    route_specific_resolution_required: bool = True

    def __post_init__(self) -> None:
        if not self.finding_id or self.finding_id != self.finding_id.upper():
            raise ValueError("finding_id must be non-empty uppercase")
        if not self.source_url.startswith("https://"):
            raise ValueError("session-window finding requires source URL")
        if not self.route_specific_resolution_required:
            raise ValueError("V48 session clocks must be resolved per source route")


FINDINGS: tuple[V48SessionWindowFinding, ...] = (
    V48SessionWindowFinding(
        "NEW_YORK_ICT_0700_0900_GLOBAL_VETO",
        "NEW_YORK",
        (
            "capitalizer_source_session_context_v2 marks NEW_YORK eligible only in the "
            "half-open 07:00-09:00 New York window and OUTSIDE otherwise."
        ),
        (
            "TTrades New York Manipulation explicitly watches liquidity sweeps around "
            "08:30 or 09:30 and notes 09:30 or 10:00 as potential expansion times."
        ),
        "https://ttrades.com/daily-profile-understanding-the-new-york-manipulation/",
        V48SessionWindowStatus.SOURCE_CONFLICT,
    ),
    V48SessionWindowFinding(
        "LONDON_ICT_0200_0500_GLOBAL_VETO",
        "LONDON",
        (
            "capitalizer_source_session_context_v2 marks LONDON eligible only in the "
            "half-open 02:00-05:00 New York ICT killzone."
        ),
        (
            "TTrades London states the exact killzone is not extremely important; the setup "
            "and higher-timeframe wick/structure matter more, and reversals can form in Asia "
            "or the beginning portions of London."
        ),
        "https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/",
        V48SessionWindowStatus.CROSS_SOURCE_OVERCONSTRAINT,
    ),
    V48SessionWindowFinding(
        "ASIA_ICT_TWO_HOUR_WINDOW_GLOBAL_VETO",
        "ASIA",
        (
            "capitalizer_source_session_context_v2 requires the historical Asian Open and "
            "accepts only the following two hours."
        ),
        (
            "The TTrades Asia route is defined from HTF expansion conditions and two execution "
            "choices; V48 has not established that the ICT two-hour window is mandatory for "
            "every TTrades Asia route."
        ),
        "https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/",
        V48SessionWindowStatus.CROSS_SOURCE_UNRESOLVED,
    ),
)


@dataclass(frozen=True, slots=True)
class V48SessionWindowDifferential:
    identity: str = IDENTITY
    findings: tuple[V48SessionWindowFinding, ...] = FINDINGS
    one_author_window_may_globally_veto_other_author_routes: bool = False
    route_specific_time_context_required: bool = True
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 session-window differential identity is frozen")
        if self.one_author_window_may_globally_veto_other_author_routes:
            raise ValueError("cross-author session window veto is forbidden")
        if not self.route_specific_time_context_required:
            raise ValueError("V48 requires route-specific session time semantics")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("session-window differential is pre-economic")


V48_SESSION_WINDOW_DIFFERENTIAL = V48SessionWindowDifferential()
