"""AGRI-2 agricultural identity qualification composed over UMI owners.

This module does not create economic identity authority. It verifies that
agricultural reference and futures identities are internally consistent with
UMI-02, UMI-05 and UMI-07.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.commodity_contract_delivery_semantics import (
    CommodityFuturesContractTerms,
    CommodityReferenceTerms,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    ListingIdentity,
)


class AgriculturalIdentityQualificationError(ValueError):
    """AGRI-2 identity composition failed closed."""


class AgriculturalCommodityClass(StrEnum):
    AGRICULTURE = "agriculture"
    SOFTS = "softs"
    LIVESTOCK = "livestock"


class AgriculturalCropYearCode:
    """Opaque crop-year code; interpretation requires region/evidence."""

    __slots__ = ("value",)

    def __init__(self, value: str) -> None:
        if (
            not isinstance(value, str)
            or len(value) > 32
            or fullmatch(r"[a-z0-9]+(?:[._/-][a-z0-9]+)*", value) is None
        ):
            raise AgriculturalIdentityQualificationError(
                "crop-year code must use bounded canonical syntax"
            )
        self.value = value

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, AgriculturalCropYearCode)
            and self.value == other.value
        )

    def __hash__(self) -> int:
        return hash(self.value)

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class AgriculturalCropYearReference:
    """Region-scoped crop-year context; never a universal crop calendar."""

    code: AgriculturalCropYearCode
    region_identity_id: EconomicIdentityId
    evidence_ref: IdentityEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.code, AgriculturalCropYearCode):
            raise AgriculturalIdentityQualificationError(
                "crop year code must be AgriculturalCropYearCode"
            )
        if not isinstance(self.region_identity_id, EconomicIdentityId):
            raise AgriculturalIdentityQualificationError(
                "crop year region must be UMI EconomicIdentityId"
            )
        if not isinstance(self.evidence_ref, IdentityEvidenceRef):
            raise AgriculturalIdentityQualificationError(
                "crop year evidence must be UMI IdentityEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.code.logical_values(),
            self.region_identity_id.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class AgriculturalCommodityReferenceQualification:
    """Agricultural specialization of one existing UMI commodity reference."""

    economic_identity: EconomicIdentity
    commodity_reference: CommodityReferenceTerms
    agricultural_class: AgriculturalCommodityClass
    crop_year: AgriculturalCropYearReference | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.economic_identity, EconomicIdentity):
            raise AgriculturalIdentityQualificationError(
                "agricultural reference requires UMI EconomicIdentity"
            )
        if not isinstance(self.commodity_reference, CommodityReferenceTerms):
            raise AgriculturalIdentityQualificationError(
                "agricultural reference requires UMI-07 CommodityReferenceTerms"
            )
        if not isinstance(
            self.agricultural_class,
            AgriculturalCommodityClass,
        ):
            raise AgriculturalIdentityQualificationError(
                "agricultural_class must be AgriculturalCommodityClass"
            )
        if self.economic_identity.kind is not EconomicIdentityKind.REFERENCE_OBJECT:
            raise AgriculturalIdentityQualificationError(
                "agricultural commodity reference must be UMI reference object"
            )
        if self.economic_identity.construction is not IdentityConstructionKind.NATIVE:
            raise AgriculturalIdentityQualificationError(
                "agricultural base commodity reference must be native identity"
            )
        if self.economic_identity.family.value != "commodities":
            raise AgriculturalIdentityQualificationError(
                "agricultural reference must retain UMI commodities family"
            )
        if (
            self.commodity_reference.reference_identity_id
            != self.economic_identity.identity_id
        ):
            raise AgriculturalIdentityQualificationError(
                "commodity reference identity must match UMI economic identity"
            )
        if (
            self.commodity_reference.commodity_class.value
            != self.agricultural_class.value
        ):
            raise AgriculturalIdentityQualificationError(
                "agricultural class must match UMI-07 commodity class"
            )
        if self.crop_year is not None and not isinstance(
            self.crop_year,
            AgriculturalCropYearReference,
        ):
            raise AgriculturalIdentityQualificationError(
                "crop_year must be AgriculturalCropYearReference or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "agricultural-reference-qualification",
            self.economic_identity.logical_values(),
            self.commodity_reference.logical_values(),
            self.agricultural_class.value,
            (
                self.crop_year.logical_values()
                if self.crop_year is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class AgriculturalFuturesContractQualification:
    """Dated agricultural futures identity composed over UMI-02/05/07."""

    economic_identity: EconomicIdentity
    listing: ListingIdentity
    agricultural_reference: AgriculturalCommodityReferenceQualification
    commodity_contract: CommodityFuturesContractTerms

    def __post_init__(self) -> None:
        if not isinstance(self.economic_identity, EconomicIdentity):
            raise AgriculturalIdentityQualificationError(
                "agricultural futures requires UMI EconomicIdentity"
            )
        if not isinstance(self.listing, ListingIdentity):
            raise AgriculturalIdentityQualificationError(
                "agricultural futures requires UMI ListingIdentity"
            )
        if not isinstance(
            self.agricultural_reference,
            AgriculturalCommodityReferenceQualification,
        ):
            raise AgriculturalIdentityQualificationError(
                "agricultural futures requires agricultural reference qualification"
            )
        if not isinstance(
            self.commodity_contract,
            CommodityFuturesContractTerms,
        ):
            raise AgriculturalIdentityQualificationError(
                "agricultural futures requires UMI-07 CommodityFuturesContractTerms"
            )
        if self.economic_identity.kind is not EconomicIdentityKind.TRADABLE_INSTRUMENT:
            raise AgriculturalIdentityQualificationError(
                "agricultural futures identity must be tradable instrument"
            )
        if self.economic_identity.construction is not IdentityConstructionKind.NATIVE:
            raise AgriculturalIdentityQualificationError(
                "dated agricultural futures must be native identity"
            )
        if self.economic_identity.family.value != "futures":
            raise AgriculturalIdentityQualificationError(
                "agricultural futures must retain UMI futures family"
            )
        if self.listing.economic_identity_id != self.economic_identity.identity_id:
            raise AgriculturalIdentityQualificationError(
                "listing must reference agricultural futures economic identity"
            )
        futures = self.commodity_contract.futures
        if futures.instrument_identity_id != self.economic_identity.identity_id:
            raise AgriculturalIdentityQualificationError(
                "UMI-05 futures instrument identity mismatch"
            )
        reference_identity = (
            self.agricultural_reference.economic_identity.identity_id
        )
        if futures.reference_identity_id != reference_identity:
            raise AgriculturalIdentityQualificationError(
                "UMI-05 futures reference identity mismatch"
            )
        if (
            self.commodity_contract.commodity_reference.reference_identity_id
            != reference_identity
        ):
            raise AgriculturalIdentityQualificationError(
                "UMI-07 commodity reference identity mismatch"
            )
        if (
            self.commodity_contract.commodity_reference
            != self.agricultural_reference.commodity_reference
        ):
            raise AgriculturalIdentityQualificationError(
                "agricultural reference terms must be exactly retained"
            )

    @property
    def contract_year(self) -> int:
        return self.commodity_contract.futures.contract_month.year

    @property
    def contract_month(self) -> int:
        return self.commodity_contract.futures.contract_month.month

    def logical_values(self) -> tuple[object, ...]:
        return (
            "agricultural-futures-contract-qualification",
            self.economic_identity.logical_values(),
            self.listing.logical_values(),
            self.agricultural_reference.logical_values(),
            self.commodity_contract.logical_values(),
        )


def assert_agricultural_native_execution_identity(
    identity: EconomicIdentity,
) -> None:
    """Reject reference/composite/continuous identities as execution contracts."""

    if not isinstance(identity, EconomicIdentity):
        raise AgriculturalIdentityQualificationError(
            "execution identity guard requires UMI EconomicIdentity"
        )
    if identity.kind is not EconomicIdentityKind.TRADABLE_INSTRUMENT:
        raise AgriculturalIdentityQualificationError(
            "agricultural execution identity must be tradable instrument"
        )
    if identity.construction is not IdentityConstructionKind.NATIVE:
        raise AgriculturalIdentityQualificationError(
            "agricultural execution identity must be native contract"
        )
