"""Mechanical source-valid Daily Candle-2 bias route for Capitalizer V48.

This is one documented TTrades Daily-bias path, not the complete universe of valid bias
methods. It is intentionally suitable for lower-bound Asia/London research:

Daily Candle-2 sweeps the previous Daily extreme and closes back inside
-> direction-aligned lower-timeframe CISD confirms the swing
-> the Daily bias becomes known at the Daily close.

The lower-timeframe CISD may occur before the Daily close, but the bias is not exposed until
the Daily closure is known, so no future information is available at decision time.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    detect_candle2_reversal_closure,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_forex_daily_profile_v48 import (
    V48ForexDailyProfile,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48StructuralCISDObservation,
    V48TimedSourceBar,
    observe_first_structural_cisd,
)

IDENTITY = "QORE_CAPITALIZER_V48_TTRADES_DAILY_C2_BIAS"


class V48DailyC2BiasState(StrEnum):
    CONFIRMED = "CONFIRMED"
    WAIT = "WAIT"


@dataclass(frozen=True, slots=True)
class V48DailyC2BiasObservation:
    identity: str
    state: V48DailyC2BiasState
    direction: CapitalizerSourceDirection | None
    daily_opened_at_iso: str
    known_at_iso: str
    lower_timeframe_cisd: V48StructuralCISDObservation | None
    source_route: str = "DAILY_C2_SWEEP_CLOSE_PLUS_LTF_CISD"
    complete_daily_bias_universe_claimed: bool = False
    outcome_used: bool = False
    entry_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("Daily C2 bias identity is frozen")
        confirmed = self.state is V48DailyC2BiasState.CONFIRMED
        if confirmed != (
            self.direction is not None
            and self.lower_timeframe_cisd is not None
            and self.lower_timeframe_cisd.source_valid
        ):
            raise ValueError("Daily C2 bias state/payload mismatch")
        if self.complete_daily_bias_universe_claimed:
            raise ValueError("C2 route cannot claim all valid TTrades Daily-bias methods")
        if self.outcome_used or self.entry_authority or self.capital_authority:
            raise ValueError("Daily bias observation is pre-economic context only")


def _source(profile: V48ForexDailyProfile) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=profile.open,
        high=profile.high,
        low=profile.low,
        close=profile.close,
    )


def observe_daily_c2_bias(
    previous: V48ForexDailyProfile,
    current: V48ForexDailyProfile,
    *,
    lower_timeframe_bars: tuple[V48TimedSourceBar, ...],
) -> V48DailyC2BiasObservation:
    """Confirm the source-valid Daily C2 + lower-timeframe CISD bias route."""

    if previous.symbol != current.symbol:
        raise ValueError("Daily C2 profiles must use one symbol")
    if previous.profile_closed_at > current.profile_opened_at:
        raise ValueError("Daily C2 profiles overlap")

    closure = detect_candle2_reversal_closure(
        previous=_source(previous),
        candle2=_source(current),
        point_of_interest_present=True,
    )
    if closure is None:
        return V48DailyC2BiasObservation(
            identity=IDENTITY,
            state=V48DailyC2BiasState.WAIT,
            direction=None,
            daily_opened_at_iso=current.profile_opened_at.isoformat(),
            known_at_iso=current.profile_closed_at.isoformat(),
            lower_timeframe_cisd=None,
        )

    relevant = tuple(
        bar
        for bar in lower_timeframe_bars
        if current.profile_opened_at <= bar.opened_at
        and bar.closed_at <= current.profile_closed_at
    )
    if closure.direction is CapitalizerSourceDirection.BULLISH:
        sweep = next(
            (bar for bar in relevant if bar.source.low < previous.low),
            None,
        )
    else:
        sweep = next(
            (bar for bar in relevant if bar.source.high > previous.high),
            None,
        )

    if sweep is None:
        return V48DailyC2BiasObservation(
            identity=IDENTITY,
            state=V48DailyC2BiasState.WAIT,
            direction=None,
            daily_opened_at_iso=current.profile_opened_at.isoformat(),
            known_at_iso=current.profile_closed_at.isoformat(),
            lower_timeframe_cisd=None,
        )

    cisd = observe_first_structural_cisd(
        relevant,
        direction=closure.direction,
        after=sweep.opened_at,
        before=current.profile_closed_at,
        higher_timeframe_closure_confirmed=True,
    )
    if not cisd.source_valid:
        return V48DailyC2BiasObservation(
            identity=IDENTITY,
            state=V48DailyC2BiasState.WAIT,
            direction=None,
            daily_opened_at_iso=current.profile_opened_at.isoformat(),
            known_at_iso=current.profile_closed_at.isoformat(),
            lower_timeframe_cisd=None,
        )

    return V48DailyC2BiasObservation(
        identity=IDENTITY,
        state=V48DailyC2BiasState.CONFIRMED,
        direction=closure.direction,
        daily_opened_at_iso=current.profile_opened_at.isoformat(),
        known_at_iso=current.profile_closed_at.isoformat(),
        lower_timeframe_cisd=cisd,
    )
