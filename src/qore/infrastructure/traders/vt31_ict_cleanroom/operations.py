"""Brand-new Silver Bullet OPS model. No legacy VT31 imports or market policy.

A COG architect emits CognitiveDecision on closed M1. OPS independently
validates the exact ICT NY clock, directional first suitable FVG, and
as-of origin. No live order, no broker fill, no economic performance.

Only QORE RESEARCH parameters:
- all three M1 forming a gap inside original ICT clock
- CE midpoint observational pending candidate
- stop/fill policy not implemented
Those details are NOT all unconditional claims from ICT's 2023 video.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime

from .contracts import (
    MIN_INDEX_POINTS,
    CognitiveDecision,
    FvgCandidate,
    M1Bar,
    MethodologyDecision,
    SessionId,
    Side,
    utc,
    window_bounds,
)
from .m1_execution import confirmed_m1_fvg, required_timeframe_contract


class IctSilverBulletOperations:
    """Independent state for exactly one session/day, no position authority."""

    def __init__(self, *, session: SessionId, day: datetime) -> None:
        self.session = session
        self.start, self.end = window_bounds(day, session)
        self.last_closed: datetime | None = None
        self.decision = MethodologyDecision.AWAIT_COGNITION
        self.first_suitable: FvgCandidate | None = None
        self.cognitive_source: str | None = None
        self.cognitive_version: str | None = None
        self.intrawindow_raw_fvg_count = 0
        self.suitable_candidates_skipped_after_first = 0
        self.event_at: datetime | None = None
        self.source_invalidation_reason: str | None = None
        self._bars: deque[M1Bar] = deque(maxlen=3)

    def on_closed_m1(
        self, bar: M1Bar, *, cognition: CognitiveDecision | None
    ) -> MethodologyDecision:
        """Called only when M1 bar closes; same bar H/L never an entry fill."""
        opened = utc(bar.opened_at)
        closed = utc(bar.closed_at)
        if not self.start <= opened < self.end:
            raise ValueError("M1 outside original Silver Bullet source window")
        if self.last_closed is not None and opened != self.last_closed:
            raise ValueError("M1 missing, duplicate or out-of-order")
        if cognition is not None:
            if cognition.session != self.session:
                raise ValueError("cross-session cognitive leakage")
            if utc(cognition.observed_at) != closed:
                raise ValueError(
                    "cognition must be freshly assessed on EXACT current closed M1"
                )
            if utc(cognition.structure_break_confirmed_at) > closed:
                raise ValueError("future MSS")
            if utc(cognition.draw_level_observed_at) > closed:
                raise ValueError("future liquidity")
        self.last_closed = closed

        # P0: source-qualified pending orders MUST retain a FRESH, still
        # valid cognitive thesis. When DOL is swept, pivot is revoked,
        # context disappears, or a different DOL/MSS is chosen, COG sends
        # None or a changed decision. Absence is NEVER silent permission.
        # This observation happens only at this bar's CLOSE; it does NOT
        # imply any intrabar cancellation or predict historical tick order.
        selected = self.first_suitable
        if selected is not None and self.decision in (
            MethodologyDecision.RESEARCH_PENDING_CE,
            MethodologyDecision.RESEARCH_TOUCH_NOT_FILL,
        ):
            reason: str | None = None
            if cognition is None:
                reason = "COGNITIVE_THESIS_REVOKED_OR_UNAVAILABLE"
            elif (
                cognition.side != selected.side
                or cognition.draw_target != selected.target_price
            ):
                reason = "CAUSAL_DOL_DIRECTION_OR_TARGET_CHANGED"
            elif utc(cognition.structure_break_confirmed_at) > utc(
                selected.formed_at
            ):
                reason = "ORIGINAL_M1_MSS_THESIS_REPLACED"
            if reason is not None:
                self.decision = MethodologyDecision.SOURCE_INVALIDATED
                self.source_invalidation_reason = reason
                self.event_at = closed
                return self.decision

        # Selected FVG is immutable. Current candle is used ONLY AFTER
        # close for a research-price-path observation, NEVER broker fill.
        if self.first_suitable is not None:
            first = self.first_suitable
            if self.decision == MethodologyDecision.RESEARCH_PENDING_CE:
                touch = bar.low <= first.consequent_encroachment <= bar.high
                break_gap = (
                    bar.close < first.lower
                    if first.side == Side.LONG else bar.close > first.upper
                )
                if touch and break_gap:
                    self.decision = MethodologyDecision.AMBIGUOUS_PRICE_PATH
                    self.event_at = closed
                elif break_gap:
                    self.decision = MethodologyDecision.SOURCE_INVALIDATED
                    self.event_at = closed
                elif touch:
                    self.decision = MethodologyDecision.RESEARCH_TOUCH_NOT_FILL
                    self.event_at = closed
            if closed >= self.end and self.decision == MethodologyDecision.RESEARCH_PENDING_CE:
                self.decision = MethodologyDecision.WINDOW_EXPIRED
                self.event_at = closed
            return self.decision

        self._bars.append(bar)
        if len(self._bars) < 3:
            if closed >= self.end:
                self.decision = MethodologyDecision.WINDOW_EXPIRED
            return self.decision

        a, b, current = self._bars
        if utc(a.closed_at) != utc(b.opened_at) or utc(b.closed_at) != opened:
            raise ValueError("non-contiguous triple")
        m1_gap = confirmed_m1_fvg(
            session=self.session, first=a, middle=b, third=current
        )
        if m1_gap is not None:
            self.intrawindow_raw_fvg_count += 1

        if closed >= self.end:
            self.decision = MethodologyDecision.WINDOW_EXPIRED
            return self.decision
        if cognition is None:
            self.decision = MethodologyDecision.AWAIT_COGNITION
            return self.decision
        if not isinstance(cognition.side, Side):
            raise ValueError("unproven cognitive direction")
        if m1_gap is None or cognition.side != m1_gap.side:
            self.decision = MethodologyDecision.AWAIT_FVG
            return self.decision
        if utc(cognition.structure_break_confirmed_at) > closed:
            self.decision = MethodologyDecision.AWAIT_FVG
            return self.decision
        if cognition.side == Side.LONG and current.close <= cognition.structure_level:
            self.decision = MethodologyDecision.AWAIT_FVG
            return self.decision
        if cognition.side == Side.SHORT and current.close >= cognition.structure_level:
            self.decision = MethodologyDecision.AWAIT_FVG
            return self.decision

        # Trading shape originates ONLY from the three actual CLOSED M1
        # bars; M15/H1/H4 from cognition can inform DOL but cannot create
        # or time the trigger candle.
        lower, upper = m1_gap.zone_low, m1_gap.zone_high
        midpoint = m1_gap.consequent_encroachment
        room = (
            cognition.draw_target - current.close
            if cognition.side == Side.LONG else current.close - cognition.draw_target
        )
        if room < MIN_INDEX_POINTS or (
            cognition.side == Side.LONG and cognition.draw_target <= midpoint
        ) or (
            cognition.side == Side.SHORT and cognition.draw_target >= midpoint
        ):
            self.decision = MethodologyDecision.AWAIT_FVG
            return self.decision

        self.first_suitable = FvgCandidate(
            session=self.session, side=cognition.side,
            formed_at=closed, first_candle_open=utc(a.opened_at),
            lower=lower, upper=upper, consequent_encroachment=midpoint,
            target_price=cognition.draw_target, projected_index_points=room,
            observed_context_at=utc(cognition.observed_at),
        )
        self.cognitive_source = cognition.source_provenance
        self.cognitive_version = cognition.cognitive_version
        self.decision = MethodologyDecision.RESEARCH_PENDING_CE
        return self.decision

    def snapshot(self) -> dict[str, object]:
        candidate = self.first_suitable
        return {
            "schema": "qore.vt31.cleanroom.ops.v1",
            "session": self.session.value,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "last_closed_m1": None if self.last_closed is None else self.last_closed.isoformat(),
            "phase": self.decision.value,
            "raw_fvg_count": self.intrawindow_raw_fvg_count,
            "source": "ICT_2023_SILVER_BULLET",
            "execution_timeframe": "M1",
            "structure_execution_timeframe": "M1",
            "fvg_timeframe": "M1",
            "higher_timeframes_role": "CONTEXT_ONLY",
            "m1_execution_contract": required_timeframe_contract(),
            "fvg": None if candidate is None else {
                "direction": candidate.side.value,
                "formed_at": candidate.formed_at.isoformat(),
                "first_m1_open": candidate.first_candle_open.isoformat(),
                "formed_by_closed_m1": True,
                "candle_duration_seconds": 60,
                "zone_low": str(candidate.lower),
                "zone_high": str(candidate.upper),
                "ce_midpoint_research_only": str(candidate.consequent_encroachment),
                "draw_target": str(candidate.target_price),
                "projected_index_points": str(candidate.projected_index_points),
                "cognitive_observed_at": candidate.observed_context_at.isoformat(),
                "cognitive_source": self.cognitive_source,
                "cognitive_version": self.cognitive_version,
            },
            "outcome_event_at": None if self.event_at is None else self.event_at.isoformat(),
            "source_invalidation_reason": self.source_invalidation_reason,
            "cognitive_revocation_fail_closed_at_m1_close": True,
            "methodology_formalization_not_all_ict_explicit": True,
            "uses_old_vt31": False,
            "actual_mt5_fill_proven": False,
            "actual_position_management_proven": False,
            "risk_or_sizing_assigned": False,
            "trading_authorized": False,
            "certified": False,
        }
