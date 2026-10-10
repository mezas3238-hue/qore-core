"""M1 route family and prior-protected-pivot causal evidence, no trade veto."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from test_capitalizer_a1_source_sensor_independent_attestation_v1 import (
    _fixtures,
    _m1,
    _source,
)

from qore.infrastructure.trader_lab.capitalizer_a1_m1_protected_route_forensics_v2 import (
    A1M1ProtectedRouteReview,
    M1ProtectionClass,
    SourceRouteClass,
    review_source_m1,
)
from qore.infrastructure.trader_lab.capitalizer_a1_source_sensor_independent_attestation_v1 import (
    ProofStatus,
)


def test_same_close_structural_witness_matches_strict_reference() -> None:
    m1, _, _ = _fixtures()
    evidence = review_source_m1(source=_source(), m1=m1)
    assert evidence.protection_class is M1ProtectionClass.AT_SOURCE_CLOSE
    assert evidence.strict_previous_attestation is ProofStatus.OBSERVED
    assert evidence.structurally_protected_at_entry
    assert evidence.protection_confirmed_at == _source().m1_trigger_confirmed_at
    assert not evidence.eligibility_changed
    assert not evidence.live_authorized
    assert not evidence.author_methodology_certified


def test_prior_structural_pivot_that_remains_intact_is_really_protected_asof() -> None:
    m1, _, _ = _fixtures()
    original = _source()
    later = datetime(2026, 1, 5, 1, 5, tzinfo=UTC)
    candidate = replace(original, m1_trigger_confirmed_at=later.isoformat())
    continuation = _m1(
        later - timedelta(minutes=1),
        open_="101", high="102", low="99", close="101",
    )
    review = review_source_m1(source=candidate, m1=(*m1, continuation))
    assert review.strict_previous_attestation is ProofStatus.NOT_AVAILABLE
    assert review.protection_class is M1ProtectionClass.PRIOR_CONFIRMED_INTACT
    assert review.structurally_protected_at_entry
    assert review.protected_price == "97"
    assert review.protection_confirmed_at == original.m1_trigger_confirmed_at
    assert review.source_opportunity_id != review_source_m1(
        source=original, m1=m1
    ).source_opportunity_id
    assert not review.eligibility_changed


def test_pivot_is_not_protected_if_any_later_m1_revisits_pivot() -> None:
    m1, _, _ = _fixtures()
    later = datetime(2026, 1, 5, 1, 5, tzinfo=UTC)
    source = replace(_source(), m1_trigger_confirmed_at=later.isoformat())
    breach = _m1(
        later-timedelta(minutes=1),
        open_="101", high="102", low="96", close="101",
    )
    review = review_source_m1(source=source, m1=(*m1, breach))
    assert review.protection_class is M1ProtectionClass.PRIOR_CONFIRMED_BREACHED
    assert not review.structurally_protected_at_entry
    assert review.strict_previous_attestation is ProofStatus.NOT_AVAILABLE


def test_no_synthetic_confirmation_and_route_mismatch_cannot_veto() -> None:
    m1, _, _ = _fixtures()
    source = replace(_source(), m1_trigger_family="LIQUIDITY_SWEEP_CISD")
    review = review_source_m1(source=source, m1=m1)
    assert review.source_family == "LIQUIDITY_SWEEP_CISD"
    assert review.route_class in SourceRouteClass
    assert review.source_signal_preserved
    assert not review.eligibility_changed
    assert not review.future_outcome_used
    with pytest.raises(ValueError, match="future native M1"):
        review_source_m1(
            source=source,
            m1=(*m1, _m1(
                m1[-1].closed_at,
                open_="101", high="102", low="99", close="101",
            )),
        )
    with pytest.raises(ValueError, match="frozen V49"):
        review_source_m1(
            source=replace(source, decision_reference_price="102"), m1=m1
        )


def test_attestation_rejects_forged_future_protection_or_permitted_order() -> None:
    m1, _, _ = _fixtures()
    valid = review_source_m1(source=_source(), m1=m1)
    with pytest.raises(ValueError, match="future M1 protected pivot"):
        replace(
            valid,
            protection_confirmed_at=(
                datetime.fromisoformat(valid.decision_at)+timedelta(minutes=1)
            ).isoformat(),
        )
    with pytest.raises(ValueError, match="cannot erase or fabricate"):
        replace(valid, strict_previous_attestation=ProofStatus.NOT_AVAILABLE)
    with pytest.raises(ValueError, match="descriptive"):
        replace(valid, eligibility_changed=True)
    with pytest.raises(ValueError, match="descriptive"):
        replace(valid, author_methodology_certified=True)
    with pytest.raises(ValueError, match="protected verdict"):
        replace(valid, structurally_protected_at_entry=False)
