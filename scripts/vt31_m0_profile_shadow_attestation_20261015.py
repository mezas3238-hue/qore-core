#!/usr/bin/env python3
"""Read-only methodological PROFILE ATTRIBUTION of the ACTUAL VT31 G3 COG.

This is an independent research adjudicator, NOT the trader/OMS/CIBO. It
cannot convert an ICT-general decision into TTrades-certified cognition.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    CognitiveAssessment,
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    utc,
)
from scripts.vt31_cog_evidence_v2_20261014 import (
    ICT_GENERAL,
    TTRADES_AM,
    inspect_cog_evidence,
)
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    native_ttrades_am_context,
)
from scripts.vt31_original_cog_nyam_ttrades_source_conflict_20261014 import (
    nyam_source_fixture,
)
from scripts.vt31_original_g3_cog_qualitative_court_20261014 import (
    london_fixture,
    source_fingerprint,
)

PREREG = "9ca7c4a4dd1aa3180788a682b174aee605a2eda4"
PROFILES = frozenset({ICT_GENERAL, TTRADES_AM})


@dataclass(frozen=True, slots=True)
class ProfileShadowVerdict:
    declared_profile: str
    session: str
    as_of: str
    state: str
    reasons: tuple[str, ...]
    observed_action: str
    observed_cog_source_family: str | None
    observed_dol: str | None
    independent_v2_state: str | None
    native_ttrades_source_state: str | None
    ttrades_opposite_h1_dol: str | None
    original_g3_cog_invoked: bool = True
    method_certified: bool = False
    cognition_certified: bool = False
    economic_gate_run: bool = False
    orders_or_sizing: int = 0
    live_authorized: bool = False

    def record(self) -> dict[str, Any]:
        return asdict(self)


def classify_source_profile(
    *, selected_profile: str, session: SessionId,
    as_of: datetime, closed_m1: tuple[M1Bar, ...],
    assessment: CognitiveAssessment,
) -> ProfileShadowVerdict:
    """Validate original COG output against a declared doctrine, fail closed.

    Assessment MUST come from original VT31CleanroomCognition.assess on the
    same M1 closed prefix. Only tests that actually run the producer can attest
    provenance; this pure shadow cannot confer trust on arbitrary DTOs.
    """
    if selected_profile not in PROFILES:
        raise ValueError("DECLARED_METHOD_PROFILE_UNKNOWN")
    if not isinstance(session, SessionId):
        raise ValueError("COGNITIVE_SESSION_NOT_TYPED")
    at = utc(as_of)
    dto = assessment.decision
    action = dto.side.value if dto is not None else "WAIT"
    source = dto.draw_family if dto is not None else None
    target = str(dto.draw_target) if dto is not None else None

    def emit(
        state: str, *reasons: str,
        v2: str | None = None,
        native: str | None = None,
        expected_dol: str | None = None,
    ) -> ProfileShadowVerdict:
        return ProfileShadowVerdict(
            selected_profile, session.value, at.isoformat(),
            state, tuple(reasons), action, source, target,
            v2, native, expected_dol,
        )

    if selected_profile == TTRADES_AM and session is not SessionId.NY_AM:
        return emit("PROFILE_SESSION_REJECTED", "TTRADES_ONLY_NY_AM")
    if (
        assessment.session is not session
        or utc(assessment.as_of) != at
        or not closed_m1
        or utc(closed_m1[-1].closed_at) != at
        or any(utc(x.closed_at) > at for x in closed_m1)
        or any(
            utc(a.opened_at) >= utc(b.opened_at)
            or utc(a.closed_at) > utc(b.opened_at)
            for a, b in zip(closed_m1, closed_m1[1:], strict=False)
        )
        or (dto is not None and (
            dto.session is not session or utc(dto.observed_at) != at
        ))
    ):
        return emit("INPUT_INVALID_REJECTED", "ASOF_OR_SESSION_OR_M1_SOURCE_MISMATCH")
    if dto is None:
        return emit("COG_ABSTAINED", *assessment.missing)

    v2 = inspect_cog_evidence(
        profile=selected_profile, session=session,
        as_of=at, history=closed_m1, cognition=dto,
    )
    if selected_profile == ICT_GENERAL:
        # This source evidence deliberately cannot assert that ICT original
        # mandates the same NYAM 09h H1 objective as TTrades.
        if v2.state == "REJECTED":
            return emit("ICT_CONTEXT_REJECTED", *v2.rejected, v2=v2.state)
        return emit(
            "ICT_CONTEXT_WITNESS_UNDERDETERMINED",
            *(v2.rejected + v2.unknown),
            v2=v2.state,
        )

    # TTrades is valid only for a separate, explicitly declared NY AM profile.
    # Independent source records, always restricted to closed M1 as_of.
    local = at.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
    same_day = tuple(
        x for x in closed_m1
        if utc(x.opened_at).astimezone(local.tzinfo).date() == local.date()
    )
    nine = tuple(
        x for x in same_day
        if utc(x.opened_at).astimezone(local.tzinfo).hour == 9
    )
    ten = tuple(
        x for x in same_day
        if utc(x.opened_at).astimezone(local.tzinfo).hour == 10
    )
    native = native_ttrades_am_context(as_of=at, nine=nine, ten=ten)
    expected = (
        str(native.opposite_h1_dol)
        if native.opposite_h1_dol is not None else None
    )
    if v2.state == "REJECTED" or native.state == "REJECTED":
        return emit(
            "TTRADES_PROFILE_SOURCE_REJECTED",
            *(v2.rejected + native.reasons),
            v2=v2.state, native=native.state, expected_dol=expected,
        )
    if v2.state == "UNKNOWN" or native.state != "RETURN_INSIDE_OBSERVED":
        return emit(
            "TTRADES_PROFILE_SOURCE_UNKNOWN",
            *(v2.unknown + native.reasons),
            v2=v2.state, native=native.state, expected_dol=expected,
        )
    return emit(
        "TTRADES_CONTEXT_MATCH_ONLY",
        "AUTHOR_SETUP_AND_COGNITIVE_CERTIFICATION_STILL_UNVERIFIED",
        v2=v2.state, native=native.state, expected_dol=expected,
    )


def original_cog_profile_dossier() -> dict[str, Any]:
    """Same immutable original assessment compared to two declarations."""
    original_ny, _, ten = nyam_source_fixture()
    at = ten[-1].closed_at
    cog = VT31CleanroomCognition()
    for m1 in original_ny:
        cog.observe_closed_m1(m1)
    ny = cog.assess(session=SessionId.NY_AM, as_of=at)
    if ny.decision is None:
        raise ValueError("PR950_ORIGINAL_NYAM_POSITIVE_MSS_WITNESS_MISSING")

    lsource, lat = london_fixture()
    london = VT31CleanroomCognition()
    for m1 in lsource:
        london.observe_closed_m1(m1)
    lon = london.assess(session=SessionId.LONDON, as_of=lat)
    if lon.decision is None:
        raise ValueError("PR948_ORIGINAL_LONDON_POSITIVE_MSS_WITNESS_MISSING")

    pairs = [
        ("NYAM_AS_TTRADES", TTRADES_AM, SessionId.NY_AM, at, original_ny, ny),
        ("NYAM_AS_ICT_GENERAL", ICT_GENERAL, SessionId.NY_AM, at, original_ny, ny),
        ("LONDON_AS_ICT_GENERAL", ICT_GENERAL, SessionId.LONDON, lat, lsource, lon),
        ("LONDON_AS_TTRADES", TTRADES_AM, SessionId.LONDON, lat, lsource, lon),
    ]
    cases = [
        {"case": name, **classify_source_profile(
            selected_profile=profile, session=session, as_of=stamp,
            closed_m1=stream, assessment=assessment,
        ).record()}
        for name, profile, session, stamp, stream, assessment in pairs
    ]
    states = [x["state"] for x in cases]
    expected = [
        "TTRADES_PROFILE_SOURCE_REJECTED",
        "ICT_CONTEXT_WITNESS_UNDERDETERMINED",
        "ICT_CONTEXT_WITNESS_UNDERDETERMINED",
        "PROFILE_SESSION_REJECTED",
    ]
    if states != expected:
        raise ValueError(f"METHODOLOGY_SHADOW_CASE_MISMATCH:{states!r}")
    if (
        cases[0]["observed_dol"] != "150"
        or cases[0]["ttrades_opposite_h1_dol"] != "110"
        or "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" not in cases[0]["reasons"]
    ):
        raise ValueError("TTRADES_NYAM_DOCTRINAL_DISAGREEMENT_DISAPPEARED")

    return {
        "title": "VT31_ORIGINAL_COG_PROFILE_SHADOW_CERTIFICATION_BOUNDARY",
        "prereg_commit": PREREG,
        "original_g3_cog_source_hash": source_fingerprint(),
        "original_g3_cog_directly_invoked": True,
        "cases": cases,
        "methodology_certified": False,
        "cognition_certified": False,
        "g3_independent_2_signatures_validated": False,
        "human_source_review_completed": False,
        "economic_gate_run": False,
        "profit_factor_drawdown_sharpe_sortino": None,
        "market_3y_replay_used": False,
        "broker_orders": 0,
        "trader_lot_sizing": 0,
        "live_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    options = p.parse_args()
    result = original_cog_profile_dossier()
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "cases": [(x["case"], x["state"]) for x in result["cases"]],
        "methodology_certified": result["methodology_certified"],
        "cognition_certified": result["cognition_certified"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
