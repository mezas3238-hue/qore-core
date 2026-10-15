#!/usr/bin/env python3
"""VT31 pre-decision immutable M0 method identity router, RESEARCH ONLY.

Not integrated into protected original G3/OPS. One VT31, explicit source
identity before M1 data, source-first TTrades NY AM, ICT GENERAL underdetermined.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    M1Bar,
    SessionId,
    Side,
    utc,
)
from scripts.vt31_cog_evidence_v2_20261014 import (
    ICT_GENERAL,
    TTRADES_AM,
)
from scripts.vt31_m0_profile_shadow_attestation_20261015 import (
    classify_source_profile,
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
    MIN10_CONFLICT,
    SUCCESS,
    ttrades_fixture,
    ttrades_source_first_g3_cognitive_proposal,
)

PREREG = "05e55b7528636ea60168d69a97b03559fae2f0dd"
POLICY_ID = "VT31_M0_RESEARCH_PRESELECTED_METHOD_IDENTITY_V1_NOT_SIGNED"
PRE_EFFECTIVE = datetime(2025, 12, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class FrozenMethodProfilePolicy:
    policy_id: str
    effective_at: datetime
    ordered_session_map: tuple[tuple[SessionId, str], ...]

    def __post_init__(self) -> None:
        if self.policy_id != POLICY_ID:
            raise ValueError("UNAUTHORIZED_OR_UNVERSIONED_METHOD_POLICY")
        if utc(self.effective_at) != PRE_EFFECTIVE:
            raise ValueError("METHOD_POLICY_EFFECTIVE_TIME_NOT_PREREGISTERED")
        if (
            len(self.ordered_session_map) != 3
            or tuple(key for key, _ in self.ordered_session_map) != (
                SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM
            )
            or tuple(profile for _, profile in self.ordered_session_map)
            != (ICT_GENERAL, TTRADES_AM, ICT_GENERAL)
        ):
            raise ValueError("METHOD_PROFILE_MATRIX_NOT_PREREGISTERED")

    def profile_for(self, session: SessionId) -> str:
        if not isinstance(session, SessionId):
            raise ValueError("SESSION_UNKNOWN_OR_NOT_TYPED")
        for key, profile in self.ordered_session_map:
            if key == session:
                return profile
        raise ValueError("SOURCE_SESSION_MISSING_FROM_POLICY")


PREDECLARED = FrozenMethodProfilePolicy(
    policy_id=POLICY_ID,
    effective_at=PRE_EFFECTIVE,
    ordered_session_map=(
        (SessionId.LONDON, ICT_GENERAL),
        (SessionId.NY_AM, TTRADES_AM),
        (SessionId.NY_PM, ICT_GENERAL),
    ),
)


@dataclass(frozen=True, slots=True)
class ResearchProfileRouteVerdict:
    session: str
    selected_profile_before_ingress: str
    as_of: str
    policy_id: str
    policy_effective_at: str
    state: str
    reasons: tuple[str, ...]
    original_cog_invoked: bool
    original_cog_side: str | None
    original_cog_dol: str | None
    ttrades_9h_author_dol: str | None
    independent_source_v2_state: str | None
    research_proposal_dto_only: bool
    native_g3_production_integrated: bool = False
    policy_owner_signed: bool = False
    author_method_certified: bool = False
    cognition_certified: bool = False
    independent_cog_ops_roles_signed: bool = False
    oms_or_live_authorized: bool = False

    def record(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "selected_profile_before_ingress": self.selected_profile_before_ingress,
            "as_of": self.as_of,
            "policy_id": self.policy_id,
            "policy_effective_at": self.policy_effective_at,
            "state": self.state,
            "reasons": list(self.reasons),
            "original_cog_invoked": self.original_cog_invoked,
            "original_cog_side": self.original_cog_side,
            "original_cog_dol": self.original_cog_dol,
            "ttrades_9h_author_dol": self.ttrades_9h_author_dol,
            "independent_source_v2_state": self.independent_source_v2_state,
            "research_proposal_dto_only": self.research_proposal_dto_only,
            "native_g3_production_integrated": False,
            "policy_owner_signed": False,
            "author_method_certified": False,
            "cognition_certified": False,
            "independent_cog_ops_roles_signed": False,
            "oms_or_live_authorized": False,
        }


def route_preselected_method(
    *, policy: FrozenMethodProfilePolicy,
    session: SessionId,
    closed_m1: tuple[M1Bar, ...],
    as_of: datetime,
) -> ResearchProfileRouteVerdict:
    """Select RESEARCH method before feeding actual original G3, fail closed."""
    if not isinstance(policy, FrozenMethodProfilePolicy):
        raise ValueError("M0_EXPLICIT_IMMUTABLE_PROFILE_POLICY_REQUIRED")
    selected = policy.profile_for(session)
    if not closed_m1:
        raise ValueError("M1_CAUSAL_SOURCE_REQUIRED")
    at = utc(as_of)
    if (
        policy.effective_at >= utc(closed_m1[0].opened_at)
        or at != utc(closed_m1[-1].closed_at)
        or any(utc(bar.closed_at) > at for bar in closed_m1)
        or any(
            utc(a.opened_at) >= utc(z.opened_at)
            or utc(a.closed_at) > utc(z.opened_at)
            for a, z in zip(closed_m1, closed_m1[1:], strict=False)
        )
    ):
        raise ValueError("M0_POLICY_OR_M1_INGRESS_ASOF_CAUSALITY_VIOLATION")

    def emit(
        state: str, reasons: tuple[str, ...],
        *, side: str | None = None,
        original_dol: str | None = None,
        author_dol: str | None = None,
        v2: str | None = None,
        proposed: bool = False,
        cog_invoked: bool = True,
    ) -> ResearchProfileRouteVerdict:
        return ResearchProfileRouteVerdict(
            session=session.value,
            selected_profile_before_ingress=selected,
            as_of=at.isoformat(),
            policy_id=policy.policy_id,
            policy_effective_at=utc(policy.effective_at).isoformat(),
            state=state, reasons=reasons,
            original_cog_invoked=cog_invoked,
            original_cog_side=side,
            original_cog_dol=original_dol,
            ttrades_9h_author_dol=author_dol,
            independent_source_v2_state=v2,
            research_proposal_dto_only=proposed,
        )

    if selected == TTRADES_AM:
        source = ttrades_source_first_g3_cognitive_proposal(
            profile=selected, session=session, as_of=at,
            closed_m1=closed_m1,
        )
        return emit(
            source.status, source.reason_codes,
            side=source.original_mss_side,
            original_dol=(
                str(source.original_cog_dol)
                if source.original_cog_dol is not None else None
            ),
            author_dol=(
                str(source.source_opposite_h1_dol)
                if source.source_opposite_h1_dol is not None else None
            ),
            v2=source.independent_v2_state,
            proposed=source.proposed is not None,
            cog_invoked=source.original_cog_invoked,
        )
    if selected != ICT_GENERAL:
        raise ValueError("UNKNOWN_METHOD_SOURCE_DOCTRINE")
    engine = VT31CleanroomCognition(
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    for bar in closed_m1:
        engine.observe_closed_m1(bar)
    assessment = engine.assess(session=session, as_of=at)
    witness = classify_source_profile(
        selected_profile=selected, session=session,
        as_of=at, closed_m1=closed_m1,
        assessment=assessment,
    )
    dto = assessment.decision
    if witness.state != "ICT_CONTEXT_WITNESS_UNDERDETERMINED":
        return emit(
            witness.state, witness.reasons,
            side=dto.side.value if dto else None,
            original_dol=str(dto.draw_target) if dto else None,
            v2=witness.independent_v2_state,
        )
    return emit(
        witness.state, witness.reasons,
        side=dto.side.value if dto else None,
        original_dol=str(dto.draw_target) if dto else None,
        v2=witness.independent_v2_state,
    )


def source_identity_court() -> dict[str, Any]:
    cases = []
    for month in (1, 7):
        for side in (Side.LONG, Side.SHORT):
            for compatible in (False, True):
                history, at = ttrades_fixture(
                    side=side, month=month, min10_valid=compatible,
                )
                verdict = route_preselected_method(
                    policy=PREDECLARED, session=SessionId.NY_AM,
                    closed_m1=history, as_of=at,
                )
                expected = SUCCESS if compatible else MIN10_CONFLICT
                if (
                    verdict.state != expected
                    or verdict.original_cog_side != side.value
                    or verdict.research_proposal_dto_only != compatible
                ):
                    raise ValueError(
                        f"M0_TTRADES_PRECOMMITTED_ROUTING_FAILED:"
                        f"{month}:{side.value}:{compatible}:{verdict.record()}"
                    )
                cases.append({
                    "case": f"TTRADES_NY_AM_{side.value}_{month}_"
                            f"{'COMPATIBLE' if compatible else 'MIN10_WAIT'}",
                    **verdict.record(),
                })
        for session in (SessionId.LONDON, SessionId.NY_PM):
            for side in (Side.LONG, Side.SHORT):
                shorts, at = short_fixture(session=session, month=month)
                history = (
                    mirror_long_history(shorts) if side is Side.LONG else shorts
                )
                verdict = route_preselected_method(
                    policy=PREDECLARED, session=session,
                    closed_m1=history, as_of=at,
                )
                if (
                    verdict.state != "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
                    or verdict.original_cog_side != side.value
                    or verdict.research_proposal_dto_only
                ):
                    raise ValueError(
                        f"M0_ICT_ORIGINAL_COG_SOURCE_NOT_UNKNOWN:"
                        f"{session.value}:{side.value}:{month}:{verdict.record()}"
                    )
                cases.append({
                    "case": f"ICT_GENERAL_{session.value}_{side.value}_{month}",
                    **verdict.record(),
                })

    if len(cases) != 16:
        raise ValueError("M0_16_PREREGISTERED_SCENARIOS_REQUIRED")
    return {
        "title": "VT31_M0_ONE_TRADER_CAUSAL_PREDECISION_RESEARCH_PROFILE_ROUTER",
        "prereg_commit": PREREG,
        "profile_policy": {
            "policy_id": PREDECLARED.policy_id,
            "effective_at": PRE_EFFECTIVE.isoformat(),
            "session_map": {s.value: p for s, p in PREDECLARED.ordered_session_map},
        },
        "source_g3_original_sha": source_fingerprint(),
        "cases": cases,
        "single_vt31_method_profile_preselected_before_M1": True,
        "research_only_not_connected_to_original_ops": True,
        "owner_policy_approved": False,
        "ict_original_author_case_certified": False,
        "ttrades_all_four_entries_certified": False,
        "native_g3_profile_selector_integrated": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "dual_cog_ops_human_signatures": False,
        "historical_real_data_or_PNL": None,
        "orders": 0,
        "sizing": 0,
        "live": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    out = p.parse_args().out
    d = source_identity_court()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "cases": len(d["cases"]),
        "states": {state: sum(c["state"] == state for c in d["cases"])
                   for state in sorted({c["state"] for c in d["cases"]})},
        "methodology_certified": False, "cognition_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
