"""Knowledge Service foundation for QORE specialized services."""

from qore.modules.knowledge.contracts import (
    CaptureStatisticsKnowledgeCommand,
    KnowledgeError,
    KnowledgeInvariantError,
    KnowledgeRecord,
    KnowledgeRecordCapturedEvent,
    KnowledgeRecordId,
)
from qore.modules.knowledge.module import (
    CaptureStatisticsKnowledgeHandler,
    KnowledgeServiceModule,
)

__all__ = [
    "CaptureStatisticsKnowledgeCommand",
    "CaptureStatisticsKnowledgeHandler",
    "KnowledgeError",
    "KnowledgeInvariantError",
    "KnowledgeRecord",
    "KnowledgeRecordCapturedEvent",
    "KnowledgeRecordId",
    "KnowledgeServiceModule",
]
