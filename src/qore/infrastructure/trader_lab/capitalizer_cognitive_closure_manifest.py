"""Frozen Cognitive Closure Manifest V2 for QORE Capitalizer.

This manifest closes the pre-strategy cognitive architecture only. It does not claim that the
ICT/TTrades strategy source contract, market-family taxonomy, position-management laboratories,
nine-market replay, or economic certification are complete.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    COGNITIVE_LAYER_ORDER,
    CapitalizerChainStatus,
    CapitalizerCognitiveLayer,
)

COGNITIVE_CLOSURE_MANIFEST_ID = "QORE_CAPITALIZER_COGNITIVE_CLOSURE_MANIFEST_V2"


@dataclass(frozen=True, slots=True)
class CapitalizerCognitiveLayerClosure:
    layer: CapitalizerCognitiveLayer
    implementation_module: str
    invariant_scope: tuple[str, ...]
    status: CapitalizerChainStatus = CapitalizerChainStatus.FROZEN_APT

    def __post_init__(self) -> None:
        if not self.implementation_module:
            raise ValueError("cognitive layer implementation module must be non-empty")
        if not self.invariant_scope:
            raise ValueError("cognitive layer requires explicit invariant scope")
        if self.status is not CapitalizerChainStatus.FROZEN_APT:
            raise ValueError("Cognitive Closure V2 contains only FROZEN_APT layers")


_LAYER_CLOSURES: tuple[CapitalizerCognitiveLayerClosure, ...] = (
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.MASTER_BRAIN,
        "capitalizer_master_brain.py",
        ("GLOBAL_SYNTHESIS", "NO_RANKING", "NO_CAPITAL_AUTHORITY"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.GLOBAL_WORLD_MODEL,
        "capitalizer_global_world_model.py",
        ("NINE_MARKETS_EXACT", "NO_LOOKAHEAD", "SAME_SESSION_POSITIONS"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.SESSION_JOURNEY_INTELLIGENCE,
        "capitalizer_session_journey_intelligence.py",
        ("ASIA_LONDON_NEW_YORK_FORWARD_HANDOFF", "NO_SESSION_MEMORY_RESET"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.MARKET_BRAINS,
        "capitalizer_market_brain_registry.py",
        ("ONE_BRAIN_PER_MARKET", "NINE_MARKET_IDENTITY", "NO_RUNTIME_SELF_MUTATION"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.DATA_PERCEPTION_INTEGRITY,
        "capitalizer_perception_integrity.py",
        ("QUOTE_BAR_TIME_PROVENANCE_CHECKS", "FAIL_CLOSED_ON_BAD_EVIDENCE"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.REGIME_INTELLIGENCE,
        "capitalizer_regime_intelligence.py",
        ("SUPPORTED_UNRESOLVED_CONFLICTED", "NO_FINAL_FAMILY_TAXONOMY_CLAIM"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.CROSS_MARKET_CAUSALITY,
        "capitalizer_cross_market_causality.py",
        ("CAUSAL_NOT_CORRELATION_ONLY", "LEADER_FOLLOWER_REDUNDANCY_CONTRADICTION"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.ATTENTION_SYSTEM,
        "capitalizer_attention.py",
        ("BACKGROUND_WATCH_FOCUSED_DECISION_POSITION", "NO_OUTCOME_RANKING"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.HYPOTHESIS_LIFECYCLE,
        "capitalizer_hypothesis_lifecycle.py",
        ("EXPLICIT_STATE_TRANSITIONS", "KILLED_THESIS_NO_RESURRECTION"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.OPPORTUNITY_COMPETITION,
        "capitalizer_opportunity_competition.py",
        ("MAX3_SLOT_PRESSURE", "NO_WINNER_BEFORE_SOURCE_STRATEGY"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.UNCERTAINTY_METACOGNITION,
        "capitalizer_metacognition_v2.py",
        ("KNOWN_PARTIAL_UNKNOWN_CONFLICTED", "NO_FAKE_NUMERIC_CONFIDENCE"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.ADVERSARIAL_REASONING,
        "capitalizer_adversarial_reasoning_v2.py",
        ("TRY_TO_FALSIFY_BEFORE_STRATEGY", "NO_FUTURE_OUTCOME"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.DECISION_SOVEREIGNTY,
        "capitalizer_decision_sovereignty.py",
        ("PASS_TO_STRATEGY_WAIT_ABSTAIN", "COGNITIVE_CANNOT_EXECUTE"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.PORTFOLIO_POSITION_SUPERVISOR,
        "capitalizer_portfolio_position_supervisor.py",
        ("SHARED_FACTOR_AWARENESS", "NO_STOP_OR_CAPITAL_AUTHORITY"),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.POSITION_INTELLIGENCE,
        "capitalizer_position_intelligence.py",
        (
            "HOLD_PROTECT_EXIT_BASE",
            "STOP_IMPROVE_OR_HOLD_NEVER_WIDEN",
            "ADVANCED_MANAGEMENT_RESEARCH_DEFERRED",
        ),
    ),
    CapitalizerCognitiveLayerClosure(
        CapitalizerCognitiveLayer.COGNITIVE_AUDIT,
        "capitalizer_cognitive_explanation.py",
        ("DETERMINISTIC_WHY_LEDGER", "NO_FREE_FORM_HIDDEN_REASONING"),
    ),
)


@dataclass(frozen=True, slots=True)
class CapitalizerCognitiveClosureManifest:
    manifest_id: str = COGNITIVE_CLOSURE_MANIFEST_ID
    layer_closures: tuple[CapitalizerCognitiveLayerClosure, ...] = _LAYER_CLOSURES
    cognitive_base_status: CapitalizerChainStatus = CapitalizerChainStatus.FROZEN_APT

    ready_for_source_strategy_closure: bool = True
    source_strategy_closed: bool = False
    final_nine_market_family_taxonomy_closed: bool = False
    integrated_nine_market_replay_completed: bool = False
    break_even_policy_closed: bool = False
    trailing_stop_policy_closed: bool = False
    trailing_target_policy_closed: bool = False
    zig_zig_policy_closed: bool = False
    target_intelligence_closed: bool = False
    daily_loss_funded_survivability_closed: bool = False
    economic_candidate_frozen: bool = False
    wfo_mc_stress_holdout_completed: bool = False
    trader_certified: bool = False
    demo_authorized: bool = False
    live_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if self.manifest_id != COGNITIVE_CLOSURE_MANIFEST_ID:
            raise ValueError("Cognitive Closure Manifest identity is frozen")
        layers = tuple(item.layer for item in self.layer_closures)
        if layers != COGNITIVE_LAYER_ORDER:
            raise ValueError("closure manifest must cover all cognitive layers in frozen order")
        if len(set(layers)) != len(layers):
            raise ValueError("closure manifest cannot duplicate cognitive layers")
        if self.cognitive_base_status is not CapitalizerChainStatus.FROZEN_APT:
            raise ValueError("cognitive base must be FROZEN_APT to open source closure")
        if not self.ready_for_source_strategy_closure:
            raise ValueError("closed cognitive base must be ready for source strategy closure")
        if self.source_strategy_closed:
            raise ValueError("ICT/TTrades source strategy is not closed by cognitive manifest")
        if self.final_nine_market_family_taxonomy_closed:
            raise ValueError("nine market families require dedicated later laboratories")
        if self.integrated_nine_market_replay_completed:
            raise ValueError("nine-market replay occurs after source strategy closure")
        if (
            self.break_even_policy_closed
            or self.trailing_stop_policy_closed
            or self.trailing_target_policy_closed
            or self.zig_zig_policy_closed
            or self.target_intelligence_closed
        ):
            raise ValueError("advanced position/target chains remain open")
        if (
            self.daily_loss_funded_survivability_closed
            or self.economic_candidate_frozen
            or self.wfo_mc_stress_holdout_completed
            or self.trader_certified
        ):
            raise ValueError("economic/certification chains remain open")
        if self.demo_authorized or self.live_authorized or self.production_authorized:
            raise ValueError("Cognitive Closure grants no deployment authority")


FROZEN_COGNITIVE_CLOSURE_MANIFEST = CapitalizerCognitiveClosureManifest()
