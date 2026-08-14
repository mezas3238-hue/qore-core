from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from re import fullmatch
from uuid import UUID

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeSettlementStyle,
    FuturesContractTerms,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class CommodityContractSemanticsError(InfrastructureError):
    """Base error for provider-neutral commodity contract semantics."""

    __slots__ = ()


class CommodityContractValidationError(CommodityContractSemanticsError):
    """Violation of a commodity contract semantic invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise CommodityContractValidationError(f"{field_name} must be UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise CommodityContractValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise CommodityContractValidationError(f"{field_name} must be date")


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise CommodityContractValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


@dataclass(frozen=True, slots=True)
class CommodityTermsId:
    """Local immutable commodity-terms identity; never economic identity."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="commodity terms id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CommodityEvidenceRef:
    """Opaque reference to retained commodity evidence; never evidence content."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="commodity evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CommodityClassCode:
    """Bounded commodity economic class; never UMI-02 identity-family authority."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="commodity class code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CommodityGradeCode:
    """Contractual deliverable grade/specification code; no quality engine."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="commodity grade code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CommodityDeliveryMethodCode:
    """Physical delivery mechanism code; no logistics or settlement engine."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="commodity delivery method code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CommodityDeliveryWindow:
    """Contractual delivery window only; D06 owns calendar/date resolution."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        _validate_date(self.start_date, field_name="commodity delivery start_date")
        _validate_date(self.end_date, field_name="commodity delivery end_date")
        if self.end_date < self.start_date:
            raise CommodityContractValidationError(
                "commodity delivery end_date must not be before start_date"
            )

    def logical_values(self) -> tuple[str, str]:
        return (self.start_date.isoformat(), self.end_date.isoformat())


@dataclass(frozen=True, slots=True)
class CommodityReferenceTerms:
    """Commodity reference semantics attached to an existing UMI-02 identity."""

    terms_id: CommodityTermsId
    reference_identity_id: EconomicIdentityId
    commodity_class: CommodityClassCode
    measurement_unit_identity_id: EconomicIdentityId
    evidence_ref: CommodityEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CommodityTermsId):
            raise CommodityContractValidationError(
                "commodity reference terms_id must be CommodityTermsId"
            )
        _validate_identity(
            self.reference_identity_id,
            field_name="commodity reference identity",
        )
        if not isinstance(self.commodity_class, CommodityClassCode):
            raise CommodityContractValidationError(
                "commodity reference commodity_class must be CommodityClassCode"
            )
        _validate_identity(
            self.measurement_unit_identity_id,
            field_name="commodity measurement-unit identity",
        )
        if self.reference_identity_id == self.measurement_unit_identity_id:
            raise CommodityContractValidationError(
                "commodity reference and measurement-unit identities must differ"
            )
        if not isinstance(self.evidence_ref, CommodityEvidenceRef):
            raise CommodityContractValidationError(
                "commodity reference evidence_ref must be CommodityEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "commodity-reference",
            self.terms_id.logical_values(),
            self.reference_identity_id.logical_values(),
            self.commodity_class.logical_values(),
            self.measurement_unit_identity_id.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CommodityDeliveryAlternative:
    """One eligible physical grade/location/method/window combination."""

    grade: CommodityGradeCode
    location_identity_id: EconomicIdentityId
    method: CommodityDeliveryMethodCode
    window: CommodityDeliveryWindow

    def __post_init__(self) -> None:
        if not isinstance(self.grade, CommodityGradeCode):
            raise CommodityContractValidationError(
                "commodity delivery grade must be CommodityGradeCode"
            )
        _validate_identity(
            self.location_identity_id,
            field_name="commodity delivery location identity",
        )
        if not isinstance(self.method, CommodityDeliveryMethodCode):
            raise CommodityContractValidationError(
                "commodity delivery method must be CommodityDeliveryMethodCode"
            )
        if not isinstance(self.window, CommodityDeliveryWindow):
            raise CommodityContractValidationError(
                "commodity delivery window must be CommodityDeliveryWindow"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.grade.logical_values(),
            self.location_identity_id.logical_values(),
            self.method.logical_values(),
            self.window.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CommodityPhysicalDeliveryTerms:
    """Eligible alternatives; no delivery selection or settlement engine."""

    alternatives: tuple[CommodityDeliveryAlternative, ...]

    def __post_init__(self) -> None:
        if type(self.alternatives) is not tuple or not self.alternatives:
            raise CommodityContractValidationError(
                "commodity physical delivery alternatives must be a non-empty tuple"
            )
        for alternative in self.alternatives:
            if not isinstance(alternative, CommodityDeliveryAlternative):
                raise CommodityContractValidationError(
                    "commodity physical delivery alternatives must contain "
                    "CommodityDeliveryAlternative"
                )

        logical = tuple(
            alternative.logical_values() for alternative in self.alternatives
        )
        if len(set(logical)) != len(logical):
            raise CommodityContractValidationError(
                "commodity physical delivery alternatives must be unique"
            )
        ordered = tuple(
            sorted(
                self.alternatives,
                key=lambda alternative: alternative.logical_values(),
            )
        )
        object.__setattr__(self, "alternatives", ordered)

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(
                alternative.logical_values() for alternative in self.alternatives
            ),
        )


@dataclass(frozen=True, slots=True)
class CommodityFuturesContractTerms:
    """Commodity qualification composed over existing UMI-05 futures terms."""

    terms_id: CommodityTermsId
    futures: FuturesContractTerms
    commodity_reference: CommodityReferenceTerms
    evidence_ref: CommodityEvidenceRef
    physical_delivery: CommodityPhysicalDeliveryTerms | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CommodityTermsId):
            raise CommodityContractValidationError(
                "commodity futures terms_id must be CommodityTermsId"
            )
        if not isinstance(self.futures, FuturesContractTerms):
            raise CommodityContractValidationError(
                "commodity futures futures must be FuturesContractTerms"
            )
        if not isinstance(self.commodity_reference, CommodityReferenceTerms):
            raise CommodityContractValidationError(
                "commodity futures commodity_reference must be CommodityReferenceTerms"
            )
        if not isinstance(self.evidence_ref, CommodityEvidenceRef):
            raise CommodityContractValidationError(
                "commodity futures evidence_ref must be CommodityEvidenceRef"
            )
        if self.physical_delivery is not None and not isinstance(
            self.physical_delivery,
            CommodityPhysicalDeliveryTerms,
        ):
            raise CommodityContractValidationError(
                "commodity futures physical_delivery must be "
                "CommodityPhysicalDeliveryTerms or None"
            )

        if (
            self.futures.reference_identity_id
            != self.commodity_reference.reference_identity_id
        ):
            raise CommodityContractValidationError(
                "commodity futures reference identity must match commodity reference"
            )
        if (
            self.futures.multiplier.unit_identity_id
            != self.commodity_reference.measurement_unit_identity_id
        ):
            raise CommodityContractValidationError(
                "commodity futures multiplier unit must match commodity measurement unit"
            )

        if self.futures.settlement_style is DerivativeSettlementStyle.PHYSICAL:
            if self.physical_delivery is None:
                raise CommodityContractValidationError(
                    "physical commodity futures require explicit physical delivery terms"
                )
        elif self.physical_delivery is not None:
            raise CommodityContractValidationError(
                "cash-settled commodity futures must not carry physical delivery terms"
            )

        if self.physical_delivery is not None:
            forbidden_identities = {
                self.commodity_reference.reference_identity_id,
                self.commodity_reference.measurement_unit_identity_id,
                self.futures.instrument_identity_id,
            }
            for alternative in self.physical_delivery.alternatives:
                if alternative.location_identity_id in forbidden_identities:
                    raise CommodityContractValidationError(
                        "commodity delivery location identity must be distinct from "
                        "contract, commodity, and measurement-unit identities"
                    )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "commodity-futures",
            self.terms_id.logical_values(),
            self.futures.logical_values(),
            self.commodity_reference.logical_values(),
            self.physical_delivery.logical_values()
            if self.physical_delivery is not None
            else None,
            self.evidence_ref.logical_values(),
        )
