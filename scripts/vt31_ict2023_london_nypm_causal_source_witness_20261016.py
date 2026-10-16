#!/usr/bin/env python3
"""Original ICT 2023 London + NY PM Silver Bullet source geometry, RESEARCH ONLY.

The original 2023 ICT lesson has 03-04 / 10-11 / 14-15 NY windows and a
projected >=10 index-handle framework, MSS and FVG. This research witness
covers London/PM ONLY: the frozen VT31 NYAM selector uses TTrades 2025.
Witnessed geometry is NOT a verified ICT chart, entry, stop or trade.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    M1Bar,
    SessionId,
    Side,
    price,
    utc,
    window_bounds,
)

PREREG = "6b76b2f3ab75afa84bc0baf2a8b04f7ecfa838f2"
VERSION = "VT31_ICT2023_LONDON_NYPM_M1_SOURCE_GEOMETRY_RESEARCH"
ICT_GENERAL = "ICT_GENERAL_2023"
WAIT = "WAIT"
REJECT = "REJECT"
WITNESS = "ICT_2023_CONTEXT_GEOMETRY_ONLY_ENTRY_RETEST_UNATTESTED"
SHORTFALL = "ICT_2023_PROJECTED_FRAMEWORK_BELOW_10_WAIT"


@dataclass(frozen=True, slots=True)
class ICT2023SourceVerdict:
    action: str
    reason: str
    session: str
    profile: str
    side: str | None = None
    as_of: str | None = None
    projected_framework_handles: str | None = None
    geometry_state: str | None = None
    source_video_url: str = "https://www.youtube.com/watch?v=tRq1hyGGtl4"
    primary_author_example_verified: bool = False
    dol_origin_verified: bool = False
    chosen_fvg_author_verified: bool = False
    chosen_mss_author_verified: bool = False
    entry_retest_confirmed: bool = False
    method_certified: bool = False
    cognition_certified: bool = False
    owner_signed_m0: bool = False
    independent_cog_ops_signed: bool = False
    native_cog_connected: bool = False
    broker_orders: int = 0
    lot_sizing: int = 0

    def record(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "action": self.action,
            "reason": self.reason,
            "session": self.session,
            "profile": self.profile,
            "side": self.side,
            "as_of": self.as_of,
            "projected_framework_handles": self.projected_framework_handles,
            "geometry_state": self.geometry_state,
            "source_video_url": self.source_video_url,
            "primary_author_example_verified": False,
            "dol_origin_verified": False,
            "chosen_fvg_author_verified": False,
            "chosen_mss_author_verified": False,
            "entry_retest_confirmed": False,
            "method_certified": False,
            "cognition_certified": False,
            "owner_signed_m0": False,
            "independent_cog_ops_signed": False,
            "native_cog_connected": False,
            "broker_orders": 0,
            "lot_sizing": 0,
        }


def ict2023_london_pm_source_witness(
    *, profile: str, session: SessionId, side: Side,
    closed_m1: tuple[M1Bar, ...], as_of: datetime,
    target_level: Decimal, target_observed_at: datetime,
    swing_index: int, mss_confirm_index: int,
    fvg_first_index: int,
) -> ICT2023SourceVerdict:
    """Only attest timestamped price geometry, not the author's chart case."""
    name = session.value if isinstance(session, SessionId) else "INVALID"

    def out(
        action: str, reason: str, *,
        geometry: str | None = None, projected: Decimal | None = None,
        at: datetime | None = None,
    ) -> ICT2023SourceVerdict:
        return ICT2023SourceVerdict(
            action=action, reason=reason, session=name, profile=profile,
            side=side.value if isinstance(side, Side) else None,
            as_of=at.isoformat() if at else None,
            projected_framework_handles=str(projected)
            if projected is not None else None,
            geometry_state=geometry,
        )

    if profile != ICT_GENERAL:
        return out(REJECT, "ICT2023_PROFILE_NOT_FROZEN_LONDON_PM")
    if session not in (SessionId.LONDON, SessionId.NY_PM):
        return out(REJECT, "ICT2023_RESEARCH_LONDON_OR_NYPM_ONLY")
    if not isinstance(side, Side):
        return out(REJECT, "SOURCE_DIRECTION_NOT_TYPED")
    if not isinstance(closed_m1, tuple) or len(closed_m1) < 6 or any(
        not isinstance(b, M1Bar) for b in closed_m1
    ):
        return out(REJECT, "SOURCE_CLOSED_M1_TYPED_TUPLE_REQUIRED")
    try:
        at = utc(as_of)
        target_known = utc(target_observed_at)
        target = price(target_level)
        starts = tuple(utc(b.opened_at) for b in closed_m1)
        ends = tuple(utc(b.closed_at) for b in closed_m1)
    except (TypeError, ValueError):
        return out(REJECT, "SOURCE_NAIVE_CLOCK_OR_INVALID_TARGET")
    if ends[-1] != at or any(e > at for e in ends) or any(
        ends[i] != starts[i+1] for i in range(len(closed_m1) - 1)
    ):
        return out(REJECT, "SOURCE_TIME_GAP_FUTURE_OR_ASOF_CONTRADICTION")
    first, last = window_bounds(at, session)
    if not (first < at <= last) or target_known > first:
        return out(REJECT, "SOURCE_WINDOW_OR_DOL_SELECTION_NOT_PRECOMMITTED")
    if (
        type(swing_index) is not int
        or type(mss_confirm_index) is not int
        or type(fvg_first_index) is not int
        or not (
            1 <= swing_index < len(closed_m1) - 2
            and swing_index + 1 < mss_confirm_index
            and mss_confirm_index == fvg_first_index + 1
            and fvg_first_index >= 0
            and fvg_first_index + 2 == len(closed_m1) - 1
        )
    ):
        return out(REJECT, "SOURCE_MSS_FVG_INDICES_NOT_CAUSAL_OR_NOT_TYPED")
    left = closed_m1[swing_index - 1]
    swing = closed_m1[swing_index]
    right = closed_m1[swing_index + 1]
    confirming = closed_m1[mss_confirm_index]
    fvg = closed_m1[fvg_first_index:fvg_first_index+3]
    if (
        ends[swing_index + 1] > starts[mss_confirm_index]
        or any(not (first <= utc(b.opened_at) < utc(b.closed_at) <= last) for b in fvg)
        or ends[mss_confirm_index] > ends[fvg_first_index+2]
    ):
        return out(REJECT, "SOURCE_MSS_OR_FVG_USED_FUTURE_OR_OUTSIDE_WINDOW")

    if side is Side.LONG:
        pivot = swing.high > left.high and swing.high > right.high
        structure_close = confirming.close > swing.high
        fvg_geometry = fvg[2].low > fvg[0].high
        projected = target - confirming.close
    else:
        pivot = swing.low < left.low and swing.low < right.low
        structure_close = confirming.close < swing.low
        fvg_geometry = fvg[2].high < fvg[0].low
        projected = confirming.close - target
    if not pivot or not structure_close:
        return out(WAIT, "ICT2023_MSS_GEOMETRY_INCOMPLETE", at=at)
    if not fvg_geometry:
        return out(WAIT, "ICT2023_THREE_CLOSED_M1_FVG_NOT_PRESENT", at=at)
    if projected <= 0:
        return out(REJECT, "ICT2023_TARGET_NOT_IN_DIRECTION_OF_STRUCTURE", at=at)

    # ICT original: projected 10 index handles is a FRAMEWORK criterion,
    # never a broker fill, trade PnL or selected lot size.
    if projected < Decimal("10"):
        return out(
            WAIT, "ICT2023_PROJECTED_FRAMEWORK_NOT_TEN_HANDLES",
            projected=projected, geometry=SHORTFALL, at=at,
        )
    return out(
        WAIT, "ICT2023_MSS_FVG_CONTEXT_GEOMETRY_AUTHOR_SOURCE_NOT_HOMOLOGATED",
        projected=projected, geometry=WITNESS, at=at,
    )


def synthetic_london_pm_case(
    *, session: SessionId, side: Side, month: int, sufficient: bool,
) -> tuple[dict[str, Any], ICT2023SourceVerdict]:
    """Independent Jan/Jul EST/EDT fixture, not the original ICT chart."""
    if session not in (SessionId.LONDON, SessionId.NY_PM) or month not in (1, 7):
        raise ValueError("SOURCE_SESSION_AND_DST_FIXTURE_ONLY")
    local_start = datetime(
        2026, month, 15, 3 if session is SessionId.LONDON else 14,
        tzinfo=NEW_YORK,
    )
    start = utc(local_start)
    long_bars = (
        ("100", "102", "98", "101"),
        ("101", "105", "99", "100"),
        ("100", "103", "99", "101"),
        ("101", "104", "100", "103"),
        ("103", "112", "103", "110"),
        ("110", "114", "107", "113"),
    )
    result = []
    for idx, prices in enumerate(long_bars):
        o, h, lo, c = (Decimal(v) for v in prices)
        if side is Side.SHORT:
            o, h, lo, c = 210-o, 210-lo, 210-h, 210-c
        result.append(M1Bar(
            opened_at=start + timedelta(minutes=idx),
            closed_at=start + timedelta(minutes=idx+1),
            open=o, high=h, low=lo, close=c,
        ))
    target = Decimal("125" if sufficient else "115")
    if side is Side.SHORT:
        target = Decimal("85" if sufficient else "95")
    args: dict[str, Any] = {
        "profile": ICT_GENERAL,
        "session": session,
        "side": side,
        "closed_m1": tuple(result),
        "as_of": result[-1].closed_at,
        "target_level": target,
        "target_observed_at": start - timedelta(minutes=1),
        "swing_index": 1,
        "mss_confirm_index": 4,
        "fvg_first_index": 3,
    }
    return args, ict2023_london_pm_source_witness(**args)


def ict_three_session_source_court() -> dict[str, Any]:
    rows = []
    for month in (1, 7):
        for side in (Side.LONG, Side.SHORT):
            for session in (SessionId.LONDON, SessionId.NY_PM):
                for sufficient in (False, True):
                    _, result = synthetic_london_pm_case(
                        session=session, side=side, month=month,
                        sufficient=sufficient,
                    )
                    expected = WITNESS if sufficient else SHORTFALL
                    if result.action != WAIT or result.geometry_state != expected:
                        raise ValueError(
                            f"ICT2023_DST_SESSION_SOURCE_DRIFT:{month}:{side}:{session}:{result}"
                        )
                    rows.append({
                        "case": f"{session.value}_{side.value}_{month}_{sufficient}",
                        **result.record(),
                    })
    return {
        "title": VERSION,
        "prereg_commit": PREREG,
        "original_ict_video": "https://www.youtube.com/watch?v=tRq1hyGGtl4",
        "secondary_study_notes": [
            "https://edgeofict.com/learn/mentorship-2023/29-silver-bullet-time-based-trading-model-may-15",
            "https://bestprops.com/ict/2023-mentorship/ict-silver-bullet-time-based-trading-model/",
        ],
        "cases": rows,
        "synthetic_m1_only": True,
        "ttrades_nyam_profile_not_used": True,
        "author_case_chart_not_reproduced": True,
        "projected_10handles_not_trade_profit": True,
        "source_ict2023_found": True,
        "entry_retest_author_homologated": False,
        "london_author_certified": False, "nypm_author_certified": False,
        "methodology_certified": False, "cognition_certified": False,
        "human_cog_ops_signed": False, "owner_profile_signed": False,
        "native_g3_connected": False,
        "orders": 0, "sizing": 0, "live": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    path = parser.parse_args().out
    result = ict_three_session_source_court()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "cases": len(result["cases"]),
        "source_geometry": sum(x["geometry_state"] == WITNESS for x in result["cases"]),
        "methodology_certified": False, "cognition_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
