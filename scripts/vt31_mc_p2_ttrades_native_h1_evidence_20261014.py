#!/usr/bin/env python3
"""Read-only TTrades NY AM source-native H1 -> sweep -> return context.

The author's method is narrower than general ICT Silver Bullet. A closed
M1 confirming a return within the H1 is only a context witness; it is NOT a
certified author's displacement, MSS, FVG/OB/Breaker, broker fill or order.
COG producer, OPS, G3 and sizing remain unmodified.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    CognitiveDecision,
    M1Bar,
    SessionId,
    utc,
)
from scripts.vt31_cog_evidence_v2_20261014 import (
    TTRADES_AM,
    inspect_cog_evidence,
)


@dataclass(frozen=True, slots=True)
class NativeAmContext:
    profile: str
    as_of: datetime
    state: str
    reasons: tuple[str, ...]
    high_9am: Decimal | None = None
    low_9am: Decimal | None = None
    first_sweep_side: str | None = None
    first_sweep_at: datetime | None = None
    candidate_side: str | None = None
    opposite_h1_dol: Decimal | None = None
    return_inside_at: datetime | None = None
    return_inside_close: Decimal | None = None
    method_certified: bool = False
    cognition_certified: bool = False
    execution_authorized: bool = False

    def record(self) -> dict[str, Any]:
        data = asdict(self)
        return {
            k: v.isoformat() if isinstance(v, datetime)
            else str(v) if isinstance(v, Decimal)
            else list(v) if isinstance(v, tuple)
            else v
            for k, v in data.items()
        }


@dataclass(frozen=True, slots=True)
class NativeCogComparison:
    state: str
    reasons: tuple[str, ...]
    native_state: str
    v2_state: str | None
    method_certified: bool = False
    cognition_certified: bool = False
    execution_authorized: bool = False


def _start(as_of: datetime, hour: int) -> datetime:
    day = utc(as_of).astimezone(NEW_YORK).date()
    return datetime.combine(day, time(hour), tzinfo=NEW_YORK).astimezone(
        utc(as_of).tzinfo,
    )


def _complete_prefix(bars: tuple[M1Bar, ...], start: datetime) -> bool:
    return bool(bars) and all(
        utc(b.opened_at) == start + timedelta(minutes=i)
        and utc(b.closed_at) == start + timedelta(minutes=i + 1)
        for i, b in enumerate(bars)
    )


def native_ttrades_am_context(
    *, as_of: datetime,
    nine: tuple[M1Bar, ...],
    ten: tuple[M1Bar, ...],
    session: SessionId = SessionId.NY_AM,
) -> NativeAmContext:
    """Generate contextual evidence from closed original M1, no COG DTO.

    Precedence inside a candle is unknowable from OHLC. The first sweep is
    irrevocably chosen before any later return; no second-side rescue.
    """
    at = utc(as_of)
    start9, start10, end10 = _start(at, 9), _start(at, 10), _start(at, 11)
    def outcome(
        state: str, reason: str,
        hi: Decimal | None = None, lo: Decimal | None = None,
        sweep: str | None = None, stamp: datetime | None = None,
        bias: str | None = None, target: Decimal | None = None,
        returned: datetime | None = None, returned_close: Decimal | None = None,
    ) -> NativeAmContext:
        return NativeAmContext(
            profile=TTRADES_AM, as_of=at, state=state,
            reasons=(reason,), high_9am=hi, low_9am=lo,
            first_sweep_side=sweep, first_sweep_at=stamp,
            candidate_side=bias, opposite_h1_dol=target,
            return_inside_at=returned, return_inside_close=returned_close,
        )

    if session is not SessionId.NY_AM or not (start10 < at <= end10):
        return outcome("REJECTED", "PROFILE_OR_SIGNAL_CLOCK_NOT_NY_AM")
    if (
        any(utc(b.closed_at) > at for b in (*nine, *ten))
        or (ten and utc(ten[-1].closed_at) != at)
    ):
        return outcome("REJECTED", "FUTURE_OR_STALE_ASOF_M1")
    if len(nine) != 60 or not _complete_prefix(nine, start9):
        return outcome("UNKNOWN", "H1_09_10_INCOMPLETE")
    if not (1 <= len(ten) <= 60) or not _complete_prefix(ten, start10):
        return outcome("UNKNOWN", "TEN_AM_CLOSED_M1_GAP_OR_MISSING")
    hi, lo = max(x.high for x in nine), min(x.low for x in nine)
    if hi <= lo:
        return outcome("UNKNOWN", "H1_REFERENCE_DEGENERATE", hi, lo)
    first_side: str | None = None
    first_at: datetime | None = None
    first_index: int | None = None
    bias: str | None = None
    target: Decimal | None = None
    returned: datetime | None = None
    returned_close: Decimal | None = None
    for i, b in enumerate(ten):
        high_raid = b.high > hi
        low_raid = b.low < lo
        if high_raid and low_raid:
            return outcome(
                "UNKNOWN", "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER",
                hi, lo, first_side, first_at, bias, target,
            )
        current = "HIGH" if high_raid else "LOW" if low_raid else None
        if current is not None:
            if first_side is None:
                first_side, first_at, first_index = current, utc(b.closed_at), i
                bias = "SHORT" if current == "HIGH" else "LONG"
                target = lo if current == "HIGH" else hi
            elif current != first_side:
                return outcome(
                    "REJECTED", "OPPOSITE_H1_RAID_AFTER_FIRST_SWEEP",
                    hi, lo, first_side, first_at, bias, target,
                )
        # A candle that sweeps AND closes inside cannot prove event order.
        if first_index is None or i <= first_index or returned is not None:
            continue
        inside = lo < b.close < hi
        directional = (
            b.close > b.open if bias == "LONG"
            else b.close < b.open
        )
        if inside and directional:
            returned, returned_close = utc(b.closed_at), b.close
    if first_side is None:
        return outcome("AWAIT_SWEEP", "NO_PRIOR_9AM_H1_RAID_YET", hi, lo)
    if returned is None:
        return outcome(
            "AWAIT_RETURN", "NO_LATER_CLOSED_M1_DIRECTIONAL_RETURN_INSIDE_H1",
            hi, lo, first_side, first_at, bias, target,
        )
    return outcome(
        "RETURN_INSIDE_OBSERVED",
        "CONTEXT_RETURN_ONLY_MSS_DISPLACEMENT_AND_ENTRY_FAMILY_UNCERTIFIED",
        hi, lo, first_side, first_at, bias, target,
        returned, returned_close,
    )


def compare_native_with_existing_cog(
    *, native: NativeAmContext,
    cognition: CognitiveDecision | None,
    history: tuple[M1Bar, ...],
) -> NativeCogComparison:
    """V2 source/cognition checks: never construct a CognitiveDecision."""
    if native.state != "RETURN_INSIDE_OBSERVED":
        return NativeCogComparison(
            state="NATIVE_NOT_READY", reasons=native.reasons,
            native_state=native.state, v2_state=None,
        )
    if cognition is None:
        return NativeCogComparison(
            state="COG_NOT_PRESENT", reasons=("NO_COG_DECISION_AT_ASOF",),
            native_state=native.state, v2_state=None,
        )
    at = utc(native.as_of)
    start9, start10 = _start(at, 9), _start(at, 10)
    nine = tuple(b for b in history if start9 <= utc(b.opened_at) < start10)
    ten = tuple(b for b in history if start10 <= utc(b.opened_at) < at)
    if (
        len(nine) != 60 or not _complete_prefix(nine, start9)
        or not ten or not _complete_prefix(ten, start10)
        or native.high_9am != max(b.high for b in nine)
        or native.low_9am != min(b.low for b in nine)
        or utc(ten[-1].closed_at) != at
    ):
        return NativeCogComparison(
            state="REJECTED",
            reasons=("NATIVE_AND_COG_M1_SOURCE_INCONSISTENT",),
            native_state=native.state, v2_state=None,
        )
    raw = native_ttrades_am_context(
        as_of=at, nine=nine, ten=ten,
    )
    if raw != native:
        return NativeCogComparison(
            state="REJECTED",
            reasons=("NATIVE_CONTEXT_NOT_REPRODUCIBLE_FROM_COG_M1_SOURCE",),
            native_state=native.state, v2_state=None,
        )
    reasons: list[str] = []
    if cognition.session is not SessionId.NY_AM:
        reasons.append("COG_SESSION_NOT_NY_AM")
    if cognition.side.value != native.candidate_side:
        reasons.append("COG_DIRECTION_OPPOSES_FIRST_RAID")
    if cognition.draw_target != native.opposite_h1_dol:
        reasons.append("COG_DOL_NOT_PRIOR_H1_OPPOSITE")
    if (
        native.first_sweep_at is None
        or utc(cognition.structure_break_confirmed_at) <= native.first_sweep_at
    ):
        reasons.append("COG_MSS_NOT_AFTER_SOURCE_RAID")
    if reasons:
        return NativeCogComparison(
            state="REJECTED", reasons=tuple(reasons),
            native_state=native.state, v2_state=None,
        )
    v2 = inspect_cog_evidence(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=at, history=history, cognition=cognition,
    )
    state = (
        "CONTEXT_ATTESTED_NOT_CERTIFIED" if v2.state == "CONFIRMED"
        else "COG_SOURCE_REJECTED" if v2.state == "REJECTED"
        else "COG_SOURCE_UNKNOWN"
    )
    return NativeCogComparison(
        state=state,
        reasons=v2.rejected + v2.unknown,
        native_state=native.state,
        v2_state=v2.state,
    )
