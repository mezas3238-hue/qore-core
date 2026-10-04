"""Integrator-2 mapping from B4 seam facts into the A3 factual consumer.

The mapper is deliberately loss-averse. B4 UNKNOWN/UNRESOLVED states remain
non-verified on the A side. Unresolved canonical market time prevents OBSERVED
promotion. Temporal comparability controls relational use, not ordinary factual
use once identity, canonical market time and B-09 health are established.
"""

from __future__ import annotations

from qore.infrastructure.core_stack_v2.shared_a3_b4_seam_contract import (
    SharedA3B4CalendarStatus,
    SharedA3B4IdentityStatus,
    SharedA3B4TemporalStatus,
    SharedA3B4WorldFact,
)
from qore.infrastructure.core_stack_v2.shared_a3_world_fact_consumer import (
    A3ComparabilityState,
    A3ConsumedWorldFact,
    A3DataHealthState,
    A3IdentityStatus,
    A3WorldFactEnvelope,
    A3WorldKnowledgeState,
    consume_a4_world_fact,
)


def _identity_status(value: SharedA3B4IdentityStatus) -> A3IdentityStatus:
    if value in {
        SharedA3B4IdentityStatus.PROVIDER_NEUTRAL_REFERENCE_VERIFIED,
        SharedA3B4IdentityStatus.VERSIONED_CONTRACT_VERIFIED,
    }:
        return A3IdentityStatus.VERIFIED
    if value is SharedA3B4IdentityStatus.UNRESOLVED:
        return A3IdentityStatus.UNRESOLVED
    return A3IdentityStatus.UNKNOWN


def _comparability(value: SharedA3B4TemporalStatus) -> A3ComparabilityState:
    if value is SharedA3B4TemporalStatus.COMPARABLE:
        return A3ComparabilityState.COMPARABLE
    if value is SharedA3B4TemporalStatus.NOT_COMPARABLE:
        return A3ComparabilityState.NOT_COMPARABLE
    return A3ComparabilityState.UNKNOWN


def _data_health(value: str) -> A3DataHealthState:
    if value == "HEALTHY":
        return A3DataHealthState.HEALTHY
    if value in {"STALE_UNEXPECTED", "STALE_RELATION"}:
        return A3DataHealthState.STALE
    if value in {
        "PROVIDER_UNAVAILABLE",
        "FEED_UNAVAILABLE",
        "PROVIDER_DEGRADED",
        "PARTIAL_DEGRADATION",
        "CROSSED_QUOTE",
        "IMPOSSIBLE_VALUE",
        "MISSING",
        "FUTURE_EVIDENCE",
        "DUPLICATE",
        "OUT_OF_ORDER",
        "IDENTITY_AMBIGUITY",
        "ROLL_AMBIGUITY",
    }:
        return A3DataHealthState.DEGRADED
    return A3DataHealthState.UNKNOWN


def _knowledge_state(
    fact: SharedA3B4WorldFact,
    health: A3DataHealthState,
) -> A3WorldKnowledgeState:
    if fact.calendar_status is not SharedA3B4CalendarStatus.VERIFIED_CANONICAL:
        return A3WorldKnowledgeState.NOT_OBSERVED
    if health is A3DataHealthState.HEALTHY:
        return A3WorldKnowledgeState.OBSERVED
    if health is A3DataHealthState.STALE:
        return A3WorldKnowledgeState.STALE
    if health is A3DataHealthState.DEGRADED:
        return A3WorldKnowledgeState.DEGRADED
    if fact.data_health_state == "INSUFFICIENT":
        return A3WorldKnowledgeState.INSUFFICIENT
    return A3WorldKnowledgeState.UNKNOWN


def map_b4_fact_to_a3(fact: SharedA3B4WorldFact) -> A3WorldFactEnvelope:
    """Map one B4 fact without widening epistemic or sovereign authority."""

    identity = _identity_status(fact.identity_status)
    health = _data_health(fact.data_health_state)
    comparability = _comparability(fact.temporal_status)
    knowledge = _knowledge_state(fact, health)

    reasons = {
        f"B4_IDENTITY_{fact.identity_status.value}",
        f"B4_CALENDAR_{fact.calendar_status.value}",
        f"B4_TEMPORAL_{fact.temporal_status.value}",
        f"B4_DATA_HEALTH_{fact.data_health_state}",
        f"B4_RELATION_{fact.relation_eligibility.value}",
    }
    if fact.calendar_status is not SharedA3B4CalendarStatus.VERIFIED_CANONICAL:
        reasons.add("A3_ABSTAIN_CANONICAL_MARKET_TIME_UNRESOLVED")
    if fact.data_health_state != "HEALTHY":
        reasons.add("A3_ABSTAIN_B09_DATA_NOT_HEALTHY")
    if fact.temporal_status is not SharedA3B4TemporalStatus.COMPARABLE:
        reasons.add("A3_RELATIONAL_ABSTAIN_NOT_COMPARABLE")

    return A3WorldFactEnvelope(
        fact_id=f"A3B4:{fact.instrument_key}:{fact.fingerprint()[:16]}",
        instrument_key=fact.instrument_key,
        identity_status=identity,
        canonical_identity=(
            fact.canonical_identity
            if identity is A3IdentityStatus.VERIFIED
            else None
        ),
        knowledge_state=knowledge,
        comparability_state=comparability,
        data_health_state=health,
        relational_eligible=fact.relation_claim_allowed,
        observed_at=fact.fact_timestamp,
        available_at=fact.fact_timestamp,
        decision_at=fact.decision_timestamp,
        uncertainty_bps=fact.uncertainty_bps,
        provenance_refs=fact.provenance_refs,
        reason_codes=tuple(sorted(reasons)),
    )


def map_and_consume_b4_fact(fact: SharedA3B4WorldFact) -> A3ConsumedWorldFact:
    """Map then consume through A3's own fail-closed factual boundary."""

    return consume_a4_world_fact(map_b4_fact_to_a3(fact))
