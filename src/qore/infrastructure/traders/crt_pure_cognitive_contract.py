"""Frozen cognitive architecture contract for VT08 CRT PURE.

This module reuses mature QORE cognitive patterns without importing any strategy logic
from VT31, Turtle Soup, Capitalizer, CRT-AMD, or another trader.  It freezes cognition
only; CRT methodology remains source-bound to the approved CRT corpus.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

CRT_PURE_COGNITIVE_CONTRACT_ID = "VT08_CRT_PURE_COGNITIVE_CONTRACT_V1"


class CrtPureCognitiveLayer(StrEnum):
    MASTER_BRAIN = "MASTER_BRAIN"
    GLOBAL_WORLD_MODEL = "GLOBAL_WORLD_MODEL"
    MARKET_BRAINS = "MARKET_BRAINS"
    DATA_PERCEPTION_INTEGRITY = "DATA_PERCEPTION_INTEGRITY"
    CRT_STRATEGY_IDENTITY = "CRT_STRATEGY_IDENTITY"
    CIBO_MARKET_MEMORY = "CIBO_MARKET_MEMORY"
    CRT_EXPERIENCE_MEMORY = "CRT_EXPERIENCE_MEMORY"
    ATTENTION_SYSTEM = "ATTENTION_SYSTEM"
    CAUSAL_SITUATION_MODEL = "CAUSAL_SITUATION_MODEL"
    HYPOTHESIS_LIFECYCLE = "HYPOTHESIS_LIFECYCLE"
    CROSS_MARKET_CAUSALITY = "CROSS_MARKET_CAUSALITY"
    OPPORTUNITY_COMPETITION = "OPPORTUNITY_COMPETITION"
    UNCERTAINTY_METACOGNITION = "UNCERTAINTY_METACOGNITION"
    ADVERSARIAL_REASONING = "ADVERSARIAL_REASONING"
    DECISION_SOVEREIGNTY = "DECISION_SOVEREIGNTY"
    JOURNEY_DESTINATION_INTELLIGENCE = "JOURNEY_DESTINATION_INTELLIGENCE"
    POSITION_INTELLIGENCE = "POSITION_INTELLIGENCE"
    COGNITIVE_AUDIT = "COGNITIVE_AUDIT"


COGNITIVE_LAYER_ORDER: tuple[CrtPureCognitiveLayer, ...] = tuple(CrtPureCognitiveLayer)


class CrtPureAttentionState(StrEnum):
    BACKGROUND = "BACKGROUND"
    WATCH = "WATCH"
    FOCUSED = "FOCUSED"
    DECISION = "DECISION"
    POSITION = "POSITION"


class CrtPureHypothesisStage(StrEnum):
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


class CrtPureKnowledgeState(StrEnum):
    KNOWN = "KNOWN"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    CONFLICTED = "CONFLICTED"


class CrtPureEpistemicReadiness(StrEnum):
    WELL_SUPPORTED = "WELL_SUPPORTED"
    CONDITIONALLY_SUPPORTED = "CONDITIONALLY_SUPPORTED"
    UNRESOLVED = "UNRESOLVED"
    CONFLICTED = "CONFLICTED"


class CrtPureReasoningAction(StrEnum):
    EXECUTE = "EXECUTE"
    WAIT = "WAIT"
    ABSTAIN = "ABSTAIN"


class CrtPurePositionAction(StrEnum):
    HOLD = "HOLD"
    PROTECT = "PROTECT"
    EXIT = "EXIT"


@dataclass(frozen=True, slots=True)
class CrtPureMarketBrainIdentity:
    market: CrtPureMarket
    strategy_identity_id: str
    cibo_market_memory_id: str
    experience_memory_id: str

    def __post_init__(self) -> None:
        if not self.strategy_identity_id:
            raise ValueError("strategy identity id must be non-empty")
        if not self.cibo_market_memory_id:
            raise ValueError("CIBO market memory id must be non-empty")
        if not self.experience_memory_id:
            raise ValueError("experience memory id must be non-empty")


CRT_PURE_MARKET_BRAINS: tuple[CrtPureMarketBrainIdentity, ...] = (
    CrtPureMarketBrainIdentity(
        market=CrtPureMarket.AUDUSD,
        strategy_identity_id="CRT_PURE_COMMON_STRATEGY_IDENTITY",
        cibo_market_memory_id="CIBO_AUDUSD_MARKET_MEMORY",
        experience_memory_id="CRT_PURE_AUDUSD_EXPERIENCE_MEMORY",
    ),
    CrtPureMarketBrainIdentity(
        market=CrtPureMarket.USDJPY,
        strategy_identity_id="CRT_PURE_COMMON_STRATEGY_IDENTITY",
        cibo_market_memory_id="CIBO_USDJPY_MARKET_MEMORY",
        experience_memory_id="CRT_PURE_USDJPY_EXPERIENCE_MEMORY",
    ),
    CrtPureMarketBrainIdentity(
        market=CrtPureMarket.BTCUSD,
        strategy_identity_id="CRT_PURE_COMMON_STRATEGY_IDENTITY",
        cibo_market_memory_id="CIBO_BTCUSD_MARKET_MEMORY",
        experience_memory_id="CRT_PURE_BTCUSD_EXPERIENCE_MEMORY",
    ),
)


@dataclass(frozen=True, slots=True)
class CrtPureCognitiveContract:
    contract_id: str = CRT_PURE_COGNITIVE_CONTRACT_ID
    layers: tuple[CrtPureCognitiveLayer, ...] = COGNITIVE_LAYER_ORDER
    markets: tuple[CrtPureMarket, ...] = (
        CrtPureMarket.AUDUSD,
        CrtPureMarket.USDJPY,
        CrtPureMarket.BTCUSD,
    )
    source_fidelity_required: bool = True
    crt_amd_allowed: bool = False
    causal_decision_time_only: bool = True
    future_outcome_visibility: bool = False
    online_self_training_allowed: bool = False
    runtime_strategy_mutation_allowed: bool = False
    market_experience_isolated: bool = True
    cibo_may_rewrite_strategy_identity: bool = False
    experience_may_rewrite_strategy_identity: bool = False
    pnl_may_rewrite_strategy_identity: bool = False
    killed_thesis_may_resurrect: bool = False
    same_source_fallback_after_abstain_allowed: bool = False
    genuinely_new_event_required_after_abstain: bool = True
    fake_numeric_confidence_allowed: bool = False
    adversarial_falsification_required: bool = True
    every_decision_requires_auditable_why: bool = True
    stop_may_widen_after_entry: bool = False
    qore_risk_is_final_capital_authority: bool = True
    cognitive_can_grant_capital_authority: bool = False
    demo_authorized: bool = False
    live_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if self.contract_id != CRT_PURE_COGNITIVE_CONTRACT_ID:
            raise ValueError("CRT PURE cognitive contract identity is frozen")
        if self.layers != COGNITIVE_LAYER_ORDER:
            raise ValueError("CRT PURE cognitive layer order is frozen")
        if self.markets != (
            CrtPureMarket.AUDUSD,
            CrtPureMarket.USDJPY,
            CrtPureMarket.BTCUSD,
        ):
            raise ValueError("CRT PURE cognition requires exact three-market scope")
        if not self.source_fidelity_required or self.crt_amd_allowed:
            raise ValueError("CRT PURE requires source fidelity and excludes CRT-AMD")
        if not self.causal_decision_time_only or self.future_outcome_visibility:
            raise ValueError("CRT PURE cognition must remain causal and no-lookahead")
        if self.online_self_training_allowed or self.runtime_strategy_mutation_allowed:
            raise ValueError("CRT PURE cannot self-train or mutate strategy at runtime")
        if not self.market_experience_isolated:
            raise ValueError("CRT market experience must remain isolated")
        if (
            self.cibo_may_rewrite_strategy_identity
            or self.experience_may_rewrite_strategy_identity
            or self.pnl_may_rewrite_strategy_identity
        ):
            raise ValueError("context/memory/PnL cannot rewrite CRT identity")
        if self.killed_thesis_may_resurrect:
            raise ValueError("killed CRT thesis cannot resurrect")
        if self.same_source_fallback_after_abstain_allowed:
            raise ValueError("ABSTAIN cannot be bypassed on the same source event")
        if not self.genuinely_new_event_required_after_abstain:
            raise ValueError("new CRT attempt requires a genuinely new causal event")
        if self.fake_numeric_confidence_allowed:
            raise ValueError("CRT metacognition cannot fabricate numeric confidence")
        if not self.adversarial_falsification_required:
            raise ValueError("CRT cognition must try to falsify before executing")
        if not self.every_decision_requires_auditable_why:
            raise ValueError("CRT cognitive decisions require an auditable WHY")
        if self.stop_may_widen_after_entry:
            raise ValueError("CRT Position Intelligence cannot widen a stop")
        if not self.qore_risk_is_final_capital_authority:
            raise ValueError("QORE Risk sovereignty is mandatory")
        if self.cognitive_can_grant_capital_authority:
            raise ValueError("CRT cognition cannot grant capital authority")
        if self.demo_authorized or self.live_authorized or self.production_authorized:
            raise ValueError("cognitive foundation grants no deployment authority")


FROZEN_CRT_PURE_COGNITIVE_CONTRACT = CrtPureCognitiveContract()
