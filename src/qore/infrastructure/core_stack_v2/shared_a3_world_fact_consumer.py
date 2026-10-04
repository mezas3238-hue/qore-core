"""A3 factual intake boundary for Architect-4 world/perception evidence.

This module defines the A-side seam only. It does not acquire B evidence, infer
identity, invent calendars, populate relational edges, or grant trading
authority. Integrator 2 remains the sole owner of A3<->A4 compatibility.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum


class A3WorldFactError(ValueError):
    """A3 factual seam invariant failed closed."""


class A3IdentityStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNKNOWN = "UNKNOWN"
    UNRESOLVED = "UNRESOLVED"
    REJECTED = "REJECTED"


class A3WorldKnowledgeState(StrEnum):
    OBSERVED = "OBSERVED"
    MISSING = "MISSING"
    STALE = "STALE"
    DEGRADED = "DEGRADED"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    NOT_OBSERVED = "NOT_OBSERVED"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT = "INSUFFICIENT"


class A3ComparabilityState(StrEnum):
    COMPARABLE = "COMPARABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    UNKNOWN = "UNKNOWN"


class A3DataHealthState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise A3WorldFactError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class A3WorldFactEnvelope:
    fact_id: str
    instrument_key: str
    identity_status: A3IdentityStatus
    canonical_identity: str | None
    knowledge_state: A3WorldKnowledgeState
    comparability_state: A3ComparabilityState
    data_health_state: A3DataHealthState
    relational_eligible: bool
    observed_at: datetime
    available_at: datetime
    decision_at: datetime
    uncertainty_bps: int
    provenance_refs: tuple[str, ...]
    reason_codes: tuple[str, ...]
    trader_methodology_embedded: bool = False
    directional_action_hint: bool = False
    sizing_hint: bool = False
    risk_override_hint: bool = False
    execution_hint: bool = False

    def __post_init__(self) -> None:
        if not self.fact_id.strip() or not self.instrument_key.strip():
            raise A3WorldFactError("fact identity must be explicit")
        for value, name in (
            (self.observed_at, "observed_at"),
            (self.available_at, "available_at"),
            (self.decision_at, "decision_at"),
        ):
            _aware(value, name)
        if self.observed_at > self.available_at:
            raise A3WorldFactError("fact cannot be available before observation")
        if self.available_at > self.decision_at:
            raise A3WorldFactError("future fact availability is forbidden")
        if not 0 <= self.uncertainty_bps <= 10_000:
            raise A3WorldFactError("uncertainty_bps must be within 0..10000")
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise A3WorldFactError("provenance_refs must be non-empty and canonical")
        if (
            not self.reason_codes
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise A3WorldFactError("reason_codes must be non-empty and canonical")

        if self.identity_status is A3IdentityStatus.VERIFIED:
            if self.canonical_identity is None or not self.canonical_identity.strip():
                raise A3WorldFactError(
                    "VERIFIED identity requires canonical_identity"
                )
        elif self.canonical_identity is not None:
            raise A3WorldFactError(
                "unverified identity cannot carry canonical_identity"
            )

        if self.knowledge_state is A3WorldKnowledgeState.OBSERVED:
            pass
        elif self.relational_eligible:
            raise A3WorldFactError(
                "non-observed evidence cannot be relationally eligible"
            )

        if self.relational_eligible:
            if self.identity_status is not A3IdentityStatus.VERIFIED:
                raise A3WorldFactError(
                    "relational eligibility requires verified identity"
                )
            if self.comparability_state is not A3ComparabilityState.COMPARABLE:
                raise A3WorldFactError(
                    "relational eligibility requires explicit comparability"
                )
            if self.data_health_state is not A3DataHealthState.HEALTHY:
                raise A3WorldFactError(
                    "relational eligibility requires healthy data"
                )

        if (
            self.trader_methodology_embedded
            or self.directional_action_hint
            or self.sizing_hint
            or self.risk_override_hint
            or self.execution_hint
        ):
            raise A3WorldFactError(
                "A3 factual seam forbids methodology or sovereign action hints"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload.update(
            {
                "identity_status": self.identity_status.value,
                "knowledge_state": self.knowledge_state.value,
                "comparability_state": self.comparability_state.value,
                "data_health_state": self.data_health_state.value,
                "observed_at": self.observed_at.astimezone(UTC).isoformat(),
                "available_at": self.available_at.astimezone(UTC).isoformat(),
                "decision_at": self.decision_at.astimezone(UTC).isoformat(),
            }
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class A3ConsumedWorldFact:
    fact_id: str
    instrument_key: str
    canonical_identity: str | None
    usable_for_global_cognition: bool
    usable_for_relational_claim: bool
    abstain: bool
    uncertainty_bps: int
    reason_codes: tuple[str, ...]
    source_fingerprint: str
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if (
            self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise A3WorldFactError("consumed A3 fact cannot carry authority")
        if len(self.source_fingerprint) != 64:
            raise A3WorldFactError("source_fingerprint must be sha256")
        if self.abstain and (
            self.usable_for_global_cognition or self.usable_for_relational_claim
        ):
            raise A3WorldFactError("abstention cannot simultaneously authorize use")
        if self.usable_for_relational_claim and not self.usable_for_global_cognition:
            raise A3WorldFactError(
                "relational use requires factual cognition eligibility"
            )


def consume_a4_world_fact(fact: A3WorldFactEnvelope) -> A3ConsumedWorldFact:
    """Consume one A4 fact conservatively without reinterpreting UNKNOWN."""

    reasons = set(fact.reason_codes)

    identity_ok = fact.identity_status is A3IdentityStatus.VERIFIED
    observed = fact.knowledge_state is A3WorldKnowledgeState.OBSERVED
    healthy = fact.data_health_state is A3DataHealthState.HEALTHY
    comparable = fact.comparability_state is A3ComparabilityState.COMPARABLE

    factual_use = identity_ok and observed and healthy
    relational_use = factual_use and comparable and fact.relational_eligible

    if not identity_ok:
        reasons.add("A3_ABSTAIN_IDENTITY_NOT_VERIFIED")
    if not observed:
        reasons.add("A3_ABSTAIN_WORLD_NOT_OBSERVED")
    if not healthy:
        reasons.add("A3_ABSTAIN_DATA_NOT_HEALTHY")
    if factual_use and not comparable:
        reasons.add("A3_RELATIONAL_ABSTAIN_NOT_COMPARABLE")
    if comparable and factual_use and not fact.relational_eligible:
        reasons.add("A3_RELATIONAL_ABSTAIN_NOT_ELIGIBLE")

    abstain = not factual_use
    return A3ConsumedWorldFact(
        fact_id=fact.fact_id,
        instrument_key=fact.instrument_key,
        canonical_identity=fact.canonical_identity if identity_ok else None,
        usable_for_global_cognition=factual_use,
        usable_for_relational_claim=relational_use,
        abstain=abstain,
        uncertainty_bps=fact.uncertainty_bps,
        reason_codes=tuple(sorted(reasons)),
        source_fingerprint=fact.fingerprint(),
    )
