"""Causal pending-fill observation builder for VT31's frozen NY source thesis.

It consumes only complete NAS100 M1 bars with closed_at <= prospective M1
open T. A backtest may know the future touch index for *attribution* but
nothing about the prospective fill candle enters this observation.

It does not authorize a fill, compute lot sizes, or create an independent
reasoning policy. Revalidation delegates to canonical reason().
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.traders.vt31_nas100_cibo_causal_structure import (
    last_causal_structure_event,
)
from qore.infrastructure.traders.vt31_nas100_cognitive_plumbing import (
    recent_liquidity_event_count_10m,
)
from qore.infrastructure.traders.vt31_nas100_market_context_runtime import (
    _completed_hour_closes,
    _completed_minute_bucket_closes,
    _directional_state,
    _raid_depth_ref,
    _recent_efficiency,
    _recent_overlap,
    _slice,
    _trend_state,
)
from qore.infrastructure.traders.vt31_nas100_post_entry_cognitive_runtime import (
    PostEntryCausalObservation,
)
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22SourceSetup,
)

_NY = ZoneInfo("America/New_York")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _range_state(value: Decimal | None) -> str:
    if value is None:
        return "unavailable"
    if value < Decimal("0.75"):
        return "compressed"
    if value <= Decimal("1.25"):
        return "normal"
    return "expanded"


def build_prospective_fill_observation(
    *,
    entry_situation: Nas100SituationModel,
    source: Vt31R22SourceSetup,
    selected_family: str,
    day_bars: Sequence[OhlcSnapshot],
    prospective_fill_open_at: datetime,
    previous_admitted_path_range: Decimal | None,
) -> PostEntryCausalObservation:
    """Reconstruct *only* close-confirmed cognition at pending M1 open T.

    Explicitly permit NY source observations only. London methodology is
    independently owned and must not inherit NY clock/session assumptions.
    Frozen prior-day,H4,reference width and setup identity are carried from
    entry when there is no freshly formed causal higher-context observation.
    """
    t = prospective_fill_open_at
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("prospective fill open must be timezone aware")
    entered_at = datetime.fromisoformat(entry_situation.as_of)
    if entered_at.tzinfo is None or entered_at.utcoffset() is None:
        raise ValueError("frozen entry timestamp must be timezone aware")
    if t < entered_at or t > source.pending_expires_at:
        raise ValueError("prospective fill outside frozen pending lifecycle")
    if entry_situation.session != "NY_AM_SILVER_BULLET":
        raise ValueError("NY fill sensor cannot reuse an unknown session contract")
    if selected_family != entry_situation.entry_evidence_family:
        raise ValueError("selected family differs from frozen entry thesis")
    for bar in day_bars:
        if bar.timeframe.seconds != 60 or bar.instrument.symbol != "NAS100":
            raise ValueError("fill revalidation requires NAS100 M1 evidence")

    # No candle with close > T is allowed to influence the new situation.
    closed = tuple(sorted(
        (bar for bar in day_bars if bar.closed_at <= t),
        key=lambda bar: bar.closed_at,
    ))
    if not closed or closed[-1].closed_at < entered_at:
        raise ValueError("missing causal completed M1 prefix at fill time")
    if len({bar.closed_at for bar in closed}) != len(closed):
        raise ValueError("duplicated completed M1 timestamp")
    # Reconstruct observed windows from completed bars, without fill candle.
    local = t.astimezone(_NY)
    local_minute = local.hour * 60 + local.minute
    current_path = _slice(closed, (0, 0, 0), (16, 0, 0), t)
    session_prefix = _slice(closed, (10, 0, 0), (11, 0, 0), t)
    if not session_prefix:
        raise ValueError("frozen NY source requires causal NY session prefix")

    high = max(_d(bar.high) for bar in current_path)
    low = min(_d(bar.low) for bar in current_path)
    ratio = (
        (high - low) / previous_admitted_path_range
        if previous_admitted_path_range is not None
        and previous_admitted_path_range > 0
        else None
    )
    h1 = _trend_state(_completed_hour_closes(closed, t, 1))
    m15 = _trend_state(_completed_minute_bucket_closes(closed, t, 15))
    if h1 == "unavailable":
        # No newly completed H1; entry H1 had to be causally reconstructed.
        h1 = entry_situation.h1_state
    if m15 == "unavailable":
        m15 = entry_situation.m15_state

    raid_at = source.structure.raid_at
    reclaim_at: datetime | None = None
    double_sided = entry_situation.double_sided_before_decision
    for bar in session_prefix:
        if bar.closed_at < raid_at:
            continue
        price = _d(bar.close)
        if reclaim_at is None:
            if (
                source.side.value == "long" and price > source.reference.low
            ) or (
                source.side.value == "short" and price < source.reference.high
            ):
                reclaim_at = bar.closed_at
        # Confirmation cannot depend on an intrabar sweep before bar close.
        if (
            source.side.value == "long"
            and _d(bar.high) > source.reference.high
        ) or (
            source.side.value == "short"
            and _d(bar.low) < source.reference.low
        ):
            double_sided = True

    family, age = last_causal_structure_event(
        session_prefix, source, t,
    )
    eligible = [
        candidate.formed_at
        for candidate in source.candidates
        if candidate.family.value == selected_family and candidate.formed_at <= t
    ]
    if not eligible:
        raise ValueError("selected entry evidence was not formed as-of fill")
    freshness_minutes = int((t - min(eligible)).total_seconds() // 60)
    if freshness_minutes < 0:
        raise ValueError("future selected entry evidence")
    return PostEntryCausalObservation(
        as_of=t.astimezone(UTC).isoformat(),
        decision_minute_ny=local_minute,
        prior_day_state=entry_situation.prior_day_state,
        h4_state=entry_situation.h4_state,
        h1_state=h1,
        premarket_state=_directional_state(
            _slice(closed, (8, 0, 0), (9, 0, 0), t)
        ),
        cash_open_state=_directional_state(
            _slice(closed, (9, 30, 0), (10, 0, 0), t)
        ),
        position_in_prior_day_range=entry_situation.position_in_prior_day_range,
        range_state=_range_state(ratio),
        volatility_state=entry_situation.volatility_state,
        current_path_vs_previous=ratio,
        reference_width_vs_prior5=entry_situation.reference_width_vs_prior5,
        raid_depth_ref=_raid_depth_ref(
            session_prefix,
            decision_at=t,
            side=entry_situation.side,
            reference_high=source.reference.high,
            reference_low=source.reference.low,
        ),
        recent_path_efficiency=_recent_efficiency(closed, t),
        recent_overlap_rate=_recent_overlap(closed, t),
        reference_reclaimed=reclaim_at is not None,
        reference_reclaim_age_minutes=(
            None if reclaim_at is None
            else int((t - reclaim_at).total_seconds() // 60)
        ),
        last_structure_event_family=family,
        last_structure_event_age_minutes=age,
        recent_liquidity_event_count_10m=recent_liquidity_event_count_10m(
            session_prefix, source, t,
        ),
        displacement_state=entry_situation.displacement_state,
        journey_stage="POST_CONFIRMATION_PRE_EXECUTION",
        dol1_state=entry_situation.dol1_state,
        dol2_state=entry_situation.dol2_state,
        dol3_state=entry_situation.dol3_state,
        extension_capacity_state=entry_situation.extension_capacity_state,
        exhaustion_state=entry_situation.exhaustion_state,
        cross_index_state=entry_situation.cross_index_state,
        m15_state=m15,
        current_open_r=None,
        entry_evidence_freshness=(
            "fresh-0-5m"
            if freshness_minutes <= 5 else "older-than-5m"
        ),
        double_sided_before_decision=double_sided,
    )
