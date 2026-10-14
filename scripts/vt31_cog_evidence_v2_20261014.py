#!/usr/bin/env python3
"""Causal cognitive attestation (M0-M3 only). Not trading authorization.

Independently checks a real COG DTO against closed historical M1: original
MSS-close, strict pivot geometry, actual crossing, QORE impulse reference,
and (for TTrades AM only) the distinct 09:00-H1 raid/return/DOL contract.
CONFIRMED means *causal context*, not author fidelity, trade or edge.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import median
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    NEW_YORK,
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
    utc,
)
from scripts.vt31_ttrades_am_cognitive_fidelity_witness_20261014 import (
    assess_ttrades_am_context,
)

TTRADES_AM = "TTRADES_NY_AM_2025"
ICT_GENERAL = "ICT_GENERAL_2023"
PROFILES = frozenset({TTRADES_AM, ICT_GENERAL})
AMBIGUOUS_SOURCE = frozenset({
    "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER",
})


@dataclass(frozen=True, slots=True)
class CogEvidenceV2:
    profile: str
    session: SessionId
    as_of: datetime
    state: str
    rejected: tuple[str, ...]
    unknown: tuple[str, ...]
    observed_mss_close: Decimal | None
    observed_pivot_level: Decimal | None
    observed_mss_at: datetime | None
    observed_pivot_confirmed_at: datetime | None
    context: dict[str, Any]
    method_certified: bool = False
    cognition_certified: bool = False
    live_authorized: bool = False

    def record(self) -> dict[str, Any]:
        def convert(v: Any) -> Any:
            if isinstance(v, datetime):
                return v.isoformat()
            if isinstance(v, Decimal):
                return str(v)
            if isinstance(v, dict):
                return {k: convert(x) for k, x in v.items()}
            if isinstance(v, tuple):
                return [convert(x) for x in v]
            return v

        return convert(asdict(self))


def _contiguous(bars: tuple[M1Bar, ...]) -> bool:
    return all(
        utc(a.closed_at) == utc(b.opened_at)
        for a, b in zip(bars, bars[1:], strict=False)
    )


def _structural_verify(
    cognition: CognitiveDecision,
    history: tuple[M1Bar, ...],
    reject: list[str],
    unknown: list[str],
) -> tuple[Decimal | None, Decimal | None, datetime | None, datetime | None]:
    mss_at = utc(cognition.structure_break_confirmed_at)
    pivot_at = utc(cognition.structure_level_confirmed_at)
    indices = [
        i for i, b in enumerate(history) if utc(b.closed_at) == mss_at
    ]
    if len(indices) != 1:
        unknown.append("MSS_BAR_NOT_OBSERVED_IN_HISTORY")
        return None, None, None, None
    index = indices[0]
    recent = history[:index + 1][-95:]
    actual = recent[-1]
    anchor = actual.close
    if cognition.framework_policy == G3_MSS_FRAMEWORK_POLICY:
        if cognition.mss_anchor_close != anchor:
            reject.append("MSS_ANCHOR_CLOSE_MISMATCH_WITH_M1")
    else:
        unknown.append("LEGACY_MSS_CLOSE_NOT_PINNED")

    if len(recent) < 10 or not _contiguous(recent[-7:]):
        unknown.append("MSS_IMPULSE_REFERENCE_M1_MISSING")
    else:
        ref = median(
            abs(b.close - b.open) for b in recent[-7:-2]
        )
        body = abs(actual.close - actual.open)
        if ref <= 0:
            reject.append("QORE_REFERENCE_BODY_NOT_POSITIVE")
        elif body < ref * Decimal("1.25"):
            reject.append("MSS_IMPULSE_UNDER_QORE_1P25_MEDIAN5")

    if index == 0 or utc(history[index - 1].closed_at) != mss_at-timedelta(minutes=1):
        unknown.append("MSS_PRIOR_CLOSE_UNOBSERVED")
    else:
        previous = history[index - 1]
        level = cognition.structure_level
        broken = (
            previous.close <= level < actual.close and actual.close > actual.open
            if cognition.side is Side.LONG
            else previous.close >= level > actual.close
                 and actual.close < actual.open
        )
        if not broken:
            reject.append("MSS_LEVEL_CROSSING_INCONSISTENT_WITH_M1")

    pivot_candidates = [
        j for j in range(1, len(recent)-1)
        if utc(recent[j+1].closed_at) == pivot_at
    ]
    if len(pivot_candidates) != 1:
        unknown.append("PIVOT_CONFIRMATION_M1_NOT_IN_MSS_LOOKBACK")
        return anchor, None, mss_at, None
    j = pivot_candidates[0]
    left, pivot, right = recent[j-1:j+2]
    if (
        utc(left.closed_at) != utc(pivot.opened_at)
        or utc(pivot.closed_at) != utc(right.opened_at)
    ):
        unknown.append("PIVOT_3M1_NOT_CONTIGUOUS")
    else:
        observed_level = pivot.high if cognition.side is Side.LONG else pivot.low
        verified = (
            pivot.high > left.high and pivot.high > right.high
            if cognition.side is Side.LONG
            else pivot.low < left.low and pivot.low < right.low
        )
        if (
            not verified or observed_level != cognition.structure_level
            or pivot_at >= mss_at
        ):
            reject.append("PIVOT_LEVEL_OR_CONFIRMATION_INCONSISTENT")
        return anchor, observed_level, mss_at, pivot_at
    return anchor, None, mss_at, pivot_at


def inspect_cog_evidence(
    *, profile: str, session: SessionId, as_of: datetime,
    history: tuple[M1Bar, ...],
    cognition: CognitiveDecision | None,
) -> CogEvidenceV2:
    if profile not in PROFILES:
        raise ValueError("explicit supported cognitive source profile required")
    if not isinstance(session, SessionId):
        raise ValueError("valid VT31 session required")
    t = utc(as_of)
    rejected: list[str] = []
    unknown: list[str] = []
    context: dict[str, Any] = {}
    close: Decimal | None = None
    level: Decimal | None = None
    mss_at: datetime | None = None
    pivot_at: datetime | None = None
    local = t.astimezone(NEW_YORK)
    proper_hour = {
        SessionId.LONDON: 3,
        SessionId.NY_AM: 10,
        SessionId.NY_PM: 14,
    }[session]
    if local.hour != proper_hour or local.minute == 0 and local.second == 0:
        rejected.append("OUTSIDE_SELECTED_ICT_CLOSED_M1_WINDOW")

    if not history:
        unknown.append("EMPTY_CLOSED_M1_HISTORY")
    else:
        if any(utc(b.closed_at) > t for b in history):
            rejected.append("FUTURE_BAR_IN_COG_EVIDENCE_INPUT")
        if any(
            utc(a.opened_at) >= utc(b.opened_at)
            for a, b in zip(history, history[1:], strict=False)
        ):
            rejected.append("NONMONOTONIC_M1_HISTORY")
        if utc(history[-1].closed_at) != t:
            rejected.append("EXTERNAL_AS_OF_NOT_LATEST_CLOSED_M1")
    if cognition is None:
        unknown.append("NO_COG_DECISION_AT_AS_OF")
    else:
        if cognition.session != session:
            rejected.append("COG_PROFILE_SESSION_CONFLICT")
        if utc(cognition.observed_at) != t:
            rejected.append("COG_OBSERVED_AT_CONFLICT")
        if history and not rejected:
            close, level, mss_at, pivot_at = _structural_verify(
                cognition, history, rejected, unknown
            )

    if profile == TTRADES_AM:
        if session is not SessionId.NY_AM:
            rejected.append("TTRADES_AM_ONLY_NY_AM")
        if cognition is not None and history and not rejected:
            same_day = [
                b for b in history
                if utc(b.opened_at).astimezone(NEW_YORK).date() == local.date()
            ]
            nine = tuple(
                b for b in same_day
                if utc(b.opened_at).astimezone(NEW_YORK).hour == 9
            )
            ten = tuple(
                b for b in same_day
                if utc(b.opened_at).astimezone(NEW_YORK).hour == 10
            )
            witness = assess_ttrades_am_context(
                cognition=cognition,
                previous_ny_9am=nine,
                current_ny_10am=ten,
            )
            context = witness.to_public_record()
            for code in witness.reason_codes:
                if code in AMBIGUOUS_SOURCE:
                    unknown.append(code)
                elif code in (
                    "H1_09_10_NOT_COMPLETE",
                    "M1_10AM_PREFIX_GAPPED_OR_MISSING",
                ):
                    unknown.append(code)
                else:
                    rejected.append(code)
    else:
        # A COG DTO is only a declaration of DOL source. ICT DOL needs an
        # independent prior-day/week/Asia/liquidity pool witness.
        unknown.append("ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED")
        context = {
            "not_a_universal_9am_H1_raid_gate": True,
            "contextual_DOL_evidence_pending": True,
        }

    state = (
        "REJECTED" if rejected else
        "UNKNOWN" if unknown else
        "CONFIRMED"
    )
    return CogEvidenceV2(
        profile=profile, session=session, as_of=t, state=state,
        rejected=tuple(dict.fromkeys(rejected)),
        unknown=tuple(dict.fromkeys(unknown)),
        observed_mss_close=close,
        observed_pivot_level=level,
        observed_mss_at=mss_at,
        observed_pivot_confirmed_at=pivot_at,
        context=context,
    )
