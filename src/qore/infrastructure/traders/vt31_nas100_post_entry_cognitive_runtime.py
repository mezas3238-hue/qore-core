"""Causal post-entry cognition runtime for VT31 NAS100.

The entry thesis/reasoning is frozen at admission. After fill, VT31 may
reconstruct the *current* causal Situation Model from newly closed market
observations and re-run the full cognitive synthesis before deciding whether
to HOLD, TRAIL, EXTEND, or EXIT.

This specific market-native component currently exposes no R threshold, but
that is a component design choice, not a sovereign prohibition. VT31 may use
R-based entry or management rules elsewhere when they prove causal edge.

Absolute volume, sizing, leverage, compounding, and capital weighting remain
outside trader-certification authority.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    FullCognitivePositionState,
    MarketNativePositionDecision,
    StructuralDestinationCandidate,
    StructuralProtectionCandidate,
    assess_full_cognitive_position,
    decide_market_native_position,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import (
    Nas100ReasoningDecision,
)
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)


@dataclass(frozen=True, slots=True)
class PostEntryCausalObservation:
    """Market facts observable no later than this closed-bar timestamp."""

    as_of: str
    decision_minute_ny: int

    prior_day_state: str
    h4_state: str
    h1_state: str
    premarket_state: str
    cash_open_state: str
    position_in_prior_day_range: str
    range_state: str
    volatility_state: str
    current_path_vs_previous: Decimal | None
    reference_width_vs_prior5: Decimal | None
    raid_depth_ref: Decimal | None
    recent_path_efficiency: Decimal | None
    recent_overlap_rate: Decimal | None

    reference_reclaimed: bool
    reference_reclaim_age_minutes: int | None
    last_structure_event_family: str
    last_structure_event_age_minutes: int | None
    recent_liquidity_event_count_10m: int | None

    displacement_state: str

    journey_stage: str
    dol1_state: str
    dol2_state: str
    dol3_state: str
    extension_capacity_state: str
    exhaustion_state: str
    cross_index_state: str

    # Explicit M15 state. UNWIRED is allowed during research but blocks
    # maximum-intelligence candidate freeze/certification.
    m15_state: str = "UNWIRED"


@dataclass(frozen=True, slots=True)
class PostEntryMarketFacts:
    """Market-native execution facts for this path; never volume/sizing authority."""

    side: str
    current_stop: Decimal
    primary_structural_target: Decimal
    next_structural_target: StructuralDestinationCandidate | None
    protective_swing: StructuralProtectionCandidate | None

    primary_target_reached: bool
    primary_target_accepted: bool
    structure_invalidated: bool
    liquidity_failure_confirmed: bool
    momentum_deteriorated: bool
    regime_changed_against_thesis: bool


@dataclass(frozen=True, slots=True)
class PostEntryCognitiveDecision:
    """Auditable full-cognition decision for one causal post-entry observation."""

    cognition: FullCognitivePositionState
    position: MarketNativePositionDecision
    entry_situation_fingerprint: str
    current_situation_fingerprint: str
    full_cognition_reassessed: bool = True
    r_runtime_authority: bool = False
    r_runtime_strategy_allowed: bool = True
    volume_runtime_authority: bool = False
    sizing_authority: bool = False


def rebuild_post_entry_situation(
    *,
    entry_situation: Nas100SituationModel,
    observation: PostEntryCausalObservation,
) -> Nas100SituationModel:
    """Rebuild current situation while preserving frozen setup/entry identity."""

    return replace(
        entry_situation,
        as_of=observation.as_of,
        decision_minute_ny=observation.decision_minute_ny,
        prior_day_state=observation.prior_day_state,
        h4_state=observation.h4_state,
        h1_state=observation.h1_state,
        premarket_state=observation.premarket_state,
        cash_open_state=observation.cash_open_state,
        position_in_prior_day_range=observation.position_in_prior_day_range,
        range_state=observation.range_state,
        volatility_state=observation.volatility_state,
        current_path_vs_previous=observation.current_path_vs_previous,
        reference_width_vs_prior5=observation.reference_width_vs_prior5,
        raid_depth_ref=observation.raid_depth_ref,
        recent_path_efficiency=observation.recent_path_efficiency,
        recent_overlap_rate=observation.recent_overlap_rate,
        reference_reclaimed=observation.reference_reclaimed,
        reference_reclaim_age_minutes=(
            observation.reference_reclaim_age_minutes
        ),
        last_structure_event_family=(
            observation.last_structure_event_family
        ),
        last_structure_event_age_minutes=(
            observation.last_structure_event_age_minutes
        ),
        recent_liquidity_event_count_10m=(
            observation.recent_liquidity_event_count_10m
        ),
        displacement_state=observation.displacement_state,
        # Preserve any strategy-native R plan frozen at entry. This market-native
        # path may ignore it, but sovereignty does not allow deleting it merely
        # because it is expressed in R.
        journey_stage=observation.journey_stage,
        dol1_state=observation.dol1_state,
        dol2_state=observation.dol2_state,
        dol3_state=observation.dol3_state,
        extension_capacity_state=observation.extension_capacity_state,
        exhaustion_state=observation.exhaustion_state,
        cross_index_state=observation.cross_index_state,
        m15_state=observation.m15_state,
    )


def reassess_and_decide_post_entry(
    *,
    entry_situation: Nas100SituationModel,
    entry_reasoning: Nas100ReasoningDecision,
    observation: PostEntryCausalObservation,
    market: PostEntryMarketFacts,
    entry_tier: str | None = None,
    dol1_acceptance_observed: bool | None = None,
) -> PostEntryCognitiveDecision:
    """Use the complete current cognition before any position action."""

    if market.side != entry_situation.side:
        raise ValueError("post-entry side must match frozen entry situation")

    entry_fingerprint = entry_situation.fingerprint()
    current = rebuild_post_entry_situation(
        entry_situation=entry_situation,
        observation=observation,
    )
    cognition = assess_full_cognitive_position(
        situation=current,
        reasoning=entry_reasoning,
        entry_tier=entry_tier,
        dol1_acceptance_observed=dol1_acceptance_observed,
        entry_situation_fingerprint=entry_fingerprint,
    )
    position = decide_market_native_position(
        side=market.side,
        current_stop=market.current_stop,
        primary_structural_target=market.primary_structural_target,
        next_structural_target=market.next_structural_target,
        cognition=cognition,
        protective_swing=market.protective_swing,
        primary_target_reached=market.primary_target_reached,
        primary_target_accepted=market.primary_target_accepted,
        structure_invalidated=market.structure_invalidated,
        liquidity_failure_confirmed=market.liquidity_failure_confirmed,
        momentum_deteriorated=market.momentum_deteriorated,
        regime_changed_against_thesis=(
            market.regime_changed_against_thesis
        ),
    )

    return PostEntryCognitiveDecision(
        cognition=cognition,
        position=position,
        entry_situation_fingerprint=entry_fingerprint,
        current_situation_fingerprint=current.fingerprint(),
    )
