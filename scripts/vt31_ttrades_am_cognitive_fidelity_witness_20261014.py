#!/usr/bin/env python3
"""Independent VT31 TTrades NY AM source-context witness (M0-M3 only).

Validates authentic COG CognitiveDecision against *closed* 09:00 H1 and 10:00
M1 sweep/reversal. Not wired to Trader, not certified method, no orders/PnL.
TTrades AM is a narrower PROFILE, never a universal veto for ICT London/PM.
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
)


@dataclass(frozen=True, slots=True)
class CognitiveFidelityWitness:
    profile: str
    status: str
    reason_codes: tuple[str, ...]
    as_of: datetime
    reference_high: Decimal | None
    reference_low: Decimal | None
    first_sweep_closed_at: datetime | None
    mss_closed_at: datetime | None
    target_expected: Decimal | None
    methodology_certified: bool = False
    cognitive_certified: bool = False
    execution_authorized: bool = False

    def to_public_record(self) -> dict[str, Any]:
        d = asdict(self)
        return {
            k: v.isoformat() if isinstance(v, datetime)
            else str(v) if isinstance(v, Decimal)
            else v
            for k, v in d.items()
        }


def _ny_start(at: datetime, h: int) -> datetime:
    d = utc(at).astimezone(NEW_YORK).date()
    return datetime.combine(d, time(h), tzinfo=NEW_YORK)


def _complete_m1(
    bars: tuple[M1Bar, ...], local_start: datetime,
    expected: int | None = None,
) -> bool:
    if expected is not None and len(bars) != expected:
        return False
    if not bars:
        return False
    local = local_start.astimezone(NEW_YORK)
    starts_at = local.astimezone(bars[0].opened_at.tzinfo).astimezone(
        bars[0].opened_at.tzinfo
    )
    return all(
        utc(bar.opened_at) == utc(starts_at) + timedelta(minutes=i)
        and utc(bar.closed_at) == utc(starts_at) + timedelta(minutes=i+1)
        for i, bar in enumerate(bars)
    )


def assess_ttrades_am_context(
    *, cognition: CognitiveDecision,
    previous_ny_9am: tuple[M1Bar, ...],
    current_ny_10am: tuple[M1Bar, ...],
) -> CognitiveFidelityWitness:
    """TTrades source-level conformance gate; source-only, NO fill authority.

    Both M1 sequences must be closed, contiguous and available at COG.as_of.
    The actual COG engine does not yet invoke this and is NOT TTrades-certified.
    """
    at = utc(cognition.observed_at)
    local = at.astimezone(NEW_YORK)
    errors: list[str] = []
    n9, n10 = _ny_start(at, 9), _ny_start(at, 10)
    n11 = _ny_start(at, 11)
    first_sweep: datetime | None = None
    target: Decimal | None = None
    reference_high: Decimal | None = None
    reference_low: Decimal | None = None

    if cognition.session is not SessionId.NY_AM:
        errors.append("WRONG_METHOD_PROFILE_SESSION")
    if not (n10 < local <= n11) or at == utc(n11):
        errors.append("OUTSIDE_NY_AM_SIGNAL_WINDOW")
    if not _complete_m1(previous_ny_9am, n9, 60):
        errors.append("H1_09_10_NOT_COMPLETE")
    if not _complete_m1(current_ny_10am, n10):
        errors.append("M1_10AM_PREFIX_GAPPED_OR_MISSING")
    if not current_ny_10am or (
        utc(current_ny_10am[-1].closed_at) != at
    ):
        errors.append("COG_AS_OF_NOT_LAST_CLOSED_M1")
    if len(current_ny_10am) > 60:
        errors.append("OUTSIDE_NY_AM_SOURCE_HOUR")
    if any(utc(bar.closed_at) > at for bar in previous_ny_9am + current_ny_10am):
        errors.append("FUTURE_M1_IN_SOURCE")

    if "H1_09_10_NOT_COMPLETE" not in errors:
        reference_high = max(x.high for x in previous_ny_9am)
        reference_low = min(x.low for x in previous_ny_9am)
        if reference_high <= reference_low:
            errors.append("FLAT_H1_REFERENCE")
        else:
            target = (
                reference_high
                if cognition.side is Side.LONG else reference_low
            )
            if cognition.draw_target != target:
                errors.append("DOL_NOT_OPPOSITE_9AM_H1_EXTREME")

    # Never infer a causal high/low raid if the H1 or M1 prefix is incomplete.
    if reference_high is not None and reference_low is not None and (
        "M1_10AM_PREFIX_GAPPED_OR_MISSING" not in errors
    ) and "FLAT_H1_REFERENCE" not in errors:
        first_side: str | None = None
        sweep_index: int | None = None
        for index, bar in enumerate(current_ny_10am):
            hi_raid = bar.high > reference_high
            lo_raid = bar.low < reference_low
            if hi_raid and lo_raid:
                errors.append("BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER")
                break
            if hi_raid or lo_raid:
                observed_side = "HIGH" if hi_raid else "LOW"
                if first_side is None:
                    first_side = observed_side
                    sweep_index = index
                    first_sweep = utc(bar.closed_at)
                elif first_side != observed_side:
                    errors.append("OPPOSITE_H1_RAID_AFTER_FIRST_SWEEP")
                    break
        if first_side is None and not any(
            x in errors for x in (
                "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER",
            )
        ):
            errors.append("NO_PRE_SIGNAL_9AM_H1_SWEEP")
        if first_side is not None:
            required = "LOW" if cognition.side is Side.LONG else "HIGH"
            if first_side != required:
                errors.append("SWEEP_DIRECTION_CONTRADICTS_COG")
            mss_at = utc(cognition.structure_break_confirmed_at)
            matched = [
                i for i, b in enumerate(current_ny_10am)
                if utc(b.closed_at) == mss_at
            ]
            if len(matched) != 1:
                errors.append("MSS_NOT_OBSERVED_IN_CURRENT_NY_AM_M1")
            elif sweep_index is not None:
                j = matched[0]
                if j <= sweep_index:
                    errors.append("MSS_NOT_AFTER_SWEEP")
                mss = current_ny_10am[j]
                inside = reference_low < mss.close < reference_high
                directional = (
                    mss.close > mss.open
                    if cognition.side is Side.LONG
                    else mss.close < mss.open
                )
                if not inside or not directional:
                    errors.append("MSS_DISPLACEMENT_NOT_BACK_INSIDE_9AM_H1")
                if utc(cognition.structure_level_confirmed_at) >= mss_at:
                    errors.append("PIVOT_NOT_PRECONFIRMED_BEFORE_MSS")

    return CognitiveFidelityWitness(
        profile="TTRADES_NY_AM_2025",
        status=("CONTEXT_CONFORMANT_ONLY" if not errors else "REJECTED"),
        reason_codes=tuple(dict.fromkeys(errors)),
        as_of=at,
        reference_high=reference_high,
        reference_low=reference_low,
        first_sweep_closed_at=first_sweep,
        mss_closed_at=utc(cognition.structure_break_confirmed_at),
        target_expected=target,
    )


def ict_2023_profile_scope(session: SessionId) -> dict[str, Any]:
    """Document why TTrades 09:00 H1 is NOT universally required by ICT."""
    return {
        "profile": "ICT_GENERAL_2023",
        "allowed_session": session in (
            SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM
        ),
        "9am_H1_raid_universal_required": False,
        "MSS_1p25x_universal_source_proven": False,
        "CE_midpoint_universal_entry_source_proven": False,
        "source_specific_DOL_requires_independent_review": True,
        "methodology_certified": False,
        "economic_edge_proven": False,
        "order_authority": False,
    }
