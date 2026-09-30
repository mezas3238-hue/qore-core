"""V50 cognitive bridge for the high-frequency H1 -> M15 -> M1 Scalper.

V49 solved capacity but falsified economics. V50 reconnects the existing Capitalizer cognitive
stack to each intraday candidate before it consumes one of the three session slots.

This module does NOT execute, size, allocate capital, or use future outcomes. It turns causal
decision-time facts into an auditable state family and a cognitive disposition:

- thesis freshness (H1 state age),
- execution freshness (M15 -> M1 delay),
- remaining session runway,
- M1 noise versus proposed stop distance,
- destination room in R,
- trigger family / H1 basis / session slot,
- metacognitive readiness,
- exact immutable experience memory when available.

Numeric bands below are DEVELOPMENT HYPOTHESES generated from consumed V49 forensic evidence.
They are not source rules, not certified rules, and cannot be promoted without independent
validation. Their purpose is to let cognition reason about the failure modes instead of treating
every source-complete candidate as economically interchangeable.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    EvidenceStrength,
    market_is_allowed,
)
from qore.infrastructure.trader_lab.capitalizer_experience_memory import (
    CapitalizerExperienceMemory,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerEpistemicReadiness,
)

IDENTITY = "QORE_CAPITALIZER_V50_COGNITIVE_HF_BRIDGE"
HYPOTHESIS_ORIGIN = "V49_CONSUMED_DEVELOPMENT_FORENSICS"

H1_FRESH_MAX_MINUTES = 60
H1_AGING_MAX_MINUTES = 180
M15_IMMEDIATE_MAX_MINUTES = 10
M15_AGING_MAX_MINUTES = 45
SESSION_EXHAUSTING_MAX_MINUTES = 30
SESSION_LIMITED_MAX_MINUTES = 60

STOP_NOISE_TIGHT_MAX = Decimal("4")
STOP_NOISE_BALANCED_MAX = Decimal("8")
STOP_NOISE_WATCH_MAX = Decimal("12")

DESTINATION_TINY_MAX_R = Decimal("0.50")
DESTINATION_BALANCED_MAX_R = Decimal("2.00")


class V50H1Freshness(StrEnum):
    FRESH = "FRESH"
    AGING = "AGING"
    STALE = "STALE"


class V50ExecutionFreshness(StrEnum):
    IMMEDIATE = "IMMEDIATE"
    AGING = "AGING"
    LATE = "LATE"


class V50SessionRunway(StrEnum):
    AMPLE = "AMPLE"
    LIMITED = "LIMITED"
    EXHAUSTING = "EXHAUSTING"


class V50StopNoiseState(StrEnum):
    TOO_TIGHT = "TOO_TIGHT"
    BALANCED = "BALANCED"
    WIDE_WATCH = "WIDE_WATCH"
    TOO_WIDE = "TOO_WIDE"


class V50DestinationState(StrEnum):
    TINY = "TINY"
    BALANCED = "BALANCED"
    AMBITIOUS = "AMBITIOUS"
    UNKNOWN = "UNKNOWN"


class V50CognitiveDisposition(StrEnum):
    PASS_TO_COMPETITION = "PASS_TO_COMPETITION"
    WAIT_EPISTEMIC = "WAIT_EPISTEMIC"
    WAIT_REFRESH_H1 = "WAIT_REFRESH_H1"
    WAIT_REFRESH_M15 = "WAIT_REFRESH_M15"
    WAIT_SESSION_RUNWAY = "WAIT_SESSION_RUNWAY"
    REFINE_STOP_GEOMETRY = "REFINE_STOP_GEOMETRY"
    REFINE_TARGET_LADDER = "REFINE_TARGET_LADDER"
    ABSTAIN_CONFLICTED = "ABSTAIN_CONFLICTED"
    ABSTAIN_KNOWN_NEGATIVE_STATE = "ABSTAIN_KNOWN_NEGATIVE_STATE"


@dataclass(frozen=True, slots=True)
class V50CognitiveCandidateFacts:
    symbol: str
    session: CapitalizerSession
    h1_state_age_minutes: int
    m15_to_m1_delay_minutes: int
    session_minutes_remaining: int
    stop_distance_ticks: Decimal
    recent_m1_range_ticks: Decimal
    destination_room_r: Decimal | None
    trigger_family: str
    h1_basis: str
    session_slot_ordinal: int
    metacognitive_readiness: CapitalizerEpistemicReadiness
    genuinely_new_causal_event: bool
    repeated_failure_state: bool

    def __post_init__(self) -> None:
        if not market_is_allowed(session=self.session, symbol=self.symbol):
            raise ValueError("V50 candidate outside frozen Capitalizer universe")
        if min(
            self.h1_state_age_minutes,
            self.m15_to_m1_delay_minutes,
            self.session_minutes_remaining,
        ) < 0:
            raise ValueError("V50 timing facts must be non-negative")
        if self.stop_distance_ticks <= 0:
            raise ValueError("V50 stop distance must be positive")
        if self.recent_m1_range_ticks <= 0:
            raise ValueError("V50 local M1 range must be positive")
        if self.destination_room_r is not None and self.destination_room_r <= 0:
            raise ValueError("V50 destination room must be positive when known")
        if not self.trigger_family or not self.h1_basis:
            raise ValueError("V50 trigger/basis provenance must be non-empty")
        if self.session_slot_ordinal < 1:
            raise ValueError("V50 session slot ordinal must be >= 1")


@dataclass(frozen=True, slots=True)
class V50CognitiveState:
    identity: str
    state_family_id: str
    symbol: str
    session: CapitalizerSession
    h1_freshness: V50H1Freshness
    execution_freshness: V50ExecutionFreshness
    session_runway: V50SessionRunway
    stop_noise_state: V50StopNoiseState
    stop_to_noise_ratio: Decimal
    destination_state: V50DestinationState
    destination_room_r: Decimal | None
    trigger_family: str
    h1_basis: str
    session_slot_ordinal: int
    observation_tokens: tuple[str, ...]
    hypothesis_origin: str = HYPOTHESIS_ORIGIN
    outcome_visible: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V50 cognitive state identity is frozen")
        if not self.state_family_id:
            raise ValueError("V50 cognitive state requires state family id")
        if self.outcome_visible:
            raise ValueError("V50 cognitive state cannot see future outcome")


@dataclass(frozen=True, slots=True)
class V50CognitiveAssessment:
    state: V50CognitiveState
    disposition: V50CognitiveDisposition
    reasons: tuple[str, ...]
    knowledge: CapitalizerKnowledgeState
    experience_observations: int
    experience_mean_r: Decimal | None
    experience_strength: EvidenceStrength
    strategy_may_evaluate: bool
    requests_stop_refinement: bool
    requests_target_refinement: bool
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False
    rule_promotion_allowed: bool = False

    def __post_init__(self) -> None:
        if self.grants_entry_authority:
            raise ValueError("V50 cognition cannot grant entry authority")
        if self.grants_capital_authority:
            raise ValueError("V50 cognition cannot grant capital authority")
        if self.rule_promotion_allowed:
            raise ValueError("V50 development cognition cannot promote rules")
        if self.strategy_may_evaluate != (
            self.disposition is V50CognitiveDisposition.PASS_TO_COMPETITION
        ):
            raise ValueError("strategy_may_evaluate must match PASS_TO_COMPETITION")


def _h1_freshness(minutes: int) -> V50H1Freshness:
    if minutes <= H1_FRESH_MAX_MINUTES:
        return V50H1Freshness.FRESH
    if minutes <= H1_AGING_MAX_MINUTES:
        return V50H1Freshness.AGING
    return V50H1Freshness.STALE


def _execution_freshness(minutes: int) -> V50ExecutionFreshness:
    if minutes <= M15_IMMEDIATE_MAX_MINUTES:
        return V50ExecutionFreshness.IMMEDIATE
    if minutes <= M15_AGING_MAX_MINUTES:
        return V50ExecutionFreshness.AGING
    return V50ExecutionFreshness.LATE


def _session_runway(minutes: int) -> V50SessionRunway:
    if minutes <= SESSION_EXHAUSTING_MAX_MINUTES:
        return V50SessionRunway.EXHAUSTING
    if minutes <= SESSION_LIMITED_MAX_MINUTES:
        return V50SessionRunway.LIMITED
    return V50SessionRunway.AMPLE


def _stop_noise_state(ratio: Decimal) -> V50StopNoiseState:
    if ratio < STOP_NOISE_TIGHT_MAX:
        return V50StopNoiseState.TOO_TIGHT
    if ratio <= STOP_NOISE_BALANCED_MAX:
        return V50StopNoiseState.BALANCED
    if ratio <= STOP_NOISE_WATCH_MAX:
        return V50StopNoiseState.WIDE_WATCH
    return V50StopNoiseState.TOO_WIDE


def _destination_state(room_r: Decimal | None) -> V50DestinationState:
    if room_r is None:
        return V50DestinationState.UNKNOWN
    if room_r < DESTINATION_TINY_MAX_R:
        return V50DestinationState.TINY
    if room_r <= DESTINATION_BALANCED_MAX_R:
        return V50DestinationState.BALANCED
    return V50DestinationState.AMBITIOUS


def build_v50_cognitive_state(
    facts: V50CognitiveCandidateFacts,
) -> V50CognitiveState:
    ratio = facts.stop_distance_ticks / facts.recent_m1_range_ticks
    h1 = _h1_freshness(facts.h1_state_age_minutes)
    execution = _execution_freshness(facts.m15_to_m1_delay_minutes)
    runway = _session_runway(facts.session_minutes_remaining)
    stop_state = _stop_noise_state(ratio)
    destination = _destination_state(facts.destination_room_r)

    tokens = (
        f"SYMBOL={facts.symbol}",
        f"SESSION={facts.session.value}",
        f"H1_FRESHNESS={h1.value}",
        f"M15_M1_FRESHNESS={execution.value}",
        f"SESSION_RUNWAY={runway.value}",
        f"STOP_NOISE={stop_state.value}",
        f"DESTINATION={destination.value}",
        f"TRIGGER={facts.trigger_family}",
        f"H1_BASIS={facts.h1_basis}",
        f"SLOT={facts.session_slot_ordinal}",
        (
            "NEW_CAUSAL_EVENT=YES"
            if facts.genuinely_new_causal_event
            else "NEW_CAUSAL_EVENT=NO"
        ),
    )
    digest = hashlib.sha256("|".join(tokens).encode("utf-8")).hexdigest()
    return V50CognitiveState(
        identity=IDENTITY,
        state_family_id=f"V50:{digest}",
        symbol=facts.symbol,
        session=facts.session,
        h1_freshness=h1,
        execution_freshness=execution,
        session_runway=runway,
        stop_noise_state=stop_state,
        stop_to_noise_ratio=ratio,
        destination_state=destination,
        destination_room_r=facts.destination_room_r,
        trigger_family=facts.trigger_family,
        h1_basis=facts.h1_basis,
        session_slot_ordinal=facts.session_slot_ordinal,
        observation_tokens=tokens,
    )


def assess_v50_cognitive_candidate(
    facts: V50CognitiveCandidateFacts,
    *,
    experience_memory: CapitalizerExperienceMemory,
) -> V50CognitiveAssessment:
    """Adjudicate a candidate without seeing its future outcome."""

    state = build_v50_cognitive_state(facts)
    experience = experience_memory.lookup(
        symbol=facts.symbol,
        session=facts.session,
        state_family_id=state.state_family_id,
    )
    knowledge = CapitalizerKnowledgeState.UNKNOWN
    observations = 0
    mean_r: Decimal | None = None
    strength = EvidenceStrength.UNKNOWN
    if experience is not None:
        calibration = experience.calibration
        observations = calibration.observations
        mean_r = calibration.mean_r
        strength = calibration.strength
        if strength is EvidenceStrength.LOW:
            knowledge = CapitalizerKnowledgeState.PARTIAL
        elif strength in {EvidenceStrength.MEDIUM, EvidenceStrength.HIGH}:
            knowledge = CapitalizerKnowledgeState.KNOWN

    if facts.metacognitive_readiness is CapitalizerEpistemicReadiness.CONFLICTED:
        return V50CognitiveAssessment(
            state=state,
            disposition=V50CognitiveDisposition.ABSTAIN_CONFLICTED,
            reasons=("METACOGNITION_CONFLICTED",),
            knowledge=CapitalizerKnowledgeState.CONFLICTED,
            experience_observations=observations,
            experience_mean_r=mean_r,
            experience_strength=strength,
            strategy_may_evaluate=False,
            requests_stop_refinement=False,
            requests_target_refinement=False,
        )

    if (
        experience is not None
        and strength in {EvidenceStrength.MEDIUM, EvidenceStrength.HIGH}
        and mean_r is not None
        and mean_r < 0
    ):
        return V50CognitiveAssessment(
            state=state,
            disposition=V50CognitiveDisposition.ABSTAIN_KNOWN_NEGATIVE_STATE,
            reasons=("EXACT_STATE_FAMILY_NEGATIVE_MEMORY",),
            knowledge=knowledge,
            experience_observations=observations,
            experience_mean_r=mean_r,
            experience_strength=strength,
            strategy_may_evaluate=False,
            requests_stop_refinement=False,
            requests_target_refinement=False,
        )

    if facts.repeated_failure_state and not facts.genuinely_new_causal_event:
        return V50CognitiveAssessment(
            state=state,
            disposition=V50CognitiveDisposition.WAIT_EPISTEMIC,
            reasons=("REPEATED_FAILURE_REQUIRES_NEW_CAUSAL_EVENT",),
            knowledge=knowledge,
            experience_observations=observations,
            experience_mean_r=mean_r,
            experience_strength=strength,
            strategy_may_evaluate=False,
            requests_stop_refinement=False,
            requests_target_refinement=False,
        )

    if facts.metacognitive_readiness in {
        CapitalizerEpistemicReadiness.UNRESOLVED,
        CapitalizerEpistemicReadiness.CONDITIONALLY_SUPPORTED,
    }:
        return V50CognitiveAssessment(
            state=state,
            disposition=V50CognitiveDisposition.WAIT_EPISTEMIC,
            reasons=(f"EPISTEMIC_{facts.metacognitive_readiness.value}",),
            knowledge=knowledge,
            experience_observations=observations,
            experience_mean_r=mean_r,
            experience_strength=strength,
            strategy_may_evaluate=False,
            requests_stop_refinement=False,
            requests_target_refinement=False,
        )

    if state.h1_freshness is V50H1Freshness.STALE:
        return V50CognitiveAssessment(
            state=state,
            disposition=V50CognitiveDisposition.WAIT_REFRESH_H1,
            reasons=("H1_CONTEXT_STALE",),
            knowledge=knowledge,
            experience_observations=observations,
            experience_mean_r=mean_r,
            experience_strength=strength,
            strategy_may_evaluate=False,
            requests_stop_refinement=False,
            requests_target_refinement=False,
        )

    if state.execution_freshness is V50ExecutionFreshness.LATE:
        return V50CognitiveAssessment(
            state=state,
            disposition=V50CognitiveDisposition.WAIT_REFRESH_M15,
            reasons=("M15_SETUP_EXECUTION_WINDOW_STALE",),
            knowledge=knowledge,
            experience_observations=observations,
            experience_mean_r=mean_r,
            experience_strength=strength,
            strategy_may_evaluate=False,
            requests_stop_refinement=False,
            requests_target_refinement=False,
        )

    if state.session_runway is V50SessionRunway.EXHAUSTING:
        return V50CognitiveAssessment(
            state=state,
            disposition=V50CognitiveDisposition.WAIT_SESSION_RUNWAY,
            reasons=("SESSION_RUNWAY_EXHAUSTING",),
            knowledge=knowledge,
            experience_observations=observations,
            experience_mean_r=mean_r,
            experience_strength=strength,
            strategy_may_evaluate=False,
            requests_stop_refinement=False,
            requests_target_refinement=False,
        )

    if state.stop_noise_state in {
        V50StopNoiseState.TOO_TIGHT,
        V50StopNoiseState.TOO_WIDE,
    }:
        return V50CognitiveAssessment(
            state=state,
            disposition=V50CognitiveDisposition.REFINE_STOP_GEOMETRY,
            reasons=(f"STOP_NOISE_{state.stop_noise_state.value}",),
            knowledge=knowledge,
            experience_observations=observations,
            experience_mean_r=mean_r,
            experience_strength=strength,
            strategy_may_evaluate=False,
            requests_stop_refinement=True,
            requests_target_refinement=False,
        )

    if state.destination_state in {
        V50DestinationState.TINY,
        V50DestinationState.AMBITIOUS,
        V50DestinationState.UNKNOWN,
    }:
        return V50CognitiveAssessment(
            state=state,
            disposition=V50CognitiveDisposition.REFINE_TARGET_LADDER,
            reasons=(f"DESTINATION_{state.destination_state.value}",),
            knowledge=knowledge,
            experience_observations=observations,
            experience_mean_r=mean_r,
            experience_strength=strength,
            strategy_may_evaluate=False,
            requests_stop_refinement=False,
            requests_target_refinement=True,
        )

    return V50CognitiveAssessment(
        state=state,
        disposition=V50CognitiveDisposition.PASS_TO_COMPETITION,
        reasons=("CAUSAL_COGNITIVE_STATE_COHERENT",),
        knowledge=knowledge,
        experience_observations=observations,
        experience_mean_r=mean_r,
        experience_strength=strength,
        strategy_may_evaluate=True,
        requests_stop_refinement=False,
        requests_target_refinement=False,
    )
