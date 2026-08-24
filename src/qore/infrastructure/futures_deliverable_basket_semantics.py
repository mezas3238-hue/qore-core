from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeSettlementStyle,
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
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


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
        if type(self.deliverable_identity_id) is not EconomicIdentityId:
            raise FuturesDeliverableBasketValidationError(
                "deliverable identity must be EconomicIdentityId"
            )
        self.deliverable_identity_id.__post_init__()
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
        self.futures_terms.__post_init__()
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
