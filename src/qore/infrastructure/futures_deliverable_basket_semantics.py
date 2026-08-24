from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMonth,
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativeSettlementStyle,
    DerivativeTermsId,
    DerivativeTickValue,
    FuturesContractTerms,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class FuturesDeliverableBasketSemanticsError(InfrastructureError):
    """Base error for futures deliverable-basket contractual semantics."""

    __slots__ = ()


class FuturesDeliverableBasketValidationError(FuturesDeliverableBasketSemanticsError):
    """Violation of a futures deliverable-basket invariant."""

    __slots__ = ()


def _canonical_decimal(value: Decimal) -> str:
    parts = value.as_tuple()
    if all(digit == 0 for digit in parts.digits):
        return "0"

    digits = list(parts.digits)
    exponent = int(parts.exponent)
    while digits[-1] == 0:
        digits.pop()
        exponent += 1

    normalized = Decimal((parts.sign, tuple(digits), exponent))
    compact = str(normalized).lower()
    sign_length = 1 if parts.sign else 0

    if exponent >= 0:
        fixed_length = sign_length + len(digits) + exponent
    elif -exponent < len(digits):
        fixed_length = sign_length + len(digits) + 1
    else:
        fixed_length = sign_length + 2 - exponent

    if fixed_length <= len(compact) + 1:
        return format(normalized, "f")
    return compact


def _require_exact_uuid(value: UUID, *, field_name: str) -> None:
    if type(value) is not UUID:
        raise FuturesDeliverableBasketValidationError(
            f"{field_name} must be exact UUID"
        )


def _require_exact_decimal(value: Decimal, *, field_name: str) -> None:
    if type(value) is not Decimal:
        raise FuturesDeliverableBasketValidationError(
            f"{field_name} must be exact Decimal"
        )


def _revalidate_economic_identity(
    value: EconomicIdentityId,
    *,
    field_name: str,
) -> None:
    if type(value) is not EconomicIdentityId:
        raise FuturesDeliverableBasketValidationError(
            f"{field_name} must be exact EconomicIdentityId"
        )
    _require_exact_uuid(value.value, field_name=f"{field_name} value")
    value.__post_init__()


def _revalidate_futures_terms(value: FuturesContractTerms) -> None:
    """Revalidate UMI-05 futures leaves without owning their semantics."""

    value.__post_init__()

    if type(value.terms_id) is not DerivativeTermsId:
        raise FuturesDeliverableBasketValidationError(
            "futures terms_id must be exact DerivativeTermsId"
        )
    _require_exact_uuid(value.terms_id.value, field_name="futures terms_id value")
    value.terms_id.__post_init__()

    _revalidate_economic_identity(
        value.instrument_identity_id,
        field_name="futures instrument identity",
    )
    _revalidate_economic_identity(
        value.reference_identity_id,
        field_name="futures reference identity",
    )
    _revalidate_economic_identity(
        value.settlement_identity_id,
        field_name="futures settlement identity",
    )

    if type(value.contract_month) is not DerivativeContractMonth:
        raise FuturesDeliverableBasketValidationError(
            "futures contract_month must be exact DerivativeContractMonth"
        )
    value.contract_month.__post_init__()

    if type(value.multiplier) is not DerivativeContractMultiplier:
        raise FuturesDeliverableBasketValidationError(
            "futures multiplier must be exact DerivativeContractMultiplier"
        )
    _require_exact_decimal(
        value.multiplier.value,
        field_name="futures multiplier value",
    )
    value.multiplier.__post_init__()
    _revalidate_economic_identity(
        value.multiplier.unit_identity_id,
        field_name="futures multiplier unit identity",
    )

    if type(value.evidence_ref) is not DerivativeEvidenceRef:
        raise FuturesDeliverableBasketValidationError(
            "futures evidence_ref must be exact DerivativeEvidenceRef"
        )
    _require_exact_uuid(
        value.evidence_ref.value,
        field_name="futures evidence_ref value",
    )
    value.evidence_ref.__post_init__()

    if value.tick_value is not None:
        if type(value.tick_value) is not DerivativeTickValue:
            raise FuturesDeliverableBasketValidationError(
                "futures tick_value must be exact DerivativeTickValue or None"
            )
        _require_exact_decimal(
            value.tick_value.value,
            field_name="futures tick_value value",
        )
        value.tick_value.__post_init__()
        _revalidate_economic_identity(
            value.tick_value.value_identity_id,
            field_name="futures tick value identity",
        )


@dataclass(frozen=True, slots=True)
class FuturesDeliverableBasketTermsId:
    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            raise FuturesDeliverableBasketValidationError(
                "futures deliverable basket terms id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesDeliverableBasketEvidenceRef:
    """Opaque evidence reference only; never evidence content."""

    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            raise FuturesDeliverableBasketValidationError(
                "futures deliverable basket evidence ref must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesConversionFactor:
    """Contract-defined conversion factor; no valuation methodology is implied."""

    value: Decimal

    def __post_init__(self) -> None:
        if type(self.value) is not Decimal or not self.value.is_finite():
            raise FuturesDeliverableBasketValidationError(
                "futures conversion factor must be a finite Decimal"
            )
        if self.value <= 0:
            raise FuturesDeliverableBasketValidationError(
                "futures conversion factor must be positive"
            )

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesDeliverableBasketEntry:
    """One eligible economic deliverable and its contract-defined factor."""

    deliverable_identity_id: EconomicIdentityId
    conversion_factor: FuturesConversionFactor

    def __post_init__(self) -> None:
        _revalidate_economic_identity(
            self.deliverable_identity_id,
            field_name="deliverable identity",
        )
        if type(self.conversion_factor) is not FuturesConversionFactor:
            raise FuturesDeliverableBasketValidationError(
                "conversion factor must be FuturesConversionFactor"
            )
        self.conversion_factor.__post_init__()

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.deliverable_identity_id.logical_values(),
            self.conversion_factor.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FuturesDeliverableBasketTerms:
    """Static eligibility basket for a physically settled futures contract."""

    terms_id: FuturesDeliverableBasketTermsId
    futures_terms: FuturesContractTerms
    entries: tuple[FuturesDeliverableBasketEntry, ...]
    evidence_ref: FuturesDeliverableBasketEvidenceRef

    def __post_init__(self) -> None:
        if type(self.terms_id) is not FuturesDeliverableBasketTermsId:
            raise FuturesDeliverableBasketValidationError(
                "basket terms_id must be FuturesDeliverableBasketTermsId"
            )
        self.terms_id.__post_init__()
        if type(self.futures_terms) is not FuturesContractTerms:
            raise FuturesDeliverableBasketValidationError(
                "futures_terms must be FuturesContractTerms"
            )
        _revalidate_futures_terms(self.futures_terms)
        if self.futures_terms.settlement_style is not DerivativeSettlementStyle.PHYSICAL:
            raise FuturesDeliverableBasketValidationError(
                "deliverable basket requires physically settled futures"
            )
        if type(self.entries) is not tuple or not self.entries:
            raise FuturesDeliverableBasketValidationError(
                "deliverable basket entries must be a non-empty tuple"
            )
        for entry in self.entries:
            if type(entry) is not FuturesDeliverableBasketEntry:
                raise FuturesDeliverableBasketValidationError(
                    "deliverable basket must contain FuturesDeliverableBasketEntry"
                )
            entry.__post_init__()
            if entry.deliverable_identity_id == self.futures_terms.instrument_identity_id:
                raise FuturesDeliverableBasketValidationError(
                    "futures contract identity cannot be its own deliverable"
                )

        ordered = tuple(sorted(self.entries, key=lambda entry: entry.logical_values()))
        identities = tuple(entry.deliverable_identity_id for entry in ordered)
        if len(set(identities)) != len(identities):
            raise FuturesDeliverableBasketValidationError(
                "deliverable basket identities must be unique"
            )
        object.__setattr__(self, "entries", ordered)

        if type(self.evidence_ref) is not FuturesDeliverableBasketEvidenceRef:
            raise FuturesDeliverableBasketValidationError(
                "basket evidence_ref must be FuturesDeliverableBasketEvidenceRef"
            )
        self.evidence_ref.__post_init__()

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "futures-deliverable-basket",
            self.terms_id.logical_values(),
            self.futures_terms.logical_values(),
            tuple(entry.logical_values() for entry in self.entries),
            self.evidence_ref.logical_values(),
        )
