from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.crypto_perpetual_funding_semantics import (
    CryptoEvidenceRef,
    CryptoNetworkBindingTerms,
    CryptoTermsId,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    IdentityRelationship,
)
from qore.kernel.errors import InfrastructureError


class CryptoStakingTokenizationSemanticsError(InfrastructureError):
    """Base error for bounded crypto staking/tokenization semantics."""

    __slots__ = ()


class CryptoStakingTokenizationValidationError(
    CryptoStakingTokenizationSemanticsError
):
    """Violation of a staking/tokenization semantic invariant."""

    __slots__ = ()


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise CryptoStakingTokenizationValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise CryptoStakingTokenizationValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


@dataclass(frozen=True, slots=True)
class CryptoStakingModeCode:
    """Extensible provider-neutral staking arrangement mode."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="crypto staking mode code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CryptoStakingExitScheduleCode:
    """Static governed exit/unbonding schedule code; not a clock resolver."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="crypto staking exit schedule code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CryptoStakingPenaltyPolicyCode:
    """Static penalty/slashing policy qualification; not a risk calculation."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="crypto staking penalty policy code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CryptoYieldMechanismCode:
    """Extensible yield/accrual mechanism without observed yield values."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="crypto yield mechanism code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CryptoRepresentationRoleCode:
    """Qualification code bound to an exact UMI-02 relationship."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="crypto representation role code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class CryptoStakingExitMode(StrEnum):
    """Static exit convention only; current availability/timing remains external."""

    IMMEDIATE = "immediate"
    FIXED_DELAY = "fixed-delay"
    GOVERNED_SCHEDULE = "governed-schedule"
    NETWORK_GOVERNED = "network-governed"


class CryptoTokenizedSecurityForm(StrEnum):
    """Static issuance/representation form, never a legal-status determination."""

    NATIVE_ONCHAIN_ISSUANCE = "native-onchain-issuance"
    TOKENIZED_REPRESENTATION = "tokenized-representation"


@dataclass(frozen=True, slots=True)
class CryptoStakingExitTerms:
    """Static exit/unbonding convention without current queue/state authority."""

    mode: CryptoStakingExitMode
    fixed_delay_seconds: int | None = None
    schedule_code: CryptoStakingExitScheduleCode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CryptoStakingExitMode):
            raise CryptoStakingTokenizationValidationError(
                "crypto staking exit mode must be CryptoStakingExitMode"
            )
        if self.mode is CryptoStakingExitMode.FIXED_DELAY:
            if (
                type(self.fixed_delay_seconds) is not int
                or self.fixed_delay_seconds <= 0
                or self.schedule_code is not None
            ):
                raise CryptoStakingTokenizationValidationError(
                    "fixed-delay exit requires positive int seconds and no schedule"
                )
            return
        if self.mode is CryptoStakingExitMode.GOVERNED_SCHEDULE:
            if (
                not isinstance(
                    self.schedule_code,
                    CryptoStakingExitScheduleCode,
                )
                or self.fixed_delay_seconds is not None
            ):
                raise CryptoStakingTokenizationValidationError(
                    "governed-schedule exit requires typed schedule and no fixed delay"
                )
            return
        if self.fixed_delay_seconds is not None or self.schedule_code is not None:
            raise CryptoStakingTokenizationValidationError(
                "immediate/network-governed exit must not carry invented timing"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mode.value,
            self.fixed_delay_seconds,
            self.schedule_code.logical_values()
            if self.schedule_code is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class CryptoRepresentationBinding:
    """Exact UMI-02 relationship plus local semantic qualification."""

    relationship: IdentityRelationship
    role: CryptoRepresentationRoleCode
    evidence_ref: CryptoEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.relationship, IdentityRelationship):
            raise CryptoStakingTokenizationValidationError(
                "crypto representation relationship must be IdentityRelationship"
            )
        if not isinstance(self.role, CryptoRepresentationRoleCode):
            raise CryptoStakingTokenizationValidationError(
                "crypto representation role must be CryptoRepresentationRoleCode"
            )
        if self.relationship.relationship.value != self.role.value:
            raise CryptoStakingTokenizationValidationError(
                "crypto representation role must match exact UMI-02 relationship code"
            )
        if not isinstance(self.evidence_ref, CryptoEvidenceRef):
            raise CryptoStakingTokenizationValidationError(
                "crypto representation evidence_ref must be CryptoEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.relationship.logical_values(),
            self.role.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CryptoStakingTerms:
    """Provider-neutral static staking arrangement semantics."""

    terms_id: CryptoTermsId
    staked_asset_identity_id: EconomicIdentityId
    reward_asset_identity_id: EconomicIdentityId
    mode: CryptoStakingModeCode
    exit_terms: CryptoStakingExitTerms
    evidence_ref: CryptoEvidenceRef
    penalty_policy_code: CryptoStakingPenaltyPolicyCode | None = None
    receipt_binding: CryptoRepresentationBinding | None = None
    network_binding: CryptoNetworkBindingTerms | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CryptoTermsId):
            raise CryptoStakingTokenizationValidationError(
                "crypto staking terms_id must be CryptoTermsId"
            )
        _validate_identity(
            self.staked_asset_identity_id,
            field_name="crypto staking staked asset identity",
        )
        _validate_identity(
            self.reward_asset_identity_id,
            field_name="crypto staking reward asset identity",
        )
        if not isinstance(self.mode, CryptoStakingModeCode):
            raise CryptoStakingTokenizationValidationError(
                "crypto staking mode must be CryptoStakingModeCode"
            )
        if not isinstance(self.exit_terms, CryptoStakingExitTerms):
            raise CryptoStakingTokenizationValidationError(
                "crypto staking exit_terms must be CryptoStakingExitTerms"
            )
        if not isinstance(self.evidence_ref, CryptoEvidenceRef):
            raise CryptoStakingTokenizationValidationError(
                "crypto staking evidence_ref must be CryptoEvidenceRef"
            )
        if self.penalty_policy_code is not None and not isinstance(
            self.penalty_policy_code,
            CryptoStakingPenaltyPolicyCode,
        ):
            raise CryptoStakingTokenizationValidationError(
                "crypto staking penalty_policy_code must be typed or None"
            )
        if self.receipt_binding is not None:
            if not isinstance(self.receipt_binding, CryptoRepresentationBinding):
                raise CryptoStakingTokenizationValidationError(
                    "crypto staking receipt_binding must be typed or None"
                )
            relationship = self.receipt_binding.relationship
            if relationship.target_identity_id != self.staked_asset_identity_id:
                raise CryptoStakingTokenizationValidationError(
                    "staking receipt relationship target must be staked asset"
                )
        if self.network_binding is not None and not isinstance(
            self.network_binding,
            CryptoNetworkBindingTerms,
        ):
            raise CryptoStakingTokenizationValidationError(
                "crypto staking network_binding must be typed or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "crypto-staking",
            self.terms_id.logical_values(),
            self.staked_asset_identity_id.logical_values(),
            self.reward_asset_identity_id.logical_values(),
            self.mode.logical_values(),
            self.exit_terms.logical_values(),
            self.penalty_policy_code.logical_values()
            if self.penalty_policy_code is not None
            else None,
            self.receipt_binding.logical_values()
            if self.receipt_binding is not None
            else None,
            self.network_binding.logical_values()
            if self.network_binding is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CryptoYieldBearingTokenTerms:
    """Static yield-bearing token/share qualification without observed yield."""

    terms_id: CryptoTermsId
    token_identity_id: EconomicIdentityId
    underlying_identity_id: EconomicIdentityId
    representation_binding: CryptoRepresentationBinding
    yield_mechanism: CryptoYieldMechanismCode
    evidence_ref: CryptoEvidenceRef
    network_binding: CryptoNetworkBindingTerms | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CryptoTermsId):
            raise CryptoStakingTokenizationValidationError(
                "crypto yield terms_id must be CryptoTermsId"
            )
        _validate_identity(
            self.token_identity_id,
            field_name="crypto yield token identity",
        )
        _validate_identity(
            self.underlying_identity_id,
            field_name="crypto yield underlying identity",
        )
        if self.token_identity_id == self.underlying_identity_id:
            raise CryptoStakingTokenizationValidationError(
                "yield-bearing token identity must differ from underlying identity"
            )
        if not isinstance(
            self.representation_binding,
            CryptoRepresentationBinding,
        ):
            raise CryptoStakingTokenizationValidationError(
                "crypto yield representation_binding must be typed"
            )
        relationship = self.representation_binding.relationship
        if relationship.source_identity_id != self.token_identity_id:
            raise CryptoStakingTokenizationValidationError(
                "yield representation source must be token identity"
            )
        if relationship.target_identity_id != self.underlying_identity_id:
            raise CryptoStakingTokenizationValidationError(
                "yield representation target must be underlying identity"
            )
        if not isinstance(self.yield_mechanism, CryptoYieldMechanismCode):
            raise CryptoStakingTokenizationValidationError(
                "crypto yield mechanism must be CryptoYieldMechanismCode"
            )
        if not isinstance(self.evidence_ref, CryptoEvidenceRef):
            raise CryptoStakingTokenizationValidationError(
                "crypto yield evidence_ref must be CryptoEvidenceRef"
            )
        if self.network_binding is not None and not isinstance(
            self.network_binding,
            CryptoNetworkBindingTerms,
        ):
            raise CryptoStakingTokenizationValidationError(
                "crypto yield network_binding must be typed or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "crypto-yield-bearing-token",
            self.terms_id.logical_values(),
            self.token_identity_id.logical_values(),
            self.underlying_identity_id.logical_values(),
            self.representation_binding.logical_values(),
            self.yield_mechanism.logical_values(),
            self.network_binding.logical_values()
            if self.network_binding is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CryptoTokenizedSecurityQualificationTerms:
    """Tokenized-security form/binding without legal or compliance authority."""

    terms_id: CryptoTermsId
    token_security_identity_id: EconomicIdentityId
    form: CryptoTokenizedSecurityForm
    evidence_ref: CryptoEvidenceRef
    underlying_security_identity_id: EconomicIdentityId | None = None
    representation_binding: CryptoRepresentationBinding | None = None
    network_binding: CryptoNetworkBindingTerms | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CryptoTermsId):
            raise CryptoStakingTokenizationValidationError(
                "crypto tokenized-security terms_id must be CryptoTermsId"
            )
        _validate_identity(
            self.token_security_identity_id,
            field_name="crypto tokenized-security identity",
        )
        if not isinstance(self.form, CryptoTokenizedSecurityForm):
            raise CryptoStakingTokenizationValidationError(
                "crypto tokenized-security form must be CryptoTokenizedSecurityForm"
            )
        if not isinstance(self.evidence_ref, CryptoEvidenceRef):
            raise CryptoStakingTokenizationValidationError(
                "crypto tokenized-security evidence_ref must be CryptoEvidenceRef"
            )
        if self.form is CryptoTokenizedSecurityForm.NATIVE_ONCHAIN_ISSUANCE:
            if (
                self.underlying_security_identity_id is not None
                or self.representation_binding is not None
            ):
                raise CryptoStakingTokenizationValidationError(
                    "native on-chain issuance must not invent represented underlying"
                )
        else:
            underlying = self.underlying_security_identity_id
            if not isinstance(underlying, EconomicIdentityId):
                raise CryptoStakingTokenizationValidationError(
                    "represented security identity must be EconomicIdentityId"
                )
            if underlying == self.token_security_identity_id:
                raise CryptoStakingTokenizationValidationError(
                    "tokenized representation must differ from represented security"
                )
            if not isinstance(
                self.representation_binding,
                CryptoRepresentationBinding,
            ):
                raise CryptoStakingTokenizationValidationError(
                    "tokenized representation requires exact representation binding"
                )
            relationship = self.representation_binding.relationship
            if relationship.source_identity_id != self.token_security_identity_id:
                raise CryptoStakingTokenizationValidationError(
                    "tokenized-security representation source must be token identity"
                )
            if relationship.target_identity_id != underlying:
                raise CryptoStakingTokenizationValidationError(
                    "tokenized-security representation target must be underlying security"
                )
        if self.network_binding is not None and not isinstance(
            self.network_binding,
            CryptoNetworkBindingTerms,
        ):
            raise CryptoStakingTokenizationValidationError(
                "crypto tokenized-security network_binding must be typed or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "crypto-tokenized-security-qualification",
            self.terms_id.logical_values(),
            self.token_security_identity_id.logical_values(),
            self.form.value,
            self.underlying_security_identity_id.logical_values()
            if self.underlying_security_identity_id is not None
            else None,
            self.representation_binding.logical_values()
            if self.representation_binding is not None
            else None,
            self.network_binding.logical_values()
            if self.network_binding is not None
            else None,
            self.evidence_ref.logical_values(),
        )
