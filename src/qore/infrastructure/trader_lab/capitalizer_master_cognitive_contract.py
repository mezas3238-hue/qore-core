"""Frozen master cognitive/research contract for QORE Capitalizer V2.

This module is intentionally declarative. It prevents implementation drift while the cognitive
stack is closed layer by layer. It grants no execution, capital, promotion, or production
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CAPITALIZER_IDENTITY,
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
    allowed_markets,
)

MASTER_COGNITIVE_CONTRACT_ID = "QORE_CAPITALIZER_MASTER_COGNITIVE_CONTRACT_V2"


class CapitalizerCognitiveLayer(StrEnum):
    MASTER_BRAIN = "MASTER_BRAIN"
    GLOBAL_WORLD_MODEL = "GLOBAL_WORLD_MODEL"
    SESSION_JOURNEY_INTELLIGENCE = "SESSION_JOURNEY_INTELLIGENCE"
    MARKET_BRAINS = "MARKET_BRAINS"
    DATA_PERCEPTION_INTEGRITY = "DATA_PERCEPTION_INTEGRITY"
    REGIME_INTELLIGENCE = "REGIME_INTELLIGENCE"
    CROSS_MARKET_CAUSALITY = "CROSS_MARKET_CAUSALITY"
    ATTENTION_SYSTEM = "ATTENTION_SYSTEM"
    HYPOTHESIS_LIFECYCLE = "HYPOTHESIS_LIFECYCLE"
    OPPORTUNITY_COMPETITION = "OPPORTUNITY_COMPETITION"
    UNCERTAINTY_METACOGNITION = "UNCERTAINTY_METACOGNITION"
    ADVERSARIAL_REASONING = "ADVERSARIAL_REASONING"
    DECISION_SOVEREIGNTY = "DECISION_SOVEREIGNTY"
    PORTFOLIO_POSITION_SUPERVISOR = "PORTFOLIO_POSITION_SUPERVISOR"
    POSITION_INTELLIGENCE = "POSITION_INTELLIGENCE"
    COGNITIVE_AUDIT = "COGNITIVE_AUDIT"


class CapitalizerAttentionState(StrEnum):
    BACKGROUND = "BACKGROUND"
    WATCH = "WATCH"
    FOCUSED = "FOCUSED"
    DECISION = "DECISION"
    POSITION = "POSITION"


class CapitalizerHypothesisStage(StrEnum):
    OBSERVED_EVENT = "OBSERVED_EVENT"
    HYPOTHESIS_FORMING = "HYPOTHESIS_FORMING"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    EXECUTABLE = "EXECUTABLE"
    POSITION_ACTIVE = "POSITION_ACTIVE"
    THESIS_STRENGTHENING = "THESIS_STRENGTHENING"
    THESIS_STABLE = "THESIS_STABLE"
    THESIS_WEAKENING = "THESIS_WEAKENING"
    THESIS_INVALIDATED = "THESIS_INVALIDATED"
    THESIS_KILLED = "THESIS_KILLED"


class CapitalizerCognitivePressure(StrEnum):
    NORMAL = "NORMAL"
    CAUTIOUS = "CAUTIOUS"
    HIGH_SELECTIVITY = "HIGH_SELECTIVITY"
    RECOVERY_OBSERVATION = "RECOVERY_OBSERVATION"
    STOP_SESSION = "STOP_SESSION"
    STOP_DAY = "STOP_DAY"


class CapitalizerResearchPhase(StrEnum):
    COGNITIVE_CLOSURE = "COGNITIVE_CLOSURE"
    SOURCE_STRATEGY_CLOSURE = "SOURCE_STRATEGY_CLOSURE"
    NINE_MARKET_INTEGRATED_SIMULATION = "NINE_MARKET_INTEGRATED_SIMULATION"
    MARKET_FAMILY_CAUSAL_RESEARCH = "MARKET_FAMILY_CAUSAL_RESEARCH"
    LOSS_STOP_INTELLIGENCE = "LOSS_STOP_INTELLIGENCE"
    TARGET_INTELLIGENCE = "TARGET_INTELLIGENCE"
    POSITION_MANAGEMENT_LABS = "POSITION_MANAGEMENT_LABS"
    DAILY_LOSS_FUNDED_SURVIVABILITY = "DAILY_LOSS_FUNDED_SURVIVABILITY"
    ECONOMIC_FREEZE_AND_CERTIFICATION = "ECONOMIC_FREEZE_AND_CERTIFICATION"


class CapitalizerChainStatus(StrEnum):
    FROZEN_APT = "FROZEN_APT"
    REJECTED = "REJECTED"
    RESEARCH_OPEN = "RESEARCH_OPEN"


COGNITIVE_LAYER_ORDER: tuple[CapitalizerCognitiveLayer, ...] = (
    CapitalizerCognitiveLayer.MASTER_BRAIN,
    CapitalizerCognitiveLayer.GLOBAL_WORLD_MODEL,
    CapitalizerCognitiveLayer.SESSION_JOURNEY_INTELLIGENCE,
    CapitalizerCognitiveLayer.MARKET_BRAINS,
    CapitalizerCognitiveLayer.DATA_PERCEPTION_INTEGRITY,
    CapitalizerCognitiveLayer.REGIME_INTELLIGENCE,
    CapitalizerCognitiveLayer.CROSS_MARKET_CAUSALITY,
    CapitalizerCognitiveLayer.ATTENTION_SYSTEM,
    CapitalizerCognitiveLayer.HYPOTHESIS_LIFECYCLE,
    CapitalizerCognitiveLayer.OPPORTUNITY_COMPETITION,
    CapitalizerCognitiveLayer.UNCERTAINTY_METACOGNITION,
    CapitalizerCognitiveLayer.ADVERSARIAL_REASONING,
    CapitalizerCognitiveLayer.DECISION_SOVEREIGNTY,
    CapitalizerCognitiveLayer.PORTFOLIO_POSITION_SUPERVISOR,
    CapitalizerCognitiveLayer.POSITION_INTELLIGENCE,
    CapitalizerCognitiveLayer.COGNITIVE_AUDIT,
)

RESEARCH_PHASE_ORDER: tuple[CapitalizerResearchPhase, ...] = (
    CapitalizerResearchPhase.COGNITIVE_CLOSURE,
    CapitalizerResearchPhase.SOURCE_STRATEGY_CLOSURE,
    CapitalizerResearchPhase.NINE_MARKET_INTEGRATED_SIMULATION,
    CapitalizerResearchPhase.MARKET_FAMILY_CAUSAL_RESEARCH,
    CapitalizerResearchPhase.LOSS_STOP_INTELLIGENCE,
    CapitalizerResearchPhase.TARGET_INTELLIGENCE,
    CapitalizerResearchPhase.POSITION_MANAGEMENT_LABS,
    CapitalizerResearchPhase.DAILY_LOSS_FUNDED_SURVIVABILITY,
    CapitalizerResearchPhase.ECONOMIC_FREEZE_AND_CERTIFICATION,
)

NINE_MARKET_UNIVERSE = frozenset(
    symbol
    for session in CapitalizerSession
    for symbol in allowed_markets(session)
)


@dataclass(frozen=True, slots=True)
class CapitalizerMasterCognitiveContract:
    contract_id: str = MASTER_COGNITIVE_CONTRACT_ID
    strategy_identity: str = CAPITALIZER_IDENTITY
    layers: tuple[CapitalizerCognitiveLayer, ...] = COGNITIVE_LAYER_ORDER
    research_phases: tuple[CapitalizerResearchPhase, ...] = RESEARCH_PHASE_ORDER
    market_universe: frozenset[str] = NINE_MARKET_UNIVERSE
    max_executions_per_session: int = MAX_EXECUTIONS_PER_SESSION
    max_theoretical_daily_executions: int = MAX_EXECUTIONS_PER_SESSION * 3
    positions_close_inside_session: bool = True
    max3_is_ceiling_not_quota: bool = True
    positive_pnl_alone_stops_session: bool = False
    causal_decision_time_only: bool = True
    future_outcome_visibility: bool = False
    online_self_training_allowed: bool = False
    source_fidelity_required: bool = True
    cibo_master_memory_mutation_allowed: bool = False
    qore_risk_is_final_capital_authority: bool = True
    cognitive_can_grant_capital_authority: bool = False
    no_recovery_martingale: bool = True
    audit_explanation_required: bool = True
    runtime_strategy_mutation_allowed: bool = False
    demo_authorized: bool = False
    live_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if self.contract_id != MASTER_COGNITIVE_CONTRACT_ID:
            raise ValueError("master cognitive contract identity is frozen")
        if self.strategy_identity != CAPITALIZER_IDENTITY:
            raise ValueError("master cognitive contract must bind Capitalizer identity")
        if self.layers != COGNITIVE_LAYER_ORDER:
            raise ValueError("cognitive layer order is frozen")
        if self.research_phases != RESEARCH_PHASE_ORDER:
            raise ValueError("research phase order is frozen")
        if len(self.market_universe) != 9:
            raise ValueError("Capitalizer master cognitive contract requires nine markets")
        if self.max_executions_per_session != 3:
            raise ValueError("Capitalizer MAX3 session ceiling is frozen")
        if self.max_theoretical_daily_executions != 9:
            raise ValueError("Capitalizer theoretical daily ceiling is nine")
        if not self.positions_close_inside_session:
            raise ValueError("Capitalizer positions must close inside their session")
        if not self.max3_is_ceiling_not_quota:
            raise ValueError("MAX3 cannot become a quota")
        if self.positive_pnl_alone_stops_session:
            raise ValueError("positive PnL alone cannot stop valid session flow")
        if not self.causal_decision_time_only or self.future_outcome_visibility:
            raise ValueError("Capitalizer cognition must remain causal and no-lookahead")
        if self.online_self_training_allowed:
            raise ValueError("Capitalizer cannot self-train in runtime")
        if not self.source_fidelity_required:
            raise ValueError("ICT/TTrades source fidelity is mandatory")
        if self.cibo_master_memory_mutation_allowed:
            raise ValueError("Capitalizer research cannot mutate CIBO master memory")
        if not self.qore_risk_is_final_capital_authority:
            raise ValueError("QORE Risk sovereignty is mandatory")
        if self.cognitive_can_grant_capital_authority:
            raise ValueError("cognition cannot grant capital authority")
        if not self.no_recovery_martingale:
            raise ValueError("recovery martingale is forbidden")
        if not self.audit_explanation_required:
            raise ValueError("every cognitive decision must be auditable")
        if self.runtime_strategy_mutation_allowed:
            raise ValueError("strategy identity cannot mutate in runtime")
        if self.demo_authorized or self.live_authorized or self.production_authorized:
            raise ValueError("research contract grants no deployment authority")


FROZEN_MASTER_COGNITIVE_CONTRACT = CapitalizerMasterCognitiveContract()
