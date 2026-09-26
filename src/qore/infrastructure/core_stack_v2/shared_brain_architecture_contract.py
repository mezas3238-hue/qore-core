"""Owner-directed cognitive architecture contract for Shared Brain.

Shared is the central market-intelligence operating system of Core. It observes,
models, reasons, remembers, falsifies and communicates. It does not replace
specialist methodology, QORE Risk or Execution sovereignty.
"""

from __future__ import annotations

from typing import Final

SHARED_BRAIN_ARCHITECTURE_VERSION: Final = "QORE_SHARED_BRAIN_COGNITIVE_OS_001"

_COGNITIVE_PIPELINE: Final = (
    "MARKET_OBSERVATION",
    "WORLD_MODEL",
    "LATENT_MARKET_STATE",
    "DYNAMIC_CAUSAL_GRAPH",
    "COMPETING_CAUSAL_HYPOTHESES",
    "ACTIVE_PERCEPTION",
    "BELIEF_STATE",
    "SCENARIO_TREE",
    "ONLINE_UPDATE",
    "METACOGNITION",
    "EPISODIC_MEMORY",
    "TRAJECTORY_INTELLIGENCE",
    "STABILITY_INTELLIGENCE",
    "COUNTERFACTUAL_INTELLIGENCE",
    "DECISION_INTELLIGENCE",
    "SHARED_SITUATION",
)

_REQUIRED_CAPABILITIES: Final = (
    "WORLD_MODEL",
    "DYNAMIC_CAUSAL_GRAPH",
    "EPISODIC_MARKET_MEMORY",
    "PREDICTIVE_STATE_MODEL",
    "ACTIVE_PERCEPTION",
    "PROBABILISTIC_BELIEF_STATE",
    "MARKET_PHYSICS_CONSTRAINTS",
    "METACOGNITION",
    "SPECIALIST_REASONING_COUNCIL",
    "ADVERSARIAL_HYPOTHESIS_TESTING",
    "COUNTERFACTUAL_SIMULATION",
    "LATENT_CONCEPT_REASONING",
    "TRAJECTORY_INTELLIGENCE",
    "STABILITY_ENGINE",
    "MACHINE_SCIENTIFIC_DISCOVERY",
)


def shared_brain_architecture_contract() -> dict[str, object]:
    """Return the frozen cognitive direction for Shared Brain."""

    return {
        "schema": "qore.shared_brain.architecture_contract.v1",
        "version": SHARED_BRAIN_ARCHITECTURE_VERSION,
        "role": "CENTRAL_MARKET_COGNITIVE_OPERATING_SYSTEM",
        "objective": (
            "Maintain a living, falsifiable theory of the market that can "
            "explain what it believes, quantify uncertainty, revise beliefs "
            "before terminal outcomes reveal error, and communicate generic "
            "market intelligence to sovereign specialist traders."
        ),
        "pipeline": _COGNITIVE_PIPELINE,
        "required_capabilities": _REQUIRED_CAPABILITIES,
        "world_model_law": {
            "price_prediction_is_not_primary_objective": True,
            "continuous_market_world_state_required": True,
            "observed_and_latent_state_separated": True,
            "causal_relations_required": True,
            "scenario_distribution_required": True,
            "expected_state_transitions_required": True,
            "anomaly_and_uncertainty_required": True,
        },
        "reasoning_law": {
            "multiple_competing_hypotheses_required": True,
            "single_story_commitment_forbidden": True,
            "hypothesis_falsification_required": True,
            "active_evidence_requests_required": True,
            "online_belief_update_required": True,
            "unknown_state_must_remain_explicit": True,
            "concept_reasoning_preferred_over_rule_accumulation": True,
            "threshold_patchwork_cannot_be_primary_intelligence": True,
        },
        "memory_law": {
            "episodic_market_memory_required": True,
            "structural_similarity_not_only_candle_similarity": True,
            "causal_sequence_similarity_required": True,
            "historical_closed_outcomes_allowed_offline": True,
            "current_episode_future_outcome_forbidden": True,
            "counterfactuals_must_respect_information_available_at_each_time": True,
        },
        "metacognition_law": {
            "confidence_required": True,
            "epistemic_uncertainty_required": True,
            "regime_familiarity_required": True,
            "model_disagreement_required": True,
            "novelty_and_ood_required": True,
            "causal_consistency_required": True,
            "historical_similarity_required": True,
            "prediction_calibration_required": True,
        },
        "trajectory_law": {
            "full_opportunity_journey_required": True,
            "normal_adversity_must_not_equal_structural_deterioration": True,
            "temporary_pullback_must_not_equal_failed_thesis": True,
            "market_noise_must_not_equal_stop_pressure": True,
            "hold_defend_exit_extend_must_be_causally_explainable": True,
        },
        "scientific_discovery_law": {
            "observation_to_hypothesis_to_falsification_required": True,
            "replication_required": True,
            "holdout_required_before_knowledge_promotion": True,
            "stress_required_before_knowledge_promotion": True,
            "temporal_stability_required": True,
            "market_stability_required": True,
        },
        "sovereignty_law": {
            "shared_observes_understands_reasons_and_communicates": True,
            "shared_is_not_a_trader": True,
            "shared_does_not_own_specialist_methodology": True,
            "specialist_traders_remain_sovereign": True,
            "qore_risk_remains_sovereign": True,
            "execution_remains_sovereign": True,
            "shared_direct_order_authority": False,
            "shared_sizing_authority": False,
            "shared_risk_budget_authority": False,
        },
    }
