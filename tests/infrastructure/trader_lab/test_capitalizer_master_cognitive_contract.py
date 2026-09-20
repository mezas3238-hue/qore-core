from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    COGNITIVE_LAYER_ORDER,
    FROZEN_MASTER_COGNITIVE_CONTRACT,
    NINE_MARKET_UNIVERSE,
    RESEARCH_PHASE_ORDER,
    CapitalizerAttentionState,
    CapitalizerCognitiveLayer,
    CapitalizerHypothesisStage,
    CapitalizerResearchPhase,
)


def test_master_cognitive_contract_freezes_nine_market_max3_architecture() -> None:
    contract = FROZEN_MASTER_COGNITIVE_CONTRACT

    assert len(contract.market_universe) == 9
    assert contract.market_universe == NINE_MARKET_UNIVERSE
    assert contract.max_executions_per_session == 3
    assert contract.max_theoretical_daily_executions == 9
    assert contract.max3_is_ceiling_not_quota is True
    assert contract.positive_pnl_alone_stops_session is False
    assert contract.positions_close_inside_session is True


def test_master_cognitive_contract_freezes_required_reasoning_layers() -> None:
    contract = FROZEN_MASTER_COGNITIVE_CONTRACT

    assert contract.layers == COGNITIVE_LAYER_ORDER
    assert contract.layers[0] is CapitalizerCognitiveLayer.MASTER_BRAIN
    assert CapitalizerCognitiveLayer.GLOBAL_WORLD_MODEL in contract.layers
    assert CapitalizerCognitiveLayer.REGIME_INTELLIGENCE in contract.layers
    assert CapitalizerCognitiveLayer.CROSS_MARKET_CAUSALITY in contract.layers
    assert CapitalizerCognitiveLayer.ATTENTION_SYSTEM in contract.layers
    assert CapitalizerCognitiveLayer.HYPOTHESIS_LIFECYCLE in contract.layers
    assert CapitalizerCognitiveLayer.OPPORTUNITY_COMPETITION in contract.layers
    assert CapitalizerCognitiveLayer.COGNITIVE_AUDIT in contract.layers


def test_research_chain_requires_cognitive_then_source_then_nine_market_replay() -> None:
    assert RESEARCH_PHASE_ORDER[:4] == (
        CapitalizerResearchPhase.COGNITIVE_CLOSURE,
        CapitalizerResearchPhase.SOURCE_STRATEGY_CLOSURE,
        CapitalizerResearchPhase.NINE_MARKET_INTEGRATED_SIMULATION,
        CapitalizerResearchPhase.MARKET_FAMILY_CAUSAL_RESEARCH,
    )


def test_cognitive_contract_preserves_no_lookahead_and_risk_sovereignty() -> None:
    contract = FROZEN_MASTER_COGNITIVE_CONTRACT

    assert contract.causal_decision_time_only is True
    assert contract.future_outcome_visibility is False
    assert contract.online_self_training_allowed is False
    assert contract.source_fidelity_required is True
    assert contract.cibo_master_memory_mutation_allowed is False
    assert contract.qore_risk_is_final_capital_authority is True
    assert contract.cognitive_can_grant_capital_authority is False
    assert contract.no_recovery_martingale is True
    assert contract.audit_explanation_required is True
    assert contract.demo_authorized is False
    assert contract.live_authorized is False
    assert contract.production_authorized is False


def test_attention_and_hypothesis_lifecycle_are_explicit() -> None:
    assert tuple(CapitalizerAttentionState) == (
        CapitalizerAttentionState.BACKGROUND,
        CapitalizerAttentionState.WATCH,
        CapitalizerAttentionState.FOCUSED,
        CapitalizerAttentionState.DECISION,
        CapitalizerAttentionState.POSITION,
    )
    assert CapitalizerHypothesisStage.HYPOTHESIS_FORMING.value == "HYPOTHESIS_FORMING"
    assert CapitalizerHypothesisStage.THESIS_KILLED.value == "THESIS_KILLED"
