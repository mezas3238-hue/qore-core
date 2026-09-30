"""London-specific continuation layer for Capitalizer V48.

TTrades London source requires:
Daily bias
-> H4 wick/swing
-> 15M CISD confirms protected swing
-> from there, look for continuation aligned with Daily and H4 direction.

This module consumes an already-confirmed H4/15M structural observation and applies one
documented continuation family: 15M FVG retrace + CISD. It is deliberately a lower-bound
London execution route; other source-valid continuation families can be added independently.

No outcome, exact fill, target selection, sizing or capital authority is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_h4_15m_execution_v48 import (
    V48H415MExecutionObservation,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48TimedSourceBar,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_timed_fvg_cisd_continuation_v48 import (
    V48TimedFVGContinuationObservation,
    observe_first_timed_fvg_cisd_continuation,
)

IDENTITY = "QORE_CAPITALIZER_V48_TTRADES_LONDON_CONTINUATION"


@dataclass(frozen=True, slots=True)
class V48LondonContinuationObservation:
    identity: str
    direction: CapitalizerSourceDirection
    structural_execution: V48H415MExecutionObservation
    continuation: V48TimedFVGContinuationObservation | None
    confirmed: bool
    continuation_family: str = "M15_FVG_RETRACE_CISD"
    lower_bound_route: bool = True
    outcome_used: bool = False
    exact_entry_selected: bool = False
    target_selected: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("London continuation identity is frozen")
        expected = (
            self.structural_execution.confirmed
            and self.continuation is not None
            and self.continuation.confirmed
        )
        if self.confirmed != expected:
            raise ValueError("London continuation state/payload mismatch")
        if not self.lower_bound_route:
            raise ValueError("single continuation family cannot claim complete London coverage")
        if self.outcome_used or self.exact_entry_selected or self.target_selected:
            raise ValueError("London continuation must remain pre-economic")
        if self.capital_authority:
            raise ValueError("London continuation grants no capital authority")


def observe_london_continuation(
    structural_execution: V48H415MExecutionObservation,
    m15_bars: tuple[V48TimedSourceBar, ...],
    *,
    deadline_at: datetime,
) -> V48LondonContinuationObservation:
    """Require post-protected-swing continuation for the London route."""

    if not structural_execution.confirmed or structural_execution.m15_cisd is None:
        return V48LondonContinuationObservation(
            identity=IDENTITY,
            direction=structural_execution.direction,
            structural_execution=structural_execution,
            continuation=None,
            confirmed=False,
        )
    if structural_execution.m15_cisd.confirmed_at is None:
        raise ValueError("confirmed structural execution requires CISD confirmation time")

    continuation_deadline = deadline_at
    if structural_execution.next_h4_profile_closed_at is not None:
        continuation_deadline = min(
            continuation_deadline,
            structural_execution.next_h4_profile_closed_at,
        )
    if continuation_deadline <= structural_execution.m15_cisd.confirmed_at:
        return V48LondonContinuationObservation(
            identity=IDENTITY,
            direction=structural_execution.direction,
            structural_execution=structural_execution,
            continuation=None,
            confirmed=False,
        )

    continuation = observe_first_timed_fvg_cisd_continuation(
        m15_bars,
        thesis_at=structural_execution.m15_cisd.confirmed_at,
        deadline_at=continuation_deadline,
        direction=structural_execution.direction,
    )
    return V48LondonContinuationObservation(
        identity=IDENTITY,
        direction=structural_execution.direction,
        structural_execution=structural_execution,
        continuation=continuation if continuation.confirmed else None,
        confirmed=continuation.confirmed,
    )
