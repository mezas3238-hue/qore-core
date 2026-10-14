#!/usr/bin/env python3
"""M4/M5 causal *source-only* witness: TTrades M1 first FVG & C2 full wick.

No broker tick, quote, orders, CE execution, position, return or lot sizing.
This separately assesses a frozen research *QORE proxy*, not author fidelity.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
    utc,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.m1_execution import (
    confirmed_m1_fvg,
)
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    native_ttrades_am_context,
)

PROFILE = "TTRADES_NY_AM_2025_QORE_G3_FIRST_FVG_RESEARCH_PROXY"
NY = ZoneInfo("America/New_York")
MIN_FRAMEWORK_POINTS = Decimal("10")


@dataclass(frozen=True, slots=True)
class M4M5SourcePath:
    state: str
    reasons: tuple[str, ...]
    cognitive_mss_at: datetime
    first_fvg_confirmed_at: datetime | None = None
    side: Side | None = None
    fvg_lower: Decimal | None = None
    fvg_upper: Decimal | None = None
    ce_research_only: Decimal | None = None
    c2_full_wick_reference: Decimal | None = None
    target_dol: Decimal | None = None
    mss_anchor: Decimal | None = None
    potential_points_at_mss: Decimal | None = None
    source_path_state: str = "NO_LIMIT_OFFERED"
    path_observation_at: datetime | None = None
    method_certified: bool = False
    execution_authorized: bool = False
    filled: bool = False

    def record(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field, value in asdict(self).items():
            if isinstance(value, Decimal):
                result[field] = str(value)
            elif isinstance(value, datetime):
                result[field] = value.isoformat()
            else:
                result[field] = value
        return result


def _ordered(nine: tuple[M1Bar, ...], ten: tuple[M1Bar, ...]) -> bool:
    ordered = nine + ten
    return all(
        utc(a.closed_at) == utc(b.opened_at)
        for a, b in zip(ordered, ordered[1:], strict=False)
    )


def first_fvg_and_source_path(
    *,
    nine: tuple[M1Bar, ...],
    ten: tuple[M1Bar, ...],
    cognition: CognitiveDecision,
) -> M4M5SourcePath:
    """As-of only: supplied ten must be a complete CLOSED prefix through at.

    Cannot generate an entry order. Immutable first eligible FVG; future M1
    are used only to report source-touch/invalidations, never as a fill.
    """
    mss_at = utc(cognition.structure_break_confirmed_at)

    def outcome(
        state: str, *reasons: str,
        formed: datetime | None = None, side: Side | None = None,
        lo: Decimal | None = None, hi: Decimal | None = None,
        ce: Decimal | None = None, c2: Decimal | None = None,
        room: Decimal | None = None,
        path: str = "NO_LIMIT_OFFERED",
        event: datetime | None = None,
    ) -> M4M5SourcePath:
        return M4M5SourcePath(
            state, tuple(reasons), mss_at, formed, side, lo, hi, ce, c2,
            cognition.draw_target, cognition.mss_anchor_close, room,
            path, event,
        )

    if cognition.session is not SessionId.NY_AM:
        return outcome("REJECTED", "PROFILE_NOT_TTRADES_NY_AM")
    if not ten or not nine or len(nine) != 60:
        return outcome("UNKNOWN", "H1_09H_OR_10H_INCOMPLETE")
    as_of = utc(ten[-1].closed_at)
    if not _ordered(nine, ten):
        return outcome("UNKNOWN", "CLOSED_M1_GAP_OR_DUPLICATE")
    mss_index = next(
        (k for k, b in enumerate(ten) if utc(b.closed_at) == mss_at),
        None,
    )
    if mss_index is None:
        return outcome("UNKNOWN", "MSS_M1_NOT_IN_TEN_AM_HOUR")
    source = native_ttrades_am_context(
        as_of=mss_at, nine=nine, ten=ten[:mss_index + 1],
    )
    if source.state != "RETURN_INSIDE_OBSERVED":
        return outcome("UNKNOWN", "FIRST_RETURN_SOURCE_NOT_AT_MSS", source.state)
    if (
        source.candidate_side != cognition.side.value
        or source.opposite_h1_dol != cognition.draw_target
        or cognition.observed_at != mss_at
        or cognition.mss_anchor_close is None
    ):
        return outcome("REJECTED", "COG_SOURCE_DOL_OR_MSS_WITNESS_MISMATCH")
    mss_bars = [b for b in nine + ten if utc(b.closed_at) == mss_at]
    if len(mss_bars) != 1:
        return outcome("UNKNOWN", "MSS_M1_CLOSE_NOT_OBSERVED")
    if mss_bars[0].close != cognition.mss_anchor_close:
        return outcome("REJECTED", "MSS_ANCHOR_INCONSISTENT_WITH_M1_DATA")
    room = (
        cognition.draw_target - cognition.mss_anchor_close
        if cognition.side is Side.LONG
        else cognition.mss_anchor_close - cognition.draw_target
    )
    if room < MIN_FRAMEWORK_POINTS:
        return outcome(
            "NO_FRAMEWORK", "SOURCE_MINIMUM_TEN_INDEX_POINTS_MISSING",
            room=room,
        )
    if mss_at > as_of:
        return outcome("REJECTED", "MSS_TIME_IN_FUTURE", room=room)
    start_return = source.return_inside_at
    if start_return is None or start_return != mss_at:
        return outcome("REJECTED", "FIRST_RETURN_CHANGED_OR_STALE", room=room)

    # Deliberately no reevaluation using ANY bars later than C3 to choose FVG.
    # Only the first structurally eligible FVG is selected, regardless of path.
    chosen: tuple[datetime, Side, Decimal, Decimal, Decimal, Decimal] | None = None
    chosen_idx: int | None = None
    for k in range(2, len(ten)):
        a, b, c = ten[k-2:k+1]
        if utc(c.closed_at) < mss_at:
            continue
        if not (
            utc(a.closed_at) == utc(b.opened_at)
            and utc(b.closed_at) == utc(c.opened_at)
        ):
            return outcome("UNKNOWN", "GAPPED_THREE_M1", room=room)
        prefix = ten[:k+1]
        native = native_ttrades_am_context(
            as_of=utc(c.closed_at), nine=nine, ten=prefix,
        )
        if (
            native.state != "RETURN_INSIDE_OBSERVED"
            or native.return_inside_at != mss_at
            or native.candidate_side != cognition.side.value
            or native.opposite_h1_dol != cognition.draw_target
        ):
            return outcome(
                "SOURCE_INVALIDATED_BEFORE_FIRST_FVG",
                "NATIVE_RAID_RETURN_OR_DOL_REVOKED",
                room=room,
            )
        # The DOL must remain unconsumed while searching for the setup.
        after_mss = (x for x in prefix if utc(x.closed_at) > mss_at)
        if any(
            x.high >= cognition.draw_target
            if cognition.side is Side.LONG
            else x.low <= cognition.draw_target
            for x in after_mss
        ):
            return outcome(
                "SOURCE_INVALIDATED_BEFORE_FIRST_FVG",
                "H1_OPPOSITE_DOL_ALREADY_TOUCHED",
                room=room,
            )
        if (
            c.close <= cognition.structure_level
            if cognition.side is Side.LONG
            else c.close >= cognition.structure_level
        ):
            continue
        raw = (
            (a.high, c.low)
            if cognition.side is Side.LONG and a.high < c.low
            else (c.high, a.low)
            if cognition.side is Side.SHORT and a.low > c.high
            else None
        )
        original = confirmed_m1_fvg(
            session=SessionId.NY_AM, first=a, middle=b, third=c,
        )
        if raw is None:
            continue
        lo, hi = raw
        ce = (lo + hi) / Decimal("2")
        if original is None or (
            original.side is not cognition.side
            or original.zone_low != lo or original.zone_high != hi
            or original.consequent_encroachment != ce
        ):
            return outcome(
                "REJECTED", "INDEPENDENT_FVG_ENGINE_DISAGREEMENT", room=room,
            )
        if (
            cognition.draw_target <= ce if cognition.side is Side.LONG
            else cognition.draw_target >= ce
        ):
            continue
        if utc(c.closed_at).astimezone(
            NY
        ).hour != 10:
            return outcome(
                "WINDOW_CLOSED_FOR_NEW_LIMIT", "FIRST_ELIGIBLE_FVG_AT_11AM_CLOSE",
                room=room,
            )
        chosen = (
            utc(c.closed_at), cognition.side, lo, hi, ce,
            b.low if cognition.side is Side.LONG else b.high,
        )
        chosen_idx = k
        break
    if chosen is None or chosen_idx is None:
        return outcome(
            "NO_ELIGIBLE_FVG", "NO_FIRST_M1_FVG_AFTER_MSS_WITH_FRAMEWORK",
            room=room,
        )
    formed, side, lo, hi, ce, c2 = chosen
    # No symbol-specific official tick/origin, quote, OMS or ACK exists here.
    path = "BROKER_TICK_AND_QUOTE_UNATTESTED"
    event: datetime | None = None
    for later in ten[chosen_idx+1:]:
        touch = later.low <= ce <= later.high
        invalid_close = (
            later.close < lo if side is Side.LONG
            else later.close > hi
        )
        if touch and invalid_close:
            path = "AMBIGUOUS_M1_SEQUENCE_NO_FILL"
            event = utc(later.closed_at)
            break
        if invalid_close:
            path = "INVALIDATED_AT_M1_CLOSE_NO_ORDER"
            event = utc(later.closed_at)
            break
        if touch:
            path = "TOUCH_NOT_FILL"
            event = utc(later.closed_at)
            break
    if path == "BROKER_TICK_AND_QUOTE_UNATTESTED" and as_of.astimezone(
        __import__("zoneinfo").ZoneInfo("America/New_York")
    ).hour == 11:
        path = "EXPIRED_NO_ORDER_OR_ACK"
        event = as_of
    return outcome(
        "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE",
        "QORE_FIRST_FVG_C2_WICK_WITHOUT_BROKER_EXECUTION_EVIDENCE",
        formed=formed, side=side, lo=lo, hi=hi, ce=ce, c2=c2,
        room=room, path=path, event=event,
    )
