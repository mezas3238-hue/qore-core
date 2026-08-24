from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

import qore.infrastructure.cfd_contract_qualification as cfd_module
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
    SettlementConvention,
)
from qore.infrastructure.fx_semantics import (
    FxEvidenceRef,
    FxQuoteBasis,
    FxQuotedCurrencyPair,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
    IdentityRelationship,
    IdentityRelationshipCode,
    IdentityRelationshipId,
)


def _uuid(i: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{i:012d}")


def _identity_id(i: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(i))


def _identity_evidence(i: int) -> IdentityEvidenceRef:
    return IdentityEvidenceRef(_uuid(i))


def _cfd_identity(
    identity_index: int = 1,
    *,
    evidence_index: int = 2,
    family: str = "contracts-for-difference",
    kind: EconomicIdentityKind = EconomicIdentityKind.TRADABLE_INSTRUMENT,
    construction: IdentityConstructionKind = IdentityConstructionKind.NATIVE,
) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=_identity_id(identity_index),
        kind=kind,
        family=IdentityFamilyCode(family),
        construction=construction,
        evidence_ref=_identity_evidence(evidence_index),
    )


def _qualification_id(i: int = 10) -> CfdQualificationId:
    return CfdQualificationId(_uuid(i))


def _cfd_evidence(i: int = 11) -> CfdEvidenceRef:
    return CfdEvidenceRef(_uuid(i))


def _derivative_evidence(i: int) -> DerivativeEvidenceRef:
    return DerivativeEvidenceRef(_uuid(i))


def _cash_forward(
    *,
    instrument_id: EconomicIdentityId | None = None,
    reference_id: EconomicIdentityId | None = None,
    fixing_reference_id: EconomicIdentityId | None = None,
    settlement_style: DerivativeSettlementStyle = DerivativeSettlementStyle.CASH,
    strike_basis: DerivativeStrikeBasis = DerivativeStrikeBasis.PRICE,
    settlement_convention: SettlementConvention | None = None,
) -> ForwardContractTerms:
    instrument = instrument_id or _identity_id(1)
    reference = reference_id or _identity_id(20)
    fixing_reference = fixing_reference_id or reference
    settlement = _identity_id(21)
    if strike_basis is DerivativeStrikeBasis.PRICE:
        quote_identity: EconomicIdentityId | None = settlement
        quote_basis: DerivativePriceQuoteBasisCode | None = (
            DerivativePriceQuoteBasisCode("currency-per-unit")
        )
    else:
        quote_identity = None
        quote_basis = None
    return ForwardContractTerms(
        terms_id=DerivativeTermsId(_uuid(30)),
        instrument_identity_id=instrument,
        reference_identity_id=reference,
        settlement_identity_id=settlement,
        notional=DerivativeNotional(Decimal("100"), settlement),
        agreed_strike=DerivativeStrike(
            value=Decimal("1.25"),
            basis=strike_basis,
            quote_identity_id=quote_identity,
            price_quote_basis=quote_basis,
            convention=None,
        ),
        maturity_date=date(2027, 1, 31),
        settlement_style=settlement_style,
        evidence_ref=_derivative_evidence(31),
        fixing=DerivativeFixingTerms(
            reference=DerivativeBenchmarkReference(
                reference_identity_id=fixing_reference,
                role=DerivativeReferenceRoleCode("closing-price"),
                tenor=None,
            ),
            fixing_date=date(2027, 1, 30),
            evidence_ref=_derivative_evidence(32),
        )
        if settlement_style is DerivativeSettlementStyle.CASH
        else None,
        settlement_convention=settlement_convention,
    )


def _binding(
    *,
    source: EconomicIdentityId | None = None,
    target: EconomicIdentityId | None = None,
    relationship: str = "price-determination-reference",
    ordinal: int | None = None,
    effective_from: datetime | None = None,
    effective_until: datetime | None = None,
) -> IdentityRelationship:
    start = effective_from or datetime(2026, 1, 1, tzinfo=UTC)
    return IdentityRelationship(
        relationship_id=IdentityRelationshipId(_uuid(40)),
        source_identity_id=source or _identity_id(20),
        target_identity_id=target or _identity_id(22),
        relationship=IdentityRelationshipCode(relationship),
        effective_from=start,
        effective_until=effective_until,
        evidence_ref=_identity_evidence(41),
        ordinal=ordinal,
    )


def _spot_reference(
    *,
    pair_index: int = 50,
    quote_basis: FxQuoteBasis = FxQuoteBasis.CURRENCY2_PER_CURRENCY1,
) -> FxQuotedCurrencyPair:
    return FxQuotedCurrencyPair(
        pair_identity_id=_identity_id(pair_index),
        currency1_identity_id=_identity_id(51),
        currency2_identity_id=_identity_id(52),
        quote_basis=quote_basis,
        evidence_ref=FxEvidenceRef(_uuid(53)),
    )


def _same_reference_qualification() -> CfdForwardFormQualification:
    return CfdForwardFormQualification(
        qualification_id=_qualification_id(),
        cfd_identity=_cfd_identity(),
        forward=_cash_forward(),
        evidence_ref=_cfd_evidence(),
        price_determination_binding=None,
    )


def _distinct_reference_qualification(
    *,
    binding: IdentityRelationship | None = None,
) -> CfdForwardFormQualification:
    forward = _cash_forward(fixing_reference_id=_identity_id(22))
    return CfdForwardFormQualification(
        qualification_id=_qualification_id(),
        cfd_identity=_cfd_identity(),
        forward=forward,
        evidence_ref=_cfd_evidence(),
        price_determination_binding=binding or _binding(),
    )


def _rolling_qualification(
    *,
    identity_index: int = 1,
    spot_reference: FxQuotedCurrencyPair | None = None,
    period: FinancialTenor | None = None,
) -> CfdRollingSpotLifecycleQualification:
    return CfdRollingSpotLifecycleQualification(
        qualification_id=_qualification_id(),
        cfd_identity=_cfd_identity(identity_index),
        spot_reference=spot_reference or _spot_reference(),
        contract_period=period or FinancialTenor(1, FinancialTenorUnit.DAY),
        evidence_ref=_cfd_evidence(),
    )


def test_valid_same_reference_forward_qualification() -> None:
    value = _same_reference_qualification()
    assert value.logical_values()[0] == "cfd-forward-form-qualification"
    assert value.logical_values() == value.logical_values()


def test_valid_distinct_reference_forward_qualification() -> None:
    value = _distinct_reference_qualification()
    assert value.price_determination_binding is not None
    assert value.logical_values()[4] == value.price_determination_binding.logical_values()


def test_valid_settlement_convention_is_preserved() -> None:
    convention = SettlementConvention(
        business_day_lag=2,
        calendar_ref=BusinessCalendarRef("nyc"),
        business_day_convention=BusinessDayConventionCode("modified-following"),
    )
    value = CfdForwardFormQualification(
        qualification_id=_qualification_id(),
        cfd_identity=_cfd_identity(),
        forward=_cash_forward(settlement_convention=convention),
        evidence_ref=_cfd_evidence(),
        price_determination_binding=None,
    )
    assert value.forward.settlement_convention == convention


def test_wrong_family_and_non_tradable_identity_rejected() -> None:
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(),
            _cfd_identity(family="equities"),
            _cash_forward(),
            _cfd_evidence(),
            None,
        )
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(),
            _cfd_identity(kind=EconomicIdentityKind.REFERENCE_OBJECT),
            _cash_forward(),
            _cfd_evidence(),
            None,
        )


def test_cfd_forward_identity_mismatch_rejected() -> None:
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(),
            _cfd_identity(),
            _cash_forward(instrument_id=_identity_id(99)),
            _cfd_evidence(),
            None,
        )


def test_physical_and_non_price_forward_forms_rejected() -> None:
    physical = _cash_forward(settlement_style=DerivativeSettlementStyle.PHYSICAL)
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(), _cfd_identity(), physical, _cfd_evidence(), None
        )

    rate_forward = _cash_forward(strike_basis=DerivativeStrikeBasis.SPREAD)
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(),
            _cfd_identity(),
            rate_forward,
            _cfd_evidence(),
            None,
        )


def test_same_reference_redundant_binding_rejected() -> None:
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(),
            _cfd_identity(),
            _cash_forward(),
            _cfd_evidence(),
            _binding(source=_identity_id(20), target=_identity_id(22)),
        )


def test_distinct_reference_requires_exact_binding() -> None:
    forward = _cash_forward(fixing_reference_id=_identity_id(22))
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(), _cfd_identity(), forward, _cfd_evidence(), None
        )
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(),
            _cfd_identity(),
            forward,
            _cfd_evidence(),
            _binding(source=_identity_id(23)),
        )
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(),
            _cfd_identity(),
            forward,
            _cfd_evidence(),
            _binding(target=_identity_id(24)),
        )
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(),
            _cfd_identity(),
            forward,
            _cfd_evidence(),
            _binding(relationship="other-reference"),
        )
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(),
            _cfd_identity(),
            forward,
            _cfd_evidence(),
            _binding(ordinal=1),
        )


def test_no_invented_complete_utc_fixing_day_law() -> None:
    start = datetime(2027, 1, 30, 12, 0, tzinfo=UTC)
    end = start + timedelta(hours=2)
    value = _distinct_reference_qualification(
        binding=_binding(effective_from=start, effective_until=end)
    )
    assert value.price_determination_binding is not None
    assert value.price_determination_binding.effective_from == start
    assert value.price_determination_binding.effective_until == end


def test_binding_timezone_state_is_revalidated_not_executed() -> None:
    value = _distinct_reference_qualification()
    binding = value.price_determination_binding
    assert binding is not None
    object.__setattr__(binding, "effective_from", datetime(2026, 1, 1))
    with pytest.raises(CfdQualificationValidationError):
        value.logical_values()


def test_valid_rolling_spot_qualification_reuses_fx_pair_semantics() -> None:
    value = _rolling_qualification()
    logical = value.logical_values()
    assert logical[0] == "cfd-rolling-spot-lifecycle-qualification"
    assert logical[3] == _spot_reference().logical_values()
    assert logical[5:7] == (
        "automatic-contract-rollover",
        "party-termination-capability",
    )


def test_rolling_spot_reference_and_period_are_identity_material() -> None:
    base = _rolling_qualification()
    other_pair = _rolling_qualification(spot_reference=_spot_reference(pair_index=60))
    other_quote = _rolling_qualification(
        spot_reference=_spot_reference(
            quote_basis=FxQuoteBasis.CURRENCY1_PER_CURRENCY2
        )
    )
    other_period = _rolling_qualification(
        period=FinancialTenor(2, FinancialTenorUnit.DAY)
    )
    assert len(
        {
            base.logical_values(),
            other_pair.logical_values(),
            other_quote.logical_values(),
            other_period.logical_values(),
        }
    ) == 4


def test_rolling_cfd_identity_cannot_collapse_into_fx_pair_identity() -> None:
    with pytest.raises(CfdQualificationValidationError):
        _rolling_qualification(identity_index=50)


def test_exact_field_surfaces() -> None:
    assert tuple(field.name for field in fields(CfdForwardFormQualification)) == (
        "qualification_id",
        "cfd_identity",
        "forward",
        "evidence_ref",
        "price_determination_binding",
    )
    assert tuple(field.name for field in fields(CfdRollingSpotLifecycleQualification)) == (
        "qualification_id",
        "cfd_identity",
        "spot_reference",
        "contract_period",
        "evidence_ref",
    )


class BadUUID(UUID):
    pass


class BadDecimal(Decimal):
    pass


class BadIdentityId(EconomicIdentityId):
    pass


class BadFamily(IdentityFamilyCode):
    pass


class BadRelationshipCode(IdentityRelationshipCode):
    pass


class BadPriceQuoteBasis(DerivativePriceQuoteBasisCode):
    pass


def test_local_ids_require_exact_uuid_and_revalidate() -> None:
    with pytest.raises(CfdQualificationValidationError):
        CfdQualificationId(BadUUID(int=1))
    value = _qualification_id()
    object.__setattr__(value, "value", "not-a-uuid")
    with pytest.raises(CfdQualificationValidationError):
        value.logical_values()


def test_nested_identity_wrappers_and_family_require_exact_state() -> None:
    identity = _cfd_identity()
    object.__setattr__(identity, "identity_id", BadIdentityId(_uuid(1)))
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(), identity, _cash_forward(), _cfd_evidence(), None
        )

    identity = _cfd_identity()
    object.__setattr__(identity, "family", BadFamily("contracts-for-difference"))
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(), identity, _cash_forward(), _cfd_evidence(), None
        )

    identity = _cfd_identity()
    object.__setattr__(identity.identity_id, "value", "bad")
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(), identity, _cash_forward(), _cfd_evidence(), None
        )


def test_nested_forward_decimal_and_quote_code_subclasses_rejected() -> None:
    forward = _cash_forward()
    object.__setattr__(forward.notional, "value", BadDecimal("100"))
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(), _cfd_identity(), forward, _cfd_evidence(), None
        )

    forward = _cash_forward()
    object.__setattr__(
        forward.agreed_strike,
        "price_quote_basis",
        BadPriceQuoteBasis("currency-per-unit"),
    )
    with pytest.raises(CfdQualificationValidationError):
        CfdForwardFormQualification(
            _qualification_id(), _cfd_identity(), forward, _cfd_evidence(), None
        )


def test_nested_fixing_corruption_fails_closed_on_logical_values() -> None:
    value = _same_reference_qualification()
    fixing = value.forward.fixing
    assert fixing is not None
    object.__setattr__(fixing, "fixing_date", datetime(2027, 1, 30, tzinfo=UTC))
    with pytest.raises(CfdQualificationValidationError):
        value.logical_values()

    value = _same_reference_qualification()
    fixing = value.forward.fixing
    assert fixing is not None
    object.__setattr__(fixing.reference, "role", cast(DerivativeReferenceRoleCode, "bad"))
    with pytest.raises(CfdQualificationValidationError):
        value.logical_values()


def test_postconstruction_parent_corruption_fails_closed() -> None:
    forward_value = _same_reference_qualification()
    object.__setattr__(forward_value.evidence_ref, "value", "bad")
    with pytest.raises(CfdQualificationValidationError):
        forward_value.logical_values()

    rolling = _rolling_qualification()
    object.__setattr__(rolling.contract_period, "value", 0)
    with pytest.raises(CfdQualificationValidationError):
        rolling.logical_values()


def test_spot_reference_nested_corruption_fails_closed() -> None:
    rolling = _rolling_qualification()
    object.__setattr__(rolling.spot_reference, "quote_basis", "bad")
    with pytest.raises(CfdQualificationValidationError):
        rolling.logical_values()

    rolling = _rolling_qualification()
    object.__setattr__(rolling.spot_reference.pair_identity_id, "value", "bad")
    with pytest.raises(CfdQualificationValidationError):
        rolling.logical_values()


def test_binding_nested_corruption_fails_closed() -> None:
    value = _distinct_reference_qualification()
    binding = value.price_determination_binding
    assert binding is not None
    object.__setattr__(
        binding,
        "relationship",
        BadRelationshipCode("price-determination-reference"),
    )
    with pytest.raises(CfdQualificationValidationError):
        value.logical_values()


def test_settlement_convention_nested_corruption_fails_closed() -> None:
    convention = SettlementConvention(
        2,
        BusinessCalendarRef("nyc"),
        BusinessDayConventionCode("following"),
    )
    value = CfdForwardFormQualification(
        _qualification_id(),
        _cfd_identity(),
        _cash_forward(settlement_convention=convention),
        _cfd_evidence(),
        None,
    )
    object.__setattr__(convention, "business_day_lag", True)
    with pytest.raises(CfdQualificationValidationError):
        value.logical_values()


def test_partially_fabricated_objects_never_become_logical_identity() -> None:
    fabricated = object.__new__(CfdQualificationId)
    with pytest.raises((AttributeError, CfdQualificationValidationError)):
        fabricated.logical_values()

    fabricated_parent = object.__new__(CfdRollingSpotLifecycleQualification)
    with pytest.raises((AttributeError, CfdQualificationValidationError)):
        fabricated_parent.logical_values()


def test_values_are_frozen_and_slotted() -> None:
    value = _same_reference_qualification()
    assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(value, "evidence_ref", _cfd_evidence(999))


def test_forward_logical_identity_does_not_collapse_material_dimensions() -> None:
    base = _same_reference_qualification()
    different_qid = CfdForwardFormQualification(
        _qualification_id(99),
        base.cfd_identity,
        base.forward,
        base.evidence_ref,
        None,
    )
    different_identity_evidence = CfdForwardFormQualification(
        base.qualification_id,
        _cfd_identity(evidence_index=99),
        base.forward,
        base.evidence_ref,
        None,
    )
    different_evidence = CfdForwardFormQualification(
        base.qualification_id,
        base.cfd_identity,
        base.forward,
        _cfd_evidence(99),
        None,
    )
    assert len(
        {
            base.logical_values(),
            different_qid.logical_values(),
            different_identity_evidence.logical_values(),
            different_evidence.logical_values(),
        }
    ) == 4


def test_distinct_binding_identity_is_material() -> None:
    first = _distinct_reference_qualification()
    second_binding = IdentityRelationship(
        relationship_id=IdentityRelationshipId(_uuid(44)),
        source_identity_id=_identity_id(20),
        target_identity_id=_identity_id(22),
        relationship=IdentityRelationshipCode("price-determination-reference"),
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        evidence_ref=_identity_evidence(41),
        ordinal=None,
    )
    second = _distinct_reference_qualification(binding=second_binding)
    assert first.logical_values() != second.logical_values()


_FORBIDDEN_FIELDS = {
    "current_price",
    "observed_fixing_value",
    "pnl",
    "payoff",
    "margin",
    "leverage",
    "provider_symbol",
    "order",
    "trade",
    "settlement_mutation",
    "legal_eligibility",
    "spread_bet",
}

_FORBIDDEN_CALL_NAMES = {
    "execute",
    "settle",
    "calculate_pnl",
    "calculate_payoff",
    "observe",
    "sleep",
    "submit",
    "connect",
}

_FORBIDDEN_IMPORT_ROOTS = {
    "requests",
    "httpx",
    "socket",
    "subprocess",
    "threading",
    "secrets",
    "random",
}


def test_negative_space_field_and_method_surface() -> None:
    owners = (CfdForwardFormQualification, CfdRollingSpotLifecycleQualification)
    for owner in owners:
        assert {field.name for field in fields(owner)}.isdisjoint(_FORBIDDEN_FIELDS)
        if owner is CfdForwardFormQualification:
            instance = _same_reference_qualification()
        else:
            instance = _rolling_qualification()
        for name in _FORBIDDEN_CALL_NAMES:
            assert not hasattr(instance, name)


def test_source_ast_has_no_operational_authority_or_wall_clock() -> None:
    source = inspect.getsource(cfd_module)
    tree = ast.parse(source)
    import_roots: set[str] = set()
    called_names: set[str] = set()
    called_attributes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            import_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            import_roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_attributes.add(node.func.attr)
    assert import_roots.isdisjoint(_FORBIDDEN_IMPORT_ROOTS)
    assert called_names.isdisjoint(_FORBIDDEN_CALL_NAMES | {"uuid4"})
    assert called_attributes.isdisjoint(
        _FORBIDDEN_CALL_NAMES | {"now", "today", "uuid4"}
    )


def test_module_constants_are_immutable_primitives_not_mutable_value_objects() -> None:
    assert cfd_module._CFD_FAMILY_CODE == "contracts-for-difference"
    assert type(cfd_module._CFD_FAMILY_CODE) is str
    assert cfd_module._PRICE_DETERMINATION_RELATIONSHIP_CODE == (
        "price-determination-reference"
    )
    assert type(cfd_module._PRICE_DETERMINATION_RELATIONSHIP_CODE) is str
