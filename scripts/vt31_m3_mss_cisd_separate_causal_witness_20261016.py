#!/usr/bin/env python3
"""VT31 M3: distinguish MSS swing-close from CISD series-open on sealed M1.

Both results are geometry-only RESEARCH WITNESSES; displacement and swing/series
selection by the original author are NOT certified. The AM 2025 model does not
make both methods universal entry requirements. Original G3 COG/OPS untouched.
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
    utc,
)
from scripts.vt31_cog_v4_transactional_context_20261016 import (
    VT31TwoPhaseCognitiveCandidate,
)
from scripts.vt31_m0_m4_context_memory_cog_candidate_20261015 import (
    tape_sha256,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    ttrades_fixture,
)

PREREG = "ea9df7d0f1fd7404d9e9e8271e0967aee8b36f09"
VERSION = "VT31_M3_MSS_CISD_SEPARATE_SOURCE_WITNESS_RESEARCH_20261016"
WAIT = "WAIT"
REJECT = "REJECT"
YES_MSS = "SWING_CLOSE_GEOMETRY_ONLY_DISPLACEMENT_NOT_PROVEN"
YES_CISD = "OPPOSING_SERIES_OPEN_CLOSE_GEOMETRY_ONLY_SELECTION_NOT_PROVEN"
NO_GEOMETRY = "GEOMETRIC_CLOSE_NOT_OBSERVED"
NO_SOURCE = "SOURCE_WITNESS_NOT_SUBMITTED"


@dataclass(frozen=True, slots=True)
class M3SourceVerdict:
    action: str
    reason: str
    session: str
    side: str | None = None
    as_of: str | None = None
    mss_status: str = NO_SOURCE
    cisd_status: str = NO_SOURCE
    mss_swing_level: str | None = None
    cisd_series_open: str | None = None
    sealed_sha256: str | None = None
    mss_author_certified: bool = False
    cisd_author_certified: bool = False
    displacement_author_proven: bool = False
    am_family_approved: bool = False
    methodology_certified: bool = False
    cognition_certified: bool = False
    independent_human_signed: bool = False
    orders_authorized: bool = False
    lot_sizing: int = 0
    broker_orders: int = 0

    def record(self) -> dict[str, Any]:
        return {
            "version": VERSION, "action": self.action, "reason": self.reason,
            "session": self.session, "side": self.side,
            "as_of": self.as_of, "mss_status": self.mss_status,
            "cisd_status": self.cisd_status,
            "mss_swing_level": self.mss_swing_level,
            "cisd_series_open": self.cisd_series_open,
            "sealed_sha256": self.sealed_sha256,
            "mss_author_certified": False,
            "cisd_author_certified": False,
            "displacement_author_proven": False,
            "am_family_approved": False,
            "methodology_certified": False,
            "cognition_certified": False,
            "independent_human_signed": False,
            "orders_authorized": False,
            "lot_sizing": 0, "broker_orders": 0,
        }


def separate_mss_cisd_on_sealed_m1(
    *,
    actor: VT31TwoPhaseCognitiveCandidate,
    session: SessionId,
    closed_m1: tuple[M1Bar, ...],
    as_of: datetime,
    swing_index: int | None,
    cisd_start_index: int | None,
    cisd_end_index: int | None,
) -> M3SourceVerdict:
    """Independent evidence classification, NOT a Silver Bullet author gate."""
    name = session.value if isinstance(session, SessionId) else "INVALID"

    def out(
        action: str, reason: str, *,
        side: str | None = None, at: str | None = None,
        mss: str = NO_SOURCE, cisd: str = NO_SOURCE,
        swing: Decimal | None = None, series: Decimal | None = None,
        digest: str | None = None,
    ) -> M3SourceVerdict:
        return M3SourceVerdict(
            action=action, reason=reason, session=name,
            side=side, as_of=at, mss_status=mss, cisd_status=cisd,
            mss_swing_level=str(swing) if swing is not None else None,
            cisd_series_open=str(series) if series is not None else None,
            sealed_sha256=digest,
        )

    if not isinstance(actor, VT31TwoPhaseCognitiveCandidate):
        return out(REJECT, "V4_CONTEXT_OWNER_REQUIRED")
    ctx, seal = actor.context, actor.seal
    if ctx is None or seal is None:
        return out(WAIT, "M0_CONTEXT_NOT_COMMITTED")
    if session is not SessionId.NY_AM or ctx.session is not session:
        return out(REJECT, "M3_TTRADES_NYAM_SOURCE_ONLY")
    if not isinstance(closed_m1, tuple) or not closed_m1 or any(
        not isinstance(bar, M1Bar) for bar in closed_m1
    ):
        return out(REJECT, "M3_TYPED_CLOSED_M1_TUPLE_REQUIRED")
    try:
        at = utc(as_of)
        digest = tape_sha256(closed_m1)
    except (ValueError, TypeError):
        return out(REJECT, "M3_INVALID_ASOF_OR_NONFINITE_OHLC")
    if (
        at != utc(closed_m1[-1].closed_at)
        or at != seal.last_as_of
        or len(closed_m1) != seal.count
        or digest != seal.sha256_total
    ):
        return out(REJECT, "M3_M1_NOT_IDENTICAL_TO_COMMITTED_V4_SNAPSHOT")
    local = at.astimezone(NEW_YORK)
    confirmation = closed_m1[-1]
    if (
        local.date().isoformat() != ctx.ny_date
        or not (local.hour == 10 or (local.hour == 11 and local.minute == 0))
        or utc(confirmation.opened_at) < ctx.at
        or at <= ctx.at
    ):
        return out(REJECT, "M3_CONFIRMATION_OUTSIDE_POST_M0_NYAM")
    if any(
        utc(a.closed_at) != utc(z.opened_at)
        for a, z in zip(closed_m1, closed_m1[1:], strict=False)
        if utc(a.opened_at) >= ctx.at
    ):
        return out(REJECT, "M3_POST_M0_CLOSED_M1_GAP")
    side = ctx.side
    if side not in (Side.LONG.value, Side.SHORT.value):
        return out(REJECT, "M3_SIDE_NOT_ATTESTED_BY_M0")
    if swing_index is not None and (
        type(swing_index) is not int
        or swing_index < 1
        or swing_index >= len(closed_m1) - 2
    ):
        return out(REJECT, "M3_SWING_INDEX_FUTURE_OR_UNTYPED")
    if (cisd_start_index is None) != (cisd_end_index is None):
        return out(REJECT, "M3_PARTIAL_CISD_SERIES_WITNESS")
    if cisd_start_index is not None and (
        type(cisd_start_index) is not int
        or type(cisd_end_index) is not int
        or not (0 <= cisd_start_index <= cisd_end_index < len(closed_m1) - 1)
    ):
        return out(REJECT, "M3_CISD_SERIES_FUTURE_OR_UNTYPED")

    pivot_level = None
    mss_state = NO_SOURCE
    if swing_index is not None:
        pivot = closed_m1[swing_index]
        left, right = closed_m1[swing_index - 1], closed_m1[swing_index + 1]
        if utc(pivot.opened_at) < ctx.at or utc(right.closed_at) > utc(confirmation.opened_at):
            return out(REJECT, "M3_SWING_NOT_CONFIRMED_POST_M0_PREBREAK")
        if side == Side.LONG.value:
            pivot_level = pivot.high
            valid_swing = pivot.high > left.high and pivot.high > right.high
            closes_past = confirmation.close > pivot_level
        else:
            pivot_level = pivot.low
            valid_swing = pivot.low < left.low and pivot.low < right.low
            closes_past = confirmation.close < pivot_level
        if not valid_swing:
            return out(REJECT, "M3_DECLARED_SWING_IS_NOT_THREE_BAR_PIVOT")
        mss_state = YES_MSS if closes_past else NO_GEOMETRY

    series_open = None
    cisd_state = NO_SOURCE
    if cisd_start_index is not None:
        series = closed_m1[cisd_start_index:cisd_end_index + 1]
        if (
            utc(series[0].opened_at) < ctx.at
            or utc(series[-1].closed_at) > utc(confirmation.opened_at)
            or any(
                utc(a.closed_at) != utc(z.opened_at)
                for a, z in zip(series, series[1:], strict=False)
            )
        ):
            return out(REJECT, "M3_CISD_SERIES_NOT_CLOSED_CONTIGUOUS_POST_M0")
        if side == Side.LONG.value:
            opposite = all(b.close < b.open for b in series)
            beyond = confirmation.close > series[0].open
        else:
            opposite = all(b.close > b.open for b in series)
            beyond = confirmation.close < series[0].open
        if not opposite:
            return out(REJECT, "M3_CISD_WITNESS_CANDLES_NOT_ALL_OPPOSITE")
        series_open = series[0].open
        cisd_state = YES_CISD if beyond else NO_GEOMETRY

    return out(
        WAIT, "M3_TWO_INDEPENDENT_SOURCE_GEOMETRIES_AUTHOR_NOT_CERTIFIED",
        side=side, at=at.isoformat(),
        mss=mss_state, cisd=cisd_state,
        swing=pivot_level, series=series_open, digest=digest,
    )


def synthetic_m3_case(
    *, side: Side, month: int, scenario: str,
) -> tuple[VT31TwoPhaseCognitiveCandidate, tuple[M1Bar, ...], datetime, dict[str, int]]:
    """Four contrasts LONG/SHORT in EST/EDT. Not data from the author."""
    params = {
        "BOTH": ("100", "101", "103"),
        "MSS_ONLY": ("105", "101", "103"),
        "CISD_ONLY": ("100", "106", "103"),
        "NEITHER": ("100", "106", "98"),
    }
    if scenario not in params or month not in (1, 7):
        raise ValueError("UNREGISTERED_M3_SYNTHETIC_CASE")
    base, start = ttrades_fixture(
        side=side, month=month, min10_valid=True,
    )
    first_open, pivot_hi, last_close = (Decimal(v) for v in params[scenario])
    long_bars = (
        (first_open, max(first_open + 1, Decimal("102")), Decimal("97"), Decimal("99")),
        (Decimal("99"), Decimal("100"), Decimal("97"), Decimal("98")),
        (Decimal("98"), pivot_hi, Decimal("96"), Decimal("97")),
        (Decimal("97"), pivot_hi - 1, Decimal("95"), Decimal("96")),
        (Decimal("97"), max(pivot_hi + 1, last_close + 1), Decimal("96"), last_close),
    )
    series = []
    for i, (o, hi, lo, cl) in enumerate(long_bars):
        if side is Side.SHORT:
            o, hi, lo, cl = 200 - o, 200 - lo, 200 - hi, 200 - cl
        series.append(M1Bar(
            opened_at=start + timedelta(minutes=i),
            closed_at=start + timedelta(minutes=i + 1),
            open=o, high=hi, low=lo, close=cl,
        ))
    whole = base + tuple(series)
    actor = VT31TwoPhaseCognitiveCandidate()
    admitted = actor.capture_context(
        session=SessionId.NY_AM, closed_m1=base, as_of=start,
    )
    if admitted.action != WAIT or not admitted.committed:
        raise ValueError("SYNTHETIC_M0_CONTEXT_NOT_COMMITTED")
    accepted = actor.assess_later_retest(
        session=SessionId.NY_AM,
        closed_m1=whole,
        as_of=whole[-1].closed_at,
    )
    if accepted.action != WAIT or not accepted.committed:
        raise ValueError(f"SYNTHETIC_M3_DATA_REJECTED_PRECONTEXT:{accepted.reason}")
    return actor, whole, whole[-1].closed_at, {
        "swing_index": len(base) + 2,
        "cisd_start_index": len(base),
        "cisd_end_index": len(base) + 3,
    }


def m3_independent_source_court() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for month in (1, 7):
        for side in (Side.LONG, Side.SHORT):
            for scenario in ("BOTH", "MSS_ONLY", "CISD_ONLY", "NEITHER"):
                actor, bars, at, witnesses = synthetic_m3_case(
                    side=side, month=month, scenario=scenario,
                )
                v = separate_mss_cisd_on_sealed_m1(
                    actor=actor, session=SessionId.NY_AM,
                    closed_m1=bars, as_of=at, **witnesses,
                )
                expected_mss = scenario in ("BOTH", "MSS_ONLY")
                expected_cisd = scenario in ("BOTH", "CISD_ONLY")
                if (
                    v.action != WAIT or
                    (v.mss_status == YES_MSS) != expected_mss or
                    (v.cisd_status == YES_CISD) != expected_cisd
                ):
                    raise ValueError(f"M3_SOURCE_CONTRAST_FAILED:{scenario}:{side}:{month}:{v}")
                results.append({
                    "case": f"{side.value}_{month}_{scenario}",
                    **v.record(),
                })
    return {
        "title": VERSION,
        "prereg_commit": PREREG,
        "source_primary": [
            "https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/",
            "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/",
        ],
        "synthetic_m1_only": True,
        "cases": results,
        "mss_and_cisd_distinct": True,
        "not_universal_am_gates": True,
        "author_displacement_approved": False,
        "author_swing_relevance_approved": False,
        "author_cisd_series_selection_approved": False,
        "m3_author_certified": False,
        "methodology_certified": False, "cognition_certified": False,
        "owner_m0_signed": False, "human_cog_ops_signed": False,
        "native_cog_integrated": False, "orders": 0, "sizing": 0, "live": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    path = parser.parse_args().out
    report = m3_independent_source_court()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "cases": len(report["cases"]),
        "mss_geometry_only": sum(x["mss_status"] == YES_MSS for x in report["cases"]),
        "cisd_geometry_only": sum(x["cisd_status"] == YES_CISD for x in report["cases"]),
        "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
