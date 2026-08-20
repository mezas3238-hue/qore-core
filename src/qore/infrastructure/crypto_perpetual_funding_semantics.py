from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMultiplier,
    DerivativeTickValue,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    ExternalIdentifier,
    ExternalIdentifierKind,
    IdentityRelationshipId,
)
from qore.kernel.errors import InfrastructureError


class CryptoPerpetualSemanticsError(InfrastructureError):
    """Base error for provider-neutral crypto/perpetual semantics."""

    __slots__ = ()


class CryptoPerpetualValidationError(CryptoPerpetualSemanticsError):
    """Violation of a crypto/perpetual semantic invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if type(value) is not UUID:
        raise CryptoPerpetualValidationError(f"{field_name} must be UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise CryptoPerpetualValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise CryptoPerpetualValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


@dataclass(frozen=True, slots=True)
class CryptoTermsId:
    """Local crypto semantic artifact identity; never economic identity."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="crypto terms id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CryptoEvidenceRef:
    """Opaque retained-evidence reference; never evidence content."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="crypto evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CryptoFundingScheduleCode:
    """Governed funding schedule code; it grants no scheduler authority."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="crypto funding schedule code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CryptoNetworkBindingRoleCode:
    """Network relationship qualification; UMI-02 owns relationship endpoints."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="crypto network binding role code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class CryptoPerpetualPriceRole(StrEnum):
    """Semantic price roles only; values/observations remain D07/UMI-10 authority."""

    MARK_PRICE = "mark-price"
    INDEX_PRICE = "index-price"
    LAST_PRICE = "last-price"


class CryptoFundingSignConvention(StrEnum):
    """Meaning of a positive observed funding rate; no rate value is retained here."""

    POSITIVE_LONG_PAYS = "positive-long-pays"
    POSITIVE_SHORT_PAYS = "positive-short-pays"


@dataclass(frozen=True, slots=True)
class CryptoFundingInterval:
    """Funding cadence: fixed duration OR externally governed schedule code."""

    fixed_seconds: int | None = None
    schedule_code: CryptoFundingScheduleCode | None = None

    def __post_init__(self) -> None:
        modes = int(self.fixed_seconds is not None) + int(self.schedule_code is not None)
        if modes != 1:
            raise CryptoPerpetualValidationError(
                "crypto funding interval requires exactly one cadence mode"
            )
        if self.fixed_seconds is not None and (
            type(self.fixed_seconds) is not int or self.fixed_seconds <= 0
        ):
            raise CryptoPerpetualValidationError(
                "crypto funding fixed_seconds must be a positive int"
            )
        if self.schedule_code is not None and not isinstance(
            self.schedule_code,
            CryptoFundingScheduleCode,
        ):
            raise CryptoPerpetualValidationError(
                "crypto funding schedule_code must be CryptoFundingScheduleCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        if self.fixed_seconds is not None:
            return ("fixed-seconds", self.fixed_seconds)
        assert self.schedule_code is not None
        return ("schedule-code", self.schedule_code.logical_values())


@dataclass(frozen=True, slots=True)
class CryptoFundingTerms:
    """Contractual funding convention; contains no observed funding-rate value."""

    interval: CryptoFundingInterval
    sign_convention: CryptoFundingSignConvention
    payment_identity_id: EconomicIdentityId
    evidence_ref: CryptoEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.interval, CryptoFundingInterval):
            raise CryptoPerpetualValidationError(
                "crypto funding interval must be CryptoFundingInterval"
            )
        if not isinstance(self.sign_convention, CryptoFundingSignConvention):
            raise CryptoPerpetualValidationError(
                "crypto funding sign_convention must be CryptoFundingSignConvention"
            )
        _validate_identity(
            self.payment_identity_id,
            field_name="crypto funding payment identity",
        )
        if not isinstance(self.evidence_ref, CryptoEvidenceRef):
            raise CryptoPerpetualValidationError(
                "crypto funding evidence_ref must be CryptoEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.interval.logical_values(),
            self.sign_convention.value,
            self.payment_identity_id.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CryptoNetworkBindingTerms:
    """Qualification of an existing UMI-02 network relationship."""

    terms_id: CryptoTermsId
    relationship_id: IdentityRelationshipId
    role: CryptoNetworkBindingRoleCode
    evidence_ref: CryptoEvidenceRef
    network_identifier: ExternalIdentifier | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CryptoTermsId):
            raise CryptoPerpetualValidationError(
                "crypto network terms_id must be CryptoTermsId"
            )
        if not isinstance(self.relationship_id, IdentityRelationshipId):
            raise CryptoPerpetualValidationError(
                "crypto network relationship_id must be IdentityRelationshipId"
            )
        if not isinstance(self.role, CryptoNetworkBindingRoleCode):
            raise CryptoPerpetualValidationError(
                "crypto network role must be CryptoNetworkBindingRoleCode"
            )
        if not isinstance(self.evidence_ref, CryptoEvidenceRef):
            raise CryptoPerpetualValidationError(
                "crypto network evidence_ref must be CryptoEvidenceRef"
            )
        if self.network_identifier is not None:
            if not isinstance(self.network_identifier, ExternalIdentifier):
                raise CryptoPerpetualValidationError(
                    "crypto network identifier must be ExternalIdentifier or None"
                )
            if self.network_identifier.kind is not ExternalIdentifierKind.NETWORK_NATIVE:
                raise CryptoPerpetualValidationError(
                    "crypto network identifier must use NETWORK_NATIVE semantics"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "crypto-network-binding",
            self.terms_id.logical_values(),
            self.relationship_id.logical_values(),
            self.role.logical_values(),
            self.network_identifier.logical_values()
            if self.network_identifier is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CryptoPerpetualPricingTerms:
    """Required perpetual price-role vocabulary; contains no observed price values."""

    index_relationship_id: IdentityRelationshipId
    roles: tuple[CryptoPerpetualPriceRole, ...]
    evidence_ref: CryptoEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.index_relationship_id, IdentityRelationshipId):
            raise CryptoPerpetualValidationError(
                "crypto pricing index_relationship_id must be IdentityRelationshipId"
            )
        if type(self.roles) is not tuple:
            raise CryptoPerpetualValidationError(
                "crypto pricing roles must be an immutable tuple"
            )
        for role in self.roles:
            if not isinstance(role, CryptoPerpetualPriceRole):
                raise CryptoPerpetualValidationError(
                    "crypto pricing roles must contain CryptoPerpetualPriceRole"
                )
        if len(set(self.roles)) != len(self.roles):
            raise CryptoPerpetualValidationError(
                "crypto pricing roles must be unique"
            )
        required = {
            CryptoPerpetualPriceRole.MARK_PRICE,
            CryptoPerpetualPriceRole.INDEX_PRICE,
            CryptoPerpetualPriceRole.LAST_PRICE,
        }
        if set(self.roles) != required:
            raise CryptoPerpetualValidationError(
                "crypto perpetual pricing must retain mark, index, and last price roles"
            )
        if not isinstance(self.evidence_ref, CryptoEvidenceRef):
            raise CryptoPerpetualValidationError(
                "crypto pricing evidence_ref must be CryptoEvidenceRef"
            )
        object.__setattr__(
            self,
            "roles",
            tuple(sorted(self.roles, key=lambda role: role.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.index_relationship_id.logical_values(),
            tuple(role.value for role in self.roles),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CryptoPerpetualContractTerms:
    """Perpetual contract terms without dated-futures expiry or observation authority."""

    terms_id: CryptoTermsId
    instrument_identity_id: EconomicIdentityId
    reference_identity_id: EconomicIdentityId
    settlement_identity_id: EconomicIdentityId
    collateral_identity_id: EconomicIdentityId
    multiplier: DerivativeContractMultiplier
    funding: CryptoFundingTerms
    pricing: CryptoPerpetualPricingTerms
    evidence_ref: CryptoEvidenceRef
    tick_value: DerivativeTickValue | None = None
    network_binding: CryptoNetworkBindingTerms | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CryptoTermsId):
            raise CryptoPerpetualValidationError(
                "crypto perpetual terms_id must be CryptoTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="crypto perpetual instrument identity",
        )
        _validate_identity(
            self.reference_identity_id,
            field_name="crypto perpetual reference identity",
        )
        _validate_identity(
            self.settlement_identity_id,
            field_name="crypto perpetual settlement identity",
        )
        _validate_identity(
            self.collateral_identity_id,
            field_name="crypto perpetual collateral identity",
        )
        if not isinstance(self.multiplier, DerivativeContractMultiplier):
            raise CryptoPerpetualValidationError(
                "crypto perpetual multiplier must be DerivativeContractMultiplier"
            )
        if not isinstance(self.funding, CryptoFundingTerms):
            raise CryptoPerpetualValidationError(
                "crypto perpetual funding must be CryptoFundingTerms"
            )
        if not isinstance(self.pricing, CryptoPerpetualPricingTerms):
            raise CryptoPerpetualValidationError(
                "crypto perpetual pricing must be CryptoPerpetualPricingTerms"
            )
        if not isinstance(self.evidence_ref, CryptoEvidenceRef):
            raise CryptoPerpetualValidationError(
                "crypto perpetual evidence_ref must be CryptoEvidenceRef"
            )
        if self.tick_value is not None and not isinstance(
            self.tick_value,
            DerivativeTickValue,
        ):
            raise CryptoPerpetualValidationError(
                "crypto perpetual tick_value must be DerivativeTickValue or None"
            )
        if self.network_binding is not None and not isinstance(
            self.network_binding,
            CryptoNetworkBindingTerms,
        ):
            raise CryptoPerpetualValidationError(
                "crypto perpetual network_binding must be CryptoNetworkBindingTerms or None"
            )

        economic_roles = (
            self.reference_identity_id,
            self.settlement_identity_id,
            self.collateral_identity_id,
            self.funding.payment_identity_id,
        )
        if any(
            self.instrument_identity_id == identity
            for identity in economic_roles
        ):
            raise CryptoPerpetualValidationError(
                "crypto perpetual instrument identity must differ from reference, "
                "settlement, collateral, and funding-payment identities"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "crypto-perpetual",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.reference_identity_id.logical_values(),
            self.settlement_identity_id.logical_values(),
            self.collateral_identity_id.logical_values(),
            self.multiplier.logical_values(),
            self.tick_value.logical_values() if self.tick_value is not None else None,
            self.funding.logical_values(),
            self.pricing.logical_values(),
            self.network_binding.logical_values()
            if self.network_binding is not None
            else None,
            self.evidence_ref.logical_values(),
        )
