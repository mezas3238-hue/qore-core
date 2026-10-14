#!/usr/bin/env python3
"""Independent QORE DOL *price lineage* attestor for general ICT Silver Bullet.

Reconstructs liquidity source windows and consumption from closed M1. This is
not a statement that ICT mandates QORE-specific pool selection or 10-point
minimum. It cannot authorize orders, sizing, trading or economic claims.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
    utc,
    window_bounds,
)
from scripts.vt31_cog_evidence_v2_20261014 import (
    ICT_GENERAL,
    inspect_cog_evidence,
)

KNOWN_WINDOWS = {
    "ASIA_NY_CLOCK": (0, 3, 180),
    "LONDON_NY_CLOCK": (3, 5, 120),
    "PRIOR_NY_CASH_SESSION": (9, 16, 390),
}


@dataclass(frozen=True, slots=True)
class IndependentDolEvidence:
    state: str
    reasons: tuple[str, ...]
    as_of: datetime
    source_family: str | None = None
    observed_level: Decimal | None = None
    source_start: datetime | None = None
    source_confirmed_at: datetime | None = None
    reviewed_monitor_bars: int = 0
    method_certified: bool = False
    cognition_certified: bool = False
    execution_authorized: bool = False

    def record(self) -> dict[str, Any]:
        data = asdict(self)
        return {
            k: v.isoformat() if isinstance(v, datetime)
            else str(v) if isinstance(v, Decimal)
            else list(v) if isinstance(v, tuple)
            else v
            for k, v in data.items()
        }


@dataclass(frozen=True, slots=True)
class GeneralCogDolComparison:
    state: str
    reasons: tuple[str, ...]
    source_state: str
    v2_state: str
    method_certified: bool = False
    cognition_certified: bool = False
    execution_authorized: bool = False


def _local_start(day, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=NEW_YORK)


def _complete_window(
    history: tuple[M1Bar, ...], day, kind: str,
) -> tuple[M1Bar, ...]:
    if kind == "PRIOR_NY_CASH_SESSION":
        start = _local_start(day, 9, 30).astimezone(utc(history[-1].closed_at).tzinfo)
        count = 390
    else:
        h0, _, count = KNOWN_WINDOWS[kind]
        start = _local_start(day, h0).astimezone(utc(history[-1].closed_at).tzinfo)
    end = start + timedelta(minutes=count)
    rows = tuple(
        b for b in history if start <= utc(b.opened_at) < end
    )
    if len(rows) != count:
        return ()
    if any(
        utc(b.opened_at) != start + timedelta(minutes=i)
        or utc(b.closed_at) != start + timedelta(minutes=i+1)
        for i, b in enumerate(rows)
    ):
        return ()
    return rows


def verify_ict_dol_from_m1(
    *, as_of: datetime, session: SessionId,
    cognition: CognitiveDecision | None, history: tuple[M1Bar, ...],
) -> IndependentDolEvidence:
    at = utc(as_of)
    def answer(
        state: str, reason: str, family: str | None = None,
        level: Decimal | None = None,
        source_first: datetime | None = None,
        source_last: datetime | None = None,
        monitored: int = 0,
    ) -> IndependentDolEvidence:
        return IndependentDolEvidence(
            state=state, reasons=(reason,), as_of=at,
            source_family=family, observed_level=level,
            source_start=source_first, source_confirmed_at=source_last,
            reviewed_monitor_bars=monitored,
        )
    if not isinstance(session, SessionId):
        return answer("REJECTED", "NOT_A_VT31_SESSION")
    begin, end = window_bounds(at - timedelta(microseconds=1), session)
    if not begin < at <= end:
        return answer("REJECTED", "ASOF_OUTSIDE_SELECTED_ICT_SESSION")
    if not history:
        return answer("UNKNOWN", "SOURCE_M1_HISTORY_MISSING")
    if any(utc(b.closed_at) > at for b in history):
        return answer("REJECTED", "FUTURE_M1_IN_EXTERNAL_SOURCE")
    if any(
        utc(a.opened_at) >= utc(b.opened_at)
        for a, b in zip(history, history[1:], strict=False)
    ) or utc(history[-1].closed_at) != at:
        return answer("REJECTED", "UNORDERED_OR_STALE_M1_SOURCE")
    if cognition is None:
        return answer("UNKNOWN", "NO_COG_DECISION_AT_ASOF")
    if cognition.session is not session or utc(cognition.observed_at) != at:
        return answer("REJECTED", "COG_SESSION_OR_ASOF_CONTRADICTS_MARKET")
    family = cognition.draw_family
    if family.endswith("_HIGH"):
        kind, target_side = family.removesuffix("_HIGH"), Side.LONG
    elif family.endswith("_LOW"):
        kind, target_side = family.removesuffix("_LOW"), Side.SHORT
    else:
        return answer("REJECTED", "UNRECOGNIZED_QORE_DOL_FAMILY", family)
    if kind not in KNOWN_WINDOWS:
        return answer("REJECTED", "UNRECOGNIZED_QORE_DOL_FAMILY", family)
    if cognition.side is not target_side:
        return answer("REJECTED", "DOL_SOURCE_SIDE_CONTRADICTS_COG", family)
    today = at.astimezone(NEW_YORK).date()
    source: tuple[M1Bar, ...] = ()
    if kind == "PRIOR_NY_CASH_SESSION":
        earlier = sorted({
            utc(b.opened_at).astimezone(NEW_YORK).date()
            for b in history
            if utc(b.opened_at).astimezone(NEW_YORK).date() < today
        }, reverse=True)
        for day in earlier:
            candidate = _complete_window(history, day, kind)
            if candidate:
                source = candidate
                break
        if not source:
            return answer("UNKNOWN", "PRIOR_NY_CASH_SESSION_COMPLETE_M1_UNKNOWN", family)
        if at - utc(source[-1].closed_at) > timedelta(days=5):
            return answer("UNKNOWN", "PRIOR_NY_CASH_POOL_TOO_OLD", family)
    else:
        if kind == "LONDON_NY_CLOCK" and session is SessionId.LONDON:
            return answer("REJECTED", "LONDON_POOL_NOT_AVAILABLE_IN_LONDON_SESSION", family)
        source = _complete_window(history, today, kind)
        if not source:
            return answer("UNKNOWN", "SOURCE_RANGE_INCOMPLETE_OR_M1_GAPPED", family)
    confirmed_at = utc(source[-1].closed_at)
    origin = utc(source[0].opened_at)
    observed_level = (
        max(b.high for b in source)
        if target_side is Side.LONG else min(b.low for b in source)
    )
    if cognition.draw_target != observed_level:
        return answer(
            "REJECTED", "COG_DOL_PRICE_DIFFERS_FROM_INDEPENDENT_M1_SOURCE",
            family, observed_level, origin, confirmed_at,
        )
    if utc(cognition.draw_level_observed_at) != confirmed_at:
        return answer(
            "REJECTED", "COG_DOL_CONFIRMATION_TIMESTAMP_MISMATCH",
            family, observed_level, origin, confirmed_at,
        )
    if confirmed_at >= at:
        return answer(
            "UNKNOWN", "POOL_NOT_PRECONFIRMED_AT_ASOF",
            family, observed_level, origin, confirmed_at,
        )
    follow = tuple(
        b for b in history
        if confirmed_at <= utc(b.opened_at) < at
    )
    # An observed touch is sufficient to falsify pool availability, even if
    # source has other gaps. Never resurrect a mitigated level.
    if any(
        b.high >= observed_level if target_side is Side.LONG
        else b.low <= observed_level
        for b in follow
    ):
        return answer(
            "REJECTED", "DOL_ALREADY_CONSUMED_AFTER_CONFIRMATION",
            family, observed_level, origin, confirmed_at, len(follow),
        )
    expected = int((at - confirmed_at).total_seconds() // 60)
    if (
        len(follow) != expected
        or any(
            utc(b.opened_at) != confirmed_at + timedelta(minutes=i)
            or utc(b.closed_at) != confirmed_at + timedelta(minutes=i+1)
            for i, b in enumerate(follow)
        )
    ):
        return answer(
            "UNKNOWN", "POST_CONFIRMATION_M1_MONITORING_GAP",
            family, observed_level, origin, confirmed_at, len(follow),
        )
    return answer(
        "VERIFIED_QORE_DOL_PRICE_LINEAGE",
        "CONTEXTUAL_POOL_PRICE_AND_UNCONSUMED_SOURCE_OBSERVED_NOT_ICT_DOCTRINE",
        family, observed_level, origin, confirmed_at, len(follow),
    )


def compare_general_cog_v2_with_dol(
    *, as_of: datetime, session: SessionId,
    cognition: CognitiveDecision | None, history: tuple[M1Bar, ...],
) -> GeneralCogDolComparison:
    """Only replaces V2's specific missing DOL witness when independently true."""
    price = verify_ict_dol_from_m1(
        as_of=as_of, session=session, cognition=cognition, history=history,
    )
    v2 = inspect_cog_evidence(
        profile=ICT_GENERAL, session=session, as_of=as_of,
        history=history, cognition=cognition,
    )
    if v2.rejected or price.state == "REJECTED":
        return GeneralCogDolComparison(
            state="REJECTED",
            reasons=v2.rejected + price.reasons,
            source_state=price.state, v2_state=v2.state,
        )
    remaining = tuple(
        reason for reason in v2.unknown
        if reason != "ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED"
    )
    if price.state != "VERIFIED_QORE_DOL_PRICE_LINEAGE" or remaining:
        return GeneralCogDolComparison(
            state="UNKNOWN",
            reasons=remaining + (
                price.reasons if price.state != "VERIFIED_QORE_DOL_PRICE_LINEAGE" else ()
            ),
            source_state=price.state, v2_state=v2.state,
        )
    return GeneralCogDolComparison(
        state="QORE_MSS_AND_DOL_SOURCE_SUPPORTED_NOT_ICT_CERTIFIED",
        reasons=("PRICE_LINEAGE_IS_NOT_ICT_SOURCE_FIDELITY_OR_TRADE_AUTHORITY",),
        source_state=price.state, v2_state=v2.state,
    )
