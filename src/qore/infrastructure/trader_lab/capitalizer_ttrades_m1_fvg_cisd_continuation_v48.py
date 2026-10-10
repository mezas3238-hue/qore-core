"""M1 Fair-Value-Gap + CISD continuation observer for Capitalizer V48.

Reviewed TTrades continuation semantics permit:
confirmed higher-timeframe thesis
-> directional FVG forms
-> price retraces into that FVG
-> CISD confirms the local swing
-> continuation becomes source-valid.

The observer stops at confirmation. It does not choose an exact entry, stop, target,
position size, route priority or outcome.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOIKind,
    bar_interacts_with_poi,
    detect_fair_value_gap,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48TimedSourceBar,
    observe_first_structural_cisd,
)

IDENTITY = "QORE_CAPITALIZER_V48_M1_FVG_CISD_CONTINUATION"


@dataclass(frozen=True, slots=True)
class V48M1FVGContinuationObservation:
    identity: str
    direction: CapitalizerSourceDirection
    thesis_at: datetime
    deadline_at: datetime
    fvg_confirmed_at: datetime | None
    fvg_lower_price: str | None
    fvg_upper_price: str | None
    fvg_interaction_at: datetime | None
    cisd_confirmed_at: datetime | None
    confirmed: bool
    outcome_used: bool = False
    exact_entry_selected: bool = False
    target_selected: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("M1 FVG+CISD continuation identity is frozen")
        payload = (
            self.fvg_confirmed_at,
            self.fvg_lower_price,
            self.fvg_upper_price,
            self.fvg_interaction_at,
            self.cisd_confirmed_at,
        )
        if self.confirmed != all(value is not None for value in payload):
            raise ValueError("FVG+CISD continuation status/payload mismatch")
        if self.outcome_used or self.exact_entry_selected or self.target_selected:
            raise ValueError("FVG+CISD observation must remain pre-economic")
        if self.capital_authority:
            raise ValueError("FVG+CISD observation grants no capital authority")


def _source_bar(bar: CapitalizerM1Bar) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
    )


def _timed(bar: CapitalizerM1Bar) -> V48TimedSourceBar:
    return V48TimedSourceBar(
        opened_at=bar.opened_at,
        closed_at=bar.closed_at,
        source=_source_bar(bar),
    )


def observe_first_m1_fvg_cisd_continuation(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    thesis_at: datetime,
    deadline_at: datetime,
    direction: CapitalizerSourceDirection,
) -> V48M1FVGContinuationObservation:
    """Return first directional FVG retrace followed by source-valid CISD."""

    if thesis_at.tzinfo is None or thesis_at.utcoffset() is None:
        raise ValueError("continuation thesis_at must be timezone-aware")
    if deadline_at.tzinfo is None or deadline_at.utcoffset() is None:
        raise ValueError("continuation deadline_at must be timezone-aware")
    if deadline_at <= thesis_at:
        raise ValueError("continuation deadline must follow thesis")

    ordered = tuple(sorted(bars, key=lambda item: item.opened_at))
    if ordered != bars:
        raise ValueError("M1 continuation bars must be chronological")

    opened = tuple(item.opened_at for item in bars)
    first = max(2, bisect.bisect_left(opened, thesis_at))
    expected_kind = (
        CapitalizerSourcePOIKind.BULLISH_FVG
        if direction is CapitalizerSourceDirection.BULLISH
        else CapitalizerSourcePOIKind.BEARISH_FVG
    )

    for third_index in range(first, len(bars)):
        third = bars[third_index]
        if third.closed_at > deadline_at:
            break
        poi = detect_fair_value_gap(
            candle1=_source_bar(bars[third_index - 2]),
            candle2=_source_bar(bars[third_index - 1]),
            candle3=_source_bar(third),
        )
        if poi is None or poi.kind is not expected_kind:
            continue

        for interaction_index in range(third_index + 1, len(bars)):
            interaction = bars[interaction_index]
            if interaction.closed_at > deadline_at:
                break
            if not bar_interacts_with_poi(bar=_source_bar(interaction), poi=poi):
                continue

            context_left = max(0, interaction_index - 3)
            timed = tuple(_timed(item) for item in bars[context_left:])
            cisd = observe_first_structural_cisd(
                timed,
                direction=direction,
                after=interaction.opened_at,
                before=deadline_at,
                higher_timeframe_closure_confirmed=True,
            )
            if not cisd.source_valid or cisd.confirmed_at is None:
                continue

            return V48M1FVGContinuationObservation(
                identity=IDENTITY,
                direction=direction,
                thesis_at=thesis_at,
                deadline_at=deadline_at,
                fvg_confirmed_at=third.closed_at,
                fvg_lower_price=str(poi.lower_price),
                fvg_upper_price=str(poi.upper_price),
                fvg_interaction_at=interaction.closed_at,
                cisd_confirmed_at=cisd.confirmed_at,
                confirmed=True,
            )

    return V48M1FVGContinuationObservation(
        identity=IDENTITY,
        direction=direction,
        thesis_at=thesis_at,
        deadline_at=deadline_at,
        fvg_confirmed_at=None,
        fvg_lower_price=None,
        fvg_upper_price=None,
        fvg_interaction_at=None,
        cisd_confirmed_at=None,
        confirmed=False,
    )
