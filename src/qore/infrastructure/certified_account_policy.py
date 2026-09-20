from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from urllib.parse import urlsplit
from uuid import UUID

from qore.infrastructure.account_policy import (
    AccountPolicyRegistrySnapshot,
    AccountPolicyResolutionError,
    AccountPropPolicySnapshot,
    PropFirmReference,
    PropProgramReference,
)
from qore.infrastructure.client_accounts import (
    AccountPolicyReference,
    TradingAccountId,
    TradingAccountKind,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class CertifiedPolicyError(InfrastructureError):
    """Base error for certified account-policy source contracts."""

    __slots__ = ()


class CertifiedPolicyValidationError(CertifiedPolicyError):
    """A certified policy/source invariant is invalid."""

    __slots__ = ()


class CertifiedPolicyResolutionError(CertifiedPolicyError):
    """A certified policy cannot be resolved safely for Risk consumption."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CertifiedPolicyValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CertifiedPolicyValidationError(f"{field_name} must be timezone-aware")


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise CertifiedPolicyValidationError(f"{field_name} must be a UUID")


@dataclass(frozen=True, slots=True)
class PolicySourceEvidenceId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="policy source evidence id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class PolicySourceCertificateId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="policy source certificate id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class PolicyCertificationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="policy certification id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class PolicyVerifierReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="policy verifier reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class Sha256Digest:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise CertifiedPolicyValidationError(
                "sha256 digest must be 64 lowercase hexadecimal characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class PolicySourceLocator:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise CertifiedPolicyValidationError("policy source locator must be a string")
        parsed = urlsplit(self.value)
        if parsed.scheme != "https" or parsed.hostname is None:
            raise CertifiedPolicyValidationError(
                "policy source locator must be an absolute HTTPS URL"
            )
        if parsed.username is not None or parsed.password is not None:
            raise CertifiedPolicyValidationError(
                "policy source locator must not embed credentials"
            )
        if parsed.fragment:
            raise CertifiedPolicyValidationError(
                "policy source locator must not contain a fragment"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class PolicySourceAuthority(StrEnum):
    OFFICIAL_PROVIDER_TERMS = "official_provider_terms"
    OFFICIAL_PROVIDER_HELP_CENTER = "official_provider_help_center"
    OFFICIAL_PROVIDER_ACCOUNT_CONTRACT = "official_provider_account_contract"
    OFFICIAL_PROVIDER_DASHBOARD = "official_provider_dashboard"


@dataclass(frozen=True, slots=True)
class CertifiedPolicyVerifier:
    """Governed trust anchor allowed to certify policy facts and/or source evidence."""

    verifier_ref: PolicyVerifierReference
    authorized_at: datetime
    valid_until: datetime
    may_certify_policies: bool
    source_authorities: tuple[PolicySourceAuthority, ...]
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.verifier_ref, PolicyVerifierReference):
            raise CertifiedPolicyValidationError(
                "trusted verifier_ref must be PolicyVerifierReference"
            )
        _validate_timestamp(self.authorized_at, field_name="verifier authorized_at")
        _validate_timestamp(self.valid_until, field_name="verifier valid_until")
        if self.valid_until <= self.authorized_at:
            raise CertifiedPolicyValidationError(
                "verifier valid_until must be after authorized_at"
            )
        if type(self.may_certify_policies) is not bool:
            raise CertifiedPolicyValidationError(
                "verifier may_certify_policies must be bool"
            )
        if not isinstance(self.source_authorities, tuple):
            raise CertifiedPolicyValidationError(
                "verifier source_authorities must be a tuple"
            )
        if any(
            not isinstance(authority, PolicySourceAuthority)
            for authority in self.source_authorities
        ):
            raise CertifiedPolicyValidationError(
                "verifier source_authorities must contain PolicySourceAuthority values"
            )
        if len(set(self.source_authorities)) != len(self.source_authorities):
            raise CertifiedPolicyValidationError(
                "verifier source_authorities must be unique"
            )
        if not self.may_certify_policies and not self.source_authorities:
            raise CertifiedPolicyValidationError(
                "verifier must have at least one certification capability"
            )
        if self.revoked_at is not None:
            _validate_timestamp(self.revoked_at, field_name="verifier revoked_at")
            if self.revoked_at < self.authorized_at:
                raise CertifiedPolicyValidationError(
                    "verifier revoked_at cannot be before authorized_at"
                )

        object.__setattr__(
            self,
            "source_authorities",
            tuple(sorted(self.source_authorities, key=lambda authority: authority.value)),
        )

    def is_active_at(self, evaluated_at: datetime) -> bool:
        _validate_timestamp(evaluated_at, field_name="verifier evaluated_at")
        if evaluated_at < self.authorized_at or evaluated_at >= self.valid_until:
            return False
        return self.revoked_at is None or evaluated_at < self.revoked_at

    def permits_source(self, authority: PolicySourceAuthority) -> bool:
        return authority in self.source_authorities

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.verifier_ref.logical_values(),
            self.authorized_at.isoformat(),
            self.valid_until.isoformat(),
            self.may_certify_policies,
            tuple(authority.value for authority in self.source_authorities),
            self.revoked_at.isoformat() if self.revoked_at is not None else None,
        )


@dataclass(frozen=True, slots=True)
class PolicyVerifierRegistrySnapshot:
    """Immutable trust-root registry for account-policy certification."""

    verifiers: tuple[CertifiedPolicyVerifier, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.verifiers, tuple) or not self.verifiers:
            raise CertifiedPolicyValidationError(
                "verifier registry must be a non-empty tuple"
            )
        if any(
            not isinstance(verifier, CertifiedPolicyVerifier)
            for verifier in self.verifiers
        ):
            raise CertifiedPolicyValidationError(
                "verifier registry accepts only CertifiedPolicyVerifier values"
            )
        refs = [verifier.verifier_ref.value for verifier in self.verifiers]
        if len(set(refs)) != len(refs):
            raise CertifiedPolicyValidationError(
                "verifier registry references must be unique"
            )
        object.__setattr__(
            self,
            "verifiers",
            tuple(
                sorted(
                    self.verifiers,
                    key=lambda verifier: verifier.verifier_ref.value.hex,
                )
            ),
        )

    def resolve(
        self,
        *,
        verifier_ref: PolicyVerifierReference,
        evaluated_at: datetime,
    ) -> Result[CertifiedPolicyVerifier, CertifiedPolicyError]:
        if not isinstance(verifier_ref, PolicyVerifierReference):
            return Failure(
                CertifiedPolicyResolutionError(
                    "verifier_ref must be PolicyVerifierReference"
                )
            )
        try:
            _validate_timestamp(evaluated_at, field_name="verifier evaluated_at")
        except CertifiedPolicyValidationError as error:
            return Failure(CertifiedPolicyResolutionError(str(error)))

        for verifier in self.verifiers:
            if verifier.verifier_ref != verifier_ref:
                continue
            if not verifier.is_active_at(evaluated_at):
                return Failure(
                    CertifiedPolicyResolutionError(
                        "policy verifier is expired, revoked or not yet authorized"
                    )
                )
            return Success(verifier)

        return Failure(CertifiedPolicyResolutionError("policy verifier is not trusted"))


@dataclass(frozen=True, slots=True)
class CertifiedPolicySourceEvidence:
    """Certified evidence from one provider-authoritative source.

    This object contains provenance and content identity only. It does not fetch the source,
    interpret commercial text, or grant trading authority.
    """

    evidence_id: PolicySourceEvidenceId
    certificate_id: PolicySourceCertificateId
    verifier_ref: PolicyVerifierReference
    authority: PolicySourceAuthority
    locator: PolicySourceLocator
    content_sha256: Sha256Digest
    observed_at: datetime
    certified_at: datetime
    valid_until: datetime
    firm_ref: PropFirmReference | None
    program_ref: PropProgramReference | None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, PolicySourceEvidenceId):
            raise CertifiedPolicyValidationError(
                "source evidence_id must be PolicySourceEvidenceId"
            )
        if not isinstance(self.certificate_id, PolicySourceCertificateId):
            raise CertifiedPolicyValidationError(
                "source certificate_id must be PolicySourceCertificateId"
            )
        if not isinstance(self.verifier_ref, PolicyVerifierReference):
            raise CertifiedPolicyValidationError(
                "source verifier_ref must be PolicyVerifierReference"
            )
        if not isinstance(self.authority, PolicySourceAuthority):
            raise CertifiedPolicyValidationError(
                "source authority must be PolicySourceAuthority"
            )
        if not isinstance(self.locator, PolicySourceLocator):
            raise CertifiedPolicyValidationError(
                "source locator must be PolicySourceLocator"
            )
        if not isinstance(self.content_sha256, Sha256Digest):
            raise CertifiedPolicyValidationError(
                "source content_sha256 must be Sha256Digest"
            )
        _validate_timestamp(self.observed_at, field_name="source observed_at")
        _validate_timestamp(self.certified_at, field_name="source certified_at")
        _validate_timestamp(self.valid_until, field_name="source valid_until")
        if self.observed_at > self.certified_at:
            raise CertifiedPolicyValidationError(
                "source observed_at cannot be after certified_at"
            )
        if self.valid_until <= self.certified_at:
            raise CertifiedPolicyValidationError(
                "source valid_until must be after certified_at"
            )
        if (self.firm_ref is None) != (self.program_ref is None):
            raise CertifiedPolicyValidationError(
                "source firm_ref and program_ref must be both present or both absent"
            )
        if self.firm_ref is not None and not isinstance(self.firm_ref, PropFirmReference):
            raise CertifiedPolicyValidationError(
                "source firm_ref must be PropFirmReference or None"
            )
        if self.program_ref is not None and not isinstance(
            self.program_ref, PropProgramReference
        ):
            raise CertifiedPolicyValidationError(
                "source program_ref must be PropProgramReference or None"
            )
        if self.revoked_at is not None:
            _validate_timestamp(self.revoked_at, field_name="source revoked_at")
            if self.revoked_at < self.certified_at:
                raise CertifiedPolicyValidationError(
                    "source revoked_at cannot be before certified_at"
                )

        identities = {
            self.evidence_id.value,
            self.certificate_id.value,
            self.verifier_ref.value,
        }
        if len(identities) != 3:
            raise CertifiedPolicyValidationError(
                "source evidence, certificate and verifier identities must differ"
            )

    def is_valid_at(self, evaluated_at: datetime) -> bool:
        _validate_timestamp(evaluated_at, field_name="source evaluated_at")
        if evaluated_at < self.certified_at or evaluated_at >= self.valid_until:
            return False
        return self.revoked_at is None or evaluated_at < self.revoked_at

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evidence_id.logical_values(),
            self.certificate_id.logical_values(),
            self.verifier_ref.logical_values(),
            self.authority.value,
            self.locator.logical_values(),
            self.content_sha256.logical_values(),
            self.observed_at.isoformat(),
            self.certified_at.isoformat(),
            self.valid_until.isoformat(),
            self.firm_ref.logical_values() if self.firm_ref is not None else None,
            self.program_ref.logical_values() if self.program_ref is not None else None,
            self.revoked_at.isoformat() if self.revoked_at is not None else None,
        )


def derive_account_policy_sha256(policy: AccountPropPolicySnapshot) -> Sha256Digest:
    if not isinstance(policy, AccountPropPolicySnapshot):
        raise CertifiedPolicyValidationError(
            "policy digest input must be AccountPropPolicySnapshot"
        )
    canonical = json.dumps(
        policy.logical_values(),
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return Sha256Digest(hashlib.sha256(canonical).hexdigest())


@dataclass(frozen=True, slots=True)
class CertifiedAccountPolicy:
    """One account policy cryptographically bound to certified provider evidence."""

    certification_id: PolicyCertificationId
    verifier_ref: PolicyVerifierReference
    policy: AccountPropPolicySnapshot
    policy_sha256: Sha256Digest
    sources: tuple[CertifiedPolicySourceEvidence, ...]
    certified_at: datetime
    valid_until: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.certification_id, PolicyCertificationId):
            raise CertifiedPolicyValidationError(
                "policy certification_id must be PolicyCertificationId"
            )
        if not isinstance(self.verifier_ref, PolicyVerifierReference):
            raise CertifiedPolicyValidationError(
                "policy verifier_ref must be PolicyVerifierReference"
            )
        if not isinstance(self.policy, AccountPropPolicySnapshot):
            raise CertifiedPolicyValidationError(
                "certified policy must contain AccountPropPolicySnapshot"
            )
        if not isinstance(self.policy_sha256, Sha256Digest):
            raise CertifiedPolicyValidationError(
                "certified policy policy_sha256 must be Sha256Digest"
            )
        if self.policy_sha256 != derive_account_policy_sha256(self.policy):
            raise CertifiedPolicyValidationError(
                "certified policy digest does not match canonical policy content"
            )
        if not isinstance(self.sources, tuple) or not self.sources:
            raise CertifiedPolicyValidationError(
                "certified policy sources must be a non-empty tuple"
            )
        if any(not isinstance(source, CertifiedPolicySourceEvidence) for source in self.sources):
            raise CertifiedPolicyValidationError(
                "certified policy sources must contain only CertifiedPolicySourceEvidence"
            )
        _validate_timestamp(self.certified_at, field_name="policy certified_at")
        _validate_timestamp(self.valid_until, field_name="policy valid_until")
        if self.valid_until <= self.certified_at:
            raise CertifiedPolicyValidationError(
                "policy valid_until must be after certified_at"
            )

        source_ids: set[UUID] = set()
        source_certificate_ids: set[UUID] = set()
        for source in self.sources:
            if source.evidence_id.value in source_ids:
                raise CertifiedPolicyValidationError(
                    "certified policy source evidence identities must be unique"
                )
            if source.certificate_id.value in source_certificate_ids:
                raise CertifiedPolicyValidationError(
                    "certified policy source certificate identities must be unique"
                )
            source_ids.add(source.evidence_id.value)
            source_certificate_ids.add(source.certificate_id.value)

            if source.certified_at > self.certified_at:
                raise CertifiedPolicyValidationError(
                    "policy cannot be certified before its supporting source"
                )
            if self.valid_until > source.valid_until:
                raise CertifiedPolicyValidationError(
                    "policy certification cannot outlive supporting source evidence"
                )

            if self.policy.account_kind is TradingAccountKind.PROP_FIRM:
                if (
                    source.firm_ref != self.policy.firm_ref
                    or source.program_ref != self.policy.program_ref
                ):
                    raise CertifiedPolicyValidationError(
                        "certified source does not match policy firm/program"
                    )
            elif source.firm_ref is not None or source.program_ref is not None:
                raise CertifiedPolicyValidationError(
                    "non-prop policy sources must not carry prop firm/program references"
                )

        ordered = tuple(
            sorted(
                self.sources,
                key=lambda source: (
                    source.authority.value,
                    source.locator.value,
                    source.evidence_id.value.hex,
                ),
            )
        )
        object.__setattr__(self, "sources", ordered)

    def is_source_certification_valid_at(self, evaluated_at: datetime) -> bool:
        _validate_timestamp(evaluated_at, field_name="policy evaluated_at")
        if evaluated_at < self.certified_at or evaluated_at >= self.valid_until:
            return False
        return all(source.is_valid_at(evaluated_at) for source in self.sources)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.certification_id.logical_values(),
            self.verifier_ref.logical_values(),
            self.policy_sha256.logical_values(),
            self.certified_at.isoformat(),
            self.valid_until.isoformat(),
            self.policy.logical_values(),
            tuple(source.logical_values() for source in self.sources),
        )


@dataclass(frozen=True, slots=True)
class CertifiedAccountPolicyRegistrySnapshot:
    """Risk-facing registry that accepts only source-certified account policies."""

    policies: tuple[CertifiedAccountPolicy, ...]
    verifiers: PolicyVerifierRegistrySnapshot

    def __post_init__(self) -> None:
        if not isinstance(self.verifiers, PolicyVerifierRegistrySnapshot):
            raise CertifiedPolicyValidationError(
                "certified policy registry requires PolicyVerifierRegistrySnapshot"
            )
        if not isinstance(self.policies, tuple) or not self.policies:
            raise CertifiedPolicyValidationError(
                "certified policy registry policies must be a non-empty tuple"
            )
        if any(not isinstance(policy, CertifiedAccountPolicy) for policy in self.policies):
            raise CertifiedPolicyValidationError(
                "certified policy registry accepts only CertifiedAccountPolicy values"
            )

        certification_ids: set[UUID] = set()
        account_ids: set[UUID] = set()
        policy_refs: set[UUID] = set()
        snapshot_ids: set[UUID] = set()
        for certified in self.policies:
            if certified.certification_id.value in certification_ids:
                raise CertifiedPolicyValidationError(
                    "certified policy certification identities must be unique"
                )
            if certified.policy.account_id.value in account_ids:
                raise CertifiedPolicyValidationError(
                    "each account must have one current certified policy"
                )
            if certified.policy.policy_ref.value in policy_refs:
                raise CertifiedPolicyValidationError(
                    "certified policy references must be unique"
                )
            if certified.policy.snapshot_id.value in snapshot_ids:
                raise CertifiedPolicyValidationError(
                    "certified policy snapshot identities must be unique"
                )
            certification_ids.add(certified.certification_id.value)
            account_ids.add(certified.policy.account_id.value)
            policy_refs.add(certified.policy.policy_ref.value)
            snapshot_ids.add(certified.policy.snapshot_id.value)

        ordered = tuple(
            sorted(
                self.policies,
                key=lambda certified: (
                    certified.policy.account_id.value.hex,
                    certified.policy.policy_ref.value.hex,
                ),
            )
        )
        object.__setattr__(self, "policies", ordered)

    def resolve_for_risk(
        self,
        *,
        account_id: TradingAccountId,
        policy_ref: AccountPolicyReference,
        evaluated_at: datetime,
    ) -> Result[AccountPropPolicySnapshot, CertifiedPolicyError]:
        """Resolve a source-certified policy for Risk or fail closed."""

        if not isinstance(account_id, TradingAccountId):
            return Failure(
                CertifiedPolicyResolutionError("account_id must be TradingAccountId")
            )
        if not isinstance(policy_ref, AccountPolicyReference):
            return Failure(
                CertifiedPolicyResolutionError(
                    "policy_ref must be AccountPolicyReference"
                )
            )
        try:
            _validate_timestamp(evaluated_at, field_name="policy evaluated_at")
        except CertifiedPolicyValidationError as error:
            return Failure(CertifiedPolicyResolutionError(str(error)))

        for certified in self.policies:
            if certified.policy.policy_ref != policy_ref:
                continue
            if certified.policy.account_id != account_id:
                return Failure(
                    CertifiedPolicyResolutionError(
                        "certified policy reference belongs to a different account"
                    )
                )
            policy_verifier = self.verifiers.resolve(
                verifier_ref=certified.verifier_ref,
                evaluated_at=evaluated_at,
            )
            if isinstance(policy_verifier, Failure):
                return Failure(CertifiedPolicyResolutionError(str(policy_verifier.error)))
            if not policy_verifier.value.may_certify_policies:
                return Failure(
                    CertifiedPolicyResolutionError(
                        "trusted verifier is not authorized to certify policies"
                    )
                )

            try:
                source_valid = certified.is_source_certification_valid_at(evaluated_at)
            except CertifiedPolicyValidationError as error:
                return Failure(CertifiedPolicyResolutionError(str(error)))
            if not source_valid:
                return Failure(
                    CertifiedPolicyResolutionError(
                        "certified policy source evidence is stale, revoked or not yet valid"
                    )
                )

            for source in certified.sources:
                source_verifier = self.verifiers.resolve(
                    verifier_ref=source.verifier_ref,
                    evaluated_at=evaluated_at,
                )
                if isinstance(source_verifier, Failure):
                    return Failure(
                        CertifiedPolicyResolutionError(str(source_verifier.error))
                    )
                if not source_verifier.value.permits_source(source.authority):
                    return Failure(
                        CertifiedPolicyResolutionError(
                            "trusted verifier is not authorized for source authority"
                        )
                    )

            raw_registry = AccountPolicyRegistrySnapshot((certified.policy,))
            resolved = raw_registry.resolve_for_new_trading(
                account_id=account_id,
                policy_ref=policy_ref,
                evaluated_at=evaluated_at,
            )
            if isinstance(resolved, Failure):
                resolution_error = resolved.error
                if isinstance(resolution_error, AccountPolicyResolutionError):
                    return Failure(
                        CertifiedPolicyResolutionError(str(resolution_error))
                    )
                return Failure(
                    CertifiedPolicyResolutionError(
                        "underlying account policy could not be resolved"
                    )
                )
            if isinstance(resolved, Success):
                return Success(resolved.value)

        return Failure(CertifiedPolicyResolutionError("certified policy reference not found"))
