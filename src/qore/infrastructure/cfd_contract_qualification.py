"""Bounded CFD qualification/composition over existing UMI-02 and UMI-05.

This module does not own universal CFD economics, market observations,
valuation, execution, settlement mutation, provider support, or legal
eligibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeBenchmarkReference,
    DerivativeFixingTerms,
    DerivativeSettlementStyle,
    ForwardContractTerms,
)
from qore.infrastructure.fixed_income_economics import (
    FinancialTenor,
    FinancialTenorUnit,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    IdentityFamilyCode,
    IdentityRelationship,
    IdentityRelationshipCode,
)
from qore.kernel.errors import InfrastructureError

_CFD_FAMILY = IdentityFamilyCode("contracts-for-difference")
_PRICE_DETERMINATION_RELATIONSHIP = IdentityRelationshipCode(
    "price-determination-reference"
)


class CfdQualificationSemanticsError(InfrastructureError):
    __slots__ = ()


class CfdQualificationValidationError(CfdQualificationSemanticsError):
    __slots__ = ()


def _fail(message: str) -> None:
    raise CfdQualificationValidationError(message)


def _require_uuid(value: object) -> None:
    if type(value) is not UUID:
        _fail("expected UUID")


def _require_economic_identity_id(value: object) -> None:
    if type(value) is not EconomicIdentityId:
        _fail("expected EconomicIdentityId")


@dataclass(frozen=True, slots=True)
class CfdQualificationId:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value)

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CfdEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value)

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


def _validate_cfd_identity(identity: EconomicIdentity) -> None:
    if type(identity) is not EconomicIdentity:
        _fail("expected EconomicIdentity")
    if type(identity.family) is not IdentityFamilyCode:
        _fail("family must be exact IdentityFamilyCode")
    if type(identity.family.value) is not str:
        _fail("family value must be str")
    if identity.family != _CFD_FAMILY:
        _fail("CFD identity family must be contracts-for-difference")
    _require_economic_identity_id(identity.identity_id)


@dataclass(frozen=True, slots=True)
class CfdForwardFormQualification:
    """Bounded fixed-maturity forward-form CFD qualification.

    This value qualifies an existing UMI-05 ForwardContractTerms as a
    CFD-family, cash-settled forward-form instrument with a contractually
    bound price-determination/fixing reference.

    It does not calculate payoff, retain observations, or mutate settlement.
    """

    qualification_id: CfdQualificationId
    cfd_identity: EconomicIdentity
    forward: ForwardContractTerms
    evidence_ref: CfdEvidenceRef
    price_determination_binding: IdentityRelationship | None

    def __post_init__(self) -> None:
        if type(self.qualification_id) is not CfdQualificationId:
            _fail("expected CfdQualificationId")
        if type(self.evidence_ref) is not CfdEvidenceRef:
            _fail("expected CfdEvidenceRef")

        _validate_cfd_identity(self.cfd_identity)

        if type(self.forward) is not ForwardContractTerms:
            _fail("expected ForwardContractTerms")

        _require_economic_identity_id(self.forward.instrument_identity_id)
        if self.cfd_identity.identity_id != self.forward.instrument_identity_id:
            _fail(
                "CFD identity id must equal ForwardContractTerms."
                "instrument_identity_id"
            )

        if type(self.forward.settlement_style) is not DerivativeSettlementStyle:
            _fail("expected DerivativeSettlementStyle")
        if self.forward.settlement_style is not DerivativeSettlementStyle.CASH:
            _fail(
                "bounded forward-form CFD qualification requires CASH "
                "settlement"
            )

        fixing = self.forward.fixing
        if fixing is None:
            _fail("bounded forward-form CFD qualification requires fixing terms")
        if type(fixing) is not DerivativeFixingTerms:
            _fail("expected DerivativeFixingTerms")
        if type(fixing.fixing_date) is not date:
            _fail("fixing date must be exact date")
        if fixing.fixing_date > self.forward.maturity_date:
            _fail("fixing date cannot exceed forward maturity date")

        if type(fixing.reference) is not DerivativeBenchmarkReference:
            _fail("expected DerivativeBenchmarkReference")
        _require_economic_identity_id(fixing.reference.reference_identity_id)

        economic_reference = self.forward.reference_identity_id
        fixing_reference = fixing.reference.reference_identity_id
        _require_economic_identity_id(economic_reference)
        _require_economic_identity_id(fixing_reference)

        if economic_reference == fixing_reference:
            if self.price_determination_binding is not None:
                _fail(
                    "price-determination binding is not required when "
                    "economic reference and fixing reference are identical"
                )
            return

        if self.price_determination_binding is None:
            _fail(
                "distinct fixing reference requires explicit "
                "price-determination binding"
            )

        binding = self.price_determination_binding
        if type(binding) is not IdentityRelationship:
            _fail("expected IdentityRelationship")

        _require_economic_identity_id(binding.source_identity_id)
        _require_economic_identity_id(binding.target_identity_id)

        if binding.source_identity_id != economic_reference:
            _fail(
                "price-determination binding source must be the CFD "
                "economic reference"
            )
        if binding.target_identity_id != fixing_reference:
            _fail(
                "price-determination binding target must be the fixing "
                "reference"
            )

        if type(binding.relationship) is not IdentityRelationshipCode:
            _fail("expected IdentityRelationshipCode")
        if type(binding.relationship.value) is not str:
            _fail("relationship code value must be str")
        if binding.relationship != _PRICE_DETERMINATION_RELATIONSHIP:
            _fail(
                "price-determination binding must use "
                "price-determination-reference"
            )

        self._validate_binding_covers_fixing_day(binding, fixing.fixing_date)

    @staticmethod
    def _validate_binding_covers_fixing_day(
        binding: IdentityRelationship,
        fixing_date: date,
    ) -> None:
        if type(binding.effective_from) is not datetime:
            _fail("effective_from must be datetime")
        if binding.effective_from.tzinfo is None:
            _fail("effective_from must be timezone-aware")

        effective_from_utc = binding.effective_from.astimezone(UTC)
        fixing_day_start = datetime.combine(
            fixing_date,
            time.min,
            tzinfo=UTC,
        )
        if effective_from_utc > fixing_day_start:
            _fail(
                "price-determination binding is not effective at the "
                "start of the fixing date"
            )

        next_day_start = fixing_day_start + timedelta(days=1)

        effective_until = binding.effective_until
        if effective_until is None:
            return

        if type(effective_until) is not datetime:
            _fail("effective_until must be datetime")
        if effective_until.tzinfo is None:
            _fail("effective_until must be timezone-aware")

        effective_until_utc = effective_until.astimezone(UTC)
        if effective_until_utc < next_day_start:
            _fail(
                "price-determination binding does not cover the complete "
                "fixing date"
            )

    def logical_values(self) -> tuple[object, ...]:
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
    """Bounded ESMA-style rolling-spot CFD lifecycle qualification.

    Existence of this value means the bounded specimen retains:

    - automatic contract rollover at the end of each contract period;
    - contractual party termination capability.

    It grants NO scheduler, execution, generated roll dates, margin close-out,
    current price, or financing authority.
    """

    qualification_id: CfdQualificationId
    cfd_identity: EconomicIdentity
    contract_period: FinancialTenor
    evidence_ref: CfdEvidenceRef

    def __post_init__(self) -> None:
        if type(self.qualification_id) is not CfdQualificationId:
            _fail("expected CfdQualificationId")
        if type(self.evidence_ref) is not CfdEvidenceRef:
            _fail("expected CfdEvidenceRef")

        _validate_cfd_identity(self.cfd_identity)

        if type(self.contract_period) is not FinancialTenor:
            _fail("expected FinancialTenor")
        if type(self.contract_period.unit) is not FinancialTenorUnit:
            _fail("expected FinancialTenorUnit")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "cfd-rolling-spot-lifecycle-qualification",
            self.qualification_id.logical_values(),
            self.cfd_identity.logical_values(),
            self.contract_period.logical_values(),
            "automatic-contract-rollover",
            "party-termination-capability",
            self.evidence_ref.logical_values(),
        )
