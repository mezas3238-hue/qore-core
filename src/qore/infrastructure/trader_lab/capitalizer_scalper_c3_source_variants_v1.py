"""Research-only, preregistered TTrades Candle 3 source interpretation probe.

The December-2025 and January-2026 articles use different descriptions.
Never pick the branch by winner labels, MFE, PF, or later performance.
This module cannot veto a V49 opportunity or authorize an execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    detect_candle3_confirmation,
)

DECEMBER_SOURCE = (
    "https://ttrades.com/candle-3-closure-a-complete-guide-to-"
    "identifying-continuations-and-reversals/"
)
JANUARY_SOURCE = (
    "https://ttrades.com/how-change-in-the-state-of-delivery-"
    "confirms-swing-points/"
)
IDENTITY = "QORE_SCALPER_A2_C3_SOURCE_VARIANTS_RESEARCH_V1"


class C3SourceVariant(StrEnum):
    DECEMBER_2025_NO_SWEEP_BODY_ENGULF = "DECEMBER_2025_NO_SWEEP_BODY_ENGULF"
    JANUARY_2026_CLOSE_BEYOND_C2_RANGE = "JANUARY_2026_CLOSE_BEYOND_C2_RANGE"


@dataclass(frozen=True, slots=True)
class C3AsOfInput:
    """Only closed H1 bars and independently witnessed as-of facts.

    A None witness means unavailable, not disproven. No strategy result,
    hindsight entry, upcoming H1-state expiry, or future R is accepted.
    """

    candle2: CapitalizerSourceBar
    candle3: CapitalizerSourceBar
    candle2_closed_at: datetime
    candle3_closed_at: datetime
    candle2_reversal_already_confirmed: bool
    poi_confirmed_at: datetime | None = None
    ltf_cisd_confirmed_at: datetime | None = None

    def __post_init__(self) -> None:
        if (
            self.candle2_closed_at.utcoffset() is None
            or self.candle3_closed_at.utcoffset() is None
            or self.candle2_closed_at >= self.candle3_closed_at
        ):
            raise ValueError("strict aware H1 closure sequence required")
        for name, t in (
            ("POI", self.poi_confirmed_at),
            ("LTF_CISD", self.ltf_cisd_confirmed_at),
        ):
            if t is not None and (
                t.utcoffset() is None or t > self.candle3_closed_at
            ):
                raise ValueError(f"{name} witness cannot come from the future")
        if (
            self.ltf_cisd_confirmed_at is not None
            and self.ltf_cisd_confirmed_at <= self.candle2_closed_at
        ):
            raise ValueError("LTF CISD must be witnessed inside H1 Candle 3")


@dataclass(frozen=True, slots=True)
class C3VariantWitness:
    variant: C3SourceVariant
    primary_url: str
    geometric_direction: str | None
    geometric_match: bool
    poi_attested: bool
    ltf_cisd_attested: bool
    chain_observed_as_of_c3_close: bool
    source_fidelity_certified: bool = False
    changes_v49_admission: bool = False
    authorizes_execution: bool = False

    def __post_init__(self) -> None:
        if (
            self.source_fidelity_certified
            or self.changes_v49_admission
            or self.authorizes_execution
        ):
            raise ValueError("C3 source-research branch has no trade authority")
        if self.chain_observed_as_of_c3_close and not (
            self.geometric_match and self.poi_attested and self.ltf_cisd_attested
        ):
            raise ValueError("contextual C3 chain needs all three witnesses")


def _january_direction(c2: CapitalizerSourceBar, c3: CapitalizerSourceBar) -> str | None:
    """Explicit *engineering interpretation* of 'beyond opening price and range'.

    Strict beyond C2 high/low. This interpretation requires source review;
    it must never silently replace the December production primitive.
    """

    if c3.close > c2.high and c3.close > c2.body_high:
        return "BULLISH"
    if c3.close < c2.low and c3.close < c2.body_low:
        return "BEARISH"
    return None


def compare_c3_primary_readings(context: C3AsOfInput) -> tuple[C3VariantWitness, ...]:
    """Side-by-side, outcome-blind C3 geometries; NOT full trading eligibility."""

    december = detect_candle3_confirmation(
        candle2=context.candle2,
        candle3=context.candle3,
        point_of_interest_present=context.poi_confirmed_at is not None,
        candle2_reversal_already_confirmed=context.candle2_reversal_already_confirmed,
    )
    dec_direction = december.direction.value if december is not None else None
    jan_direction = (
        None
        if context.candle2_reversal_already_confirmed
        else _january_direction(context.candle2, context.candle3)
    )
    poi = context.poi_confirmed_at is not None
    ltf = context.ltf_cisd_confirmed_at is not None
    results = (
        (C3SourceVariant.DECEMBER_2025_NO_SWEEP_BODY_ENGULF, DECEMBER_SOURCE, dec_direction),
        (C3SourceVariant.JANUARY_2026_CLOSE_BEYOND_C2_RANGE, JANUARY_SOURCE, jan_direction),
    )
    return tuple(
        C3VariantWitness(
            variant=variant,
            primary_url=url,
            geometric_direction=direction,
            geometric_match=direction is not None,
            poi_attested=poi,
            ltf_cisd_attested=ltf,
            chain_observed_as_of_c3_close=direction is not None and poi and ltf,
        )
        for variant, url, direction in results
    )
