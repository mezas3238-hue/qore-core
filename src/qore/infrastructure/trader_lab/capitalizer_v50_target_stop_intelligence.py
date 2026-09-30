"""V50 causal target-ladder and dual-invalidation intelligence.

V49 collapsed the economic destination into one H1 witness and used the M15 protected swing as
the economic stop. V50 separates two questions that cognition must answer before entry:

1. Where can price plausibly travel?
   -> keep every causally confirmed, still-untouched H1 pivot ahead of entry as a target ladder.

2. What exactly invalidates the execution versus the thesis?
   -> execution invalidation = latest causally confirmed M1 pivot on the risk side;
   -> thesis invalidation = frozen M15 protected swing from the V49 setup.

Neither layer chooses a profitable target after the fact. No future bar, MFE/MAE, terminal
outcome or P&L is visible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
)

TARGET_IDENTITY = "QORE_CAPITALIZER_V50_H1_TARGET_LADDER"
STOP_IDENTITY = "QORE_CAPITALIZER_V50_DUAL_INVALIDATION"


@dataclass(frozen=True, slots=True)
class V50H1TargetCandidate:
    candidate_id: str
    price: Decimal
    pivot_confirmed_at: datetime
    distance_price: Decimal
    room_r_vs_thesis_stop: Decimal
    rank: int

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("V50 target candidate requires identity")
        if self.price <= 0 or self.distance_price <= 0 or self.room_r_vs_thesis_stop <= 0:
            raise ValueError("V50 target candidate geometry must be positive")
        if self.rank < 1:
            raise ValueError("V50 target rank must be >=1")
        if self.pivot_confirmed_at.tzinfo is None:
            raise ValueError("V50 target confirmation must be timezone-aware")


@dataclass(frozen=True, slots=True)
class V50H1TargetLadder:
    identity: str
    side: CapitalizerSide
    decision_at: datetime
    entry_price: Decimal
    thesis_stop_price: Decimal
    candidates: tuple[V50H1TargetCandidate, ...]
    post_decision_outcome_used: bool = False
    exact_target_selected: bool = False

    def __post_init__(self) -> None:
        if self.identity != TARGET_IDENTITY:
            raise ValueError("unexpected V50 target ladder identity")
        if self.decision_at.tzinfo is None:
            raise ValueError("V50 target decision time must be timezone-aware")
        if self.post_decision_outcome_used or self.exact_target_selected:
            raise ValueError("V50 target ladder is causal availability only")
        risk = abs(self.entry_price - self.thesis_stop_price)
        if risk <= 0:
            raise ValueError("V50 target ladder requires positive thesis risk")
        if tuple(item.rank for item in self.candidates) != tuple(
            range(1, len(self.candidates) + 1)
        ):
            raise ValueError("V50 target ladder ranks must be contiguous")

    @property
    def nearest_room_r(self) -> Decimal | None:
        return None if not self.candidates else self.candidates[0].room_r_vs_thesis_stop

    @property
    def farthest_room_r(self) -> Decimal | None:
        return None if not self.candidates else self.candidates[-1].room_r_vs_thesis_stop

    @property
    def has_one_r_destination(self) -> bool:
        return any(item.room_r_vs_thesis_stop >= Decimal("1") for item in self.candidates)

    @property
    def has_two_r_destination(self) -> bool:
        return any(item.room_r_vs_thesis_stop >= Decimal("2") for item in self.candidates)


@dataclass(frozen=True, slots=True)
class V50DualInvalidation:
    identity: str
    side: CapitalizerSide
    decision_at: datetime
    entry_price: Decimal
    thesis_stop_price: Decimal
    execution_stop_price: Decimal | None
    thesis_risk_price: Decimal
    execution_risk_price: Decimal | None
    execution_vs_thesis_ratio: Decimal | None
    execution_anchor_confirmed_at: datetime | None
    execution_anchor_available: bool
    post_decision_outcome_used: bool = False
    stop_widening_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != STOP_IDENTITY:
            raise ValueError("unexpected V50 dual invalidation identity")
        if self.decision_at.tzinfo is None:
            raise ValueError("V50 stop decision time must be timezone-aware")
        if self.thesis_risk_price <= 0:
            raise ValueError("V50 thesis risk must be positive")
        payload = (
            self.execution_stop_price is not None
            and self.execution_risk_price is not None
            and self.execution_vs_thesis_ratio is not None
            and self.execution_anchor_confirmed_at is not None
        )
        if self.execution_anchor_available != payload:
            raise ValueError("V50 execution invalidation payload mismatch")
        if self.post_decision_outcome_used:
            raise ValueError("V50 stop intelligence cannot see future outcomes")
        if self.stop_widening_authorized:
            raise ValueError("V50 cognition cannot authorize post-entry widening")


def _confirmed_h1_pivots(
    h1: tuple[V48AggregatedBar, ...],
    *,
    side: CapitalizerSide,
    decision_at: datetime,
) -> tuple[tuple[str, Decimal, datetime], ...]:
    result: list[tuple[str, Decimal, datetime]] = []
    for index in range(1, len(h1) - 1):
        left, center, right = h1[index - 1], h1[index], h1[index + 1]
        if right.closed_at > decision_at:
            break
        if side is CapitalizerSide.LONG:
            is_pivot = (
                center.source.high > left.source.high
                and center.source.high > right.source.high
            )
            price = center.source.high
            kind = "H1_PIVOT_HIGH"
        else:
            is_pivot = center.source.low < left.source.low and center.source.low < right.source.low
            price = center.source.low
            kind = "H1_PIVOT_LOW"
        if is_pivot:
            result.append((kind, price, right.closed_at))
    return tuple(result)


def build_h1_target_ladder(
    h1: tuple[V48AggregatedBar, ...],
    m1: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    decision_at: datetime,
    entry_price: Decimal,
    thesis_stop_price: Decimal,
    max_candidates: int = 5,
) -> V50H1TargetLadder:
    """Build an outcome-blind ordered ladder of untouched confirmed H1 pivots."""

    risk = abs(entry_price - thesis_stop_price)
    if risk <= 0:
        raise ValueError("V50 target ladder requires positive thesis risk")
    if max_candidates < 1:
        raise ValueError("max_candidates must be >=1")

    eligible: list[tuple[Decimal, str, Decimal, datetime]] = []
    for kind, price, confirmed_at in _confirmed_h1_pivots(
        h1,
        side=side,
        decision_at=decision_at,
    ):
        ahead = price > entry_price if side is CapitalizerSide.LONG else price < entry_price
        if not ahead:
            continue
        touched = any(
            (
                bar.high >= price
                if side is CapitalizerSide.LONG
                else bar.low <= price
            )
            for bar in m1
            if confirmed_at < bar.closed_at <= decision_at
        )
        if touched:
            continue
        distance = abs(price - entry_price)
        eligible.append((distance, kind, price, confirmed_at))

    eligible.sort(key=lambda item: (item[0], item[3], item[2]))
    candidates = tuple(
        V50H1TargetCandidate(
            candidate_id=f"{kind}:{confirmed_at.isoformat()}:{price}",
            price=price,
            pivot_confirmed_at=confirmed_at,
            distance_price=distance,
            room_r_vs_thesis_stop=distance / risk,
            rank=rank,
        )
        for rank, (distance, kind, price, confirmed_at) in enumerate(
            eligible[:max_candidates],
            start=1,
        )
    )
    return V50H1TargetLadder(
        identity=TARGET_IDENTITY,
        side=side,
        decision_at=decision_at,
        entry_price=entry_price,
        thesis_stop_price=thesis_stop_price,
        candidates=candidates,
    )


def build_dual_invalidation(
    m1: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    setup_confirmed_at: datetime,
    decision_at: datetime,
    entry_price: Decimal,
    thesis_stop_price: Decimal,
) -> V50DualInvalidation:
    """Bind latest confirmed M1 pivot as execution invalidation, separately from M15 thesis."""

    thesis_risk = abs(entry_price - thesis_stop_price)
    if thesis_risk <= 0:
        raise ValueError("V50 dual invalidation requires positive thesis risk")

    eligible: list[tuple[datetime, Decimal]] = []
    window = tuple(
        bar
        for bar in m1
        if bar.opened_at >= setup_confirmed_at and bar.closed_at <= decision_at
    )
    for index in range(1, len(window) - 1):
        left, center, right = window[index - 1], window[index], window[index + 1]
        if right.closed_at > decision_at:
            break
        if side is CapitalizerSide.LONG:
            pivot = center.low < left.low and center.low < right.low
            price = center.low
            valid_side = price < entry_price
        else:
            pivot = center.high > left.high and center.high > right.high
            price = center.high
            valid_side = price > entry_price
        inside_thesis = abs(entry_price - price) < thesis_risk
        if not (pivot and valid_side and inside_thesis):
            continue

        # Execution invalidation must remain strictly inside the M15 thesis boundary.
        # A deeper/equal pivot would allow the trade to survive beyond thesis invalidation.
        # The selected M1 level must also still exist at decision time.
        # If price has already touched/breached the pivot after its causal
        # right-hand confirmation, that level has been consumed and cannot
        # serve as a fresh stop anchor for a new entry.
        later = window[index + 2 :]
        intact = (
            all(item.low > price for item in later)
            if side is CapitalizerSide.LONG
            else all(item.high < price for item in later)
        )
        if intact:
            eligible.append((right.closed_at, price))

    if not eligible:
        return V50DualInvalidation(
            identity=STOP_IDENTITY,
            side=side,
            decision_at=decision_at,
            entry_price=entry_price,
            thesis_stop_price=thesis_stop_price,
            execution_stop_price=None,
            thesis_risk_price=thesis_risk,
            execution_risk_price=None,
            execution_vs_thesis_ratio=None,
            execution_anchor_confirmed_at=None,
            execution_anchor_available=False,
        )

    confirmed_at, execution_stop = eligible[-1]
    execution_risk = abs(entry_price - execution_stop)
    if execution_risk <= 0:
        raise ValueError("V50 execution stop must define positive risk")
    return V50DualInvalidation(
        identity=STOP_IDENTITY,
        side=side,
        decision_at=decision_at,
        entry_price=entry_price,
        thesis_stop_price=thesis_stop_price,
        execution_stop_price=execution_stop,
        thesis_risk_price=thesis_risk,
        execution_risk_price=execution_risk,
        execution_vs_thesis_ratio=execution_risk / thesis_risk,
        execution_anchor_confirmed_at=confirmed_at,
        execution_anchor_available=True,
    )
