"""Deterministic lifecycle, attention-board and routing for Shared STI."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedAlertLifecycle,
    SharedIntelligenceClass,
    SharedOpportunityAlert,
    SharedOpportunityMaturity,
    SharedTraderCapability,
    SharedTraderIntelligenceSnapshot,
    SharedTraderIntelligenceValidationError,
    SharedTraderRelevantProjection,
)

_TERMINAL_ALERT_STATES = frozenset(
    {
        SharedAlertLifecycle.RESOLVED,
        SharedAlertLifecycle.INVALIDATED,
        SharedAlertLifecycle.EXPIRED,
    }
)

_ALLOWED_ALERT_TRANSITIONS = {
    SharedAlertLifecycle.NEW: frozenset(
        {
            SharedAlertLifecycle.ACTIVE,
            SharedAlertLifecycle.INVALIDATED,
            SharedAlertLifecycle.EXPIRED,
        }
    ),
    SharedAlertLifecycle.ACTIVE: frozenset(
        {
            SharedAlertLifecycle.STRENGTHENING,
            SharedAlertLifecycle.WEAKENING,
            SharedAlertLifecycle.RESOLVED,
            SharedAlertLifecycle.INVALIDATED,
            SharedAlertLifecycle.EXPIRED,
        }
    ),
    SharedAlertLifecycle.STRENGTHENING: frozenset(
        {
            SharedAlertLifecycle.ACTIVE,
            SharedAlertLifecycle.WEAKENING,
            SharedAlertLifecycle.RESOLVED,
            SharedAlertLifecycle.INVALIDATED,
            SharedAlertLifecycle.EXPIRED,
        }
    ),
    SharedAlertLifecycle.WEAKENING: frozenset(
        {
            SharedAlertLifecycle.ACTIVE,
            SharedAlertLifecycle.STRENGTHENING,
            SharedAlertLifecycle.RESOLVED,
            SharedAlertLifecycle.INVALIDATED,
            SharedAlertLifecycle.EXPIRED,
        }
    ),
    SharedAlertLifecycle.RESOLVED: frozenset(),
    SharedAlertLifecycle.INVALIDATED: frozenset(),
    SharedAlertLifecycle.EXPIRED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class SharedAlertLifecycleTransition:
    alert_id: str
    hypothesis_id: str
    previous_state: SharedAlertLifecycle
    next_state: SharedAlertLifecycle
    transitioned_at: datetime
    evidence_cutoff_at: datetime
    reason_codes: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    emits_material_event: bool = True
    resurrects_terminal_alert: bool = False

    def __post_init__(self) -> None:
        for name in ("alert_id", "hypothesis_id"):
            value = str(getattr(self, name))
            if not value.strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        for name in ("transitioned_at", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be timezone-aware"
                )
        if self.evidence_cutoff_at > self.transitioned_at:
            raise SharedTraderIntelligenceValidationError(
                "alert lifecycle cannot use future evidence"
            )
        for field_name in ("reason_codes", "provenance_refs"):
            refs = getattr(self, field_name)
            if not refs:
                raise SharedTraderIntelligenceValidationError(
                    f"{field_name} must be non-empty"
                )
            if refs != tuple(sorted(set(refs))):
                raise SharedTraderIntelligenceValidationError(
                    f"{field_name} must be unique and canonical"
                )
        if self.previous_state == self.next_state:
            raise SharedTraderIntelligenceValidationError(
                "unchanged alert state must be deduplicated"
            )
        if self.resurrects_terminal_alert:
            raise SharedTraderIntelligenceValidationError(
                "terminal alert resurrection is forbidden"
            )
        if not self.emits_material_event:
            raise SharedTraderIntelligenceValidationError(
                "persisted lifecycle transition must be material"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["previous_state"] = self.previous_state.value
        payload["next_state"] = self.next_state.value
        payload["transitioned_at"] = (
            self.transitioned_at.astimezone(UTC).isoformat()
        )
        payload["evidence_cutoff_at"] = (
            self.evidence_cutoff_at.astimezone(UTC).isoformat()
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def transition_alert_lifecycle(
    *,
    alert_id: str,
    hypothesis_id: str,
    previous_state: SharedAlertLifecycle,
    next_state: SharedAlertLifecycle,
    transitioned_at: datetime,
    evidence_cutoff_at: datetime,
    reason_codes: tuple[str, ...],
    provenance_refs: tuple[str, ...],
) -> SharedAlertLifecycleTransition | None:
    """Emit only legal material state transitions; unchanged state is deduped."""

    if previous_state == next_state:
        return None
    if previous_state in _TERMINAL_ALERT_STATES:
        raise SharedTraderIntelligenceValidationError(
            "terminal alert cannot transition or resurrect"
        )
    allowed = _ALLOWED_ALERT_TRANSITIONS[previous_state]
    if next_state not in allowed:
        raise SharedTraderIntelligenceValidationError(
            "illegal Shared alert lifecycle transition"
        )
    return SharedAlertLifecycleTransition(
        alert_id=alert_id,
        hypothesis_id=hypothesis_id,
        previous_state=previous_state,
        next_state=next_state,
        transitioned_at=transitioned_at,
        evidence_cutoff_at=evidence_cutoff_at,
        reason_codes=reason_codes,
        provenance_refs=provenance_refs,
    )


@dataclass(frozen=True, slots=True)
class SharedGlobalOpportunityBoard:
    """Attention board only; no order ranking, sizing or execution authority."""

    board_id: str
    as_of: datetime
    evidence_cutoff_at: datetime
    alerts: tuple[SharedOpportunityAlert, ...]
    ranking_is_order_priority: bool = False
    execution_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        if not self.board_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "opportunity board_id must be non-empty"
            )
        for name in ("as_of", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be timezone-aware"
                )
        if self.evidence_cutoff_at > self.as_of:
            raise SharedTraderIntelligenceValidationError(
                "opportunity board cannot use future evidence"
            )
        alert_ids = tuple(item.alert_id for item in self.alerts)
        if alert_ids != tuple(sorted(alert_ids)):
            raise SharedTraderIntelligenceValidationError(
                "opportunity board alerts must be canonical by alert_id"
            )
        if len(alert_ids) != len(set(alert_ids)):
            raise SharedTraderIntelligenceValidationError(
                "opportunity board alert identity must be unique"
            )
        for alert in self.alerts:
            if alert.updated_at > self.as_of:
                raise SharedTraderIntelligenceValidationError(
                    "opportunity board cannot contain future alert"
                )
            if alert.lifecycle in _TERMINAL_ALERT_STATES:
                raise SharedTraderIntelligenceValidationError(
                    "terminal opportunity alert must not remain active on board"
                )
            if alert.maturity is SharedOpportunityMaturity.EXPIRED:
                raise SharedTraderIntelligenceValidationError(
                    "expired opportunity must not remain on board"
                )
        if (
            self.ranking_is_order_priority
            or self.execution_authority
            or self.capital_authority
            or self.risk_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "opportunity board is attention-only"
            )

    @property
    def is_empty(self) -> bool:
        return not self.alerts

    def fingerprint(self) -> str:
        payload = {
            "board_id": self.board_id,
            "as_of": self.as_of.astimezone(UTC).isoformat(),
            "evidence_cutoff_at": (
                self.evidence_cutoff_at.astimezone(UTC).isoformat()
            ),
            "alerts": [
                {
                    "alert_id": item.alert_id,
                    "fingerprint": item.fingerprint(),
                }
                for item in self.alerts
            ],
            "ranking_is_order_priority": False,
            "execution_authority": False,
            "capital_authority": False,
            "risk_authority": False,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def build_trader_relevant_projection(
    *,
    projection_id: str,
    snapshot: SharedTraderIntelligenceSnapshot,
    capability: SharedTraderCapability,
    projected_at: datetime,
    intelligence_classes: tuple[SharedIntelligenceClass, ...],
    relevant_fact_refs: tuple[str, ...],
    omitted_fact_refs: tuple[str, ...],
) -> SharedTraderRelevantProjection:
    """Project relevance without exposing methodology or changing world truth."""

    if snapshot.asset not in capability.markets:
        raise SharedTraderIntelligenceValidationError(
            "snapshot asset is outside Trader routing capability"
        )
    if snapshot.trader_horizon not in capability.horizons:
        raise SharedTraderIntelligenceValidationError(
            "snapshot horizon is outside Trader routing capability"
        )
    supported = set(capability.supported_intelligence_classes)
    if any(item not in supported for item in intelligence_classes):
        raise SharedTraderIntelligenceValidationError(
            "projection requests unsupported Trader intelligence class"
        )
    if projected_at.tzinfo is None or projected_at.utcoffset() is None:
        raise SharedTraderIntelligenceValidationError(
            "projected_at must be timezone-aware"
        )
    if snapshot.observed_at > projected_at:
        raise SharedTraderIntelligenceValidationError(
            "projection cannot consume future Shared snapshot"
        )
    return SharedTraderRelevantProjection(
        projection_id=projection_id,
        snapshot_id=snapshot.snapshot_id,
        trader_id=capability.trader_id,
        projected_at=projected_at,
        evidence_cutoff_at=snapshot.evidence_cutoff_at,
        intelligence_classes=tuple(
            sorted(set(intelligence_classes), key=lambda item: item.value)
        ),
        relevant_fact_refs=tuple(sorted(set(relevant_fact_refs))),
        omitted_fact_refs=tuple(sorted(set(omitted_fact_refs))),
        global_state_fingerprint=snapshot.fingerprint(),
    )
