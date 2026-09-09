"""Append-only Trader Historical Intelligence Registry.

This package is the durable longitudinal memory of every QORE Trader version. It
preserves the complete technical/scientific biography of each exact Trader
version and derives current capability views from certified historical evidence
only. It composes (never replaces) the Trader Lab, the CIBO capability profile,
the CIBO development review, and the CIBO Trader Manager.

``TRADER HISTORY IS APPEND-ONLY``

``CURRENT CAPABILITY = PROJECTION OF CERTIFIED HISTORICAL EVIDENCE``
"""

from qore.infrastructure.trader_history.cibo_adapter import (
    CiboTraderHistoryAdapterError,
    project_cibo_capability_profile,
)
from qore.infrastructure.trader_history.contracts import (
    TraderHistoryBlockedError,
    TraderHistoryEpistemicStatus,
    TraderHistoryError,
    TraderHistoryEvidenceRef,
    TraderHistoryFavorableKind,
    TraderHistoryFinding,
    TraderHistoryHypothesisId,
    TraderHistoryMarketRef,
    TraderHistoryMetric,
    TraderHistoryPartitionIdentity,
    TraderHistoryProducerId,
    TraderHistoryRegimeRef,
    TraderHistorySessionRef,
    TraderHistorySide,
    TraderHistorySoftwareSha,
    TraderHistoryStudyFingerprint,
    TraderHistoryStudyId,
    TraderHistoryStudyKind,
    TraderHistoryStudyRecord,
    TraderHistoryStudyVersion,
    TraderHistorySufficiency,
    TraderHistoryTimeframeRef,
    TraderHistoryValidationError,
    TraderVersionFingerprint,
    TraderVersionIdentity,
    build_study_record,
    build_trader_version_identity,
    validate_study_record,
)
from qore.infrastructure.trader_history.registry import (
    TraderHistoricalIntelligenceRegistry,
    TraderHistoryContradiction,
    TraderHistoryCurrentView,
    TraderHistoryMarketEvidence,
    TraderHistoryMetricView,
    TraderHistoryVersionDiff,
    consumed_holdouts,
    diff_versions,
    hypothesis_lineage,
    market_evidence,
    project_current_capability,
    studies_by_kind,
    studies_for_version,
)

__all__ = [
    "CiboTraderHistoryAdapterError",
    "TraderHistoricalIntelligenceRegistry",
    "TraderHistoryBlockedError",
    "TraderHistoryContradiction",
    "TraderHistoryCurrentView",
    "TraderHistoryEpistemicStatus",
    "TraderHistoryError",
    "TraderHistoryEvidenceRef",
    "TraderHistoryFavorableKind",
    "TraderHistoryFinding",
    "TraderHistoryHypothesisId",
    "TraderHistoryMarketEvidence",
    "TraderHistoryMarketRef",
    "TraderHistoryMetric",
    "TraderHistoryMetricView",
    "TraderHistoryPartitionIdentity",
    "TraderHistoryProducerId",
    "TraderHistoryRegimeRef",
    "TraderHistorySessionRef",
    "TraderHistorySide",
    "TraderHistorySoftwareSha",
    "TraderHistoryStudyFingerprint",
    "TraderHistoryStudyId",
    "TraderHistoryStudyKind",
    "TraderHistoryStudyRecord",
    "TraderHistoryStudyVersion",
    "TraderHistorySufficiency",
    "TraderHistoryTimeframeRef",
    "TraderHistoryValidationError",
    "TraderHistoryVersionDiff",
    "TraderVersionFingerprint",
    "TraderVersionIdentity",
    "build_study_record",
    "build_trader_version_identity",
    "consumed_holdouts",
    "diff_versions",
    "hypothesis_lineage",
    "market_evidence",
    "project_cibo_capability_profile",
    "project_current_capability",
    "studies_by_kind",
    "studies_for_version",
    "validate_study_record",
]
