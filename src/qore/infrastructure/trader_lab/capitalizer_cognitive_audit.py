"""Immutable cognitive audit ledger for QORE Capitalizer.

Every material cognitive decision must preserve the causal WHY. This ledger is designed for
nine-market simulation and later certification replay. It stores only decision-time facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerDecision,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerAttentionState,
    CapitalizerHypothesisStage,
)


@dataclass(frozen=True, slots=True)
class CapitalizerCognitiveAuditRecord:
    audit_id: str
    observed_at: datetime
    session: CapitalizerSession
    symbol: str
    attention: CapitalizerAttentionState
    knowledge: CapitalizerKnowledgeState
    hypothesis_stage: CapitalizerHypothesisStage | None
    hypothesis_id: str | None
    source_event_id: str | None
    regime_family_id: str | None
    observations: tuple[str, ...]
    contradictions: tuple[str, ...]
    adversarial_findings: tuple[str, ...]
    decision: CapitalizerDecision | None
    cognitive_gate_decision: CapitalizerCognitiveGateDecision | None
    reasons: tuple[str, ...]
    selected_for_slot: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if not self.audit_id:
            raise ValueError("audit_id must be non-empty")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("audit timestamp must be timezone-aware")
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("audit symbol must be uppercase")
        if self.grants_capital_authority:
            raise ValueError("audit record cannot grant capital authority")
        active_identity = self.hypothesis_id is not None or self.source_event_id is not None
        if active_identity and (
            self.hypothesis_id is None
            or self.source_event_id is None
            or self.hypothesis_stage is None
        ):
            raise ValueError("audit hypothesis identity must be complete")
        if (
            self.decision is not None or self.cognitive_gate_decision is not None
        ) and not self.reasons:
            raise ValueError("every audited decision requires causal reasons")
        if self.selected_for_slot and self.decision is not CapitalizerDecision.EXECUTE:
            raise ValueError("slot selection requires an EXECUTE decision")


@dataclass(frozen=True, slots=True)
class CapitalizerCognitiveAuditLedger:
    records: tuple[CapitalizerCognitiveAuditRecord, ...] = ()
    runtime_mutation_allowed: bool = False

    def __post_init__(self) -> None:
        if self.runtime_mutation_allowed:
            raise ValueError("cognitive audit ledger cannot self-mutate")
        ids: set[str] = set()
        previous: datetime | None = None
        for record in self.records:
            if record.audit_id in ids:
                raise ValueError("cognitive audit ids must be unique")
            ids.add(record.audit_id)
            if previous is not None and record.observed_at < previous:
                raise ValueError("cognitive audit ledger must be chronological")
            previous = record.observed_at

    def append(
        self,
        record: CapitalizerCognitiveAuditRecord,
    ) -> CapitalizerCognitiveAuditLedger:
        if any(item.audit_id == record.audit_id for item in self.records):
            raise ValueError("cognitive audit id already exists")
        if self.records and record.observed_at < self.records[-1].observed_at:
            raise ValueError("cognitive audit append cannot move backward in time")
        return CapitalizerCognitiveAuditLedger(records=(*self.records, record))
