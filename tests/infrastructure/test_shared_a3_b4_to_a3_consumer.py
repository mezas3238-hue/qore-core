from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.shared_a3_b4_seam_contract import (
    SharedA3B4CalendarStatus,
    SharedA3B4IdentityStatus,
    SharedA3B4RelationEligibility,
    SharedA3B4TemporalStatus,
    SharedA3B4WorldFact,
)
from qore.infrastructure.core_stack_v2.shared_a3_b4_to_a3_consumer import (
    map_and_consume_b4_fact,
    map_b4_fact_to_a3,
)
from qore.infrastructure.core_stack_v2.shared_a3_world_fact_consumer import (
    A3ComparabilityState,
    A3DataHealthState,
    A3IdentityStatus,
    A3WorldKnowledgeState,
)

NOW = datetime(2026, 10, 4, 20, 0, tzinfo=UTC)


def _fact(**overrides) -> SharedA3B4WorldFact:
    values = {
        "source_workstream": "B-06+B-07+B-08+B-09+B-10",
        "instrument_key": "CTRADER_DEMO:000001",
        "canonical_identity": "QORE:REFERENCE:EURUSD",
        "identity_status": (
            SharedA3B4IdentityStatus.PROVIDER_NEUTRAL_REFERENCE_VERIFIED
        ),
        "calendar_status": SharedA3B4CalendarStatus.VERIFIED_CANONICAL,
        "data_health_state": "HEALTHY",
        "temporal_status": SharedA3B4TemporalStatus.COMPARABLE,
        "relation_eligibility": SharedA3B4RelationEligibility.ELIGIBLE,
        "fact_timestamp": NOW,
        "decision_timestamp": NOW,
        "provenance_refs": ("b4://sealed",),
        "uncertainty_bps": 500,
    }
    values.update(overrides)
    return SharedA3B4WorldFact(**values)


def test_fully_ready_b4_fact_is_consumed_by_a3() -> None:
    mapped = map_b4_fact_to_a3(_fact())
    consumed = map_and_consume_b4_fact(_fact())
    assert mapped.identity_status is A3IdentityStatus.VERIFIED
    assert mapped.knowledge_state is A3WorldKnowledgeState.OBSERVED
    assert mapped.comparability_state is A3ComparabilityState.COMPARABLE
    assert mapped.data_health_state is A3DataHealthState.HEALTHY
    assert consumed.usable_for_global_cognition is True
    assert consumed.usable_for_relational_claim is True
    assert consumed.abstain is False


def test_noncomparable_b4_fact_can_be_factual_not_relational() -> None:
    fact = _fact(
        temporal_status=SharedA3B4TemporalStatus.NOT_COMPARABLE,
        relation_eligibility=SharedA3B4RelationEligibility.INELIGIBLE,
    )
    consumed = map_and_consume_b4_fact(fact)
    assert consumed.usable_for_global_cognition is True
    assert consumed.usable_for_relational_claim is False
    assert consumed.abstain is False
    assert "A3_RELATIONAL_ABSTAIN_NOT_COMPARABLE" in consumed.reason_codes


def test_current_b07_b09_pending_fact_abstains() -> None:
    fact = _fact(
        calendar_status=SharedA3B4CalendarStatus.UNRESOLVED,
        data_health_state="NOT_ASSESSED_B09_PENDING",
        temporal_status=SharedA3B4TemporalStatus.NOT_COMPARABLE,
        relation_eligibility=SharedA3B4RelationEligibility.INELIGIBLE,
        uncertainty_bps=10_000,
    )
    mapped = map_b4_fact_to_a3(fact)
    consumed = map_and_consume_b4_fact(fact)
    assert mapped.knowledge_state is A3WorldKnowledgeState.NOT_OBSERVED
    assert mapped.data_health_state is A3DataHealthState.UNKNOWN
    assert consumed.usable_for_global_cognition is False
    assert consumed.usable_for_relational_claim is False
    assert consumed.abstain is True


def test_unknown_identity_remains_unknown() -> None:
    fact = _fact(
        canonical_identity=None,
        identity_status=SharedA3B4IdentityStatus.UNKNOWN,
        calendar_status=SharedA3B4CalendarStatus.UNKNOWN,
        data_health_state="UNKNOWN",
        temporal_status=SharedA3B4TemporalStatus.UNKNOWN,
        relation_eligibility=SharedA3B4RelationEligibility.UNKNOWN,
        uncertainty_bps=10_000,
    )
    mapped = map_b4_fact_to_a3(fact)
    consumed = map_and_consume_b4_fact(fact)
    assert mapped.identity_status is A3IdentityStatus.UNKNOWN
    assert mapped.canonical_identity is None
    assert consumed.canonical_identity is None
    assert consumed.abstain is True


def test_stale_and_degraded_health_are_not_promoted() -> None:
    stale = map_b4_fact_to_a3(
        _fact(
            data_health_state="STALE_UNEXPECTED",
            relation_eligibility=SharedA3B4RelationEligibility.INELIGIBLE,
        )
    )
    degraded = map_b4_fact_to_a3(
        _fact(
            data_health_state="PROVIDER_DEGRADED",
            relation_eligibility=SharedA3B4RelationEligibility.INELIGIBLE,
        )
    )
    assert stale.data_health_state is A3DataHealthState.STALE
    assert stale.knowledge_state is A3WorldKnowledgeState.STALE
    assert degraded.data_health_state is A3DataHealthState.DEGRADED
    assert degraded.knowledge_state is A3WorldKnowledgeState.DEGRADED


def test_mapping_is_deterministic() -> None:
    first = map_b4_fact_to_a3(_fact())
    second = map_b4_fact_to_a3(_fact())
    assert first.fingerprint() == second.fingerprint()
