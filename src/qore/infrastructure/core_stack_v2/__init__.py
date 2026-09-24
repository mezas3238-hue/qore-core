"""QORE CORE STACK V2 shared, authority-free cognitive context layer."""

from qore.infrastructure.core_stack_v2.ab import (
    DecisionABSummary,
    DecisionObservation,
    summarize_decision_ab,
)
from qore.infrastructure.core_stack_v2.adapters import (
    CoreAdapter,
    TraderCognitiveContext,
    build_shared_context,
)
from qore.infrastructure.core_stack_v2.architecture_freeze import (
    SUPERINTELLIGENCE_FREEZE_VERSION,
    superintelligence_freeze_contract,
    superintelligence_freeze_fingerprint,
)
from qore.infrastructure.core_stack_v2.audit import CoreAuditRecord, make_audit_record
from qore.infrastructure.core_stack_v2.compatibility import (
    CompatibilityEntry,
    CompatibilityStatus,
    compatibility_manifest,
    compatibility_manifest_fingerprint,
)
from qore.infrastructure.core_stack_v2.contracts import (
    CORE_STACK_VERSION,
    CognitiveState,
    CoreHypothesis,
    CoreSnapshot,
    HypothesisStatus,
    KnowledgeState,
    MarketEvent,
    PerceptionIntegrity,
    PortfolioIntent,
    PortfolioSituation,
    PositionContext,
    UncertaintyState,
    WorldState,
    freeze_facts,
)
from qore.infrastructure.core_stack_v2.engine import CoreStackConfig, build_snapshot
from qore.infrastructure.core_stack_v2.market_universe import (
    GLOBAL_MARKET_UNIVERSE_REQUIRED,
    CoreGlobalMarketUniverse,
    CoreInstrumentFamilyKnowledge,
    CoreMarketKnowledge,
    build_global_market_universe,
)
from qore.infrastructure.core_stack_v2.operational_falsification import (
    ActualTrade,
    CurveMetrics,
    OperationalFalsificationResult,
    ShadowAction,
    SharedShadowDecision,
    evaluate_real_operation_falsification,
)
from qore.infrastructure.core_stack_v2.runtime import (
    CoreRuntimeCheckpoint,
    CoreRuntimeResult,
    CoreStackV2Runtime,
    SnapshotConsumer,
    SnapshotDelivery,
)

__all__ = [
    "CORE_STACK_VERSION",
    "ActualTrade",
    "GLOBAL_MARKET_UNIVERSE_REQUIRED",
    "SUPERINTELLIGENCE_FREEZE_VERSION",
    "CognitiveState",
    "CompatibilityEntry",
    "CompatibilityStatus",
    "CoreAdapter",
    "CoreAuditRecord",
    "CurveMetrics",
    "CoreGlobalMarketUniverse",
    "CoreHypothesis",
    "CoreInstrumentFamilyKnowledge",
    "CoreMarketKnowledge",
    "CoreSnapshot",
    "CoreStackConfig",
    "CoreRuntimeCheckpoint",
    "CoreRuntimeResult",
    "CoreStackV2Runtime",
    "DecisionABSummary",
    "OperationalFalsificationResult",
    "DecisionObservation",
    "HypothesisStatus",
    "KnowledgeState",
    "MarketEvent",
    "PerceptionIntegrity",
    "PortfolioIntent",
    "PortfolioSituation",
    "PositionContext",
    "ShadowAction",
    "SharedShadowDecision",
    "SnapshotConsumer",
    "SnapshotDelivery",
    "TraderCognitiveContext",
    "UncertaintyState",
    "WorldState",
    "build_global_market_universe",
    "build_shared_context",
    "build_snapshot",
    "compatibility_manifest",
    "compatibility_manifest_fingerprint",
    "evaluate_real_operation_falsification",
    "freeze_facts",
    "make_audit_record",
    "summarize_decision_ab",
    "superintelligence_freeze_contract",
    "superintelligence_freeze_fingerprint",
]
