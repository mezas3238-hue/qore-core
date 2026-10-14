#!/usr/bin/env python3
"""COG_EVIDENCE_V2: immutable as-of shadow evaluation, never trading authority.

Consumes actual VT31 CognitiveAssessment and the close-M1 source context.
Two source profiles are never mixed. Neither CONFIRMED context nor a PASS in
these tests is a certificate for cognition, methodology, trader or economics.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    CognitiveAssessment,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    CognitiveDecision,
    M1Bar,
    SessionId,
    utc,
)
from scripts.vt31_ttrades_am_cognitive_fidelity_witness_20261014 import (
    assess_ttrades_am_context,
)

VERSION = "qore.vt31.cog_evidence.v2.research_only"
TTRADES = "TTRADES_NY_AM_2025"
ICT = "ICT_GENERAL_2023"
PROFILES = frozenset({TTRADES, ICT})
UNKNOWN_CONTEXT = frozenset({
    "H1_09_10_NOT_COMPLETE",
    "M1_10AM_PREFIX_GAPPED_OR_MISSING",
    "COG_AS_OF_NOT_LAST_CLOSED_M1",
    "MSS_NOT_OBSERVED_IN_CURRENT_NY_AM_M1",
})


class Status(StrEnum):
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CogEvidenceV2:
    schema: str
    profile: str
    status: Status
    reasons: tuple[str, ...]
    as_of_utc: str
    session: str
    cog_state: str
    cog_missing: tuple[str, ...]
    verified_htf: tuple[str, ...]
    source_pool_count: int
    causal_closed_m1_count: int
    cog_decision_present: bool
    side: str | None
    draw_family: str | None
    draw_target: str | None
    expected_source_target: str | None
    mss_closed_at: str | None
    pivot_confirmed_at: str | None
    first_sweep_closed_at: str | None
    h1_09_high: str | None
    h1_09_low: str | None
    input_m1_closed_asof: int
    verified_closed_m1_sha256: str
    evidence_sha256: str
    context_confirmed_only: bool
    methodology_certified: bool = False
    cognition_certified: bool = False
    execution_authorized: bool = False
    economic_edge_proven: bool = False

    def to_json(self) -> str:
        return json.dumps(
            asdict(self), sort_keys=True, separators=(",", ":"),
            ensure_ascii=True,
        )


def _digest(data: Any) -> str:
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("utf-8")).hexdigest()


def _asof_bars(
    *, as_of: datetime,
    prior: tuple[M1Bar, ...],
    current: tuple[M1Bar, ...],
) -> tuple[str, int]:
    """Never include future M1 prices in a hashed *as-of* evidence payload."""
    rows = []
    for x in prior + current:
        if utc(x.closed_at) > as_of:
            continue
        rows.append([
            utc(x.opened_at).isoformat(),
            utc(x.closed_at).isoformat(),
            str(x.open), str(x.high), str(x.low), str(x.close),
        ])
    return _digest(rows), len(rows)


def record(
    *, profile: str,
    assessment: CognitiveAssessment,
    previous_ny_9am: tuple[M1Bar, ...] = (),
    current_ny_10am: tuple[M1Bar, ...] = (),
) -> CogEvidenceV2:
    """Create audit record only; do NOT accept market orders or mutate COG.

    CONFIRMED means context coherence for narrow TTrades NY-AM. Other source
    profiles and insufficient witness history remain UNKNOWN.
    """
    if profile not in PROFILES:
        raise ValueError("unrecognized source methodology profile")
    if not isinstance(assessment, CognitiveAssessment):
        raise ValueError("authentic COG assessment DTO required")
    at = utc(assessment.as_of)
    decision: CognitiveDecision | None = assessment.decision
    reasons = []
    status = Status.UNKNOWN
    h, lo, target, sweep = None, None, None, None
    mss, pivot, side, family, draw = None, None, None, None, None

    if assessment.trade_authorized or not assessment.research_only:
        reasons.append("RESEARCH_ONLY_ASSESSMENT_INVARIANT_VIOLATED")
    if decision is not None:
        mss = utc(decision.structure_break_confirmed_at).isoformat()
        pivot = utc(decision.structure_level_confirmed_at).isoformat()
        side = decision.side.value
        family = decision.draw_family
        draw = str(decision.draw_target)
        if decision.session is not assessment.session:
            reasons.append("COG_DECISION_SESSION_MISMATCH")
        if utc(decision.observed_at) != at:
            reasons.append("COG_DECISION_AS_OF_MISMATCH")
        if assessment.state != "CAUSAL_DRAW_AND_SHIFT_PROVEN":
            reasons.append("COG_DECISION_STATE_MISMATCH")
    else:
        reasons.append("COG_DECISION_NOT_PRESENT")
    if decision is not None and not {"M15", "H1"}.issubset(
        set(assessment.verified_htf)
    ):
        reasons.append("COG_HTF_EVIDENCE_CONTRADICTS_PROVEN_DECISION")
    if decision is None:
        reasons.extend(
            "COG_MISSING_" + item for item in assessment.missing
        )
    if decision is None and assessment.state == "CAUSAL_DRAW_AND_SHIFT_PROVEN":
        reasons.append("COG_STATE_CLAIMS_ABSENT_DECISION")

    if profile == TTRADES:
        if assessment.session is not SessionId.NY_AM:
            reasons.append("PROFILE_NOT_NY_AM")
        elif decision is not None:
            # The prior witness is deliberately unchanged from PR #926.
            proof = assess_ttrades_am_context(
                cognition=decision,
                previous_ny_9am=previous_ny_9am,
                current_ny_10am=current_ny_10am,
            )
            reasons.extend(proof.reason_codes)
            if current_ny_10am:
                mss_bars = [
                    b for b in current_ny_10am
                    if utc(b.closed_at) == utc(decision.structure_break_confirmed_at)
                ]
                if len(mss_bars) == 1:
                    candle = mss_bars[0]
                    if (
                        decision.framework_policy
                        == "QORE_G3_MSS_CLOSE_V1_PROPOSED"
                        and decision.mss_anchor_close != candle.close
                    ):
                        reasons.append("MSS_ANCHOR_CLOSE_NOT_EQUAL_WITNESS_M1")
                    if (
                        decision.side.value == "LONG"
                        and candle.close <= decision.structure_level
                    ) or (
                        decision.side.value == "SHORT"
                        and candle.close >= decision.structure_level
                    ):
                        reasons.append("MSS_BREAK_LEVEL_NOT_CROSSED_BY_CLOSE")
            if proof.reference_high is not None:
                h = str(proof.reference_high)
            if proof.reference_low is not None:
                lo = str(proof.reference_low)
            if proof.target_expected is not None:
                target = str(proof.target_expected)
            if proof.first_sweep_closed_at is not None:
                sweep = utc(proof.first_sweep_closed_at).isoformat()
    else:
        # This is a deliberate source-fidelity UNKNOWN, not an ICT rejection.
        reasons.append("ICT_SOURCE_DOCTRINE_NOT_YET_FORMALIZED")

    # The prior witness may report UNKNOWN or REJECTED. Known contradictions
    # outrank missing history; no UNKNOWN is ever promoted to confirmation.
    faults = tuple(dict.fromkeys(reasons))
    hard_errors = [x for x in faults if not x.startswith("COG_MISSING_") and x not in UNKNOWN_CONTEXT and x not in {
        "COG_DECISION_NOT_PRESENT",
        "ICT_SOURCE_DOCTRINE_NOT_YET_FORMALIZED",
    }]
    if hard_errors:
        status = Status.REJECTED
    elif faults:
        status = Status.UNKNOWN
    elif profile == TTRADES:
        status = Status.CONFIRMED
    else:
        status = Status.UNKNOWN

    market_hash, bar_count = _asof_bars(
        as_of=at, prior=previous_ny_9am, current=current_ny_10am,
    )
    fields: dict[str, Any] = {
        "schema": VERSION,
        "profile": profile,
        "status": status.value,
        "reasons": faults,
        "as_of_utc": at.isoformat(),
        "session": assessment.session.value,
        "cog_state": assessment.state,
        "cog_missing": assessment.missing,
        "verified_htf": assessment.verified_htf,
        "source_pool_count": assessment.source_pool_count,
        "causal_closed_m1_count": assessment.causal_closed_m1_count,
        "cog_decision_present": decision is not None,
        "side": side,
        "draw_family": family,
        "draw_target": draw,
        "expected_source_target": target,
        "mss_closed_at": mss,
        "pivot_confirmed_at": pivot,
        "first_sweep_closed_at": sweep,
        "h1_09_high": h,
        "h1_09_low": lo,
        "input_m1_closed_asof": bar_count,
        "verified_closed_m1_sha256": market_hash,
        "context_confirmed_only": status is Status.CONFIRMED,
        "methodology_certified": False,
        "cognition_certified": False,
        "execution_authorized": False,
        "economic_edge_proven": False,
    }
    return CogEvidenceV2(
        **fields,
        evidence_sha256=_digest(fields),
    )
