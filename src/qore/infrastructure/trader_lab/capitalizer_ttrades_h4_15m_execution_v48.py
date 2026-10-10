"""Source-native H4 -> 15M execution layer for Capitalizer V48.

This primitive assumes a higher-timeframe/Daily bias has already been confirmed and known.
It then implements the shared TTrades H4/15M sequence used by Asia and London:

aligned H4 Candle-2 closure
-> next H4 candle begins
-> 15M CISD confirms the intra-candle protected swing.

Asia can use that 15M confirmation as its minimum source-required lower-timeframe execution
confirmation. London adds a continuation layer afterward in its route-specific orchestration.

No outcome, exact entry, target selection, sizing or capital authority exists here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    detect_candle2_reversal_closure,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_forex_h4_profile_v48 import (
    V48ForexH4Profile,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48StructuralCISDObservation,
    V48TimedSourceBar,
    observe_first_structural_cisd,
)

IDENTITY = "QORE_CAPITALIZER_V48_TTRADES_H4_15M_EXECUTION"


@dataclass(frozen=True, slots=True)
class V48H415MExecutionObservation:
    identity: str
    direction: CapitalizerSourceDirection
    bias_known_at: datetime
    h4_c2_confirmed_at: datetime | None
    h4_profile_opened_at: datetime | None
    next_h4_profile_closed_at: datetime | None
    m15_cisd: V48StructuralCISDObservation | None
    confirmed: bool
    outcome_used: bool = False
    exact_entry_selected: bool = False
    target_selected: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("H4/15M execution identity is frozen")
        payload_complete = (
            self.h4_c2_confirmed_at is not None
            and self.h4_profile_opened_at is not None
            and self.next_h4_profile_closed_at is not None
            and self.m15_cisd is not None
            and self.m15_cisd.source_valid
        )
        if self.confirmed != payload_complete:
            raise ValueError("H4/15M execution state/payload mismatch")
        if self.outcome_used or self.exact_entry_selected or self.target_selected:
            raise ValueError("H4/15M execution must remain pre-economic")
        if self.capital_authority:
            raise ValueError("H4/15M execution grants no capital authority")


def _source(profile: V48ForexH4Profile) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=profile.open,
        high=profile.high,
        low=profile.low,
        close=profile.close,
    )


def observe_first_h4_15m_execution(
    h4_profiles: tuple[V48ForexH4Profile, ...],
    m15_bars: tuple[V48TimedSourceBar, ...],
    *,
    direction: CapitalizerSourceDirection,
    bias_known_at: datetime,
    deadline_at: datetime,
) -> V48H415MExecutionObservation:
    """Find first aligned H4 C2 followed by 15M protected-swing CISD."""

    if deadline_at <= bias_known_at:
        raise ValueError("H4/15M deadline must follow bias time")
    ordered_h4 = tuple(sorted(h4_profiles, key=lambda item: item.profile_opened_at))
    if ordered_h4 != h4_profiles:
        raise ValueError("H4 profiles must be chronological")
    ordered_m15 = tuple(sorted(m15_bars, key=lambda item: item.opened_at))
    if ordered_m15 != m15_bars:
        raise ValueError("M15 bars must be chronological")

    for index in range(1, len(h4_profiles) - 1):
        previous = h4_profiles[index - 1]
        current = h4_profiles[index]
        following = h4_profiles[index + 1]
        if current.profile_opened_at < bias_known_at:
            continue
        if current.profile_closed_at > deadline_at:
            break

        closure = detect_candle2_reversal_closure(
            previous=_source(previous),
            candle2=_source(current),
            point_of_interest_present=True,
        )
        if closure is None or closure.direction is not direction:
            continue

        window_end = min(following.profile_closed_at, deadline_at)
        context_start = current.profile_closed_at
        relevant = tuple(
            bar
            for bar in m15_bars
            if bar.closed_at > context_start and bar.closed_at <= window_end
        )
        if len(relevant) < 4:
            continue

        cisd = observe_first_structural_cisd(
            relevant,
            direction=direction,
            after=context_start,
            before=window_end,
            higher_timeframe_closure_confirmed=True,
        )
        if not cisd.source_valid:
            continue

        return V48H415MExecutionObservation(
            identity=IDENTITY,
            direction=direction,
            bias_known_at=bias_known_at,
            h4_c2_confirmed_at=current.profile_closed_at,
            h4_profile_opened_at=current.profile_opened_at,
            next_h4_profile_closed_at=window_end,
            m15_cisd=cisd,
            confirmed=True,
        )

    return V48H415MExecutionObservation(
        identity=IDENTITY,
        direction=direction,
        bias_known_at=bias_known_at,
        h4_c2_confirmed_at=None,
        h4_profile_opened_at=None,
        next_h4_profile_closed_at=None,
        m15_cisd=None,
        confirmed=False,
    )
