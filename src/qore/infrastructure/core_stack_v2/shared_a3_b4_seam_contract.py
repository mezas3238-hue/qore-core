"""Executable seam contract between Shared Architect 3 and Architect 4.

Integrator 2 owns this boundary. B4 world facts may be consumed by A3 only
when epistemic and temporal status is explicit. UNKNOWN / UNRESOLVED /
NOT_COMPARABLE are first-class states and can never be silently promoted.

Provider-neutral reference identity is deliberately distinct from a versioned
contract identity. Neither implies tradable/listing/calendar authority.

This module carries no Trader methodology, order filtering, sizing, Risk,
capital or Execution authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum


class SharedA3B4SeamValidationError(ValueError):
    """A3/B4 seam evidence violates the integration contract."""


class SharedA3B4IdentityStatus(StrEnum):
    PROVIDER_NEUTRAL_REFERENCE_VERIFIED = "PROVIDER_NEUTRAL_REFERENCE_VERIFIED"
    VERSIONED_CONTRACT_VERIFIED = "VERSIONED_CONTRACT_VERIFIED"
    UNKNOWN = "UNKNOWN"
    UNRESOLVED = "UNRESOLVED"


class SharedA3B4CalendarStatus(StrEnum):
    VERIFIED_CANONICAL = "VERIFIED_CANONICAL"
    DISTRIBUTED_OTC_UNRESOLVED = "DISTRIBUTED_OTC_UNRESOLVED"
    HISTORICAL_SESSION_PARTIAL = "HISTORICAL_SESSION_PARTIAL"
    UNKNOWN = "UNKNOWN"
    UNRESOLVED = "UNRESOLVED"


class SharedA3B4TemporalStatus(StrEnum):
    COMPARABLE = "COMPARABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    UNKNOWN = "UNKNOWN"
    UNRESOLVED = "UNRESOLVED"


class SharedA3B4RelationEligibility(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"


_RESOLVED_IDENTITY = frozenset(
    {
        SharedA3B4IdentityStatus.PROVIDER_NEUTRAL_REFERENCE_VERIFIED,
        SharedA3B4IdentityStatus.VERSIONED_CONTRACT_VERIFIED,
    }
)


@dataclass(frozen=True, slots=True)
class SharedA3B4WorldFact:
    """Provider-neutral fact envelope admitted across the A3/B4 seam."""

    source_workstream: str
    instrument_key: str
    canonical_identity: str | None
    identity_status: SharedA3B4IdentityStatus
    calendar_status: SharedA3B4CalendarStatus
    data_health_state: str
    temporal_status: SharedA3B4TemporalStatus
    relation_eligibility: SharedA3B4RelationEligibility
    fact_timestamp: datetime
    decision_timestamp: datetime
    provenance_refs: tuple[str, ...]
    uncertainty_bps: int
    trader_methodology_present: bool = False
    hidden_trade_filter_present: bool = False
    execution_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if not self.source_workstream.strip():
            raise SharedA3B4SeamValidationError(
                "source_workstream must be non-empty"
            )
        if not self.instrument_key.strip():
            raise SharedA3B4SeamValidationError(
                "instrument_key must be non-empty"
            )
        if not self.data_health_state.strip():
            raise SharedA3B4SeamValidationError(
                "data_health_state must be non-empty"
            )
        for name in ("fact_timestamp", "decision_timestamp"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise SharedA3B4SeamValidationError(
                    f"{name} must be timezone-aware"
                )
        if self.fact_timestamp > self.decision_timestamp:
            raise SharedA3B4SeamValidationError(
                "B4 fact timestamp cannot exceed A3 decision timestamp"
            )
        if not 0 <= self.uncertainty_bps <= 10_000:
            raise SharedA3B4SeamValidationError(
                "uncertainty_bps must be within 0..10000"
            )
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise SharedA3B4SeamValidationError(
                "provenance_refs must be non-empty, unique and canonical"
            )

        if self.identity_status in _RESOLVED_IDENTITY:
            if self.canonical_identity is None or not self.canonical_identity.strip():
                raise SharedA3B4SeamValidationError(
                    "verified seam identity requires canonical_identity"
                )
        elif self.canonical_identity is not None:
            raise SharedA3B4SeamValidationError(
                "UNKNOWN/UNRESOLVED identity cannot carry guessed canonical_identity"
            )

        if self.relation_eligibility is SharedA3B4RelationEligibility.ELIGIBLE:
            if self.identity_status not in _RESOLVED_IDENTITY:
                raise SharedA3B4SeamValidationError(
                    "relation eligibility requires resolved identity"
                )
            if self.temporal_status is not SharedA3B4TemporalStatus.COMPARABLE:
                raise SharedA3B4SeamValidationError(
                    "relation eligibility requires temporal comparability"
                )
            if self.calendar_status is not SharedA3B4CalendarStatus.VERIFIED_CANONICAL:
                raise SharedA3B4SeamValidationError(
                    "relation eligibility requires canonical market-time semantics"
                )

        if self.trader_methodology_present:
            raise SharedA3B4SeamValidationError(
                "B facts cannot contain Trader methodology"
            )
        if self.hidden_trade_filter_present:
            raise SharedA3B4SeamValidationError(
                "A3/B4 seam cannot encode hidden trade filters"
            )
        if (
            self.execution_authority
            or self.sizing_authority
            or self.risk_authority
            or self.capital_authority
        ):
            raise SharedA3B4SeamValidationError(
                "A3/B4 seam cannot carry productive authority"
            )

    @property
    def identity_resolved(self) -> bool:
        return self.identity_status in _RESOLVED_IDENTITY

    @property
    def relation_claim_allowed(self) -> bool:
        return self.relation_eligibility is SharedA3B4RelationEligibility.ELIGIBLE

    @property
    def a3_consumable_as_certainty(self) -> bool:
        return (
            self.identity_resolved
            and self.temporal_status is SharedA3B4TemporalStatus.COMPARABLE
            and self.calendar_status is SharedA3B4CalendarStatus.VERIFIED_CANONICAL
        )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["identity_status"] = self.identity_status.value
        payload["calendar_status"] = self.calendar_status.value
        payload["temporal_status"] = self.temporal_status.value
        payload["relation_eligibility"] = self.relation_eligibility.value
        payload["fact_timestamp"] = self.fact_timestamp.astimezone(UTC).isoformat()
        payload["decision_timestamp"] = (
            self.decision_timestamp.astimezone(UTC).isoformat()
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
