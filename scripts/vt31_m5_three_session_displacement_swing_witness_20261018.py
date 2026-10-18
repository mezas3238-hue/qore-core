#!/usr/bin/env python3
"""VT31 M5 cross-session displacement-swing reference FALSIFIER, no broker stop.

This can REJECT impossible causal candidates. It can NEVER certify the author's
swing choice or produce an executable stop, decision, order, PnL or sizing.
PRECODE prereg: 89f8d8e87d287aae40946b75e9fde2f3e9307bc5
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
    M1Bar,
    SessionId,
    Side,
    utc,
    window_bounds,
)
from scripts.vt31_cog_v4_transactional_context_20261016 import (
    VT31TwoPhaseCognitiveCandidate,
)
from scripts.vt31_ict2023_london_nypm_causal_source_witness_20261016 import (
    ICT_GENERAL,
    WITNESS,
    ict2023_london_pm_source_witness,
    synthetic_london_pm_case,
)
from scripts.vt31_m0_m4_context_memory_cog_candidate_20261015 import (
    tape_sha256,
)
from scripts.vt31_m4_ob_breaker_author_evidence_gate_20261015 import PROFILE
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    ttrades_fixture,
)

PREREG = "89f8d8e87d287aae40946b75e9fde2f3e9307bc5"
VERSION = "VT31_M5_THREE_SESSIONS_CAUSAL_SWING_FALSIFIER_V1_20261018"
WAIT, REJECT = "WAIT", "REJECT"
CANDIDATE = "UNIQUE_PRE_DISPLACEMENT_EXTREME_GEOMETRY_CAUSE_AUTHOR_UNVERIFIED"


@dataclass(frozen=True, slots=True)
class M5SourceVerdict:
    action: str
    reason: str
    session: str
    profile: str
    side: str | None = None
    as_of: str | None = None
    candidate_extreme_reference: str | None = None
    swing_opened_at: str | None = None
    displacement_closed_at: str | None = None
    candidate_unique: bool = False
    geometry_state: str | None = None
    displacement_causing_swing_author_certified: bool = False
    protected_swing_author_certified: bool = False
    stop_tick_price: None = None
    native_g3_integrated: bool = False
    methodology_certified: bool = False
    cognition_certified: bool = False
    human_cog_ops_signed: bool = False
    owner_m0_signed: bool = False
    broker_orders: int = 0
    lot_sizing: int = 0

    def record(self) -> dict[str, Any]:
        return {
            "version": VERSION, "action": self.action, "reason": self.reason,
            "session": self.session, "profile": self.profile,
            "side": self.side, "as_of": self.as_of,
            "candidate_extreme_reference": self.candidate_extreme_reference,
            "swing_opened_at": self.swing_opened_at,
            "displacement_closed_at": self.displacement_closed_at,
            "candidate_unique": self.candidate_unique,
            "geometry_state": self.geometry_state,
            "displacement_causing_swing_author_certified": False,
            "protected_swing_author_certified": False,
            "stop_tick_price": None, "native_g3_integrated": False,
            "methodology_certified": False, "cognition_certified": False,
            "human_cog_ops_signed": False, "owner_m0_signed": False,
            "broker_orders": 0, "lot_sizing": 0,
        }


def adjudicate_m5_swing_reference(
    *, session: SessionId, profile: str, side: Side,
    closed_m1: tuple[M1Bar, ...], as_of: datetime,
    displacement_index: int, candidate_swing_index: int,
    nyam_actor: VT31TwoPhaseCognitiveCandidate | None = None,
    ict_setup: dict[str, Any] | None = None,
) -> M5SourceVerdict:
    """Source-locked candidate-extreme lineage; WAIT even if geometry aligns."""
    session_name = session.value if isinstance(session, SessionId) else "INVALID"

    def emit(
        action: str, reason: str, *,
        at: datetime | None = None,
        geometry: str | None = None,
        reference: M1Bar | None = None,
        extreme: Decimal | None = None,
        displacement: M1Bar | None = None,
    ) -> M5SourceVerdict:
        return M5SourceVerdict(
            action=action, reason=reason, session=session_name, profile=profile,
            side=side.value if isinstance(side, Side) else None,
            as_of=at.isoformat() if at else None,
            candidate_extreme_reference=str(extreme)
            if extreme is not None else None,
            swing_opened_at=utc(reference.opened_at).isoformat()
            if reference is not None else None,
            displacement_closed_at=utc(displacement.closed_at).isoformat()
            if displacement is not None else None,
            candidate_unique=geometry == CANDIDATE,
            geometry_state=geometry,
        )

    if not isinstance(session, SessionId) or not isinstance(side, Side):
        return emit(REJECT, "M5_SESSION_OR_DIRECTION_UNTYPED")
    expected = PROFILE if session is SessionId.NY_AM else ICT_GENERAL
    if profile != expected:
        return emit(REJECT, "M5_METHODOLOGY_PROFILE_CROSSED")
    if not isinstance(closed_m1, tuple) or len(closed_m1) < 4 or any(
        not isinstance(row, M1Bar) for row in closed_m1
    ):
        return emit(REJECT, "M5_CLOSED_M1_TYPED_TUPLE_REQUIRED")
    try:
        at = utc(as_of)
        starts = tuple(utc(b.opened_at) for b in closed_m1)
        ends = tuple(utc(b.closed_at) for b in closed_m1)
        first, last = window_bounds(at, session)
    except (TypeError, ValueError):
        return emit(REJECT, "M5_TIME_OR_WINDOW_INVALID")
    if at != ends[-1] or any(
        ends[i] != starts[i + 1] for i in range(len(closed_m1) - 1)
    ):
        return emit(REJECT, "M5_TAPE_ASOF_GAP_OR_FUTURE")
    if (
        type(displacement_index) is not int
        or type(candidate_swing_index) is not int
        or not (0 <= candidate_swing_index < displacement_index < len(closed_m1))
    ):
        return emit(REJECT, "M5_SWING_OR_DISPLACEMENT_FUTURE_OR_UNTYPED")
    displacement = closed_m1[displacement_index]
    if not (
        first <= starts[displacement_index] < ends[displacement_index] <= last
        and first < at <= last
    ):
        return emit(REJECT, "M5_DISPLACEMENT_NOT_CLOSED_IN_SOURCE_SESSION")
    if not (
        displacement.close > displacement.open
        if side is Side.LONG else displacement.close < displacement.open
    ):
        return emit(WAIT, "M5_DIRECTIONAL_DISPLACEMENT_CLOSE_NOT_EVEN_GEOMETRIC", at=at)

    if session is SessionId.NY_AM:
        if not isinstance(nyam_actor, VT31TwoPhaseCognitiveCandidate):
            return emit(WAIT, "M5_NYAM_COG_V4_NOT_PROVIDED", at=at)
        ctx, seal = nyam_actor.context, nyam_actor.seal
        if ctx is None or seal is None:
            return emit(WAIT, "M5_NYAM_M0_SOURCE_TOKEN_NOT_COMMITTED", at=at)
        if (
            ctx.session is not session
            or ctx.side != side.value
            or ctx.ny_date != at.astimezone(
                __import__("zoneinfo").ZoneInfo("America/New_York")
            ).date().isoformat()
        ):
            return emit(REJECT, "M5_NYAM_SOURCE_SESSION_SIDE_OR_DATE_CONFLICT", at=at)
        if (
            at != seal.last_as_of or len(closed_m1) != seal.count
            or tape_sha256(closed_m1) != seal.sha256_total
        ):
            return emit(REJECT, "M5_NYAM_FULL_M1_SOURCE_SEAL_FORK", at=at)
        if ends[displacement_index] <= ctx.returned_at:
            return emit(REJECT, "M5_DISPLACEMENT_BEFORE_CONTEXT_RETURN", at=at)
        anchor_start = next(
            (i for i, t in enumerate(starts) if t >= ctx.at), len(closed_m1),
        )
    else:
        if nyam_actor is not None or not isinstance(ict_setup, dict):
            return emit(REJECT, "M5_ICT_CONTEXT_REQUIRES_INDEPENDENT_RECHECK", at=at)
        keys = {
            "target_level", "target_observed_at", "swing_index",
            "mss_confirm_index", "fvg_first_index",
        }
        if set(ict_setup) != keys:
            return emit(REJECT, "M5_ICT_CONTEXT_FIELDS_NOT_EXACT", at=at)
        prior = ict2023_london_pm_source_witness(
            profile=ICT_GENERAL, session=session, side=side,
            closed_m1=closed_m1, as_of=at, **ict_setup,
        )
        if prior.action == REJECT:
            return emit(REJECT, "M5_ICT2023_RECHECK_REJECTED", at=at)
        if prior.geometry_state != WITNESS:
            return emit(WAIT, "M5_ICT2023_CONTEXT_NOT_GEOMETRICALLY_OBSERVED", at=at)
        if displacement_index != ict_setup["mss_confirm_index"]:
            return emit(REJECT, "M5_DISPLACEMENT_NOT_SAME_ICT_MSS_EVENT", at=at)
        anchor_start = next(
            (i for i, t in enumerate(starts) if t >= first), len(closed_m1),
        )

    if not (anchor_start <= candidate_swing_index < displacement_index):
        return emit(REJECT, "M5_SWING_NOT_IN_CAUSAL_SOURCE_INTERVAL", at=at)
    series = closed_m1[anchor_start:displacement_index]
    if len(series) < 2:
        return emit(WAIT, "M5_NOT_ENOUGH_PRIOR_CLOSED_M1_TO_COMPARE", at=at)
    if side is Side.LONG:
        extreme = min(b.low for b in series)
        extremes = [
            i for i in range(anchor_start, displacement_index)
            if closed_m1[i].low == extreme
        ]
    else:
        extreme = max(b.high for b in series)
        extremes = [
            i for i in range(anchor_start, displacement_index)
            if closed_m1[i].high == extreme
        ]
    if len(extremes) != 1:
        return emit(WAIT, "M5_PRE_DISPLACEMENT_EXTREMA_TIED_CAUSE_UNKNOWN", at=at)
    if candidate_swing_index != extremes[0]:
        return emit(REJECT, "M5_PROPOSED_SWING_IS_NOT_SOURCE_EXTREME", at=at)
    if any(
        (row.low < extreme if side is Side.LONG else row.high > extreme)
        for row in closed_m1[displacement_index + 1:]
    ):
        return emit(REJECT, "M5_SOURCE_EXTREME_ALREADY_INVALIDATED", at=at)
    reference = closed_m1[candidate_swing_index]
    return emit(
        WAIT, "M5_GEOMETRIC_PRECEDENCE_ONLY_CAUSAL_SWING_AUTHOR_UNVERIFIED",
        at=at, geometry=CANDIDATE, reference=reference,
        extreme=extreme, displacement=displacement,
    )


def synthetic_m5_case(
    *, session: SessionId, side: Side, month: int,
) -> tuple[dict[str, Any], M5SourceVerdict]:
    """12 cross-session examples; synthetic only, NEVER original author charts."""
    if session is SessionId.NY_AM:
        hist, at = ttrades_fixture(side=side, month=month, min10_valid=True)
        tail = (
            (
                ("103", "104", "100", "101"),
                ("101", "109", "99", "106"),
                ("104", "106", "102", "105"),
                ("102", "104", "99", "102"),
            ) if side is Side.LONG else (
                ("101", "104", "100", "103"),
                ("103", "105", "95", "97"),
                ("100", "102", "98", "99"),
                ("102", "104", "100", "101"),
            )
        )
        extension = []
        for i, (o, h, lo, cl) in enumerate(tail):
            extension.append(M1Bar(
                opened_at=at + timedelta(minutes=i),
                closed_at=at + timedelta(minutes=i+1),
                open=Decimal(o), high=Decimal(h),
                low=Decimal(lo), close=Decimal(cl),
            ))
        tape = hist + tuple(extension)
        actor = VT31TwoPhaseCognitiveCandidate()
        m0 = actor.capture_context(
            session=session, closed_m1=hist, as_of=at,
        )
        if m0.action != WAIT or not m0.committed:
            raise ValueError("M5_SYNTHETIC_NYAM_M0_NOT_COMMITTED")
        later = actor.assess_later_retest(
            session=session, closed_m1=tape, as_of=tape[-1].closed_at,
        )
        if later.action != WAIT or not later.committed:
            raise ValueError(f"M5_SYNTHETIC_NYAM_V4_NO_CONTEXT:{later.reason}")
        kwargs: dict[str, Any] = {
            "session": session, "profile": PROFILE, "side": side,
            "closed_m1": tape, "as_of": tape[-1].closed_at,
            "displacement_index": len(hist) + 2,
            "candidate_swing_index": len(hist) + 1,
            "nyam_actor": actor,
        }
    else:
        original, initial = synthetic_london_pm_case(
            session=session, side=side, month=month, sufficient=True,
        )
        if initial.geometry_state != WITNESS:
            raise ValueError("M5_ICT_SYNTHETIC_CONTEXT_NOT_GEOMETRIC")
        kwargs = {
            "session": session, "profile": ICT_GENERAL, "side": side,
            "closed_m1": original["closed_m1"], "as_of": original["as_of"],
            "displacement_index": original["mss_confirm_index"],
            "candidate_swing_index": 0,
            "ict_setup": {
                k: original[k] for k in (
                    "target_level", "target_observed_at", "swing_index",
                    "mss_confirm_index", "fvg_first_index",
                )
            },
        }
    return kwargs, adjudicate_m5_swing_reference(**kwargs)


def m5_three_session_court() -> dict[str, Any]:
    rows = []
    for month in (1, 7):
        for session in (SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM):
            for side in (Side.LONG, Side.SHORT):
                _, verdict = synthetic_m5_case(session=session, side=side, month=month)
                if verdict.action != WAIT or verdict.geometry_state != CANDIDATE:
                    raise ValueError(f"M5_METHODOLOGY_GEOMETRY_REGRESSION:{verdict}")
                rows.append({
                    "case": f"{session.value}_{side.value}_{month}",
                    **verdict.record(),
                })
    return {
        "title": VERSION, "prereg_commit": PREREG,
        "source_primary_ttrades": "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/",
        "source_primary_ict": "https://www.youtube.com/watch?v=tRq1hyGGtl4",
        "source_protected_swing": "https://ttrades.com/protected-swings-understanding-trends-and-invalidations/",
        "source_10handle_interpretation_disputed": True,
        "synthetic_m1_not_real_market_or_author_charts": True,
        "cases": rows, "three_sessions_covered_in_research": True,
        "causing_swing_author_certified": False,
        "stop_tick_price_certified": False,
        "m5_methodology_certified": False, "cognition_certified": False,
        "owner_m0_signed": False, "human_cog_ops_signed": False,
        "native_g3_connected": False, "broker_orders": 0,
        "sizing": 0, "live": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    path = parser.parse_args().out
    report = m5_three_session_court()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "cases": len(report["cases"]),
        "candidate_extrema": sum(r["candidate_unique"] for r in report["cases"]),
        "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
