from __future__ import annotations

from dataclasses import fields
from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.cfd_contract_qualification import (
    CfdEvidenceRef,
    CfdForwardFormQualification,
    CfdQualificationId,
    CfdQualificationValidationError,
    CfdRollingSpotLifecycleQualification,
)
from qore.infrastructure.derivative_contract_semantics import (
    DerivativeBenchmarkReference,
    DerivativeEvidenceRef,
    DerivativeFixingTerms,
    DerivativeNotional,
    DerivativePriceQuoteBasisCode,
    DerivativeReferenceRoleCode,
    DerivativeScheduleConvention,
    DerivativeScheduleRollCode,
    DerivativeScheduleStubCode,
    DerivativeSettlementStyle,
    DerivativeStrike,
    DerivativeStrikeBasis,
    DerivativeTermsId,
    ForwardContractTerms,
)
from qore.infrastructure.fixed_income_economics import (
    BusinessCalendarRef,
    BusinessDayConventionCode,
    FinancialTenor,
    FinancialTenorUnit,
    FixedIncomeEconomicsValidationError,
)
from qore.infrastructure.universal_instrument_identity import (
    CanonicalIdentityRef,
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
    IdentityLifecycleEvent,
    IdentityLifecycleEventId,
    IdentityRelationship,
    IdentityRelationshipCode,
    IdentityRelationshipId,
    LifecycleEventCode,
    UniversalInstrumentIdentityValidationError,
)


def _uuid(i: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{i:012d}")


def _identity_id(i: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(i))


def _identity_evidence(i: int) -> IdentityEvidenceRef:
    return IdentityEvidenceRef(_uuid(i))


def _relationship_id(i: int) -> IdentityRelationshipId:
    return IdentityRelationshipId(_uuid(i))


def _terms_id(i: int) -> DerivativeTermsId:
    return DerivativeTermsId(_uuid(i))


def _derivative_evidence(i: int) -> DerivativeEvidenceRef:
    return DerivativeEvidenceRef(_uuid(i))


def _qualification_id(i: int) -> CfdQualificationId:
    return CfdQualificationId(_uuid(i))


def _cfd_evidence(i: int) -> CfdEvidenceRef:
    return CfdEvidenceRef(_uuid(i))


def _cfd_identity_with_evidence(
    identity_index: int,
    evidence_index: int,
) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=_identity_id(identity_index),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("contracts-for-difference"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(evidence_index),
    )


def _cfd_identity(i: int) -> EconomicIdentity:
    return _cfd_identity_with_evidence(i, i)


def _cash_forward(
    instrument_id: EconomicIdentityId,
    reference_id: EconomicIdentityId,
    fixing_reference_id: EconomicIdentityId | None = None,
) -> ForwardContractTerms:
    fixing_ref = fixing_reference_id or reference_id
    settlement_identity = _identity_id(900)
    return ForwardContractTerms(
        terms_id=_terms_id(901),
        instrument_identity_id=instrument_id,
        reference_identity_id=reference_id,
        settlement_identity_id=settlement_identity,
        notional=DerivativeNotional(
            value=Decimal("1"),
            unit_identity_id=settlement_identity,
        ),
        agreed_strike=DerivativeStrike(
            value=Decimal("100"),
            basis=DerivativeStrikeBasis.PRICE,
            quote_identity_id=settlement_identity,
            price_quote_basis=DerivativePriceQuoteBasisCode(
                "currency-per-unit"
            ),
            convention=None,
        ),
        maturity_date=date(2026, 8, 24),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_derivative_evidence(902),
        fixing=DerivativeFixingTerms(
            reference=DerivativeBenchmarkReference(
                reference_identity_id=fixing_ref,
                role=DerivativeReferenceRoleCode("closing-price"),
                tenor=None,
            ),
            fixing_date=date(2026, 8, 20),
            evidence_ref=_derivative_evidence(903),
        ),
        settlement_convention=None,
    )


def _physical_forward(
    instrument_id: EconomicIdentityId,
    reference_id: EconomicIdentityId,
) -> ForwardContractTerms:
    settlement_identity = _identity_id(900)
    return ForwardContractTerms(
        terms_id=_terms_id(901),
        instrument_identity_id=instrument_id,
        reference_identity_id=reference_id,
        settlement_identity_id=settlement_identity,
        notional=DerivativeNotional(
            value=Decimal("1"),
            unit_identity_id=settlement_identity,
        ),
        agreed_strike=DerivativeStrike(
            value=Decimal("100"),
            basis=DerivativeStrikeBasis.PRICE,
            quote_identity_id=settlement_identity,
            price_quote_basis=DerivativePriceQuoteBasisCode(
                "currency-per-unit"
            ),
            convention=None,
        ),
        maturity_date=date(2026, 8, 24),
        settlement_style=DerivativeSettlementStyle.PHYSICAL,
        evidence_ref=_derivative_evidence(902),
        fixing=None,
        settlement_convention=None,
    )


def _binding(
    source: EconomicIdentityId,
    target: EconomicIdentityId,
    effective_from: datetime | None = None,
    effective_until: datetime | None = None,
) -> IdentityRelationship:
    return IdentityRelationship(
        relationship_id=_relationship_id(700),
        source_identity_id=source,
        target_identity_id=target,
        relationship=IdentityRelationshipCode(
            "price-determination-reference"
        ),
        effective_from=effective_from or datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=effective_until,
        evidence_ref=_identity_evidence(701),
    )


def _valid_same_reference_forward() -> ForwardContractTerms:
    return _cash_forward(_identity_id(1), _identity_id(2))


def _valid_distinct_forward() -> ForwardContractTerms:
    return _cash_forward(_identity_id(1), _identity_id(2), _identity_id(3))


def _valid_same_reference_qualification() -> CfdForwardFormQualification:
    return CfdForwardFormQualification(
        qualification_id=_qualification_id(3),
        cfd_identity=_cfd_identity(1),
        forward=_valid_same_reference_forward(),
        evidence_ref=_cfd_evidence(4),
        price_determination_binding=None,
    )


def _valid_distinct_qualification() -> CfdForwardFormQualification:
    return CfdForwardFormQualification(
        qualification_id=_qualification_id(3),
        cfd_identity=_cfd_identity(1),
        forward=_valid_distinct_forward(),
        evidence_ref=_cfd_evidence(4),
        price_determination_binding=_binding(_identity_id(2), _identity_id(3)),
    )


def _valid_rolling_qualification() -> CfdRollingSpotLifecycleQualification:
    return CfdRollingSpotLifecycleQualification(
        qualification_id=_qualification_id(3),
        cfd_identity=_cfd_identity(1),
        contract_period=FinancialTenor(
            value=1,
            unit=FinancialTenorUnit.DAY,
        ),
        evidence_ref=_cfd_evidence(4),
    )


def test_valid_same_reference_forward_qualification() -> None:
    q = _valid_same_reference_qualification()
    assert q.logical_values()[0] == "cfd-forward-form-qualification"


def test_wrong_family_rejected() -> None:
    instrument_id = _identity_id(1)
    bad_identity = EconomicIdentity(
        identity_id=instrument_id,
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("equities"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(5),
    )
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=bad_identity,
            forward=_valid_same_reference_forward(),
            evidence_ref=_cfd_evidence(4),
            price_determination_binding=None,
        )


def test_identity_forward_instrument_mismatch_rejected() -> None:
    forward_id = _identity_id(99)
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            forward=_cash_forward(forward_id, _identity_id(2)),
            evidence_ref=_cfd_evidence(4),
            price_determination_binding=None,
        )


def test_physical_forward_rejected() -> None:
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            forward=_physical_forward(_identity_id(1), _identity_id(2)),
            evidence_ref=_cfd_evidence(4),
            price_determination_binding=None,
        )


def test_same_reference_unnecessary_binding_rejected() -> None:
    unnecessary = _binding(_identity_id(10), _identity_id(11))
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            forward=_valid_same_reference_forward(),
            evidence_ref=_cfd_evidence(4),
            price_determination_binding=unnecessary,
        )


def test_distinct_fixing_without_binding_rejected() -> None:
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            forward=_valid_distinct_forward(),
            evidence_ref=_cfd_evidence(4),
            price_determination_binding=None,
        )


def test_distinct_fixing_with_binding_accepted() -> None:
    q = _valid_distinct_qualification()
    assert q.logical_values()[0] == "cfd-forward-form-qualification"


def test_binding_wrong_source_rejected() -> None:
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            forward=_valid_distinct_forward(),
            evidence_ref=_cfd_evidence(4),
            price_determination_binding=_binding(
                _identity_id(4),
                _identity_id(3),
            ),
        )


def test_binding_wrong_target_rejected() -> None:
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            forward=_valid_distinct_forward(),
            evidence_ref=_cfd_evidence(4),
            price_determination_binding=_binding(
                _identity_id(2),
                _identity_id(4),
            ),
        )


def test_binding_wrong_relationship_code_rejected() -> None:
    bad = IdentityRelationship(
        relationship_id=_relationship_id(700),
        source_identity_id=_identity_id(2),
        target_identity_id=_identity_id(3),
        relationship=IdentityRelationshipCode("not-price-determination"),
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        evidence_ref=_identity_evidence(701),
    )
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            forward=_valid_distinct_forward(),
            evidence_ref=_cfd_evidence(4),
            price_determination_binding=bad,
        )


def _make_temporal_binding(
    effective_from: datetime,
    effective_until: datetime | None,
) -> IdentityRelationship:
    return _binding(
        _identity_id(2),
        _identity_id(3),
        effective_from=effective_from,
        effective_until=effective_until,
    )


def _build_forward_with_binding(
    binding: IdentityRelationship,
) -> CfdForwardFormQualification:
    return CfdForwardFormQualification(
        qualification_id=_qualification_id(3),
        cfd_identity=_cfd_identity(1),
        forward=_valid_distinct_forward(),
        evidence_ref=_cfd_evidence(4),
        price_determination_binding=binding,
    )


def test_temporal_binding_start_before_day_open_accepted() -> None:
    day_start = datetime.combine(date(2026, 8, 20), time.min, tzinfo=UTC)
    _build_forward_with_binding(
        _make_temporal_binding(day_start - timedelta(days=1), None)
    )


def test_temporal_binding_start_exactly_day_start_accepted() -> None:
    day_start = datetime.combine(date(2026, 8, 20), time.min, tzinfo=UTC)
    _build_forward_with_binding(_make_temporal_binding(day_start, None))


def test_temporal_binding_start_intraday_rejected() -> None:
    day_start = datetime.combine(date(2026, 8, 20), time.min, tzinfo=UTC)
    with pytest.raises(CfdQualificationValidationError):
        _build_forward_with_binding(
            _make_temporal_binding(day_start + timedelta(hours=1), None)
        )


def test_temporal_binding_start_next_day_rejected() -> None:
    day_start = datetime.combine(date(2026, 8, 20), time.min, tzinfo=UTC)
    with pytest.raises(CfdQualificationValidationError):
        _build_forward_with_binding(
            _make_temporal_binding(day_start + timedelta(days=1), None)
        )


def test_temporal_binding_expires_before_day_rejected() -> None:
    day_start = datetime.combine(date(2026, 8, 20), time.min, tzinfo=UTC)
    with pytest.raises(CfdQualificationValidationError):
        _build_forward_with_binding(
            _make_temporal_binding(
                day_start - timedelta(days=2),
                day_start - timedelta(days=1),
            )
        )


def test_temporal_binding_expires_exactly_day_start_rejected() -> None:
    day_start = datetime.combine(date(2026, 8, 20), time.min, tzinfo=UTC)
    with pytest.raises(CfdQualificationValidationError):
        _build_forward_with_binding(
            _make_temporal_binding(
                day_start - timedelta(days=1),
                day_start,
            )
        )


def test_temporal_binding_expires_intraday_rejected() -> None:
    day_start = datetime.combine(date(2026, 8, 20), time.min, tzinfo=UTC)
    with pytest.raises(CfdQualificationValidationError):
        _build_forward_with_binding(
            _make_temporal_binding(
                day_start - timedelta(days=1),
                day_start + timedelta(hours=1),
            )
        )


def test_temporal_binding_expires_exactly_next_day_start_accepted() -> None:
    day_start = datetime.combine(date(2026, 8, 20), time.min, tzinfo=UTC)
    next_day_start = day_start + timedelta(days=1)
    _build_forward_with_binding(
        _make_temporal_binding(
            day_start - timedelta(days=1),
            next_day_start,
        )
    )


def test_temporal_binding_expires_after_next_day_start_accepted() -> None:
    day_start = datetime.combine(date(2026, 8, 20), time.min, tzinfo=UTC)
    next_day_start = day_start + timedelta(days=1)
    _build_forward_with_binding(
        _make_temporal_binding(
            day_start - timedelta(days=1),
            next_day_start + timedelta(days=1),
        )
    )


def test_non_utc_offset_normalization_exact_utc_projection() -> None:
    plus_two = timezone(timedelta(hours=2))
    effective_from = datetime(2026, 8, 20, 2, 0, tzinfo=plus_two)
    effective_until = datetime(2026, 8, 22, 2, 0, tzinfo=plus_two)
    binding = _binding(
        _identity_id(2),
        _identity_id(3),
        effective_from=effective_from,
        effective_until=effective_until,
    )
    q = _build_forward_with_binding(binding)
    retained_binding = q.price_determination_binding
    assert retained_binding is not None
    assert retained_binding.logical_values()[4] == (
        "2026-08-20T00:00:00.000000+00:00"
    )
    assert retained_binding.logical_values()[5] == (
        "2026-08-22T00:00:00.000000+00:00"
    )


def test_naive_relationship_rejected_by_umi02() -> None:
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        IdentityRelationship(
            relationship_id=_relationship_id(700),
            source_identity_id=_identity_id(2),
            target_identity_id=_identity_id(3),
            relationship=IdentityRelationshipCode(
                "price-determination-reference"
            ),
            effective_from=datetime(2026, 1, 1),
            effective_until=None,
            evidence_ref=_identity_evidence(701),
        )


class DeceptiveFamily(IdentityFamilyCode):
    pass


class DeceptiveRelationshipCode(IdentityRelationshipCode):
    pass


class DeceptiveEconomicIdentityId(EconomicIdentityId):
    pass


def test_polymorphic_family_subclass_rejected() -> None:
    bad_identity = EconomicIdentity(
        identity_id=_identity_id(1),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=DeceptiveFamily("contracts-for-difference"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(5),
    )
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=bad_identity,
            forward=_valid_same_reference_forward(),
            evidence_ref=_cfd_evidence(4),
            price_determination_binding=None,
        )


def test_polymorphic_relationship_code_subclass_rejected() -> None:
    bad = IdentityRelationship(
        relationship_id=_relationship_id(700),
        source_identity_id=_identity_id(2),
        target_identity_id=_identity_id(3),
        relationship=DeceptiveRelationshipCode(
            "price-determination-reference"
        ),
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        evidence_ref=_identity_evidence(701),
    )
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            forward=_valid_distinct_forward(),
            evidence_ref=_cfd_evidence(4),
            price_determination_binding=bad,
        )


def test_polymorphic_economic_identity_id_subclass_rejected() -> None:
    deceptive_instrument = DeceptiveEconomicIdentityId(_uuid(1))
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            forward=_cash_forward(deceptive_instrument, _identity_id(2)),
            evidence_ref=_cfd_evidence(4),
            price_determination_binding=None,
        )


def test_same_reference_exact_logical_values_oracle() -> None:
    q = _valid_same_reference_qualification()
    expected = (
        "cfd-forward-form-qualification",
        _qualification_id(3).logical_values(),
        _cfd_identity(1).logical_values(),
        _valid_same_reference_forward().logical_values(),
        None,
        _cfd_evidence(4).logical_values(),
    )
    assert q.logical_values() == expected
    assert q.logical_values() == q.logical_values()


def test_distinct_reference_exact_logical_values_oracle() -> None:
    q = _valid_distinct_qualification()
    binding = _binding(_identity_id(2), _identity_id(3))
    expected = (
        "cfd-forward-form-qualification",
        _qualification_id(3).logical_values(),
        _cfd_identity(1).logical_values(),
        _valid_distinct_forward().logical_values(),
        binding.logical_values(),
        _cfd_evidence(4).logical_values(),
    )
    assert q.logical_values() == expected
    assert q.logical_values() == q.logical_values()


def test_forward_field_surface_exact() -> None:
    assert tuple(
        field.name for field in fields(CfdForwardFormQualification)
    ) == (
        "qualification_id",
        "cfd_identity",
        "forward",
        "evidence_ref",
        "price_determination_binding",
    )


def test_rolling_field_surface_exact() -> None:
    assert tuple(
        field.name
        for field in fields(CfdRollingSpotLifecycleQualification)
    ) == (
        "qualification_id",
        "cfd_identity",
        "contract_period",
        "evidence_ref",
    )


def test_rolling_exact_logical_values_oracle() -> None:
    q = _valid_rolling_qualification()
    expected = (
        "cfd-rolling-spot-lifecycle-qualification",
        _qualification_id(3).logical_values(),
        _cfd_identity(1).logical_values(),
        FinancialTenor(
            value=1,
            unit=FinancialTenorUnit.DAY,
        ).logical_values(),
        "automatic-contract-rollover",
        "party-termination-capability",
        _cfd_evidence(4).logical_values(),
    )
    assert q.logical_values() == expected
    assert q.logical_values() == q.logical_values()


def test_rolling_wrong_family_rejected() -> None:
    bad_identity = EconomicIdentity(
        identity_id=_identity_id(1),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("equities"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(5),
    )
    with pytest.raises(CfdQualificationValidationError):
        CfdRollingSpotLifecycleQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=bad_identity,
            contract_period=FinancialTenor(
                value=1,
                unit=FinancialTenorUnit.DAY,
            ),
            evidence_ref=_cfd_evidence(4),
        )


def test_rolling_zero_period_rejected() -> None:
    with pytest.raises(FixedIncomeEconomicsValidationError):
        FinancialTenor(value=0, unit=FinancialTenorUnit.DAY)


def test_rolling_negative_period_rejected() -> None:
    with pytest.raises(FixedIncomeEconomicsValidationError):
        FinancialTenor(value=-1, unit=FinancialTenorUnit.DAY)


def test_rolling_plain_string_unit_rejected() -> None:
    with pytest.raises(FixedIncomeEconomicsValidationError):
        FinancialTenor(
            value=1,
            unit=cast(FinancialTenorUnit, "DAY"),
        )


def test_rolling_schedule_convention_cannot_substitute() -> None:
    schedule = DerivativeScheduleConvention(
        stub=DerivativeScheduleStubCode("none"),
        roll=DerivativeScheduleRollCode("end-of-month"),
        calendar_ref=BusinessCalendarRef("nyc"),
        business_day_convention=BusinessDayConventionCode(
            "modified-following"
        ),
    )
    bad = cast(FinancialTenor, schedule)
    with pytest.raises(CfdQualificationValidationError):
        CfdRollingSpotLifecycleQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            contract_period=bad,
            evidence_ref=_cfd_evidence(4),
        )


def test_rolling_identity_lifecycle_event_cannot_substitute() -> None:
    event = IdentityLifecycleEvent(
        event_id=IdentityLifecycleEventId(_uuid(800)),
        subject=CanonicalIdentityRef(_identity_id(1)),
        event_type=LifecycleEventCode("expiry"),
        effective_at=datetime(2026, 1, 1, tzinfo=UTC),
        recorded_at=datetime(2026, 1, 2, tzinfo=UTC),
        evidence_ref=_identity_evidence(801),
    )
    bad = cast(FinancialTenor, event)
    with pytest.raises(CfdQualificationValidationError):
        CfdRollingSpotLifecycleQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            contract_period=bad,
            evidence_ref=_cfd_evidence(4),
        )


def test_rolling_crypto_perpetual_cannot_substitute_type_boundary() -> None:
    from qore.infrastructure.crypto_perpetual_funding_semantics import (
        CryptoPerpetualContractTerms,
    )

    bad = cast(
        FinancialTenor,
        object.__new__(CryptoPerpetualContractTerms),
    )
    with pytest.raises(CfdQualificationValidationError):
        CfdRollingSpotLifecycleQualification(
            qualification_id=_qualification_id(3),
            cfd_identity=_cfd_identity(1),
            contract_period=bad,
            evidence_ref=_cfd_evidence(4),
        )


_FORBIDDEN_AUTHORITY_FIELDS = {
    "current_price",
    "observed_fixing_value",
    "fixing_value",
    "pnl",
    "payoff",
    "margin",
    "account_equity",
    "leverage",
    "margin_closeout",
    "provider_symbol",
    "provider_capability",
    "overnight_funding",
    "fx_pair",
    "quote_basis",
    "order",
    "trade",
    "receipt",
    "settlement_mutation",
    "legal_eligibility",
    "spread_bet",
    "automatic_rollover",
    "party_termination_capability",
}

_FORBIDDEN_OPERATIONAL_METHODS = {
    "execute",
    "settle",
    "calculate_pnl",
    "calculate_payoff",
    "observe",
    "schedule",
    "roll",
    "sleep",
    "timer",
    "thread",
}


def test_forward_field_names_disjoint_forbidden_authority_fields() -> None:
    actual = {field.name for field in fields(CfdForwardFormQualification)}
    assert actual.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)


def test_rolling_field_names_disjoint_forbidden_authority_fields() -> None:
    actual = {
        field.name
        for field in fields(CfdRollingSpotLifecycleQualification)
    }
    assert actual.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)


def test_forward_has_no_forbidden_operational_methods() -> None:
    q = _valid_same_reference_qualification()
    for method in _FORBIDDEN_OPERATIONAL_METHODS:
        assert not hasattr(q, method)


def test_rolling_has_no_forbidden_operational_methods() -> None:
    q = _valid_rolling_qualification()
    for method in _FORBIDDEN_OPERATIONAL_METHODS:
        assert not hasattr(q, method)


def test_logical_projection_collision_regression() -> None:
    identity_a = _cfd_identity_with_evidence(1, 100)
    identity_b = _cfd_identity_with_evidence(1, 200)
    forward = _valid_same_reference_forward()

    q_a = CfdForwardFormQualification(
        qualification_id=_qualification_id(3),
        cfd_identity=identity_a,
        forward=forward,
        evidence_ref=_cfd_evidence(4),
        price_determination_binding=None,
    )
    q_b = CfdForwardFormQualification(
        qualification_id=_qualification_id(3),
        cfd_identity=identity_b,
        forward=forward,
        evidence_ref=_cfd_evidence(4),
        price_determination_binding=None,
    )
    assert q_a.logical_values() != q_b.logical_values()

    roll_a = CfdRollingSpotLifecycleQualification(
        qualification_id=_qualification_id(3),
        cfd_identity=identity_a,
        contract_period=FinancialTenor(
            value=1,
            unit=FinancialTenorUnit.DAY,
        ),
        evidence_ref=_cfd_evidence(4),
    )
    roll_b = CfdRollingSpotLifecycleQualification(
        qualification_id=_qualification_id(3),
        cfd_identity=identity_b,
        contract_period=FinancialTenor(
            value=1,
            unit=FinancialTenorUnit.DAY,
        ),
        evidence_ref=_cfd_evidence(4),
    )
    assert roll_a.logical_values() != roll_b.logical_values()
