"""Timeframe-agnostic FVG-retrace + CISD continuation observer for Capitalizer V48.

This is the same source semantics used by the M1 continuation route, expressed over
V48TimedSourceBar so it can be reused on 15-minute Asia/London structures.

directional FVG forms
-> price retraces into that FVG
-> direction-aligned CISD confirms the continuation swing.

No exact entry, stop, target, outcome, sizing or capital decision is made here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOIKind,
    bar_interacts_with_poi,
    detect_fair_value_gap,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48StructuralCISDObservation,
    V48TimedSourceBar,
    observe_first_structural_cisd,
)

IDENTITY = "QORE_CAPITALIZER_V48_TIMED_FVG_CISD_CONTINUATION"


@dataclass(frozen=True, slots=True)
class V48TimedFVGContinuationObservation:
    identity: str
    direction: CapitalizerSourceDirection
    thesis_at: datetime
    deadline_at: datetime
    fvg_confirmed_at: datetime | None
    fvg_interaction_at: datetime | None
    cisd: V48StructuralCISDObservation | None
    confirmed: bool
    outcome_used: bool = False
    exact_entry_selected: bool = False
    target_selected: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("timed continuation identity is frozen")
        payload_complete = (
            self.fvg_confirmed_at is not None
            and self.fvg_interaction_at is not None
            and self.cisd is not None
            and self.cisd.source_valid
        )
        if self.confirmed != payload_complete:
            raise ValueError("timed continuation state/payload mismatch")
        if self.outcome_used or self.exact_entry_selected or self.target_selected:
            raise ValueError("timed continuation must remain pre-economic")
        if self.capital_authority:
            raise ValueError("timed continuation grants no capital authority")


def observe_first_timed_fvg_cisd_continuation(
    bars: tuple[V48TimedSourceBar, ...],
    *,
    thesis_at: datetime,
    deadline_at: datetime,
    direction: CapitalizerSourceDirection,
) -> V48TimedFVGContinuationObservation:
    """Find the first causal FVG-retrace+CISD continuation after the thesis."""

    if deadline_at <= thesis_at:
        raise ValueError("continuation deadline must follow thesis")
    ordered = tuple(sorted(bars, key=lambda item: item.opened_at))
    if ordered != bars:
        raise ValueError("timed continuation bars must be chronological")

    expected_kind = (
        CapitalizerSourcePOIKind.BULLISH_FVG
        if direction is CapitalizerSourceDirection.BULLISH
        else CapitalizerSourcePOIKind.BEARISH_FVG
    )

    for third_index in range(2, len(bars)):
        third = bars[third_index]
        if third.closed_at <= thesis_at:
            continue
        if third.closed_at > deadline_at:
            break
        poi = detect_fair_value_gap(
            candle1=bars[third_index - 2].source,
            candle2=bars[third_index - 1].source,
            candle3=third.source,
        )
        if poi is None or poi.kind is not expected_kind:
            continue

        for interaction_index in range(third_index + 1, len(bars)):
            interaction = bars[interaction_index]
            if interaction.closed_at > deadline_at:
                break
            if not bar_interacts_with_poi(bar=interaction.source, poi=poi):
                continue

            context_left = max(0, interaction_index - 3)
            cisd = observe_first_structural_cisd(
                bars[context_left:],
                direction=direction,
                after=interaction.opened_at,
                before=deadline_at,
                higher_timeframe_closure_confirmed=True,
            )
            if not cisd.source_valid:
                continue
            return V48TimedFVGContinuationObservation(
                identity=IDENTITY,
                direction=direction,
                thesis_at=thesis_at,
                deadline_at=deadline_at,
                fvg_confirmed_at=third.closed_at,
                fvg_interaction_at=interaction.closed_at,
                cisd=cisd,
                confirmed=True,
            )

    return V48TimedFVGContinuationObservation(
        identity=IDENTITY,
        direction=direction,
        thesis_at=thesis_at,
        deadline_at=deadline_at,
        fvg_confirmed_at=None,
        fvg_interaction_at=None,
        cisd=None,
        confirmed=False,
    )
