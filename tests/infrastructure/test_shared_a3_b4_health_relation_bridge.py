from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_a3_b4_health_relation_bridge import (
    apply_b09_data_health,
    apply_b10_relation_eligibility,
)
from qore.infrastructure.core_stack_v2.shared_a3_b4_seam_contract import (
    SharedA3B4CalendarStatus,
    SharedA3B4IdentityStatus,
    SharedA3B4RelationEligibility,
    SharedA3B4SeamValidationError,
    SharedA3B4TemporalStatus,
    SharedA3B4WorldFact,
)


NOW = datetime(2026, 10, 4, 19, 55, tzinfo=UTC)


def _fact(**overrides) -> SharedA3B4WorldFact:
    values = {
        "source_workstream": "B-06+B-07+B-08",
        "instrument_key": "CTRADER_DEMO:000001",
        "canonical_identity": "QORE:REFERENCE:EURUSD",
        "identity_status": (
            SharedA3B4IdentityStatus.PROVIDER_NEUTRAL_REFERENCE_VERIFIED
        ),
        "calendar_status": SharedA3B4CalendarStatus.VERIFIED_CANONICAL,
        "data_health_state": "NOT_ASSESSED_B09_PENDING",
        "temporal_status": SharedA3B4TemporalStatus.COMPARABLE,
        "relation_eligibility": SharedA3B4RelationEligibility.INELIGIBLE,
        "fact_timestamp": NOW,
        "decision_timestamp": NOW,
        "provenance_refs": ("b08://sealed",),
        "uncertainty_bps": 500,
    }
    values.update(overrides)
    return SharedA3B4WorldFact(**values)


def test_b09_can_make_fact_consumable_but_not_relation_eligible() -> None:
    fact = apply_b09_data_health(
        _fact(),
        data_health_state="HEALTHY",
        uncertainty_floor_bps=700,
        evidence_cutoff_at=NOW,
        provenance_refs=("b09://sealed",),
    )
    assert fact.a3_consumable_as_certainty is True
    assert fact.relation_claim_allowed is False
    assert fact.uncertainty_bps == 700


def test_b10_can_promote_relation_only_after_all_prior_gates() -> None:
    healthy = apply_b09_data_health(
        _fact(),
        data_health_state="HEALTHY",
        uncertainty_floor_bps=500,
        evidence_cutoff_at=NOW,
        provenance_refs=("b09://sealed",),
    )
    eligible = apply_b10_relation_eligibility(
        healthy,
        relation_eligibility=SharedA3B4RelationEligibility.ELIGIBLE,
        evidence_cutoff_at=NOW,
        provenance_refs=("b10://sealed",),
    )
    assert eligible.a3_consumable_as_certainty is True
    assert eligible.relation_claim_allowed is True


def test_b10_cannot_bypass_b09_health() -> None:
    with pytest.raises(
        SharedA3B4SeamValidationError,
        match="healthy B-09 data state",
    ):
        apply_b10_relation_eligibility(
            _fact(),
            relation_eligibility=SharedA3B4RelationEligibility.ELIGIBLE,
            evidence_cutoff_at=NOW,
            provenance_refs=("b10://sealed",),
        )


def test_b09_unhealthy_state_stays_non_consumable() -> None:
    unhealthy = apply_b09_data_health(
        _fact(),
        data_health_state="PROVIDER_DEGRADED",
        uncertainty_floor_bps=8_000,
        evidence_cutoff_at=NOW,
        provenance_refs=("b09://degraded",),
    )
    assert unhealthy.a3_consumable_as_certainty is False
    assert unhealthy.relation_claim_allowed is False
    assert unhealthy.uncertainty_bps == 8_000


def test_future_or_hindsight_evidence_fails_closed() -> None:
    with pytest.raises(SharedA3B4SeamValidationError):
        apply_b09_data_health(
            _fact(),
            data_health_state="HEALTHY",
            uncertainty_floor_bps=500,
            evidence_cutoff_at=NOW,
            provenance_refs=("b09://sealed",),
            target_or_outcome_used=True,
        )
    with pytest.raises(SharedA3B4SeamValidationError):
        apply_b10_relation_eligibility(
            _fact(),
            relation_eligibility=SharedA3B4RelationEligibility.INELIGIBLE,
            evidence_cutoff_at=datetime(2026, 10, 4, 19, 55, 1, tzinfo=UTC),
            provenance_refs=("b10://future",),
        )
