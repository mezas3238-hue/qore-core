"""Bounded CFD qualification/composition over certified UMI-02/05/FX semantics.

This module owns only static D04 qualification material required by UNR-015.
It does not own universal CFD economics, observations, valuation, margin/risk,
execution, settlement mutation, provider support, legal eligibility, or Production.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Never
from uuid import UUID

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
from qore.kernel.errors import InfrastructureError

_CFD_FAMILY_CODE = "contracts-for-difference"
_PRICE_DETERMINATION_RELATIONSHIP_CODE = "price-determination-reference"


class CfdQualificationSemanticsError(InfrastructureError):
    __slots__ = ()


class CfdQualificationValidationError(CfdQualificationSemanticsError):
    __slots__ = ()


def _fail(message: str) -> Never:
    raise CfdQualificationValidationError(message)


def _require_uuid(value: object, *, field_name: str) -> None:
    if type(value) is not UUID:
        _fail(f"{field_name} must be exact UUID")


def _require_decimal(
    value: object,
    *,
    field_name: str,
    positive: bool = False,
) -> None:
    if type(value) is not Decimal or not value.is_finite():
        _fail(f"{field_name} must be exact finite Decimal")
    if positive and value <= 0:
        _fail(f"{field_name} must be positive")


def _require_identity_id(value: object, *, field_name: str) -> None:
    if type(value) is not EconomicIdentityId:
        _fail(f"{field_name} must be exact EconomicIdentityId")
    _require_uuid(value.value, field_name=f"{field_name}.value")


def _require_uuid_wrapper(
    value: object,
    expected_type: type[object],
    *,
    field_name: str,
) -> None:
    if type(value) is not expected_type:
        _fail(f"{field_name} has invalid exact type")
    nested = getattr(value, "value", None)
    _require_uuid(nested, field_name=f"{field_name}.value")


def _require_code_wrapper(
    value: object,
    expected_type: type[object],
    *,
    field_name: str,
) -> None:
    if type(value) is not expected_type:
        _fail(f"{field_name} has invalid exact type")
    nested = getattr(value, "value", None)
    if type(nested) is not str or not nested:
        _fail(f"{field_name}.value must be non-empty exact str")
    post_init = getattr(value, "__post_init__", None)
    if not callable(post_init):
        _fail(f"{field_name} has no validator")
    post_init()


def _validate_financial_tenor(value: object, *, field_name: str) -> None:
    if type(value) is not FinancialTenor:
        _fail(f"{field_name} must be exact FinancialTenor")
    if type(value.value) is not int or value.value <= 0:
        _fail(f"{field_name}.value must be positive exact int")
    if type(value.unit) is not FinancialTenorUnit:
        _fail(f"{field_name}.unit must be exact FinancialTenorUnit")


def _validate_identity(identity: object) -> None:
    if type(identity) is not EconomicIdentity:
        _fail("cfd_identity must be exact EconomicIdentity")
    _require_identity_id(identity.identity_id, field_name="cfd_identity.identity_id")
    if type(identity.kind) is not EconomicIdentityKind:
        _fail("cfd_identity.kind must be exact EconomicIdentityKind")
    if identity.kind is not EconomicIdentityKind.TRADABLE_INSTRUMENT:
        _fail("CFD identity must be a tradable instrument")
    _require_code_wrapper(
        identity.family,
        IdentityFamilyCode,
        field_name="cfd_identity.family",
    )
    if identity.family.value != _CFD_FAMILY_CODE:
        _fail("CFD identity family must be contracts-for-difference")
    if type(identity.construction) is not IdentityConstructionKind:
        _fail("cfd_identity.construction must be exact IdentityConstructionKind")
    if identity.construction is IdentityConstructionKind.CONTINUOUS_REFERENCE:
        _fail("tradable CFD identity must not use continuous-reference construction")
    _require_uuid_wrapper(
        identity.evidence_ref,
        IdentityEvidenceRef,
        field_name="cfd_identity.evidence_ref",
    )


def _validate_fx_pair(pair: object) -> None:
    if type(pair) is not FxQuotedCurrencyPair:
        _fail("spot_reference must be exact FxQuotedCurrencyPair")
    _require_identity_id(pair.pair_identity_id, field_name="spot_reference.pair_identity_id")
    _require_identity_id(
        pair.currency1_identity_id,
        field_name="spot_reference.currency1_identity_id",
    )
    _require_identity_id(
        pair.currency2_identity_id,
        field_name="spot_reference.currency2_identity_id",
    )
    if pair.currency1_identity_id == pair.currency2_identity_id:
        _fail("spot-reference currencies must differ")
    if pair.pair_identity_id in (
        pair.currency1_identity_id,
        pair.currency2_identity_id,
    ):
        _fail("spot-reference pair identity must differ from currency identities")
    if type(pair.quote_basis) is not FxQuoteBasis:
        _fail("spot_reference.quote_basis must be exact FxQuoteBasis")
    _require_uuid_wrapper(
        pair.evidence_ref,
        FxEvidenceRef,
        field_name="spot_reference.evidence_ref",
    )


def _validate_settlement_convention(value: object) -> None:
    if type(value) is not SettlementConvention:
        _fail("forward settlement_convention must be exact SettlementConvention")
    if type(value.business_day_lag) is not int or value.business_day_lag < 0:
        _fail("settlement business_day_lag must be non-negative exact int")
    _require_code_wrapper(
        value.calendar_ref,
        BusinessCalendarRef,
        field_name="settlement calendar_ref",
    )
    _require_code_wrapper(
        value.business_day_convention,
        BusinessDayConventionCode,
        field_name="settlement business_day_convention",
    )


def _validate_forward(forward: object) -> None:
    if type(forward) is not ForwardContractTerms:
        _fail("forward must be exact ForwardContractTerms")

    _require_uuid_wrapper(forward.terms_id, DerivativeTermsId, field_name="forward.terms_id")
    _require_identity_id(
        forward.instrument_identity_id,
        field_name="forward.instrument_identity_id",
    )
    _require_identity_id(
        forward.reference_identity_id,
        field_name="forward.reference_identity_id",
    )
    _require_identity_id(
        forward.settlement_identity_id,
        field_name="forward.settlement_identity_id",
    )
    if forward.instrument_identity_id == forward.reference_identity_id:
        _fail("forward instrument and reference identity must differ")
    if forward.instrument_identity_id == forward.settlement_identity_id:
        _fail("forward instrument and settlement identity must differ")

    if type(forward.notional) is not DerivativeNotional:
        _fail("forward.notional must be exact DerivativeNotional")
    _require_decimal(
        forward.notional.value,
        field_name="forward.notional.value",
        positive=True,
    )
    _require_identity_id(
        forward.notional.unit_identity_id,
        field_name="forward.notional.unit_identity_id",
    )

    if type(forward.agreed_strike) is not DerivativeStrike:
        _fail("forward.agreed_strike must be exact DerivativeStrike")
    strike = forward.agreed_strike
    _require_decimal(strike.value, field_name="forward.agreed_strike.value")
    if type(strike.basis) is not DerivativeStrikeBasis:
        _fail("forward.agreed_strike.basis must be exact DerivativeStrikeBasis")
    if strike.basis is not DerivativeStrikeBasis.PRICE:
        _fail("bounded forward-form CFD requires PRICE strike semantics")
    _require_identity_id(
        strike.quote_identity_id,
        field_name="forward.agreed_strike.quote_identity_id",
    )
    _require_code_wrapper(
        strike.price_quote_basis,
        DerivativePriceQuoteBasisCode,
        field_name="forward.agreed_strike.price_quote_basis",
    )
    if strike.convention is not None:
        _fail("PRICE strike must not carry rate/yield convention")

    if type(forward.maturity_date) is not date:
        _fail("forward.maturity_date must be exact date")
    if type(forward.settlement_style) is not DerivativeSettlementStyle:
        _fail("forward.settlement_style must be exact DerivativeSettlementStyle")
    if forward.settlement_style is not DerivativeSettlementStyle.CASH:
        _fail("bounded forward-form CFD requires CASH settlement")
    _require_uuid_wrapper(
        forward.evidence_ref,
        DerivativeEvidenceRef,
        field_name="forward.evidence_ref",
    )

    fixing = forward.fixing
    if type(fixing) is not DerivativeFixingTerms:
        _fail("bounded forward-form CFD requires exact DerivativeFixingTerms")
    if type(fixing.fixing_date) is not date:
        _fail("forward.fixing.fixing_date must be exact date")
    if fixing.fixing_date > forward.maturity_date:
        _fail("forward fixing_date must not be after maturity_date")
    _require_uuid_wrapper(
        fixing.evidence_ref,
        DerivativeEvidenceRef,
        field_name="forward.fixing.evidence_ref",
    )
    if type(fixing.reference) is not DerivativeBenchmarkReference:
        _fail("forward.fixing.reference must be exact DerivativeBenchmarkReference")
    _require_identity_id(
        fixing.reference.reference_identity_id,
        field_name="forward.fixing.reference.reference_identity_id",
    )
    _require_code_wrapper(
        fixing.reference.role,
        DerivativeReferenceRoleCode,
        field_name="forward.fixing.reference.role",
    )
    if fixing.reference.tenor is not None:
        _validate_financial_tenor(
            fixing.reference.tenor,
            field_name="forward.fixing.reference.tenor",
        )

    if forward.settlement_convention is not None:
        _validate_settlement_convention(forward.settlement_convention)


def _validate_binding(
    binding: object,
    *,
    economic_reference: EconomicIdentityId,
    fixing_reference: EconomicIdentityId,
) -> None:
    if type(binding) is not IdentityRelationship:
        _fail("price_determination_binding must be exact IdentityRelationship")
    _require_uuid_wrapper(
        binding.relationship_id,
        IdentityRelationshipId,
        field_name="price_determination_binding.relationship_id",
    )
    _require_identity_id(
        binding.source_identity_id,
        field_name="price_determination_binding.source_identity_id",
    )
    _require_identity_id(
        binding.target_identity_id,
        field_name="price_determination_binding.target_identity_id",
    )
    if binding.source_identity_id != economic_reference:
        _fail("price-determination binding source must be economic reference")
    if binding.target_identity_id != fixing_reference:
        _fail("price-determination binding target must be fixing reference")
    _require_code_wrapper(
        binding.relationship,
        IdentityRelationshipCode,
        field_name="price_determination_binding.relationship",
    )
    if binding.relationship.value != _PRICE_DETERMINATION_RELATIONSHIP_CODE:
        _fail("binding relationship must be price-determination-reference")
    if type(binding.effective_from) is not datetime:
        _fail("binding effective_from must be exact datetime")
    if binding.effective_from.tzinfo is None or binding.effective_from.utcoffset() is None:
        _fail("binding effective_from must be timezone-aware")
    if binding.effective_until is not None:
        if type(binding.effective_until) is not datetime:
            _fail("binding effective_until must be exact datetime or None")
        if (
            binding.effective_until.tzinfo is None
            or binding.effective_until.utcoffset() is None
        ):
            _fail("binding effective_until must be timezone-aware")
        if binding.effective_until <= binding.effective_from:
            _fail("binding effective_until must be after effective_from")
    _require_uuid_wrapper(
        binding.evidence_ref,
        IdentityEvidenceRef,
        field_name="price_determination_binding.evidence_ref",
    )
    if binding.ordinal is not None and (
        type(binding.ordinal) is not int or binding.ordinal <= 0
    ):
        _fail("binding ordinal must be positive exact int or None")


@dataclass(frozen=True, slots=True)
class CfdQualificationId:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="qualification_id.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CfdEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="evidence_ref.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CfdForwardFormQualification:
    """Static qualification for a bounded cash-settled forward-form CFD."""

    qualification_id: CfdQualificationId
    cfd_identity: EconomicIdentity
    forward: ForwardContractTerms
    evidence_ref: CfdEvidenceRef
    price_determination_binding: IdentityRelationship | None

    def __post_init__(self) -> None:
        if type(self.qualification_id) is not CfdQualificationId:
            _fail("qualification_id must be exact CfdQualificationId")
        self.qualification_id.__post_init__()
        if type(self.evidence_ref) is not CfdEvidenceRef:
            _fail("evidence_ref must be exact CfdEvidenceRef")
        self.evidence_ref.__post_init__()
        _validate_identity(self.cfd_identity)
        _validate_forward(self.forward)

        if self.cfd_identity.identity_id != self.forward.instrument_identity_id:
            _fail("CFD identity id must equal forward instrument identity id")

        fixing = self.forward.fixing
        if fixing is None:
            _fail("validated forward unexpectedly lacks fixing terms")
        economic_reference = self.forward.reference_identity_id
        fixing_reference = fixing.reference.reference_identity_id

        if economic_reference == fixing_reference:
            if self.price_determination_binding is not None:
                _fail("same reference must not carry redundant price binding")
            return

        if self.price_determination_binding is None:
            _fail("distinct fixing reference requires explicit price binding")
        _validate_binding(
            self.price_determination_binding,
            economic_reference=economic_reference,
            fixing_reference=fixing_reference,
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "cfd-forward-form-qualification",
            self.qualification_id.logical_values(),
            self.cfd_identity.logical_values(),
            self.forward.logical_values(),
            self.price_determination_binding.logical_values()
            if self.price_determination_binding is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CfdRollingSpotLifecycleQualification:
    """Static qualification for the bounded ESMA-style rolling-spot specimen."""

    qualification_id: CfdQualificationId
    cfd_identity: EconomicIdentity
    spot_reference: FxQuotedCurrencyPair
    contract_period: FinancialTenor
    evidence_ref: CfdEvidenceRef

    def __post_init__(self) -> None:
        if type(self.qualification_id) is not CfdQualificationId:
            _fail("qualification_id must be exact CfdQualificationId")
        self.qualification_id.__post_init__()
        if type(self.evidence_ref) is not CfdEvidenceRef:
            _fail("evidence_ref must be exact CfdEvidenceRef")
        self.evidence_ref.__post_init__()
        _validate_identity(self.cfd_identity)
        _validate_fx_pair(self.spot_reference)
        _validate_financial_tenor(self.contract_period, field_name="contract_period")
        if self.cfd_identity.identity_id == self.spot_reference.pair_identity_id:
            _fail("CFD identity must not collapse into FX pair reference identity")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "cfd-rolling-spot-lifecycle-qualification",
            self.qualification_id.logical_values(),
            self.cfd_identity.logical_values(),
            self.spot_reference.logical_values(),
            self.contract_period.logical_values(),
            "automatic-contract-rollover",
            "party-termination-capability",
            self.evidence_ref.logical_values(),
        )
