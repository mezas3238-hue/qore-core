#!/usr/bin/env python3
"""Versioned TTrades NYAM SOURCE-FIRST cognitive research; original G3 UNCHANGED.

Rebind a genuine original G3 M1 MSS to the TTrades 09-H1 opposite DOL
ONLY if source confirms and QORE G3 10pt floor allows it. No trading authority.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    MIN_INDEX_POINTS,
    NEW_YORK,
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
    utc,
)
from scripts.vt31_cog_evidence_v2_20261014 import (
    TTRADES_AM,
    inspect_cog_evidence,
)
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    native_ttrades_am_context,
)
from scripts.vt31_original_g3_cog_qualitative_court_20261014 import (
    source_fingerprint,
)
from scripts.vt31_original_g3_cog_short_sessions_qualitative_20261015 import (
    short_fixture,
)

PREREG = "39d64d80c9090dd2d1dd97be6003084b75f1eb1f"
NEW_RESEARCH_VERSION = "VT31_TTRADES_AM_SOURCE_FIRST_G3_MSS_PROFILE_PROPOSAL_V1"
SUCCESS = "RESEARCH_TTRADES_CONTEXT_CONFORMANT_NOT_CERTIFIED"
MIN10_CONFLICT = "G3_MIN10_AND_TTRADES_SOURCE_TARGET_CONFLICT_WAIT"


@dataclass(frozen=True, slots=True)
class SourceFirstCogProposal:
    status: str
    reason_codes: tuple[str, ...]
    profile: str
    observed_at: datetime
    original_cog_dol: Decimal | None
    source_opposite_h1_dol: Decimal | None
    projected_index_points: Decimal | None
    original_mss_side: str | None
    original_mss_at: datetime | None
    proposed: CognitiveDecision | None
    independent_v2_state: str | None
    original_cog_invoked: bool = False
    actual_original_cog_unchanged: bool = True
    author_complete_method_certified: bool = False
    method_certified: bool = False
    cognition_certified: bool = False
    human_signed: bool = False
    operations_authorized: bool = False
    broker_orders: int = 0
    trader_sizing: int = 0

    def record(self) -> dict[str, Any]:
        dto = self.proposed
        return {
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "profile": self.profile,
            "observed_at": self.observed_at.isoformat(),
            "observed_ny": self.observed_at.astimezone(NEW_YORK).isoformat(),
            "original_cog_dol": (
                str(self.original_cog_dol)
                if self.original_cog_dol is not None else None
            ),
            "source_opposite_h1_dol": (
                str(self.source_opposite_h1_dol)
                if self.source_opposite_h1_dol is not None else None
            ),
            "projected_index_points": (
                str(self.projected_index_points)
                if self.projected_index_points is not None else None
            ),
            "g3_required_min_index_points": str(MIN_INDEX_POINTS),
            "original_mss_side": self.original_mss_side,
            "original_mss_at": (
                self.original_mss_at.isoformat()
                if self.original_mss_at is not None else None
            ),
            "proposed": {
                "source_provenance": dto.source_provenance,
                "cognitive_version": dto.cognitive_version,
                "draw_family": dto.draw_family,
                "side": dto.side.value,
                "draw_target": str(dto.draw_target),
                "draw_level_observed_at": dto.draw_level_observed_at.isoformat(),
                "mss_anchor_close": str(dto.mss_anchor_close),
                "mss_at": dto.structure_break_confirmed_at.isoformat(),
            } if dto is not None else None,
            "independent_v2_state": self.independent_v2_state,
            "original_cog_invoked": self.original_cog_invoked,
            "actual_original_cog_unchanged": self.actual_original_cog_unchanged,
            "author_complete_method_certified": self.author_complete_method_certified,
            "method_certified": self.method_certified,
            "cognition_certified": self.cognition_certified,
            "human_signed": self.human_signed,
            "operations_authorized": self.operations_authorized,
            "broker_orders": self.broker_orders,
            "trader_sizing": self.trader_sizing,
        }


def ttrades_source_first_g3_cognitive_proposal(
    *, profile: str, session: SessionId, as_of: datetime,
    closed_m1: tuple[M1Bar, ...],
) -> SourceFirstCogProposal:
    """Source-first cognitive *proposal* based on a real G3 original producer.

    Only a distinct versioned RESEARCH DTO can claim TTrades 09h DOL;
    the frozen original CognitiveDecision is neither mutated nor certified.
    """
    if profile != TTRADES_AM:
        raise ValueError("TTRADES_EXPLICIT_METHOD_PROFILE_REQUIRED")
    at = utc(as_of)
    cog_assessed = False  # True only after the actual original assess() call.

    def emit(
        status: str, *reasons: str,
        original: CognitiveDecision | None = None,
        opposite: Decimal | None = None,
        distance: Decimal | None = None,
        proposal: CognitiveDecision | None = None,
        independent: str | None = None,
    ) -> SourceFirstCogProposal:
        return SourceFirstCogProposal(
            status=status, reason_codes=tuple(reasons), profile=profile,
            observed_at=at,
            original_cog_dol=original.draw_target if original else None,
            source_opposite_h1_dol=opposite,
            projected_index_points=distance,
            original_cog_invoked=cog_assessed,
            original_mss_side=original.side.value if original else None,
            original_mss_at=(
                original.structure_break_confirmed_at if original else None
            ),
            proposed=proposal, independent_v2_state=independent,
        )

    if session is not SessionId.NY_AM:
        return emit("PROFILE_SESSION_REJECTED", "TTRADES_NYAM_ONLY")
    if (
        not closed_m1
        or utc(closed_m1[-1].closed_at) != at
        or any(utc(row.closed_at) > at for row in closed_m1)
        or any(
            utc(left.opened_at) >= utc(right.opened_at)
            or utc(left.closed_at) > utc(right.opened_at)
            for left, right in zip(closed_m1, closed_m1[1:], strict=False)
        )
    ):
        return emit("INPUT_INVALID_REJECTED", "M1_ASOF_FUTURE_OR_ORDER_CONFLICT")

    today = at.astimezone(NEW_YORK).date()
    same_day = tuple(
        bar for bar in closed_m1
        if utc(bar.opened_at).astimezone(NEW_YORK).date() == today
    )
    nine = tuple(
        bar for bar in same_day
        if utc(bar.opened_at).astimezone(NEW_YORK).hour == 9
    )
    ten = tuple(
        bar for bar in same_day
        if utc(bar.opened_at).astimezone(NEW_YORK).hour == 10
    )
    source = native_ttrades_am_context(as_of=at, nine=nine, ten=ten)
    if source.state != "RETURN_INSIDE_OBSERVED":
        return emit(
            "TTRADES_SOURCE_NOT_CONFIRMED_WAIT",
            source.state, *source.reasons,
        )
    if (
        source.return_inside_at != at
        or source.first_sweep_at is None
        or source.first_sweep_at >= at
        or source.opposite_h1_dol is None
        or source.candidate_side not in ("LONG", "SHORT")
    ):
        return emit(
            "TTRADES_SOURCE_UNKNOWN_WAIT",
            "SOURCE_NOT_FRESH_OR_FIRST_RAID_OR_OPPOSITE_DOL_MISSING",
        )

    engine = VT31CleanroomCognition(
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    for bar in closed_m1:
        engine.observe_closed_m1(bar)
    assessment = engine.assess(session=session, as_of=at)
    cog_assessed = True
    original = assessment.decision
    if original is None:
        return emit(
            "ORIGINAL_COG_MSS_NOT_CONFIRMED_WAIT",
            *assessment.missing,
            opposite=source.opposite_h1_dol,
        )
    if (
        original.side.value != source.candidate_side
        or original.structure_break_confirmed_at != at
        or original.structure_level_confirmed_at >= at
        or original.mss_anchor_close != closed_m1[-1].close
        or original.framework_policy != G3_MSS_FRAMEWORK_POLICY
    ):
        return emit(
            "COG_AND_AUTHOR_SOURCE_STRUCTURE_CONFLICT_REJECTED",
            "COG_SIDE_OR_MSS_TIME_OR_ANCHOR_NOT_SOURCE_MATCHED",
            original=original,
            opposite=source.opposite_h1_dol,
        )

    target = source.opposite_h1_dol
    distance = (
        target - closed_m1[-1].close if original.side is Side.LONG
        else closed_m1[-1].close - target
    )
    if distance < MIN_INDEX_POINTS:
        # Never alter the author's destination to artificially meet G3 10pt.
        return emit(
            MIN10_CONFLICT,
            "TTRADES_AUTHOR_DOL_VALID_BUT_QORE_G3_MIN10_NOT_SATISFIED",
            original=original, opposite=target, distance=distance,
        )

    # This new research DTO is NOT the frozen original producer output.
    # Only DOL identity/provenance is adapted. Source MSS remains unchanged.
    direction = "HIGH" if original.side is Side.LONG else "LOW"
    candidate = replace(
        original,
        draw_target=target,
        draw_family=f"TTRADES_09H_H1_OPPOSITE_{direction}_SOURCE_V1",
        draw_level_observed_at=nine[-1].closed_at,
        source_provenance=(
            "QORE_RESEARCH_TTRADES_AM_SOURCE_BOUND_09H_OPPOSITE"
            "|ORIGINAL_G3_MSS_PASSTHROUGH_NOT_AUTHOR_CERTIFIED"
            f"|ORIGINAL_COG={original.cognitive_version}"
        ),
        cognitive_version=NEW_RESEARCH_VERSION,
    )
    inspected = inspect_cog_evidence(
        profile=TTRADES_AM, session=session,
        as_of=at, history=closed_m1, cognition=candidate,
    )
    if inspected.state != "CONFIRMED":
        return emit(
            "INDEPENDENT_SOURCE_VERIFIER_NOT_CONFIRMED_WAIT",
            *inspected.rejected, *inspected.unknown,
            original=original, opposite=target, distance=distance,
            independent=inspected.state,
        )
    return emit(
        SUCCESS,
        "ONLY_TTRADES_09H_M1_CONTEXT_ATTESTED_NOT_AUTHOR_ENTRY_OR_STOP",
        original=original, opposite=target, distance=distance,
        proposal=candidate, independent=inspected.state,
    )


def ttrades_fixture(
    *, side: Side, month: int, min10_valid: bool,
) -> tuple[tuple[M1Bar, ...], datetime]:
    """Preregistered contrasts, same G3 COG, no post-outcome candle selection."""
    original, at = short_fixture(session=SessionId.NY_AM, month=month)
    rows = list(original)
    prior_count = 390
    if side is Side.SHORT:
        if min10_valid:
            rows[45] = replace(rows[45], low=Decimal("60"))
            rows[prior_count + 560] = replace(
                rows[prior_count + 560], low=Decimal("80"),
            )
    else:
        rows[prior_count + 597] = replace(
            rows[prior_count + 597],
            high=Decimal("104"),
            low=Decimal("98"),
        )
        rows[prior_count + 601] = replace(
            rows[prior_count + 601],
            open=Decimal("96"), high=Decimal("99"),
            low=Decimal("89"), close=Decimal("95"),
        )
        rows[prior_count + 602] = replace(
            rows[prior_count + 602],
            open=Decimal("94"), high=Decimal("106"),
            low=Decimal("93"), close=Decimal("105"),
        )
        if min10_valid:
            rows[prior_count + 550] = replace(
                rows[prior_count + 550], high=Decimal("120"),
            )
    return tuple(rows), at


def cognitive_profile_court() -> dict[str, Any]:
    cases = []
    for month in (1, 7):
        for side in (Side.LONG, Side.SHORT):
            for eligible in (False, True):
                hist, at = ttrades_fixture(
                    side=side, month=month, min10_valid=eligible,
                )
                result = ttrades_source_first_g3_cognitive_proposal(
                    profile=TTRADES_AM, session=SessionId.NY_AM,
                    as_of=at, closed_m1=hist,
                )
                expected = SUCCESS if eligible else MIN10_CONFLICT
                if result.status != expected:
                    raise ValueError(
                        f"SOURCE_FIRST_PREREG_CONTRADICTION:"
                        f"{month}:{side.value}:{eligible}:"
                        f"{result.record()}"
                    )
                cases.append({
                    "case": (
                        f"{side.value}_{month}_"
                        f"{'MIN10_VALID' if eligible else 'MIN10_CONFLICT'}"
                    ),
                    "scenario_is_synthetic_no_market_PNL": True,
                    **result.record(),
                })
    return {
        "title": "VT31_PROFILE_TTRADES_SOURCE_FIRST_G3_MSS_RESEARCH_V1",
        "prereg_commit": PREREG,
        "author_source_url": "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/",
        "original_frozen_g3_code_sha": source_fingerprint(),
        "version": NEW_RESEARCH_VERSION,
        "cases": cases,
        "input_historical_3y_data_used": False,
        "trader_method_certified": False,
        "trader_cognitive_certified": False,
        "independent_human_method_source_review": False,
        "independent_human_cog_ops_dual_signatures": False,
        "economic_backtest_run": False,
        "orders_filled": 0,
        "lots_selected": 0,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args().out
    p = cognitive_profile_court()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(p, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "cases": [
            (x["case"], x["status"], x["projected_index_points"])
            for x in p["cases"]
        ],
        "author_certified": False,
        "original_g3_unchanged": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
