# ruff: noqa: I001
"""Machine-readable maximum cognitive ceiling program for Shared Brain.

This manifest turns the owner-approved architecture into an ordered engineering
program. It is deliberately separate from runtime cognition: it describes what
must be built and the gates each capability must pass before the next layer may
depend on it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


PROGRAM_ID: Final = "QORE_META_COGNITIVE_SCIENTIFIC_INTELLIGENCE_005"


TRANSVERSAL_ARCHITECTURE_REQUIREMENTS: Final = (
    "COGNITIVE_FIREWALL",
    "MARKET_CORE_COGNITIVE_REALITY_PLANES",
    "QORE_CORE_DIGITAL_TWIN",
    "INFRASTRUCTURE_INTELLIGENCE",
    "BROKER_INTELLIGENCE",
    "UNKNOWN_WORLD_FIRST_CLASS",
    "REFLEXIVITY_ENGINE",
    "NEGATIVE_EVIDENCE_ENGINE",
    "ACTIVE_PERCEPTION",
    "VALUE_OF_INFORMATION",
    "SELF_MODEL",
    "VALUE_OF_COMPUTATION",
    "COGNITIVE_FAILURE_MEMORY",
    "KNOWLEDGE_HALF_LIFE",
    "KNOWLEDGE_TRANSPORTABILITY",
    "MARKET_INVARIANT_DISCOVERY",
    "ONTOLOGY_EVOLUTION",
    "BLINDSPOT_ENGINE",
    "PROVENANCE_GRAPH",
    "ANTI_HALLUCINATION_ABSTENTION",
    "SECURITY_TRUST_BOUNDARIES",
    "DEGRADED_MODE",
    "RUNTIME_COGNITIVE_TIERS",
    "DISTRIBUTED_COGNITIVE_ATTENTION",
)


@dataclass(frozen=True, slots=True)
class WorkPackage:
    work_id: str
    name: str
    depends_on: tuple[str, ...]
    required_outputs: tuple[str, ...]
    exit_gates: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.work_id.startswith("WP-"):
            raise ValueError("work_id must use WP-* identity")
        if not self.name:
            raise ValueError("work-package name must be non-empty")
        if not self.required_outputs:
            raise ValueError("work package must define outputs")
        if not self.exit_gates:
            raise ValueError("work package must define exit gates")


WORK_CHAIN: Final = (
    WorkPackage(
        "WP-01",
        "Probabilistic Market Digital Twin",
        (),
        (
            "continuous_market_world_state",
            "market_core_cognitive_reality_planes",
            "qore_core_digital_twin",
            "infrastructure_observation_state",
            "broker_observation_state",
            "observable_state",
            "latent_state",
            "behavior_state",
            "liquidity_topology",
            "volatility_topology",
            "cross_market_dependencies",
            "regime_structure",
            "uncertainty",
            "expected_state_transitions",
            "prediction_error_ledger",
        ),
        (
            "deterministic_point_in_time_replay",
            "no_future_leakage",
            "prediction_error_accounting",
            "no_trading_authority",
        ),
    ),
    WorkPackage(
        "WP-02",
        "Federation of Worlds",
        ("WP-01",),
        (
            "momentum_world",
            "liquidity_world",
            "mean_reversion_world",
            "inventory_or_agency_world",
            "macro_or_event_world",
            "unknown_regime_world",
            "reflexive_or_crowding_world",
            "posterior_world_weights",
            "world_model_disagreement",
        ),
        (
            "calibrated_world_posteriors",
            "prediction_error_scoring",
            "causal_coherence_scoring",
            "trajectory_accuracy_scoring",
            "single_world_monopoly_forbidden",
        ),
    ),
    WorkPackage(
        "WP-03",
        "Causal Discovery Engine",
        ("WP-02",),
        (
            "candidate_causal_relations",
            "conditional_independence_controls",
            "cross_regime_stability",
            "counterfactual_consistency",
            "falsification_evidence",
            "replication_evidence",
        ),
        (
            "precedence_is_not_causality",
            "observational_association_research_only",
            "replication_before_validation",
        ),
    ),
    WorkPackage(
        "WP-04",
        "Market Representation Discovery",
        ("WP-03",),
        (
            "latent_concept_discovery",
            "concept_provenance",
            "episode_clusters",
            "predictive_contribution",
            "interpretable_probes",
            "ontology_evolution_candidates",
            "market_invariant_candidates",
        ),
        (
            "out_of_sample_incremental_information",
            "no_identity_leakage",
            "human_ontology_not_a_ceiling",
        ),
    ),
    WorkPackage(
        "WP-05",
        "Temporal Hierarchical Brain",
        ("WP-04",),
        (
            "microstructure_state",
            "seconds_state",
            "m1_state",
            "m3_state",
            "m5_state",
            "m15_state",
            "h1_state",
            "h4_state",
            "daily_state",
            "weekly_state",
            "macro_regime_state",
            "cross_level_reconciliation",
            "bottom_up_causal_propagation",
            "top_down_context_conditioning",
            "critical_transition_state",
            "recovery_and_irreversibility_state",
        ),
        (
            "local_pressure_not_equal_structural_reversal",
            "reversal_requires_higher_level_fragility_or_transition",
            "reduce_false_structural_failure_without_recall_loss",
        ),
    ),
    WorkPackage(
        "WP-06",
        "Market Agency Model",
        ("WP-05",),
        (
            "liquidity_seeking_probability",
            "hedging_probability",
            "forced_liquidation_probability",
            "momentum_chasing_probability",
            "inventory_adjustment_probability",
            "passive_absorption_probability",
            "arbitrage_probability",
            "rebalancing_probability",
            "risk_off_transition_probability",
        ),
        (
            "agency_is_probabilistic_not_actor_identity",
            "out_of_sample_scenario_discrimination_gain",
            "calibration_gain",
        ),
    ),
    WorkPackage(
        "WP-07",
        "Counterfactual World Engine",
        ("WP-06",),
        (
            "alternative_worlds",
            "path_distribution",
            "tail_risk",
            "thesis_robustness",
            "failure_probability",
            "survivability",
        ),
        (
            "no_hindsight_oracle",
            "timestamp_information_boundary",
            "causal_intervention_provenance",
        ),
    ),
    WorkPackage(
        "WP-08",
        "Epistemic Engine",
        ("WP-07",),
        (
            "belief_provenance",
            "negative_evidence",
            "active_perception_requests",
            "value_of_information",
            "supporting_evidence",
            "contradicting_evidence",
            "assumptions",
            "falsification_conditions",
            "historical_familiarity",
            "ood_risk",
            "causal_support",
            "aleatoric_uncertainty",
            "epistemic_uncertainty",
            "calibration",
        ),
        (
            "epistemic_uncertainty_reduces_assertiveness",
            "aleatoric_uncertainty_not_model_failure",
            "every_major_belief_auditable",
        ),
    ),
    WorkPackage(
        "WP-09",
        "Scientific Society and Ensemble of Minds",
        ("WP-08",),
        (
            "observer",
            "hypothesis_generator",
            "causal_scientist",
            "statistician",
            "adversarial_critic",
            "counterfactual_analyst",
            "regime_specialist",
            "trajectory_specialist",
            "risk_of_error_analyst",
            "replication_scientist",
            "heterogeneous_model_specialists",
        ),
        (
            "minority_falsification_evidence_preserved",
            "disagreement_explicit",
            "reasoning_provenance_preserved",
            "single_model_supremacy_forbidden",
        ),
    ),
    WorkPackage(
        "WP-10",
        "Autonomous Scientific Laboratory",
        ("WP-09",),
        (
            "error_pattern_detection",
            "research_question_generation",
            "hypothesis_generation",
            "experiment_design",
            "leakage_controls",
            "falsification",
            "replication",
            "holdout",
            "stress",
            "research_conclusion",
        ),
        (
            "research_has_no_runtime_mutation_authority",
            "holdout_required",
            "replication_required",
            "stress_required",
        ),
    ),
    WorkPackage(
        "WP-11",
        "Governed Self-Improvement and Continual Learning",
        ("WP-10",),
        (
            "stable_certified_knowledge",
            "knowledge_half_life",
            "knowledge_transportability",
            "cognitive_failure_memory",
            "recent_validated_adaptation",
            "experimental_knowledge",
            "versioning",
            "rollback",
            "provenance",
            "reproduction",
            "catastrophic_forgetting_protection",
        ),
        (
            "no_direct_experimental_to_certified_promotion",
            "discovery_to_sandbox_to_falsification",
            "replication_to_holdout_to_stress_to_shadow",
            "owner_governed_certification",
        ),
    ),
    WorkPackage(
        "WP-12",
        "Cognitive Arbitration and Meta-Cognitive Scientific Intelligence",
        ("WP-11",),
        (
            "self_prediction_diagnosis",
            "self_model",
            "meta_reasoning_policy",
            "value_of_computation",
            "runtime_cognitive_tiers",
            "distributed_cognitive_attention",
            "blindspot_engine",
            "core_health_cognition",
            "misunderstanding_detection",
            "overconfidence_detection",
            "failing_world_model_detection",
            "specialist_dominance_detection",
            "regime_change_detection",
            "ontology_gap_detection",
            "research_priority_generation",
            "shared_situation",
            "sovereign_trader_adapters",
        ),
        (
            "self_diagnosis_must_improve_out_of_sample_results",
            "shared_does_not_seize_methodology",
            "qore_risk_remains_sovereign",
            "execution_remains_sovereign",
            "final_economic_certification_required",
        ),
    ),
)


FINAL_CERTIFICATION_GATES: Final = (
    "profit_factor_increases",
    "drawdown_reduces",
    "total_r_preserved_or_improved",
    "winner_count_protected",
    "winner_r_protected",
    "avoidable_losses_reduced",
    "valid_expansion_extensions_add_value",
    "fresh_holdout_pass",
    "stress_pass",
    "cross_window_replication_pass",
    "cross_regime_replication_pass",
    "no_future_leakage",
    "no_identity_shortcut",
    "no_production_self_promotion",
)


def validate_work_chain() -> None:
    """Fail closed if the ceiling program loses ordering or governance."""

    seen: set[str] = set()
    for package in WORK_CHAIN:
        if package.work_id in seen:
            raise ValueError(f"duplicate work package: {package.work_id}")
        missing = set(package.depends_on) - seen
        if missing:
            raise ValueError(
                f"{package.work_id} depends on unresolved packages: {sorted(missing)}"
            )
        seen.add(package.work_id)

    expected = tuple(f"WP-{index:02d}" for index in range(1, 13))
    actual = tuple(package.work_id for package in WORK_CHAIN)
    if actual != expected:
        raise ValueError("maximum cognitive ceiling work chain must remain WP-01..WP-12")
