#!/usr/bin/env python3
"""VT31 M0 method/cognition source identity: selected BEFORE NY session.

Never route research DTO into OPS or change stop/sizing. The TTrades
adapter invokes genuine G3 COG with H1 09 source-first V2 attestation.
ICT_GENERAL and QORE_G3 share frozen original G3 implementation but
MUST NOT share an authorial TTrades claim.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    NEW_YORK,
    M1Bar,
    SessionId,
    Side,
    utc,
    window_bounds,
)
from scripts.vt31_cog_evidence_v2_20261014 import TTRADES_AM
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    MIN10_CONFLICT,
    SUCCESS,
    ttrades_fixture,
    ttrades_source_first_g3_cognitive_proposal,
)

PREREG = "e5aa05d533a46a6ecf88f3a20bbbd8b0a746fb98"
ICT = "ICT_GENERAL_2023"
QORE = "QORE_G3_PROPUESTA"
PROFILES = frozenset({ICT, TTRADES_AM, QORE})
COMPATIBLE = frozenset({SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM})


@dataclass(frozen=True)
class SourceProfileBinding:
    profile: str
    session: SessionId
    selected_at: datetime
    implementation_version: str = "VT31_M0_SOURCE_PROFILE_RESEARCH_ROUTER_V1"


@dataclass(frozen=True)
class CognitiveProfileVerdict:
    profile: str
    session: str
    selected_at: datetime
    assessed_at: datetime
    status: str
    method_source_status: str
    genuine_original_g3_cog_called: bool
    ttrades_source_first_adapter_called: bool
    original_g3_cognitive_decision_available: bool
    source_bound_research_dto_available: bool
    source_dol_provenance: str
    author_method_complete_certified: bool = False
    cognitive_certified: bool = False
    ops_authorized: bool = False
    trader_certified: bool = False
    broker_orders_ack_fills: int = 0
    lot_sizing: int = 0

    def record(self) -> dict[str, object]:
        record = asdict(self)
        record["selected_at"] = self.selected_at.isoformat()
        record["assessed_at"] = self.assessed_at.isoformat()
        return record


class PreSessionMethodRouter:
    """One immutable methodology selected at or before session opening."""

    def __init__(self, binding: SourceProfileBinding) -> None:
        if binding.profile not in PROFILES:
            raise ValueError("UNKNOWN_METHOD_SOURCE_PROFILE")
        if binding.session not in COMPATIBLE:
            raise ValueError("UNKNOWN_SILVER_BULLET_SESSION")
        if binding.profile == TTRADES_AM and binding.session != SessionId.NY_AM:
            raise ValueError("TTRADES_NYAM_ONLY")
        self.binding = binding

    def assess(
        self, *, as_of: datetime, closed_m1: tuple[M1Bar, ...],
    ) -> CognitiveProfileVerdict:
        b = self.binding
        at = utc(as_of)
        start,end = window_bounds(at,b.session)
        selected = utc(b.selected_at)
        if selected > start:
            raise ValueError("METHOD_PROFILE_SELECTED_AFTER_SESSION_STARTED")
        if selected.astimezone(NEW_YORK).date() != at.astimezone(NEW_YORK).date():
            raise ValueError("PRESESSION_SELECTION_MUST_NAME_SAME_NY_DAY")
        if not (start < at < end):
            raise ValueError("COGNITIVE_ASOF_MUST_BE_WITHIN_SOURCE_WINDOW")
        if (
            not closed_m1 or utc(closed_m1[-1].closed_at) != at
            or any(utc(x.closed_at) > at for x in closed_m1)
            or any(
                utc(left.opened_at) >= utc(right.opened_at)
                or utc(left.closed_at) > utc(right.opened_at)
                for left,right in zip(closed_m1,closed_m1[1:],strict=False)
            )
        ):
            raise ValueError("COG_INPUT_IS_NOT_CLOSED_ASOF_SOURCE")

        if b.profile == TTRADES_AM:
            source = ttrades_source_first_g3_cognitive_proposal(
                profile=TTRADES_AM, session=b.session,
                as_of=at, closed_m1=closed_m1,
            )
            if source.status == SUCCESS:
                status = "TTRADES_SOURCE_FIRST_CONTEXT_RESEARCH_ONLY"
            elif source.status == MIN10_CONFLICT:
                status = "WAIT_TTRADES_AUTHOR_DOL_QORE_MIN10_CONFLICT"
            else:
                status = "WAIT_OR_REJECT_TTRADES_SOURCE_NOT_CONFIRMED"
            return CognitiveProfileVerdict(
                b.profile,b.session.value,selected,at,status,
                source.status,
                genuine_original_g3_cog_called=source.original_mss_at is not None,
                ttrades_source_first_adapter_called=True,
                original_g3_cognitive_decision_available=source.original_mss_at is not None,
                source_bound_research_dto_available=source.proposed is not None,
                source_dol_provenance="TTRADES_09_H1_OPPOSITE_NOT_PRIOR_CASH",
            )

        # Same genuine original producer, different EXPLICIT methodology.
        engine = VT31CleanroomCognition(framework_policy=G3_MSS_FRAMEWORK_POLICY)
        for candle in closed_m1:
            engine.observe_closed_m1(candle)
        assessment = engine.assess(session=b.session,as_of=at)
        has = assessment.decision is not None
        label = (
            "ICT_GENERAL_G3_QORE_DIAGNOSTIC_NOT_AUTHOR_VERIFIED"
            if b.profile == ICT else
            "QORE_G3_OWN_METHOD_GENUINE_COG_UNCERTIFIED"
        )
        return CognitiveProfileVerdict(
            b.profile,b.session.value,selected,at,
            label if has else label+"_WAIT",
            "AUTHOR_SOURCE_NOT_FULLY_ATTESTED" if b.profile == ICT
            else "QORE_G3_SOURCE_POLICY_NOT_DUAL_SIGNED",
            genuine_original_g3_cog_called=True,
            ttrades_source_first_adapter_called=False,
            original_g3_cognitive_decision_available=has,
            source_bound_research_dto_available=False,
            source_dol_provenance=(
                "QORE_CASH_CONTEXT_NOT_TTRADES_09H"
                if b.profile == ICT else
                "QORE_G3_POLICY_NO_LECTURE_CLAIM"
            ),
        )


def profile_router_court() -> dict[str, object]:
    observations: list[dict[str, object]] = []
    for month in (1,7):
        for side in (Side.LONG,Side.SHORT):
            for min10 in (False,True):
                bars,at=ttrades_fixture(
                    side=side,month=month,min10_valid=min10,
                )
                start,_=window_bounds(at,SessionId.NY_AM)
                router=PreSessionMethodRouter(SourceProfileBinding(
                    profile=TTRADES_AM,session=SessionId.NY_AM,
                    selected_at=start,
                ))
                ans=router.assess(as_of=at,closed_m1=bars)
                expect=(
                    "TTRADES_SOURCE_FIRST_CONTEXT_RESEARCH_ONLY" if min10 else
                    "WAIT_TTRADES_AUTHOR_DOL_QORE_MIN10_CONFLICT"
                )
                if ans.status!=expect:
                    raise AssertionError("METHOD_PROFILE_SOURCE_DECISION_CHANGED")
                observations.append({
                    "month":month, "side":side.value,
                    "g3_min10_compatible":min10,
                    "synthetic_market_fixture_real_g3_cognition":True,
                    **ans.record(),
                })
    return {
        "schema":"VT31_M0_EXPLICIT_PRESESSION_METHOD_ROUTER_V1",
        "prereg_sha":PREREG,
        "real_g3_cognition_source_first_evaluations":len(observations),
        "cases":observations,
        "one_trader_multiple_explicit_source_profiles":True,
        "profile_binding_requires_pre_session_selection":True,
        "methodology_certified":False,
        "cognition_certified":False,
        "M6_dual_human_signatures_verified":False,
        "broker_orders_fills":0,
        "vt31_sizing":False,
        "live_authorized":False,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    o=p.parse_args().out
    out=profile_router_court()
    o.parent.mkdir(parents=True,exist_ok=True)
    o.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({
        "cog_synthetic_casebook":len(out["cases"]),
        "source_first_research":sum(
            x["status"]=="TTRADES_SOURCE_FIRST_CONTEXT_RESEARCH_ONLY"
            for x in out["cases"]
        ),
        "conflict_wait":sum(
            x["status"]=="WAIT_TTRADES_AUTHOR_DOL_QORE_MIN10_CONFLICT"
            for x in out["cases"]
        ),
        "methodology_certified":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
