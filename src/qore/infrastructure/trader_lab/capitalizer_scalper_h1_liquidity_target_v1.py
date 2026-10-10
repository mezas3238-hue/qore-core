"""Causal H1 liquidity target candidates for TTrades scalping research.

Author-level facts:
  - external liquidity = confirmed swing high/low;
  - previous HTF candle high/low may also be targets;
  - an H1 FVG is INTERNAL liquidity and is *not* automatically a trend target.
QORE choices:
  - prioritize still-untouched CONFIRMED H1 external swings;
  - fall back to the unchanged V49 recent H1 candle-extreme witness;
  - expose internal FVG candidates for an explicit reversal thesis only.
No Daily/H4 inputs, no fixed minimum RR, no outcome-guided rank or entry veto.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)

IDENTITY = "QORE_SCALPER_A2_H1_EXTERNAL_LIQUIDITY_FIRST_V1"
AUTHOR_TARGET_GUIDE = "https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/"
AUTHOR_LIQUIDITY_GUIDE = (
    "https://ttrades.com/internal-external-liquidity-using-the-ttrades-fractal-model/"
)


class TargetKind(StrEnum):
    EXTERNAL_CONFIRMED_H1_SWING = "EXTERNAL_CONFIRMED_H1_SWING"
    RECENT_H1_CANDLE_EXTREME = "RECENT_H1_CANDLE_EXTREME"
    INTERNAL_H1_FVG_BOUNDARY = "INTERNAL_H1_FVG_BOUNDARY"


@dataclass(frozen=True, slots=True)
class H1LiquidityTarget:
    kind: TargetKind
    price: Decimal
    confirmed_at: datetime
    target_r_vs_m15_stop: Decimal
    source_bar_opened_at: datetime
    untouched_asof: bool = True

    def __post_init__(self) -> None:
        if self.confirmed_at.utcoffset() is None or self.price <= 0:
            raise ValueError("H1 liquidity target requires causal timestamp/price")
        if self.target_r_vs_m15_stop <= 0 or not self.untouched_asof:
            raise ValueError("candidate target must be valid positive-R untouched level")


@dataclass(frozen=True, slots=True)
class H1LiquidityDecision:
    identity: str
    decision_at: datetime
    source_symbol: str
    source_target_price: Decimal
    selected: H1LiquidityTarget | None
    available_external_swings: tuple[H1LiquidityTarget, ...]
    available_internal_fvgs: tuple[H1LiquidityTarget, ...]
    prior_h1_candle_extreme: H1LiquidityTarget | None
    selected_policy: str
    source_witness_reconciled: bool
    looked_ahead: bool = False
    market_authority_granted: bool = False
    economics_used_for_ranking: bool = False
    cisd_used_as_target_filter: bool = False
    trader_certified: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("liquidity target identity mismatch")
        if any((
            self.looked_ahead, self.market_authority_granted,
            self.economics_used_for_ranking, self.cisd_used_as_target_filter,
            self.trader_certified, self.live_authorized,
        )):
            raise ValueError("target research must be causal, non-executing and non-certified")
        if not self.source_witness_reconciled:
            raise ValueError("original V49 H1 target witness reconciliation is mandatory")


def _aware(raw: str) -> datetime:
    t = datetime.fromisoformat(raw)
    if t.utcoffset() is None:
        raise ValueError("timestamp must be timezone aware")
    return t


def discover_h1_liquidity_targets(
    source: V49Opportunity,
    h1: tuple[V48AggregatedBar, ...],
    m1: tuple[CapitalizerM1Bar, ...],
) -> H1LiquidityDecision:
    """Describe H1 targets available as-of a closed-M1 entry, without trading.

    H1 pivots are confirmed ONLY after the right H1 bar has CLOSED; an H1
    three-candle FVG is confirmed only after the third H1 candle closes.
    M1 high/low after decision time, including the M1 opening at decision,
    never counts toward a prior target touch.
    """

    at = _aware(source.m1_trigger_confirmed_at)
    entry = Decimal(source.decision_reference_price)
    stop = Decimal(source.m15_protected_swing_price)
    original = Decimal(source.structural_target_witness_price)
    bullish = source.h1_state_direction == "BULLISH"
    if source.h1_state_direction not in ("BULLISH", "BEARISH"):
        raise ValueError("unexpected H1 direction")
    if not (stop < entry < original if bullish else original < entry < stop):
        raise ValueError("original source stop and target geometry inconsistent")
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("zero risk V49 original stop")

    if any(a.closed_at <= a.opened_at for a in h1):
        raise ValueError("malformed H1 aggregated bar")
    if any(h1[i].opened_at >= h1[i + 1].opened_at for i in range(len(h1) - 1)):
        raise ValueError("H1 bars must be strictly chronological")
    if any(m1[i].opened_at >= m1[i + 1].opened_at for i in range(len(m1) - 1)):
        raise ValueError("M1 bars must be strictly chronological")
    if any(item.symbol != source.symbol for item in m1):
        raise ValueError("M1 symbol mismatch with source")

    completed_h1 = tuple(b for b in h1 if b.closed_at <= at)
    completed_m1 = tuple(b for b in m1 if b.closed_at <= at)
    if len(completed_h1) < 3 or not completed_m1:
        raise ValueError("no complete H1/M1 source history")

    def ahead(price: Decimal) -> bool:
        return price > entry if bullish else price < entry

    def already_touched(price: Decimal, from_at: datetime) -> bool:
        return any(
            (bar.high >= price if bullish else bar.low <= price)
            for bar in completed_m1
            if from_at <= bar.opened_at
        )

    def candidate(
        kind: TargetKind,
        price: Decimal,
        confirmed: datetime,
        opened: datetime,
    ) -> H1LiquidityTarget | None:
        if not ahead(price) or already_touched(price, confirmed):
            return None
        return H1LiquidityTarget(
            kind=kind,
            price=price,
            confirmed_at=confirmed,
            source_bar_opened_at=opened,
            target_r_vs_m15_stop=abs(price - entry) / risk,
        )

    # First independently rebuild the unchanged V49 H1 witness:
    # newest untouched HIGH/LOW from up to 24 COMPLETED H1 bars.
    fallback: H1LiquidityTarget | None = None
    for bar in reversed(completed_h1[-24:]):
        price = bar.source.high if bullish else bar.source.low
        item = candidate(
            TargetKind.RECENT_H1_CANDLE_EXTREME, price,
            bar.closed_at, bar.opened_at,
        )
        if item is not None:
            fallback = item
            break
    if fallback is None or fallback.price != original:
        raise ValueError("independent RAW M1/H1 original V49 witness mismatch")

    external: list[H1LiquidityTarget] = []
    internal: list[H1LiquidityTarget] = []
    for i in range(1, len(completed_h1) - 1):
        left, center, right = (
            completed_h1[i - 1], completed_h1[i], completed_h1[i + 1]
        )
        if bullish:
            is_pivot = (
                center.source.high > left.source.high
                and center.source.high > right.source.high
            )
            pivot_price = center.source.high
        else:
            is_pivot = (
                center.source.low < left.source.low
                and center.source.low < right.source.low
            )
            pivot_price = center.source.low
        if is_pivot:
            target = candidate(
                TargetKind.EXTERNAL_CONFIRMED_H1_SWING,
                pivot_price, right.closed_at, center.opened_at,
            )
            if target is not None:
                external.append(target)

        # FVG = internal liquidity; opposing-side FVG may become a target only
        # with a separately verified reversal narrative, not automatically.
        first = left
        third = right
        if bullish and first.source.low > third.source.high:
            fvg_price = third.source.high
        elif (not bullish) and first.source.high < third.source.low:
            fvg_price = third.source.low
        else:
            continue
        fvg = candidate(
            TargetKind.INTERNAL_H1_FVG_BOUNDARY,
            fvg_price, third.closed_at, first.opened_at,
        )
        if fvg is not None:
            internal.append(fvg)

    # Within a class choose nearest directional distance; this is a declared
    # QORE rule, not an authored universal hierarchy and not a fixed-R gate.
    ranked_external = tuple(sorted(
        external, key=lambda c: (
            c.target_r_vs_m15_stop, c.confirmed_at, c.price,
        )
    ))
    ranked_internal = tuple(sorted(
        internal, key=lambda c: (
            c.target_r_vs_m15_stop, c.confirmed_at, c.price,
        )
    ))
    chosen = ranked_external[0] if ranked_external else fallback
    return H1LiquidityDecision(
        identity=IDENTITY,
        decision_at=at,
        source_symbol=source.symbol,
        source_target_price=original,
        selected=chosen,
        available_external_swings=ranked_external,
        available_internal_fvgs=ranked_internal,
        prior_h1_candle_extreme=fallback,
        selected_policy=(
            "EXTERNAL_CONFIRMED_H1_SWING_FIRST"
            if ranked_external else "SOURCE_WITNESS_FALLBACK"
        ),
        source_witness_reconciled=True,
    )
