#!/usr/bin/env python3
"""VT31 M0-A: pre-COG temporal admission, source-H1 completeness, RESEARCH ONLY.

This guard never authorizes a trade. It is deliberately separate from the
G3-protected COG/OPS and from the unsigned method profile policy in PR #971.
Pre-registration: docs/research/VT31_M0_TEMPORAL_ADMISSION_PREREG_2026-10-15.md
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    M1Bar,
    SessionId,
    Side,
    utc,
    window_bounds,
)
from scripts.vt31_m0_predecision_method_router_20261015 import (
    PREDECLARED,
    FrozenMethodProfilePolicy,
    route_preselected_method,
)
from scripts.vt31_original_cog_traderlab_32x_long_short_20261015 import (
    mirror_long_history,
)
from scripts.vt31_original_g3_cog_qualitative_court_20261014 import (
    source_fingerprint,
)
from scripts.vt31_original_g3_cog_short_sessions_qualitative_20261015 import (
    short_fixture,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    ttrades_fixture,
)

VERSION = "VT31_M0_PRECOG_TEMPORAL_H1_ADMISSION_RESEARCH_V1"
ADMITTED = "RESEARCH_CONTEXT_ADMITTED_NOT_CERTIFIED"
REJECTED = "PRECOG_TEMPORAL_REJECT"
H1_WAIT = "SOURCE_09H_INCOMPLETE_WAIT"


@dataclass(frozen=True, slots=True)
class TemporalAdmissionVerdict:
    state: str
    reason: str
    requested_session: str
    research_source_state: str | None = None
    research_source_side: str | None = None
    original_cog_claim_from_router: bool | None = None
    gate_did_invoke_router: bool = False
    methodology_certified: bool = False
    cognition_certified: bool = False
    orders_authorized: bool = False
    sizing_performed: bool = False

    def record(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "state": self.state,
            "reason": self.reason,
            "session": self.requested_session,
            "research_source_state": self.research_source_state,
            "research_source_side": self.research_source_side,
            "original_cog_claim_from_router": self.original_cog_claim_from_router,
            "gate_did_invoke_router": self.gate_did_invoke_router,
            "methodology_certified": False,
            "cognition_certified": False,
            "orders_authorized": False,
            "sizing_performed": False,
        }


def guarded_method_route(
    *,
    policy: FrozenMethodProfilePolicy,
    session: SessionId,
    closed_m1: tuple[M1Bar, ...],
    as_of: datetime,
) -> TemporalAdmissionVerdict:
    """Validate all available temporal evidence BEFORE calling original COG.

    Rejected input never reaches route_preselected_method. H1 missing returns
    WAIT without ever inferring a partial 09:00–10:00 NY source candle.
    """
    session_name = session.value if isinstance(session, SessionId) else "UNRECOGNIZED"

    def no_entry(state: str, reason: str) -> TemporalAdmissionVerdict:
        return TemporalAdmissionVerdict(
            state=state, reason=reason, requested_session=session_name,
        )

    if (
        not isinstance(policy, FrozenMethodProfilePolicy)
        or policy != PREDECLARED
    ):
        return no_entry(REJECTED, "UNSIGNED_OR_CHANGED_M0_PROFILE_POLICY")
    if not isinstance(session, SessionId):
        return no_entry(REJECTED, "UNTYPED_SESSION")
    if not isinstance(closed_m1, tuple) or not closed_m1:
        return no_entry(REJECTED, "M1_TUPLE_NONEMPTY_REQUIRED")
    if any(not isinstance(bar, M1Bar) for bar in closed_m1):
        return no_entry(REJECTED, "INVALID_M1_TYPE")

    try:
        at = utc(as_of)
        starts = [utc(bar.opened_at) for bar in closed_m1]
        ends = [utc(bar.closed_at) for bar in closed_m1]
    except (TypeError, ValueError):
        return no_entry(REJECTED, "NAIVE_OR_INVALID_SOURCE_TIMESTAMP")

    if ends[-1] != at:
        return no_entry(REJECTED, "ASOF_MUST_EQUAL_LAST_CLOSED_M1")
    if starts[0] <= utc(policy.effective_at):
        return no_entry(REJECTED, "SOURCE_BEFORE_POLICY_EFFECTIVE")
    if any(
        starts[i] >= starts[i + 1] or ends[i] > starts[i + 1]
        for i in range(len(starts) - 1)
    ):
        return no_entry(REJECTED, "M1_UNSORTED_DUPLICATE_OR_OVERLAP")
    if any(stamp > at for stamp in ends):
        return no_entry(REJECTED, "FUTURE_M1_NOT_ALLOWED")

    start, end = window_bounds(at, session)
    if not (start <= starts[-1] < end and ends[-1] <= end):
        return no_entry(REJECTED, "M1_LAST_BAR_OUTSIDE_DECLARED_NY_WINDOW")

    if session is SessionId.NY_AM:
        local_day = at.astimezone(NEW_YORK).date()
        h1_start = datetime.combine(local_day, time(9), tzinfo=NEW_YORK)
        h1_start_utc = utc(h1_start)
        expected = {
            h1_start_utc + timedelta(minutes=i) for i in range(60)
        }
        observed = [
            stamp for stamp in starts
            if h1_start_utc <= stamp < h1_start_utc + timedelta(hours=1)
        ]
        if len(observed) != 60 or set(observed) != expected:
            return no_entry(H1_WAIT, "CLOSED_NY_09H_SOURCE_REQUIRES_EXACT_60_M1")
        if max(
            ends[i] for i, stamp in enumerate(starts) if stamp in expected
        ) > start:
            return no_entry(H1_WAIT, "H1_09H_SOURCE_NOT_CLOSED_BY_NY_10H")

    verdict = route_preselected_method(
        policy=policy, session=session, closed_m1=closed_m1, as_of=at,
    )
    return TemporalAdmissionVerdict(
        state=ADMITTED,
        reason="TEMPORAL_SOURCE_ADMISSION_ONLY_NOT_METHOD_APPROVAL",
        requested_session=session.value,
        research_source_state=verdict.state,
        research_source_side=verdict.original_cog_side,
        original_cog_claim_from_router=verdict.original_cog_invoked,
        gate_did_invoke_router=True,
    )


def admission_court() -> dict[str, Any]:
    """The exact 16 preregistered regression scenarios; NOT live price data."""
    cases = []
    for month in (1, 7):
        for side in (Side.LONG, Side.SHORT):
            for compatible in (False, True):
                history, at = ttrades_fixture(
                    side=side, month=month, min10_valid=compatible,
                )
                result = guarded_method_route(
                    policy=PREDECLARED, session=SessionId.NY_AM,
                    closed_m1=history, as_of=at,
                )
                if result.state != ADMITTED:
                    raise ValueError("PR971_NYAM_REGRESSION_CHANGED")
                cases.append({
                    "case": f"NYAM_{month}_{side.value}_{compatible}",
                    **result.record(),
                })
        for session in (SessionId.LONDON, SessionId.NY_PM):
            for side in (Side.LONG, Side.SHORT):
                history, at = short_fixture(session=session, month=month)
                if side is Side.LONG:
                    history = mirror_long_history(history)
                result = guarded_method_route(
                    policy=PREDECLARED, session=session,
                    closed_m1=history, as_of=at,
                )
                if result.state != ADMITTED:
                    raise ValueError("PR971_ICT_RESEARCH_REGRESSION_CHANGED")
                cases.append({
                    "case": f"{session.value}_{month}_{side.value}",
                    **result.record(),
                })
    if len(cases) != 16:
        raise ValueError("PREREG_16_CONTEXTS_REQUIRED")
    return {
        "title": VERSION,
        "source_g3_original_sha": source_fingerprint(),
        "profile": PREDECLARED.policy_id,
        "cases": cases,
        "temporal_admission_does_not_certify_author_source": True,
        "original_g3_unchanged": True,
        "policy_owner_signed": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "two_independent_human_reviews": False,
        "broker_orders": 0,
        "sizing": 0,
        "live": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    path = parser.parse_args().out
    result = admission_court()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "cases": len(result["cases"]),
        "states": sorted({
            x["research_source_state"] for x in result["cases"]
        }),
        "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
