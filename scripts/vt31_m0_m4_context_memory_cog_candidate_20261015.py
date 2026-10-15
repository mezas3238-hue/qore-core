#!/usr/bin/env python3
"""One VT31 M0-to-later-M4 source-bound cognitive candidate, RESEARCH ONLY.

One remembered source context; no operational CognitiveDecision or orders.
Neither protected original G3 COG/OPS nor existing M0/M4 gates are modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    NEW_YORK,
    SessionId,
    Side,
    utc,
)
from scripts.vt31_m0_predecision_method_router_20261015 import PREDECLARED
from scripts.vt31_m0_temporal_admission_20261015 import (
    ADMITTED,
    H1_WAIT,
    guarded_method_route,
)
from scripts.vt31_m4_closed_m1_author_gate_20261015 import (
    OBSERVED,
    adjudicate_closed_m1_retest,
)
from scripts.vt31_m4_closed_m1_author_gate_20261015 import REJECTED as M4_REJECTED
from scripts.vt31_m4_ob_breaker_author_evidence_gate_20261015 import (
    PROFILE,
    Candle,
    Swing,
)
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    native_ttrades_am_context,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    SUCCESS,
    ttrades_fixture,
)

PREREG = "d23ff760e3d8e66adec35f99d4743e4c232a0d0f"
VERSION = "VT31_M0_M4_RESEARCH_CONTEXT_MEMORY_COG_V2_NO_ORDERS"
WAIT = "WAIT"
REJECT = "REJECT"


def tape_sha256(rows: tuple[M1Bar, ...]) -> str:
    """Deterministic evidence-prefix fingerprint incl UTC timestamps + OHLC."""
    payload = [
        [utc(b.opened_at).isoformat(), utc(b.closed_at).isoformat(),
         str(b.open), str(b.high), str(b.low), str(b.close)]
        for b in rows
    ]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceContext:
    session: SessionId
    side: str
    at: datetime
    ny_date: str
    prefix_count: int
    prefix_sha256: str
    first_raid_at: datetime
    returned_at: datetime
    profile_id: str


@dataclass(frozen=True, slots=True)
class CandidateVerdict:
    action: str
    reason: str
    session: str
    side_context: str | None = None
    m0_source_status: str | None = None
    m4_source_status: str | None = None
    evidence_prefix_sha256: str | None = None
    source_context_remembered: bool = False
    original_cog_claim_from_m0: bool = False
    m4_judge_invoked: bool = False
    original_g3_cog_modified: bool = False
    native_cog_prod_integrated: bool = False
    methodology_certified: bool = False
    cognition_certified: bool = False
    operations_authorized: bool = False
    trader_sizing: int = 0
    broker_orders: int = 0

    def record(self) -> dict[str, Any]:
        return {
            "version": VERSION, "action": self.action, "reason": self.reason,
            "session": self.session, "side_context": self.side_context,
            "m0_source_status": self.m0_source_status,
            "m4_source_status": self.m4_source_status,
            "evidence_prefix_sha256": self.evidence_prefix_sha256,
            "source_context_remembered": self.source_context_remembered,
            "original_cog_claim_from_m0": self.original_cog_claim_from_m0,
            "m4_judge_invoked": self.m4_judge_invoked,
            "original_g3_cog_modified": False,
            "native_cog_prod_integrated": False,
            "methodology_certified": False, "cognition_certified": False,
            "operations_authorized": False,
            "trader_sizing": 0, "broker_orders": 0,
        }


def _native_source(rows: tuple[M1Bar, ...], at: datetime):
    day = at.astimezone(NEW_YORK).date()
    nine = tuple(
        b for b in rows
        if b.opened_at.astimezone(NEW_YORK).date() == day
        and b.opened_at.astimezone(NEW_YORK).hour == 9
    )
    ten = tuple(
        b for b in rows
        if b.opened_at.astimezone(NEW_YORK).date() == day
        and b.opened_at.astimezone(NEW_YORK).hour == 10
    )
    return native_ttrades_am_context(as_of=at, nine=nine, ten=ten)


def _closed_source_prefix(rows: tuple[M1Bar, ...], at: datetime) -> bool:
    if not isinstance(rows, tuple) or not rows:
        return False
    if any(not isinstance(b, M1Bar) for b in rows):
        return False
    try:
        if utc(rows[-1].closed_at) != at:
            return False
        if any(
            utc(a.closed_at) > utc(b.opened_at)
            or utc(a.opened_at) >= utc(b.opened_at)
            for a, b in zip(rows, rows[1:], strict=False)
        ):
            return False
        day = at.astimezone(NEW_YORK).date()
        ten_start = utc(datetime.combine(day, time(10), tzinfo=NEW_YORK))
        latest_open = utc(rows[-1].opened_at)
        if latest_open < ten_start:
            return False
        ten = [
            utc(b.opened_at) for b in rows
            if ten_start <= utc(b.opened_at) <= latest_open
        ]
        return ten == [
            ten_start + timedelta(minutes=i)
            for i in range(int((latest_open - ten_start) / timedelta(minutes=1)) + 1)
        ]
    except (TypeError, ValueError):
        return False


def _matches_tape(c: Candle, by_open: dict[datetime, M1Bar]) -> bool:
    try:
        row = by_open.get(utc(c.at))
    except (TypeError, ValueError):
        return False
    return row is not None and (
        row.open, row.high, row.low, row.close
    ) == (c.open, c.high, c.low, c.close)


class VT31M0M4CognitiveCandidate:
    """Stateful ONE-trader read-only research actor; not OMS integration."""

    def __init__(self) -> None:
        self._source: SourceContext | None = None
        self._last_assessed: datetime | None = None

    @property
    def context(self) -> SourceContext | None:
        return self._source

    def _out(
        self, action: str, reason: str, session: SessionId | object,
        *, m0: str | None = None, m4: str | None = None,
        judge_called: bool = False, original_cog: bool = False,
    ) -> CandidateVerdict:
        source = self._source
        return CandidateVerdict(
            action=action, reason=reason,
            session=session.value if isinstance(session, SessionId) else "INVALID",
            side_context=source.side if source is not None else None,
            m0_source_status=m0, m4_source_status=m4,
            evidence_prefix_sha256=source.prefix_sha256 if source else None,
            source_context_remembered=source is not None,
            original_cog_claim_from_m0=original_cog,
            m4_judge_invoked=judge_called,
        )

    def capture_context(
        self, *, session: SessionId, closed_m1: tuple[M1Bar, ...],
        as_of: datetime,
    ) -> CandidateVerdict:
        if self._source is not None:
            return self._out(REJECT, "M0_CONTEXT_ALREADY_FROZEN", session)
        admission = guarded_method_route(
            policy=PREDECLARED, session=session, closed_m1=closed_m1,
            as_of=as_of,
        )
        if admission.state != ADMITTED:
            return self._out(
                WAIT if admission.state == H1_WAIT else REJECT,
                admission.reason, session, m0=admission.state,
            )
        state = admission.research_source_state
        invoked = admission.original_cog_claim_from_router is True
        if (
            session is not SessionId.NY_AM
            or state != SUCCESS or not invoked
        ):
            return self._out(
                WAIT, "M0_METHOD_OR_MIN10_SOURCE_NOT_ELIGIBLE_FOR_M4",
                session, m0=state, original_cog=invoked,
            )
        at = utc(as_of)
        if not _closed_source_prefix(closed_m1, at):
            return self._out(REJECT, "M0_CLOSED_10H_PREFIX_INVALID", session)
        native = _native_source(closed_m1, at)
        if (
            native.state != "RETURN_INSIDE_OBSERVED"
            or native.return_inside_at != at
            or native.first_sweep_at is None
            or native.candidate_side != admission.research_source_side
            or native.candidate_side not in (Side.LONG.value, Side.SHORT.value)
        ):
            return self._out(REJECT, "M0_NATIVE_CONTEXT_NOT_CAUSALLY_ATTESTED", session)
        self._source = SourceContext(
            session=session, side=native.candidate_side, at=at,
            ny_date=str(at.astimezone(NEW_YORK).date()),
            prefix_count=len(closed_m1),
            prefix_sha256=tape_sha256(closed_m1),
            first_raid_at=utc(native.first_sweep_at),
            returned_at=utc(native.return_inside_at),
            profile_id=PROFILE,
        )
        self._last_assessed = at
        return self._out(
            WAIT, "M0_SOURCE_CONTEXT_REMEMBERED_M4_NOT_YET_PROVEN",
            session, m0=state, original_cog=True,
        )

    def assess_later_retest(
        self, *, session: SessionId, closed_m1: tuple[M1Bar, ...],
        as_of: datetime, family_evidence: dict[str, Any] | None = None,
    ) -> CandidateVerdict:
        ctx = self._source
        if ctx is None:
            return self._out(WAIT, "M0_SOURCE_CONTEXT_NOT_REMEMBERED", session)
        if session is not ctx.session or session is not SessionId.NY_AM:
            return self._out(REJECT, "SOURCE_SESSION_CHANGED_AFTER_M0", session)
        try:
            at = utc(as_of)
        except (TypeError, ValueError):
            return self._out(REJECT, "RETEST_ASOF_NOT_UTC_AWARE", session)
        if (
            self._last_assessed is None
            or at <= self._last_assessed
            or at.astimezone(NEW_YORK).date().isoformat() != ctx.ny_date
            or at.astimezone(NEW_YORK).hour not in (10, 11)
            or (at.astimezone(NEW_YORK).hour == 11
                and at.astimezone(NEW_YORK).minute != 0)
        ):
            return self._out(REJECT, "RETEST_TIME_NOT_STRICT_NYAM_PROGRESS", session)
        if (
            not _closed_source_prefix(closed_m1, at)
            or len(closed_m1) <= ctx.prefix_count
            or tape_sha256(closed_m1[:ctx.prefix_count]) != ctx.prefix_sha256
        ):
            return self._out(REJECT, "SOURCE_M1_PREFIX_FORK_OR_GAP", session)
        native = _native_source(closed_m1, at)
        if (
            native.state != "RETURN_INSIDE_OBSERVED"
            or native.first_sweep_at != ctx.first_raid_at
            or native.return_inside_at != ctx.returned_at
            or native.candidate_side != ctx.side
        ):
            return self._out(REJECT, "FIRST_RAID_RETURN_OR_SOURCE_THESIS_INVALIDATED", session)
        self._last_assessed = at
        if family_evidence is None:
            return self._out(WAIT, "M4_FAMILY_EVIDENCE_NOT_PROVEN", session)
        if not isinstance(family_evidence, dict):
            return self._out(REJECT, "M4_EVIDENCE_MUST_BE_EXPLICIT_MAPPING", session)
        args = dict(family_evidence)
        valid_keys = {
            "family", "profile", "side", "as_of", "first_raid_at",
            "displacement_at", "retest", "opposing_candles", "zone_candles",
            "swing_legs", "confluence_level", "confluence_confirmed_at",
            "intrabar_stop_target_ambiguous",
        }
        if not {"family", "profile", "side", "as_of", "first_raid_at",
                "displacement_at", "retest"} <= args.keys() or set(args) - valid_keys:
            return self._out(REJECT, "M4_EVIDENCE_FIELDS_NOT_VERSIONED", session)
        if (
            args["profile"] != ctx.profile_id or args["side"] != ctx.side
            or not isinstance(args["retest"], Candle)
        ):
            return self._out(REJECT, "M4_PROFILE_SIDE_OR_RETEST_MISMATCH", session)
        try:
            if (
                utc(args["as_of"]) != at
                or utc(args["first_raid_at"]) != ctx.first_raid_at
                or utc(args["displacement_at"]) < ctx.returned_at
            ):
                return self._out(REJECT, "M4_RETROACTIVE_RAID_DISPLACEMENT_OR_ASOF", session)
        except (ValueError, TypeError):
            return self._out(REJECT, "M4_TIMESTAMP_INVALID", session)
        by_open = {utc(b.opened_at): b for b in closed_m1}
        candidates = (
            (args["retest"],)
            + tuple(args.get("opposing_candles", ()))
            + tuple(args.get("zone_candles", ()))
        )
        if any(not isinstance(c, Candle) or not _matches_tape(c, by_open)
               for c in candidates):
            return self._out(REJECT, "M4_CANDLE_OHLC_NOT_IN_CLOSED_M1_TAPE", session)
        for swing in args.get("swing_legs", ()):
            if not isinstance(swing, Swing):
                return self._out(REJECT, "M4_UNTYPED_SWING", session)
            try:
                bar = by_open.get(utc(swing.extreme_at))
                known = utc(swing.confirmed_at) <= utc(args["retest"].at)
            except (TypeError, ValueError):
                return self._out(REJECT, "M4_SWING_TIMESTAMP_INVALID", session)
            if (
                bar is None or not known
                or (bar.low if swing.kind == "LOW" else
                    bar.high if swing.kind == "HIGH" else None) != swing.level
            ):
                return self._out(REJECT, "M4_SWING_NOT_VERIFIED_IN_CLOSED_M1_TAPE", session)
        verdict = adjudicate_closed_m1_retest(**args)
        if verdict.state == M4_REJECTED:
            return self._out(
                REJECT, "M4_CAUSAL_SOURCE_REJECTED", session,
                m4=verdict.reason, judge_called=True,
            )
        return self._out(
            WAIT,
            "M4_STRUCTURE_RESEARCH_ONLY_M3_M4_M5_AUTHOR_NOT_CERTIFIED"
            if verdict.state == OBSERVED else
            "M4_SOURCE_STRUCTURE_UNDERDETERMINED",
            session, m4=verdict.source_v1_status, judge_called=True,
        )


def qualitative_context_court() -> dict[str, Any]:
    rows = []
    for month in (1, 7):
        for side in (Side.LONG, Side.SHORT):
            for compatible in (False, True):
                bars, at = ttrades_fixture(
                    month=month, side=side, min10_valid=compatible,
                )
                actor = VT31M0M4CognitiveCandidate()
                initial = actor.capture_context(
                    session=SessionId.NY_AM, closed_m1=bars, as_of=at,
                )
                expected = compatible
                if (actor.context is not None) != expected:
                    raise ValueError("CONTEXT_CREATED_FROM_UNSUPPORTED_M0")
                rows.append({
                    "case": f"M0_{month}_{side.value}_{compatible}",
                    **initial.record(),
                })
    return {
        "version": VERSION, "prereg_commit": PREREG,
        "cases": rows, "original_g3_cog_untouched": True,
        "owner_method_policy_signed": False, "human_cog_ops_review": False,
        "author_m3_m4_m5_complete": False, "native_cog_production_integrated": False,
        "methodology_certified": False, "cognition_certified": False,
        "operations_authorized": False, "broker_orders": 0, "sizing": 0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    path = ap.parse_args().out
    d = qualitative_context_court()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "cases": len(d["cases"]), "contexts": sum(
            c["source_context_remembered"] for c in d["cases"]
        ), "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
