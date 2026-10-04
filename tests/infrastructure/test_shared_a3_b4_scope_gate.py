from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_a3_b4_scope_gate import (
    SharedA3B4ScopeBlocker,
    SharedA3B4ScopeGateError,
    assess_a3_b4_scope,
)
from qore.infrastructure.core_stack_v2.shared_a3_b4_seam_contract import (
    SharedA3B4CalendarStatus,
    SharedA3B4IdentityStatus,
    SharedA3B4RelationEligibility,
    SharedA3B4TemporalStatus,
    SharedA3B4WorldFact,
)

NOW = datetime(2026, 10, 4, 19, 45, tzinfo=UTC)


def _fact(key: str, **overrides) -> SharedA3B4WorldFact:
    values = {
        "source_workstream": "B-06+B-07+B-08+B-09+B-10",
        "instrument_key": key,
        "canonical_identity": f"QORE:REFERENCE:{key}",
        "identity_status": (
            SharedA3B4IdentityStatus.PROVIDER_NEUTRAL_REFERENCE_VERIFIED
        ),
        "calendar_status": SharedA3B4CalendarStatus.VERIFIED_CANONICAL,
        "data_health_state": "HEALTHY",
        "temporal_status": SharedA3B4TemporalStatus.COMPARABLE,
        "relation_eligibility": SharedA3B4RelationEligibility.ELIGIBLE,
        "fact_timestamp": NOW,
        "decision_timestamp": NOW,
        "provenance_refs": (f"fact://{key}",),
        "uncertainty_bps": 500,
    }
    values.update(overrides)
    return SharedA3B4WorldFact(**values)


def test_ready_scope_requires_only_explicit_requested_facts() -> None:
    facts = (_fact("A"), _fact("B"), _fact("UNRELATED"))
    out = assess_a3_b4_scope(
        facts=facts,
        required_instrument_keys=("A", "B"),
        require_relation_claims=True,
    )
    assert out.a3_scope_consumption_allowed is True
    assert out.a3_scope_relation_claim_allowed is True
    assert out.ready_instrument_keys == ("A", "B")
    assert out.blocked == ()
    assert out.global_inference_from_unrequested_facts_allowed is False


def test_current_b07_like_fact_stays_blocked_until_b08_b09() -> None:
    fact = _fact(
        "A",
        calendar_status=SharedA3B4CalendarStatus.UNRESOLVED,
        data_health_state="NOT_ASSESSED_B09_PENDING",
        temporal_status=SharedA3B4TemporalStatus.NOT_COMPARABLE,
        relation_eligibility=SharedA3B4RelationEligibility.INELIGIBLE,
    )
    out = assess_a3_b4_scope(
        facts=(fact,),
        required_instrument_keys=("A",),
        require_relation_claims=True,
    )
    blockers = out.blocked[0][1]
    assert SharedA3B4ScopeBlocker.MARKET_TIME_UNRESOLVED in blockers
    assert SharedA3B4ScopeBlocker.TEMPORAL_NOT_COMPARABLE in blockers
    assert SharedA3B4ScopeBlocker.DATA_HEALTH_NOT_READY in blockers
    assert SharedA3B4ScopeBlocker.RELATION_INELIGIBLE in blockers
    assert out.a3_scope_consumption_allowed is False
    assert out.a3_scope_relation_claim_allowed is False


def test_factual_scope_can_be_ready_without_relational_comparability() -> None:
    fact = _fact(
        "A",
        temporal_status=SharedA3B4TemporalStatus.NOT_COMPARABLE,
        relation_eligibility=SharedA3B4RelationEligibility.INELIGIBLE,
    )
    out = assess_a3_b4_scope(
        facts=(fact,),
        required_instrument_keys=("A",),
        require_relation_claims=False,
    )
    assert out.a3_scope_consumption_allowed is True
    assert out.a3_scope_relation_claim_allowed is False
    assert out.blocked == ()


def test_missing_or_unknown_fact_fails_closed() -> None:
    unknown = _fact(
        "A",
        canonical_identity=None,
        identity_status=SharedA3B4IdentityStatus.UNKNOWN,
        calendar_status=SharedA3B4CalendarStatus.UNKNOWN,
        data_health_state="UNKNOWN",
        temporal_status=SharedA3B4TemporalStatus.UNKNOWN,
        relation_eligibility=SharedA3B4RelationEligibility.UNKNOWN,
        uncertainty_bps=10_000,
    )
    out = assess_a3_b4_scope(
        facts=(unknown,),
        required_instrument_keys=("A", "B"),
    )
    a_blockers = dict(out.blocked)["A"]
    b_blockers = dict(out.blocked)["B"]
    assert SharedA3B4ScopeBlocker.IDENTITY_UNRESOLVED in a_blockers
    assert b_blockers == (SharedA3B4ScopeBlocker.MISSING_FACT,)
    assert out.a3_scope_consumption_allowed is False


def test_scope_keys_must_be_explicit_unique_and_canonical() -> None:
    with pytest.raises(SharedA3B4ScopeGateError):
        assess_a3_b4_scope(facts=(), required_instrument_keys=())
    with pytest.raises(SharedA3B4ScopeGateError):
        assess_a3_b4_scope(
            facts=(_fact("A"),),
            required_instrument_keys=("B", "A"),
        )
