"""Integrated V50 decision-time cognitive snapshot for one V49 opportunity.

The snapshot reconnects the high-frequency candidate to the existing cognitive architecture
without changing the source trigger itself. It exposes:

- H1 thesis age,
- M15 -> M1 execution delay,
- DST-aware session runway,
- current M15 thesis-stop / local-M1-noise geometry,
- causal H1 target ladder,
- causal M1 execution-invalidation candidate,
- exact-state experience memory,
- metacognitive readiness.

The output is advisory. PASS means the source strategy may compete for a slot; REFINE means a
specialist has causal work to do before competition. It never executes or grants capital.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from statistics import median
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_experience_memory import (
    CapitalizerExperienceMemory,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerEpistemicReadiness,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_hf_bridge import (
    V50CognitiveAssessment,
    V50CognitiveCandidateFacts,
    V50CognitiveDisposition,
    assess_v50_cognitive_candidate,
)
from qore.infrastructure.trader_lab.capitalizer_v50_target_stop_intelligence import (
    V50DualInvalidation,
    V50H1TargetLadder,
    build_dual_invalidation,
    build_h1_target_ladder,
)

IDENTITY = "QORE_CAPITALIZER_V50_COGNITIVE_OPPORTUNITY_SNAPSHOT"
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class V50CognitiveOpportunitySnapshot:
    identity: str
    symbol: str
    session: CapitalizerSession
    observed_at: datetime
    source_opportunity: V49Opportunity
    cognitive: V50CognitiveAssessment
    target_ladder: V50H1TargetLadder
    dual_invalidation: V50DualInvalidation
    recent_m1_range_ticks: Decimal
    thesis_stop_distance_ticks: Decimal
    execution_stop_distance_ticks: Decimal | None
    target_refinement_available: bool
    stop_refinement_available: bool
    outcome_visible: bool = False
    executes_trade: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V50 cognitive snapshot identity")
        if self.outcome_visible:
            raise ValueError("V50 cognitive snapshot cannot see future outcome")
        if self.executes_trade or self.grants_capital_authority:
            raise ValueError("V50 snapshot is advisory only")
        if self.target_refinement_available != bool(self.target_ladder.candidates):
            raise ValueError("V50 target refinement availability mismatch")
        if self.stop_refinement_available != self.dual_invalidation.execution_anchor_available:
            raise ValueError("V50 stop refinement availability mismatch")


def _side(opportunity: V49Opportunity) -> CapitalizerSide:
    return (
        CapitalizerSide.LONG
        if opportunity.h1_state_direction == "BULLISH"
        else CapitalizerSide.SHORT
    )


def _session_end(moment: datetime, session: CapitalizerSession) -> datetime:
    local = moment.astimezone(NEW_YORK)
    day = local.date()
    if session is CapitalizerSession.ASIA:
        if local.time() >= time(20, 0):
            day += timedelta(days=1)
        local_end = datetime.combine(day, time(2, 0), tzinfo=NEW_YORK)
    elif session is CapitalizerSession.LONDON:
        local_end = datetime.combine(day, time(8, 30), tzinfo=NEW_YORK)
    else:
        local_end = datetime.combine(day, time(16, 0), tzinfo=NEW_YORK)
    return local_end.astimezone(moment.tzinfo)


def _minutes(left: datetime, right: datetime) -> int:
    value = int((right - left).total_seconds() // 60)
    return max(0, value)


def _recent_range_ticks(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    decision_at: datetime,
    lookback: int = 15,
) -> Decimal:
    completed = tuple(bar for bar in bars if bar.closed_at <= decision_at)
    recent = completed[-lookback:]
    if not recent:
        raise ValueError("V50 cognitive snapshot requires prior completed M1 bars")
    digits = recent[-1].digits
    if any(item.digits != digits for item in recent):
        raise ValueError("V50 recent M1 bars must share digits")
    tick = Decimal(1).scaleb(-digits)
    ranges = tuple((item.high - item.low) / tick for item in recent)
    value = Decimal(str(median([float(item) for item in ranges])))
    if value <= 0:
        raise ValueError("V50 recent M1 range must be positive")
    return value


def build_v50_cognitive_snapshot(
    opportunity: V49Opportunity,
    *,
    m1_bars: tuple[CapitalizerM1Bar, ...],
    h1_bars: tuple[V48AggregatedBar, ...],
    experience_memory: CapitalizerExperienceMemory,
    metacognitive_readiness: CapitalizerEpistemicReadiness,
    repeated_failure_state: bool = False,
    genuinely_new_causal_event: bool = True,
    session_slot_ordinal: int = 1,
) -> V50CognitiveOpportunitySnapshot:
    entry_at = datetime.fromisoformat(opportunity.m1_trigger_confirmed_at)
    h1_from = datetime.fromisoformat(opportunity.h1_state_from)
    m15_at = datetime.fromisoformat(opportunity.m15_setup_confirmed_at)
    session = CapitalizerSession(opportunity.session)
    side = _side(opportunity)
    entry = Decimal(opportunity.decision_reference_price)
    thesis_stop = Decimal(opportunity.m15_protected_swing_price)
    current_target = Decimal(opportunity.structural_target_witness_price)

    completed = tuple(bar for bar in m1_bars if bar.closed_at <= entry_at)
    if not completed:
        raise ValueError("V50 snapshot requires decision-time M1 history")
    digits = completed[-1].digits
    if any(bar.symbol != opportunity.symbol for bar in completed):
        raise ValueError("V50 snapshot M1 symbol mismatch")
    tick = Decimal(1).scaleb(-digits)

    recent_range = _recent_range_ticks(completed, decision_at=entry_at)
    thesis_stop_ticks = abs(entry - thesis_stop) / tick
    current_room_r = abs(current_target - entry) / abs(entry - thesis_stop)

    ladder = build_h1_target_ladder(
        h1_bars,
        completed,
        side=side,
        decision_at=entry_at,
        entry_price=entry,
        thesis_stop_price=thesis_stop,
    )
    dual = build_dual_invalidation(
        completed,
        side=side,
        setup_confirmed_at=m15_at,
        decision_at=entry_at,
        entry_price=entry,
        thesis_stop_price=thesis_stop,
    )
    execution_ticks = (
        None
        if dual.execution_risk_price is None
        else dual.execution_risk_price / tick
    )

    end = _session_end(entry_at, session)
    facts = V50CognitiveCandidateFacts(
        symbol=opportunity.symbol,
        session=session,
        h1_state_age_minutes=_minutes(h1_from, entry_at),
        m15_to_m1_delay_minutes=_minutes(m15_at, entry_at),
        session_minutes_remaining=_minutes(entry_at, end),
        stop_distance_ticks=thesis_stop_ticks,
        recent_m1_range_ticks=recent_range,
        destination_room_r=current_room_r,
        trigger_family=opportunity.m1_trigger_family,
        h1_basis=opportunity.h1_state_basis,
        session_slot_ordinal=session_slot_ordinal,
        metacognitive_readiness=metacognitive_readiness,
        genuinely_new_causal_event=genuinely_new_causal_event,
        repeated_failure_state=repeated_failure_state,
    )
    cognitive = assess_v50_cognitive_candidate(
        facts,
        experience_memory=experience_memory,
    )
    return V50CognitiveOpportunitySnapshot(
        identity=IDENTITY,
        symbol=opportunity.symbol,
        session=session,
        observed_at=entry_at,
        source_opportunity=opportunity,
        cognitive=cognitive,
        target_ladder=ladder,
        dual_invalidation=dual,
        recent_m1_range_ticks=recent_range,
        thesis_stop_distance_ticks=thesis_stop_ticks,
        execution_stop_distance_ticks=execution_ticks,
        target_refinement_available=bool(ladder.candidates),
        stop_refinement_available=dual.execution_anchor_available,
    )


def refinement_path(snapshot: V50CognitiveOpportunitySnapshot) -> tuple[str, ...]:
    """Return causal specialist path requested before strategy competition."""

    disposition = snapshot.cognitive.disposition
    if disposition is V50CognitiveDisposition.REFINE_STOP_GEOMETRY:
        return (
            "MARKET_STOP_COGNITIVE_ENGINE",
            "M1_EXECUTION_INVALIDATION",
            "QORE_RISK_REVIEW_REQUIRED",
        )
    if disposition is V50CognitiveDisposition.REFINE_TARGET_LADDER:
        return (
            "TARGET_DESTINATION_INTELLIGENCE",
            "H1_CAUSAL_TARGET_LADDER",
        )
    if disposition is V50CognitiveDisposition.PASS_TO_COMPETITION:
        return ("OPPORTUNITY_COMPETITION",)
    return ()
