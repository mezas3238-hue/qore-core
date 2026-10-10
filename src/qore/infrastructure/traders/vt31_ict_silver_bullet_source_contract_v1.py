"""Source-conformant ICT 2023 Silver Bullet *pre-admission* audit.

Primary video: https://www.youtube.com/watch?v=tRq1hyGGtl4
The clock, first FVG inside the entry zone, causal draw on liquidity and
>=10 *projected index points* framework come from the primary lesson.

This is a strict, fail-closed RESEARCH contract, not an executable trading
authority. It deliberately makes no universal mandatory "09-10 range raid",
mandatory breaker/OB, ATR filter or fixed-risk RR claim for the ICT lesson.
Those may be TTrades/owner operational variants and must be labeled as such.

Inputs MUST be observable as-of and independently produced. A caller cannot
pass a terminal outcome, future candle, trade PnL or date/fold result here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
ICT_PRIMARY_2023 = "youtube:tRq1hyGGtl4"
MIN_PROJECTED_FRAMEWORK_INDEX_POINTS = Decimal("10")
HOURS = {"VT31_LONDON": 3, "VT31_NY_AM": 10, "VT31_NY_PM": 14}
SUPPORTED_DOL = frozenset({
    "PREVIOUS_DAY_HIGH", "PREVIOUS_DAY_LOW",
    "PREVIOUS_SESSION_HIGH", "PREVIOUS_SESSION_LOW",
    "PREVIOUS_WEEK_HIGH", "PREVIOUS_WEEK_LOW",
    "NEW_WEEK_OPENING_GAP", "PREEXISTING_INEFFICIENCY",
    "DOCUMENTED_STRUCTURAL_LIQUIDITY",
})


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class ClosedCandle:
    opened_at: datetime
    closed_at: datetime
    high: Decimal
    low: Decimal

    def __post_init__(self) -> None:
        _time(self.opened_at)
        _time(self.closed_at)
        if _time(self.closed_at) - _time(self.opened_at) != timedelta(minutes=1):
            raise ValueError("exact closed M1 candle required")
        if not self.high.is_finite() or not self.low.is_finite():
            raise ValueError("finite price required")
        if self.high <= 0 or self.low <= 0 or self.high < self.low:
            raise ValueError("invalid M1 high/low")


@dataclass(frozen=True, slots=True)
class LiquidityDraw:
    family: str
    target_price: Decimal
    observed_at: datetime
    producer: str

    def __post_init__(self) -> None:
        _time(self.observed_at)
        if not self.target_price.is_finite() or self.target_price <= 0:
            raise ValueError("invalid target")
        if not self.producer:
            raise ValueError("draw requires a producer")


@dataclass(frozen=True, slots=True)
class SourceContractAudit:
    model_id: str
    action: str
    barriers: tuple[str, ...]
    fvg_formed_at: str
    fvg_lower: str | None
    fvg_upper: str | None
    projected_framework_points: str | None
    source_video: str = ICT_PRIMARY_2023
    actionable_trade_authority: bool = False
    certified: bool = False
    uses_terminal_outcome: bool = False
    uses_sizing: bool = False


def _time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return value.astimezone(UTC)


def assess_ict_silver_bullet_source(
    *,
    session_model_id: str,
    side: Side,
    first: ClosedCandle,
    middle: ClosedCandle,
    third: ClosedCandle,
    as_of: datetime,
    prospective_fill_open: datetime,
    prospective_entry_price: Decimal,
    structural_stop_price: Decimal | None,
    structural_stop_observed_at: datetime | None,
    current_price: Decimal,
    current_price_observed_at: datetime,
    draw: LiquidityDraw | None,
    earliest_fvg_in_entry_zone_verified: bool,
) -> SourceContractAudit:
    """Fail-closed source proof. A qualifying source is NEVER a routing order.

    Three consecutive closed M1 candles define a raw classic FVG. Formation
    is the third candle closing inside the relevant NY-local one-hour window.
    The trade's *projected delivery framework* compares current causally
    observable price to DOL; it is NOT the FVG width nor guaranteed PnL.
    """
    if session_model_id not in HOURS:
        raise ValueError("unknown original ICT source session")
    if not isinstance(side, Side):
        raise TypeError("side must be explicit")
    at = _time(as_of)
    fill = _time(prospective_fill_open)
    closed = _time(third.closed_at)
    a, b, c = _time(first.opened_at), _time(middle.opened_at), _time(third.opened_at)
    if (b - a != timedelta(minutes=1)
            or c - b != timedelta(minutes=1)):
        raise ValueError("non-contiguous M1 FVG candles")
    barriers: list[str] = []
    ny_formed = closed.astimezone(NY)
    if not (ny_formed.hour == HOURS[session_model_id]
            or (ny_formed.hour == HOURS[session_model_id] + 1
                and ny_formed.minute == 0 and ny_formed.second == 0)):
        barriers.append("FVG_FORMATION_OUTSIDE_ORIGINAL_NY_HOUR")
    # At 04:00:00, the 03:59-04:00 M1 bar closes and is still valid.
    if c.astimezone(NY).hour != HOURS[session_model_id]:
        barriers.append("FVG_THIRD_CANDLE_NOT_IN_SOURCE_WINDOW")
    # Conservative OPERATIONAL FORMALIZATION, not an unambiguous literal
    # condition confirmed by the 2023 primary 19-minute lecture: all
    # three contributing closed candles start inside the source hour.
    first_ny = _time(first.opened_at).astimezone(NY)
    if first_ny.date() != ny_formed.date() or first_ny.hour != HOURS[session_model_id]:
        barriers.append("FVG_FIRST_CANDLE_BEFORE_SOURCE_WINDOW_RESEARCH_POLICY")
    if closed > at or _time(middle.closed_at) > at:
        barriers.append("UNCLOSED_FUTURE_FVG_DATA")
    # At an M1 close instant the prospective next M1 open could coincide;
    # without tick/sequence evidence a same-timestamp fill must NOT be
    # inferred as a valid broker execution. Fail closed on ambiguity.
    if fill <= at:
        barriers.append("SAME_TIMESTAMP_OR_EARLY_FILL_NOT_PROVEN")
    if fill < at or fill.astimezone(NY).date() != ny_formed.date():
        barriers.append("FILL_BEFORE_ASOF_OR_ON_OTHER_SOURCE_DAY")
    if not (fill.astimezone(NY).hour == HOURS[session_model_id]):
        barriers.append("FILL_OUTSIDE_SOURCE_HOUR")
    if not earliest_fvg_in_entry_zone_verified:
        barriers.append("FIRST_FVG_IN_ENTRY_ZONE_NOT_VERIFIED")

    lower: Decimal | None = None
    upper: Decimal | None = None
    if side is Side.LONG and third.low > first.high:
        lower, upper = first.high, third.low
    if side is Side.SHORT and third.high < first.low:
        lower, upper = third.high, first.low
    if lower is None or upper is None:
        barriers.append("NO_DIRECTIONAL_CLASSIC_3_CANDLE_FVG")
    elif not (lower <= prospective_entry_price <= upper):
        barriers.append("PROSPECTIVE_ENTRY_NOT_INSIDE_FVG")

    price = prospective_entry_price
    if not price.is_finite() or price <= 0:
        barriers.append("INVALID_ENTRY_PRICE")
    if not current_price.is_finite() or current_price <= 0:
        barriers.append("INVALID_CURRENT_MARKET_PRICE")
    if _time(current_price_observed_at) > at:
        barriers.append("MARKET_PRICE_OBSERVED_AFTER_DECISION")

    if structural_stop_price is None or structural_stop_observed_at is None:
        barriers.append("STRUCTURAL_STOP_UNPROVEN")
    elif (
        not structural_stop_price.is_finite()
        or structural_stop_price <= 0
        or _time(structural_stop_observed_at) > at
    ):
        barriers.append("STRUCTURAL_STOP_UNCAUSAL_OR_INVALID")
    elif (
        (side is Side.LONG and not structural_stop_price < price)
        or (side is Side.SHORT and not structural_stop_price > price)
    ):
        barriers.append("STRUCTURAL_STOP_WRONG_SIDE")

    distance: Decimal | None = None
    if draw is None:
        barriers.append("NEXT_DRAW_ON_LIQUIDITY_UNPROVEN")
    else:
        if draw.family not in SUPPORTED_DOL:
            barriers.append("DRAW_SOURCE_FAMILY_NOT_DOCUMENTED")
        if _time(draw.observed_at) > at:
            barriers.append("DRAW_OBSERVED_AFTER_DECISION")
        distance = (
            draw.target_price - current_price
            if side is Side.LONG else current_price - draw.target_price
        )
        if distance <= 0:
            barriers.append("DRAW_IS_OPPOSITE_THESIS_OR_ALREADY_PASSED")
        elif distance < MIN_PROJECTED_FRAMEWORK_INDEX_POINTS:
            barriers.append("PROJECTED_10_INDEX_POINT_FRAMEWORK_MISSING")
        if (
            (side is Side.LONG and draw.target_price <= price)
            or (side is Side.SHORT and draw.target_price >= price)
        ):
            barriers.append("DRAW_NOT_BEYOND_ENTRY")

    return SourceContractAudit(
        model_id=session_model_id,
        action="SOURCE_CONTRACT_ELIGIBLE_RESEARCH_ONLY" if not barriers
        else "BLOCK_SOURCE_INCOMPLETE",
        barriers=tuple(sorted(set(barriers))),
        fvg_formed_at=closed.isoformat(),
        fvg_lower=None if lower is None else format(lower, "f"),
        fvg_upper=None if upper is None else format(upper, "f"),
        projected_framework_points=(
            None if distance is None else format(distance, "f")
        ),
    )


def self_test() -> None:
    # US DST summer: source NY AM forms 10:00-11:00 = 14:00-15:00 UTC.
    base = datetime(2025, 5, 6, 14, tzinfo=UTC)
    first = ClosedCandle(base, base + timedelta(minutes=1),
                         Decimal("110"), Decimal("100"))
    middle = ClosedCandle(base + timedelta(minutes=1),
                          base + timedelta(minutes=2),
                          Decimal("108"), Decimal("99"))
    third = ClosedCandle(base + timedelta(minutes=2),
                         base + timedelta(minutes=3),
                         Decimal("97"), Decimal("94"))
    asof = third.closed_at
    kwargs = dict(
        session_model_id="VT31_NY_AM", side=Side.SHORT,
        first=first, middle=middle, third=third,
        as_of=asof,
        prospective_fill_open=asof + timedelta(minutes=1),
        prospective_entry_price=Decimal("98"),
        structural_stop_price=Decimal("112"),
        structural_stop_observed_at=asof,
        current_price=Decimal("98"),
        current_price_observed_at=asof,
        draw=LiquidityDraw("PREVIOUS_DAY_LOW", Decimal("85"), asof,
                           "prior-day-closed-M1"),
        earliest_fvg_in_entry_zone_verified=True,
    )
    x = assess_ict_silver_bullet_source(**kwargs)
    assert x.action == "SOURCE_CONTRACT_ELIGIBLE_RESEARCH_ONLY"
    assert x.projected_framework_points == "13"
    assert not x.actionable_trade_authority
    from dataclasses import replace
    no_dol = assess_ict_silver_bullet_source(**(kwargs | {"draw": None}))
    assert "NEXT_DRAW_ON_LIQUIDITY_UNPROVEN" in no_dol.barriers
    bad_range = assess_ict_silver_bullet_source(**(
        kwargs | {
            "draw": replace(kwargs["draw"], target_price=Decimal("92")),
        }
    ))
    assert "PROJECTED_10_INDEX_POINT_FRAMEWORK_MISSING" in bad_range.barriers
    future = assess_ict_silver_bullet_source(**(
        kwargs | {"as_of": asof - timedelta(minutes=1)}
    ))
    assert "UNCLOSED_FUTURE_FVG_DATA" in future.barriers
    wrong = assess_ict_silver_bullet_source(**(
        kwargs | {"session_model_id": "VT31_LONDON"}
    ))
    assert "FVG_THIRD_CANDLE_NOT_IN_SOURCE_WINDOW" in wrong.barriers
    assert assess_ict_silver_bullet_source(**(
        kwargs | {"earliest_fvg_in_entry_zone_verified": False}
    )).action == "BLOCK_SOURCE_INCOMPLETE"
    # 09:59 first candle + 10:00 middle + 10:01 third: FVG closes
    # during ICT NY AM, but strict QORE full-three-inside policy vetoes.
    crossing = (
        ClosedCandle(base - timedelta(minutes=1), base,
                     Decimal("110"), Decimal("100")),
        ClosedCandle(base, base + timedelta(minutes=1),
                     Decimal("108"), Decimal("99")),
        ClosedCandle(base + timedelta(minutes=1), base + timedelta(minutes=2),
                     Decimal("97"), Decimal("94")),
    )
    cross = assess_ict_silver_bullet_source(**(
        kwargs | dict(zip(("first", "middle", "third"), crossing))
    ))
    assert "FVG_FIRST_CANDLE_BEFORE_SOURCE_WINDOW_RESEARCH_POLICY" in cross.barriers
    same_timestamp = assess_ict_silver_bullet_source(**(
        kwargs | {"prospective_fill_open": asof}
    ))
    assert "SAME_TIMESTAMP_OR_EARLY_FILL_NOT_PROVEN" in same_timestamp.barriers


if __name__ == "__main__":
    self_test()
    print("ICT primary source FVG/DOL/10-point/causality contract: PASS")
