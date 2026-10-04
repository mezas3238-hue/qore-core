from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2 import shared_a3_world_fact_consumer as seam

NOW = datetime(2026, 10, 4, 19, 50, tzinfo=UTC)


def _fact(**overrides):
    values = dict(
        fact_id="B4:USTEC:world:001",
        instrument_key="provider:USTEC:10014",
        identity_status=seam.A3IdentityStatus.VERIFIED,
        canonical_identity="INDEX:NASDAQ_100",
        knowledge_state=seam.A3WorldKnowledgeState.OBSERVED,
        comparability_state=seam.A3ComparabilityState.COMPARABLE,
        data_health_state=seam.A3DataHealthState.HEALTHY,
        relational_eligible=True,
        observed_at=NOW - timedelta(seconds=2),
        available_at=NOW - timedelta(seconds=1),
        decision_at=NOW,
        uncertainty_bps=700,
        provenance_refs=("artifact:11125412870", "run:36775855021"),
        reason_codes=("B4_FACTUAL_WORLD_INPUT",),
    )
    values.update(overrides)
    return seam.A3WorldFactEnvelope(**values)


def test_verified_observed_comparable_fact_is_consumable() -> None:
    consumed = seam.consume_a4_world_fact(_fact())
    assert consumed.usable_for_global_cognition is True
    assert consumed.usable_for_relational_claim is True
    assert consumed.abstain is False
    assert consumed.execution_authority is False
    assert consumed.risk_authority is False
    assert consumed.sizing_authority is False
    assert consumed.capital_authority is False


def test_unknown_identity_is_preserved_and_abstains() -> None:
    fact = _fact(
        identity_status=seam.A3IdentityStatus.UNKNOWN,
        canonical_identity=None,
        relational_eligible=False,
    )
    consumed = seam.consume_a4_world_fact(fact)
    assert consumed.canonical_identity is None
    assert consumed.abstain is True
    assert consumed.usable_for_global_cognition is False
    assert "A3_ABSTAIN_IDENTITY_NOT_VERIFIED" in consumed.reason_codes


def test_not_comparable_fact_cannot_create_relation_claim() -> None:
    fact = _fact(
        comparability_state=seam.A3ComparabilityState.NOT_COMPARABLE,
        relational_eligible=False,
    )
    consumed = seam.consume_a4_world_fact(fact)
    assert consumed.usable_for_global_cognition is True
    assert consumed.usable_for_relational_claim is False
    assert consumed.abstain is False
    assert "A3_RELATIONAL_ABSTAIN_NOT_COMPARABLE" in consumed.reason_codes


def test_future_available_fact_fails_closed() -> None:
    with pytest.raises(seam.A3WorldFactError, match="future fact availability"):
        _fact(available_at=NOW + timedelta(milliseconds=1))


@pytest.mark.parametrize(
    "field",
    (
        "trader_methodology_embedded",
        "directional_action_hint",
        "sizing_hint",
        "risk_override_hint",
        "execution_hint",
    ),
)
def test_sovereign_or_methodology_hints_are_rejected(field: str) -> None:
    with pytest.raises(seam.A3WorldFactError, match="sovereign action hints"):
        _fact(**{field: True})


def test_relational_eligible_requires_verified_healthy_comparable_world() -> None:
    with pytest.raises(seam.A3WorldFactError, match="verified identity"):
        _fact(
            identity_status=seam.A3IdentityStatus.UNKNOWN,
            canonical_identity=None,
        )
    with pytest.raises(seam.A3WorldFactError, match="explicit comparability"):
        _fact(comparability_state=seam.A3ComparabilityState.UNKNOWN)
    with pytest.raises(seam.A3WorldFactError, match="healthy data"):
        _fact(data_health_state=seam.A3DataHealthState.DEGRADED)


def test_fingerprint_is_deterministic() -> None:
    first = _fact()
    second = _fact()
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
