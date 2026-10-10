"""Read-only event-sourced ICT Silver Bullet methodology research machine.

Primary lecture: https://www.youtube.com/watch?v=tRq1hyGGtl4

The machine *cannot* choose a DOL or MSS. It accepts versioned, independent
causal evidence from a cognitive producer and reconstructs an illustrative
first suitable FVG / consequent-encroachment (50%) pending-order lifecycle.
The source lecture does NOT uniquely mandate midpoint-only entry, exact
MSS threshold, or full three-candle formation boundary; these are tagged
QORE_RESEARCH_FORMALIZATION for controlled scientific comparison.

NO trading, lot sizing, order placement, broker fills or economic metrics.
M1 wick touch is ONLY a labelled observation, never an executed trade.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, time
from decimal import Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

_NY = ZoneInfo("America/New_York")
_SESSION_HOURS = {"VT31_LONDON": 3, "VT31_NY_AM": 10, "VT31_NY_PM": 14}
_ALLOWED_DOL = frozenset({
    "PREVIOUS_DAY_HIGH", "PREVIOUS_DAY_LOW",
    "PREVIOUS_SESSION_HIGH", "PREVIOUS_SESSION_LOW",
    "PREVIOUS_WEEK_HIGH", "PREVIOUS_WEEK_LOW",
    "NEW_WEEK_OPENING_GAP", "PREEXISTING_INEFFICIENCY",
    "DOCUMENTED_STRUCTURAL_LIQUIDITY",
})
_MIN_FRAMEWORK = Decimal("10")


def _utc(t: datetime) -> datetime:
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("timestamps require explicit timezone")
    return t.astimezone(UTC)


def _money(v: Decimal) -> Decimal:
    if not isinstance(v, Decimal) or not v.is_finite() or v <= 0:
        raise ValueError("finite positive Decimal NAS100 index price required")
    return v


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class Phase(StrEnum):
    WAITING_FOR_EVIDENCE = "WAITING_FOR_EVIDENCE"
    WAITING_FOR_FIRST_SUITABLE_FVG = "WAITING_FOR_FIRST_SUITABLE_FVG"
    PENDING_RESEARCH = "PENDING_RESEARCH"
    RESEARCH_MIDPOINT_TOUCH_NOT_FILL = "RESEARCH_MIDPOINT_TOUCH_NOT_FILL"
    AMBIGUOUS_TOUCH_AND_INVALIDATION = "AMBIGUOUS_TOUCH_AND_INVALIDATION"
    SOURCE_INVALIDATED = "SOURCE_INVALIDATED"
    WINDOW_EXPIRED = "WINDOW_EXPIRED"


@dataclass(frozen=True, slots=True)
class M1:
    opened_at: datetime
    closed_at: datetime
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        if _utc(self.closed_at) - _utc(self.opened_at) != timedelta(minutes=1):
            raise ValueError("one closed M1 candle required")
        if not _utc(self.opened_at).second == 0:
            raise ValueError("minute-aligned M1 opened_at required")
        if not (_money(self.low) <= _money(self.close) <= _money(self.high)):
            raise ValueError("OHLC high-low disagreement")


@dataclass(frozen=True, slots=True)
class CausalDOL:
    side: Side
    target: Decimal
    family: str
    observed_at: datetime
    producer: str

    def __post_init__(self) -> None:
        _utc(self.observed_at)
        _money(self.target)
        if not isinstance(self.side, Side) or self.family not in _ALLOWED_DOL:
            raise ValueError("explicit side and recognized liquidity family required")
        if not self.producer.strip():
            raise ValueError("cognitive DOL producer provenance required")


@dataclass(frozen=True, slots=True)
class CausalMSS:
    side: Side
    level: Decimal
    level_confirmed_at: datetime
    break_confirmed_at: datetime
    producer: str

    def __post_init__(self) -> None:
        if _utc(self.level_confirmed_at) > _utc(self.break_confirmed_at):
            raise ValueError("MSS pivot must preexist its structural break")
        _money(self.level)
        if not isinstance(self.side, Side) or not self.producer.strip():
            raise ValueError("canonical causal structure producer required")


@dataclass(frozen=True, slots=True)
class FirstSuitableFVG:
    side: Side
    first_bar_opened_at: datetime
    formed_at: datetime
    lower: Decimal
    upper: Decimal
    ce: Decimal
    projected_framework_points: Decimal
    draw_family: str
    draw_target: Decimal
    mss_break_confirmed_at: datetime
    dol_observed_at: datetime
    stop_candidate: Decimal

    def __post_init__(self) -> None:
        if not _money(self.lower) < _money(self.ce) < _money(self.upper):
            raise ValueError("invalid gap midpoint")
        if self.projected_framework_points < _MIN_FRAMEWORK:
            raise ValueError("insufficient original source framework")


class SilverBulletCausalResearch:
    """1 session, 1 NY-local date, immutable pre-window evidence, no fills.

    DOL and MSS are supplied as-of by independent producers. This prevents
    choosing bias by eventual outcome. A selected first *suitable* FVG
    freezes after admission; no retroactively selecting later prettier gaps.
    """

    def __init__(self, model: str, local_ny_date: datetime,
                 *, require_full_three_bar_inside_window: bool = True) -> None:
        if model not in _SESSION_HOURS:
            raise ValueError("unknown ICT source window")
        stamp = _utc(local_ny_date).astimezone(_NY)
        hour = _SESSION_HOURS[model]
        self.model = model
        self.day = stamp.date()
        self.start = datetime.combine(self.day, time(hour), _NY).astimezone(UTC)
        self.end = datetime.combine(self.day, time(hour+1), _NY).astimezone(UTC)
        self.require_full_three_bar_inside_window = require_full_three_bar_inside_window
        self.dol: CausalDOL | None = None
        self.mss: CausalMSS | None = None
        self.phase = Phase.WAITING_FOR_EVIDENCE
        self.first: FirstSuitableFVG | None = None
        self.last_close: datetime | None = None
        self._bars: list[M1] = []
        self._seen_fvg: int = 0
        self.touch_observed_at: datetime | None = None
        self.invalidated_at: datetime | None = None

    def present_cognitive_evidence(
        self, *, as_of: datetime, dol: CausalDOL, mss: CausalMSS,
    ) -> None:
        when = _utc(as_of)
        if not self.start <= when < self.end:
            raise ValueError("cognition evidence outside source creation hour")
        if _utc(dol.observed_at) > when or _utc(mss.break_confirmed_at) > when:
            raise ValueError("future cognitive evidence rejected")
        if dol.side != mss.side:
            raise ValueError("MSS contradicts authoritative DOL side")
        if self.first is not None:
            raise ValueError("cannot rewrite selected first FVG from future evidence")
        self.dol, self.mss = dol, mss
        self.phase = Phase.WAITING_FOR_FIRST_SUITABLE_FVG

    def on_closed_m1(self, bar: M1) -> None:
        when = _utc(bar.closed_at)
        opened = _utc(bar.opened_at)
        if self.last_close is not None and opened != self.last_close:
            raise ValueError("missing/duplicate/reordered M1 closed candle")
        if opened < self.start or opened >= self.end:
            raise ValueError("M1 observation outside exact ICT source window")
        self.last_close = when

        # A selected hypothesis receives only ex-post observational events;
        # never make an actual broker-fill claim from bar high/low.
        if self.first is not None:
            if self.phase == Phase.PENDING_RESEARCH:
                touch = bar.low <= self.first.ce <= bar.high
                invalid = (
                    bar.close < self.first.lower
                    if self.first.side == Side.LONG
                    else bar.close > self.first.upper
                )
                if touch and invalid:
                    self.phase = Phase.AMBIGUOUS_TOUCH_AND_INVALIDATION
                    self.invalidated_at = when
                elif invalid:
                    self.phase = Phase.SOURCE_INVALIDATED
                    self.invalidated_at = when
                elif touch:
                    self.phase = Phase.RESEARCH_MIDPOINT_TOUCH_NOT_FILL
                    self.touch_observed_at = when
            if when >= self.end and self.phase == Phase.PENDING_RESEARCH:
                self.phase = Phase.WINDOW_EXPIRED
            return

        self._bars.append(bar)
        if len(self._bars) > 3:
            self._bars.pop(0)
        if len(self._bars) < 3:
            return
        a, b, c = self._bars
        if _utc(a.closed_at) != _utc(b.opened_at) or _utc(b.closed_at) != opened:
            raise AssertionError("M1 source causal sequence broken")

        # Third candle CLOSING at 04/11/15 NY cannot admit a pending entry
        # because there is zero original source window remaining to enter.
        if when >= self.end or self.dol is None or self.mss is None:
            return
        if _utc(self.dol.observed_at) > when or _utc(self.mss.break_confirmed_at) > when:
            raise AssertionError("future COG data reached causal state")
        if self.require_full_three_bar_inside_window and _utc(a.opened_at) < self.start:
            raise ValueError("FVG first bar outside strict research window")
        if _utc(self.mss.break_confirmed_at) > when:
            return
        # Strict conservative research formalization: break must already be
        # confirmed before the third FVG candle closes; synchronous proof
        # still needs actual independent producer causal chronology.
        side = self.dol.side
        bullish = c.low > a.high
        bearish = c.high < a.low
        if (side == Side.LONG and not bullish) or (side == Side.SHORT and not bearish):
            return
        self._seen_fvg += 1
        low, high = ((a.high, c.low) if side == Side.LONG
                     else (c.high, a.low))
        ce = (low + high) / Decimal(2)
        room = (self.dol.target - c.close if side == Side.LONG
                else c.close - self.dol.target)
        # A gross "raw first FVG" is not automatically the first suitable
        # gap in documented entry prices, even in original ICT PM lesson.
        if room < _MIN_FRAMEWORK:
            return
        if (side == Side.LONG and not self.dol.target > ce) or (
            side == Side.SHORT and not self.dol.target < ce
        ):
            return
        if side == Side.LONG and c.close <= self.mss.level:
            return
        if side == Side.SHORT and c.close >= self.mss.level:
            return
        # Stop below/above candle 1 is a tracked RESEARCH OPTION, not
        # a universal primary-video order-routing prescription.
        stop = a.low if side == Side.LONG else a.high
        if not (stop < ce if side == Side.LONG else stop > ce):
            return
        self.first = FirstSuitableFVG(
            side=side, first_bar_opened_at=_utc(a.opened_at),
            formed_at=when, lower=low, upper=high, ce=ce,
            projected_framework_points=room,
            draw_family=self.dol.family, draw_target=self.dol.target,
            mss_break_confirmed_at=_utc(self.mss.break_confirmed_at),
            dol_observed_at=_utc(self.dol.observed_at),
            stop_candidate=stop,
        )
        self.phase = Phase.PENDING_RESEARCH

    def snapshot(self) -> dict[str, object]:
        f = self.first
        return {
            "schema": "qore.vt31.ict_silver_bullet_causal_fsm_research.v1",
            "model": self.model,
            "ny_day": self.day.isoformat(),
            "phase": self.phase.value,
            "observed_at": None if self.last_close is None else self.last_close.isoformat(),
            "fvg_seen_with_cognition": self._seen_fvg,
            "first_suitable_fvg": None if f is None else {
                "side": f.side.value,
                "first_bar_opened_at": f.first_bar_opened_at.isoformat(),
                "formed_at": f.formed_at.isoformat(),
                "lower": str(f.lower), "upper": str(f.upper),
                "ce": str(f.ce),
                "stop_candidate_research_only": str(f.stop_candidate),
                "draw_family": f.draw_family,
                "draw_target": str(f.draw_target),
                "dol_observed_at": f.dol_observed_at.isoformat(),
                "mss_break_confirmed_at": f.mss_break_confirmed_at.isoformat(),
                "projected_index_points": str(f.projected_framework_points),
            },
            "research_midpoint_touch_at": (
                None if self.touch_observed_at is None
                else self.touch_observed_at.isoformat()
            ),
            "invalidated_at": (
                None if self.invalidated_at is None
                else self.invalidated_at.isoformat()
            ),
            "source_classification": "QORE_RESEARCH_FORMALIZATION",
            "primary_ict_quote_verified_for_every_operational_detail": False,
            "has_broker_fill": False,
            "has_execution_authority": False,
            "has_canonical_cognition_route": False,
            "is_certified": False,
        }


def self_test() -> None:
    # 03-04 NY = 07-08 UTC in July. No hard London local time.
    start = datetime(2025, 7, 7, 7, tzinfo=UTC)
    def candle(i: int, high: str, low: str, close: str) -> M1:
        opened = start + timedelta(minutes=i)
        return M1(opened, opened+timedelta(minutes=1),
                  Decimal(high), Decimal(low), Decimal(close))
    fsm = SilverBulletCausalResearch("VT31_LONDON", start)
    d = CausalDOL(Side.SHORT, Decimal("80"), "PREVIOUS_DAY_LOW",
                  start, "COG_TEST_PRIOR_DAY")
    m = CausalMSS(Side.SHORT, Decimal("105"), start,
                  start+timedelta(minutes=2), "COG_TEST_CAUSAL_SWING")
    fsm.present_cognitive_evidence(
        as_of=start+timedelta(minutes=2), dol=d, mss=m
    )
    fsm.on_closed_m1(candle(0, "110", "106", "108"))
    fsm.on_closed_m1(candle(1, "109", "105", "106"))
    fsm.on_closed_m1(candle(2, "103", "100", "102"))
    assert fsm.phase == Phase.PENDING_RESEARCH
    x = fsm.snapshot()
    assert x["first_suitable_fvg"]["lower"] == "103"
    assert x["first_suitable_fvg"]["upper"] == "106"
    assert x["first_suitable_fvg"]["ce"] == "104.5"
    assert x["first_suitable_fvg"]["projected_index_points"] == "22"
    assert not x["has_broker_fill"]
    # Post-confirmation, future candles cannot rewrite the first FVG.
    fsm.on_closed_m1(candle(3, "106", "103", "104"))
    assert fsm.phase == Phase.RESEARCH_MIDPOINT_TOUCH_NOT_FILL
    assert fsm.snapshot()["first_suitable_fvg"] == x["first_suitable_fvg"]
    assert fsm.touch_observed_at == start+timedelta(minutes=4)
    try:
        fsm.on_closed_m1(candle(3, "106", "103", "104"))
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate candle accepted")
    try:
        fsm.present_cognitive_evidence(
            as_of=start+timedelta(minutes=4), dol=d, mss=m
        )
    except ValueError:
        pass
    else:
        raise AssertionError("retroactive cognitive DOL rewrite accepted")
    # Opposite DOL is rejected even when a raw gap is present.
    opposed = SilverBulletCausalResearch("VT31_LONDON", start)
    try:
        opposed.present_cognitive_evidence(
            as_of=start+timedelta(minutes=2),
            dol=CausalDOL(Side.LONG, Decimal("140"), "PREVIOUS_DAY_HIGH",
                          start, "TEST"), mss=m,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("contradictory draw/MSS accepted")
    # All three bars inside same source hour is explicit conservative
    # candidate formalization. No acceptance of 02:59->03:01 gap.
    early = SilverBulletCausalResearch("VT31_LONDON", start)
    try:
        early.on_closed_m1(candle(-1, "110", "106", "108"))
    except ValueError:
        pass
    else:
        raise AssertionError("prewindow candle passed")
    # No deterministic broker fill from ambiguous same M1 high-low.
    ambiguous = SilverBulletCausalResearch("VT31_LONDON", start)
    ambiguous.present_cognitive_evidence(
        as_of=start+timedelta(minutes=2), dol=d, mss=m
    )
    for i, vals in enumerate([
        ("110", "106", "108"), ("109", "105", "106"),
        ("103", "100", "102"), ("110", "101", "107")
    ]):
        ambiguous.on_closed_m1(candle(i, *vals))
    assert ambiguous.phase == Phase.AMBIGUOUS_TOUCH_AND_INVALIDATION
    assert not ambiguous.snapshot()["has_broker_fill"]
    # No invented mandatory 10:00-10:15 preparation / sweep timetable.
    assert "SWEEP" not in Phase.__members__
    assert all(not x["has_execution_authority"]
               for x in (fsm.snapshot(), ambiguous.snapshot()))


if __name__ == "__main__":
    self_test()
    print("ICT Silver Bullet research event FSM: causal tests PASS")
