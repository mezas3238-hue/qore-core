from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_a3_b4_seam_contract import (
    SharedA3B4CalendarStatus,
    SharedA3B4IdentityStatus,
    SharedA3B4RelationEligibility,
    SharedA3B4SeamValidationError,
    SharedA3B4TemporalStatus,
    SharedA3B4WorldFact,
)


NOW = datetime(2026, 10, 4, 16, 0, tzinfo=UTC)


def _fact(**overrides):
    values = {
        "source_workstream": "B-08",
        "instrument_key": "EURUSD",
        "canonical_identity": "FX:EURUSD",
        "identity_status": SharedA3B4IdentityStatus.VERIFIED_CANONICAL,
        "calendar_status": SharedA3B4CalendarStatus.DISTRIBUTED_OTC,
        "data_health_state": "HEALTHY",
        "temporal_status": SharedA3B4TemporalStatus.COMPARABLE,
        "relation_eligibility": SharedA3B4RelationEligibility.ELIGIBLE,
        "fact_timestamp": NOW,
        "decision_timestamp": NOW,
        "provenance_refs": ("provider://sealed/a",),
        "uncertainty_bps": 500,
    }
    values.update(overrides)
    return SharedA3B4WorldFact(**values)


def test_verified_comparable_fact_is_consumable_and_deterministic():
    fact = _fact()
    assert fact.a3_consumable_as_certainty is True
    assert fact.relation_claim_allowed is True
    assert fact.fingerprint() == fact.fingerprint()


def test_unknown_identity_cannot_be_promoted_to_guessed_identity():
    with pytest.raises(SharedA3B4SeamValidationError):
        _fact(
            identity_status=SharedA3B4IdentityStatus.UNKNOWN,
            canonical_identity="FX:EURUSD",
            temporal_status=SharedA3B4TemporalStatus.UNKNOWN,
            relation_eligibility=SharedA3B4RelationEligibility.UNKNOWN,
        )


def test_unknown_identity_is_preserved_and_not_consumable_as_certainty():
    fact = _fact(
        identity_status=SharedA3B4IdentityStatus.UNKNOWN,
        canonical_identity=None,
        calendar_status=SharedA3B4CalendarStatus.UNKNOWN,
        temporal_status=SharedA3B4TemporalStatus.NOT_COMPARABLE,
        relation_eligibility=SharedA3B4RelationEligibility.INELIGIBLE,
        uncertainty_bps=10_000,
    )
    assert fact.a3_consumable_as_certainty is False
    assert fact.relation_claim_allowed is False


def test_future_fact_is_rejected():
    with pytest.raises(SharedA3B4SeamValidationError):
        _fact(fact_timestamp=NOW + timedelta(microseconds=1))


def test_relation_claim_requires_temporal_comparability():
    with pytest.raises(SharedA3B4SeamValidationError):
        _fact(temporal_status=SharedA3B4TemporalStatus.NOT_COMPARABLE)


def test_hidden_filter_and_productive_authority_fail_closed():
    with pytest.raises(SharedA3B4SeamValidationError):
        _fact(hidden_trade_filter_present=True)
    with pytest.raises(SharedA3B4SeamValidationError):
        _fact(execution_authority=True)
