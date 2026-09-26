"""Audit/explanation ledger records for shared Core consumption."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime

from qore.infrastructure.core_stack_v2.adapters import TraderCognitiveContext
from qore.infrastructure.core_stack_v2.contracts import CoreSnapshot


@dataclass(frozen=True, slots=True)
class CoreAuditRecord:
    snapshot_id: str
    snapshot_fingerprint: str
    trader_id: str
    adapter_version: str
    adapter_context_fingerprint: str
    source_event_ids: tuple[str, ...]
    core_context_valid: bool
    contradictions: tuple[str, ...]
    decision: str
    reason: str
    recorded_at: datetime
    core_latency_us: int
    adapter_latency_us: int
    order_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        if self.core_latency_us < 0 or self.adapter_latency_us < 0:
            raise ValueError("latencies cannot be negative")
        if self.order_authority or self.risk_authority:
            raise ValueError("Core audit record cannot confer authority")
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(raw.encode()).hexdigest()


def make_audit_record(
    *,
    snapshot: CoreSnapshot,
    context: TraderCognitiveContext,
    decision: str,
    reason: str,
    recorded_at: datetime,
    core_latency_us: int,
    adapter_latency_us: int,
) -> CoreAuditRecord:
    if context.snapshot_id != snapshot.snapshot_id:
        raise ValueError("adapter context does not belong to snapshot")
    return CoreAuditRecord(
        snapshot_id=snapshot.snapshot_id,
        snapshot_fingerprint=snapshot.fingerprint(),
        trader_id=context.trader_id,
        adapter_version=context.adapter_version,
        adapter_context_fingerprint=context.fingerprint(),
        source_event_ids=snapshot.source_event_ids,
        core_context_valid=context.core_context_valid,
        contradictions=context.contradictions,
        decision=decision,
        reason=reason,
        recorded_at=recorded_at,
        core_latency_us=core_latency_us,
        adapter_latency_us=adapter_latency_us,
    )
