from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Protocol
from uuid import UUID

from qore.functional.decisions import DecisionId
from qore.infrastructure.client_accounts import (
    ClientTradingAccountBinding,
    ExecutionRuntimeReference,
    ProductEntitlementReference,
    TradingAccountId,
)
from qore.infrastructure.client_execution_agent import (
    CoreTradeDecision,
    DecisionSecurityAttestation,
    DecisionSecurityEvidenceReference,
    DecisionSecurityStatus,
)
from qore.infrastructure.secrets import SecretRef
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ClientDecisionSecurityError(InfrastructureError):
    """Base error for client Core Decision security contracts."""

    __slots__ = ()


class ClientDecisionSecurityValidationError(ClientDecisionSecurityError):
    """Violation of a decision-security contract invariant."""

    __slots__ = ()


class ClientDecisionSecurityVerificationError(ClientDecisionSecurityError):
    """A protected Core Decision cannot be verified safely."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise ClientDecisionSecurityValidationError(f"{field_name} must be a UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ClientDecisionSecurityValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ClientDecisionSecurityValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ClientDecisionEnvelopeId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="client decision envelope id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class DecisionKeyId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="decision key id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class DecisionKeyVersion:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise ClientDecisionSecurityValidationError(
                "decision key version must be a positive integer"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DecisionNonce:
    """Public anti-replay nonce carried by the protected decision envelope."""

    value: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.value, bytes) or not 16 <= len(self.value) <= 64:
            raise ClientDecisionSecurityValidationError(
                "decision nonce must be 16-64 bytes"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value.hex(),)


@dataclass(frozen=True, slots=True)
class DecisionProtocolVersion:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ClientDecisionSecurityValidationError(
                "decision protocol version must be a non-empty string"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class DecisionProtectionProfile(StrEnum):
    SIGNED_ENCRYPTED = "signed_encrypted"


@dataclass(frozen=True, slots=True, repr=False)
class ProtectedDecisionPayload:
    """Opaque protected bytes; never a plaintext reusable trading command."""

    ciphertext: bytes
    authentication_tag: bytes
    signature: bytes

    def __post_init__(self) -> None:
        for field_name, value in (
            ("ciphertext", self.ciphertext),
            ("authentication_tag", self.authentication_tag),
            ("signature", self.signature),
        ):
            if not isinstance(value, bytes) or not value:
                raise ClientDecisionSecurityValidationError(
                    f"protected decision {field_name} must be non-empty bytes"
                )

    @staticmethod
    def _digest(value: bytes) -> str:
        return sha256(value).hexdigest()

    def logical_values(self) -> tuple[object, ...]:
        return (
            len(self.ciphertext),
            self._digest(self.ciphertext),
            len(self.authentication_tag),
            self._digest(self.authentication_tag),
            len(self.signature),
            self._digest(self.signature),
        )

    def __repr__(self) -> str:
        return (
            "ProtectedDecisionPayload("
            f"ciphertext=<redacted:{len(self.ciphertext)} bytes>, "
            f"authentication_tag=<redacted:{len(self.authentication_tag)} bytes>, "
            f"signature=<redacted:{len(self.signature)} bytes>)"
        )


@dataclass(frozen=True, slots=True)
class ClientDecisionEnvelope:
    """Self-describing routing/security header plus opaque signed+encrypted payload."""

    envelope_id: ClientDecisionEnvelopeId
    protocol_version: DecisionProtocolVersion
    protection_profile: DecisionProtectionProfile
    decision_id: DecisionId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    entitlement_ref: ProductEntitlementReference
    issued_at: datetime
    expires_at: datetime
    nonce: DecisionNonce
    key_id: DecisionKeyId
    key_version: DecisionKeyVersion
    protected_payload: ProtectedDecisionPayload

    def __post_init__(self) -> None:
        if not isinstance(self.envelope_id, ClientDecisionEnvelopeId):
            raise ClientDecisionSecurityValidationError(
                "decision envelope_id must be ClientDecisionEnvelopeId"
            )
        if not isinstance(self.protocol_version, DecisionProtocolVersion):
            raise ClientDecisionSecurityValidationError(
                "decision protocol_version must be DecisionProtocolVersion"
            )
        if not isinstance(self.protection_profile, DecisionProtectionProfile):
            raise ClientDecisionSecurityValidationError(
                "decision protection_profile must be DecisionProtectionProfile"
            )
        if not isinstance(self.decision_id, DecisionId) or not isinstance(
            self.decision_id.value, UUID
        ):
            raise ClientDecisionSecurityValidationError(
                "decision envelope requires UUID-backed DecisionId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientDecisionSecurityValidationError(
                "decision account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise ClientDecisionSecurityValidationError(
                "decision runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.entitlement_ref, ProductEntitlementReference):
            raise ClientDecisionSecurityValidationError(
                "decision entitlement_ref must be ProductEntitlementReference"
            )
        _validate_timestamp(self.issued_at, field_name="decision issued_at")
        _validate_timestamp(self.expires_at, field_name="decision expires_at")
        if self.expires_at <= self.issued_at:
            raise ClientDecisionSecurityValidationError(
                "decision expires_at must be after issued_at"
            )
        if not isinstance(self.nonce, DecisionNonce):
            raise ClientDecisionSecurityValidationError(
                "decision nonce must be DecisionNonce"
            )
        if not isinstance(self.key_id, DecisionKeyId):
            raise ClientDecisionSecurityValidationError(
                "decision key_id must be DecisionKeyId"
            )
        if not isinstance(self.key_version, DecisionKeyVersion):
            raise ClientDecisionSecurityValidationError(
                "decision key_version must be DecisionKeyVersion"
            )
        if not isinstance(self.protected_payload, ProtectedDecisionPayload):
            raise ClientDecisionSecurityValidationError(
                "decision protected_payload must be ProtectedDecisionPayload"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.envelope_id.logical_values(),
            self.protocol_version.logical_values(),
            self.protection_profile.value,
            str(self.decision_id.value),
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.entitlement_ref.logical_values(),
            self.issued_at.isoformat(),
            self.expires_at.isoformat(),
            self.nonce.logical_values(),
            self.key_id.logical_values(),
            self.key_version.logical_values(),
            self.protected_payload.logical_values(),
        )


class DecisionKeyStatus(StrEnum):
    ACTIVE = "active"
    VERIFY_ONLY = "verify_only"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DecisionKeySnapshot:
    """Non-secret key lifecycle metadata and opaque key-material reference."""

    key_id: DecisionKeyId
    version: DecisionKeyVersion
    status: DecisionKeyStatus
    material_ref: SecretRef
    effective_at: datetime
    expires_at: datetime | None

    def __post_init__(self) -> None:
        if not isinstance(self.key_id, DecisionKeyId):
            raise ClientDecisionSecurityValidationError(
                "decision key snapshot key_id must be DecisionKeyId"
            )
        if not isinstance(self.version, DecisionKeyVersion):
            raise ClientDecisionSecurityValidationError(
                "decision key snapshot version must be DecisionKeyVersion"
            )
        if not isinstance(self.status, DecisionKeyStatus):
            raise ClientDecisionSecurityValidationError(
                "decision key snapshot status must be DecisionKeyStatus"
            )
        if not isinstance(self.material_ref, SecretRef):
            raise ClientDecisionSecurityValidationError(
                "decision key snapshot material_ref must be SecretRef"
            )
        _validate_timestamp(self.effective_at, field_name="decision key effective_at")
        if self.expires_at is not None:
            _validate_timestamp(self.expires_at, field_name="decision key expires_at")
            if self.expires_at <= self.effective_at:
                raise ClientDecisionSecurityValidationError(
                    "decision key expires_at must be after effective_at"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.key_id.logical_values(),
            self.version.logical_values(),
            self.status.value,
            self.material_ref.logical_values(),
            self.effective_at.isoformat(),
            self.expires_at.isoformat() if self.expires_at is not None else None,
        )


class DecisionKeyStatusSource(Protocol):
    def resolve(
        self,
        key_id: DecisionKeyId,
        version: DecisionKeyVersion,
        *,
        evaluated_at: datetime,
    ) -> Result[DecisionKeySnapshot, ClientDecisionSecurityError]: ...


@dataclass(frozen=True, slots=True)
class DecisionCryptographicVerification:
    """Successful output of a concrete signature/decryption adapter."""

    decision: CoreTradeDecision
    protected_payload_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.decision, CoreTradeDecision):
            raise ClientDecisionSecurityValidationError(
                "cryptographic verification decision must be CoreTradeDecision"
            )
        if (
            not isinstance(self.protected_payload_digest, str)
            or len(self.protected_payload_digest) != 64
            or any(character not in "0123456789abcdef" for character in self.protected_payload_digest)
        ):
            raise ClientDecisionSecurityValidationError(
                "protected_payload_digest must be a lowercase SHA-256 hex digest"
            )


class DecisionCryptoVerifier(Protocol):
    """Productive adapters verify authenticity/integrity and decrypt outside Core."""

    def verify_and_decrypt(
        self,
        envelope: ClientDecisionEnvelope,
        key: DecisionKeySnapshot,
    ) -> Result[DecisionCryptographicVerification, ClientDecisionSecurityError]: ...


@dataclass(frozen=True, slots=True)
class ClientDecisionReplayKey:
    """One strategic decision may execute at most once per trading account."""

    account_id: TradingAccountId
    decision_id: DecisionId

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientDecisionSecurityValidationError(
                "replay key account_id must be TradingAccountId"
            )
        if not isinstance(self.decision_id, DecisionId) or not isinstance(
            self.decision_id.value, UUID
        ):
            raise ClientDecisionSecurityValidationError(
                "replay key requires UUID-backed DecisionId"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.account_id.logical_values(), str(self.decision_id.value))


class ClientDecisionReplayClaimStatus(StrEnum):
    ACQUIRED = "acquired"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class ClientDecisionReplayClaim:
    key: ClientDecisionReplayKey
    fingerprint: str
    status: ClientDecisionReplayClaimStatus

    def __post_init__(self) -> None:
        if not isinstance(self.key, ClientDecisionReplayKey):
            raise ClientDecisionSecurityValidationError(
                "replay claim key must be ClientDecisionReplayKey"
            )
        if (
            not isinstance(self.fingerprint, str)
            or len(self.fingerprint) != 64
            or any(character not in "0123456789abcdef" for character in self.fingerprint)
        ):
            raise ClientDecisionSecurityValidationError(
                "replay claim fingerprint must be a lowercase SHA-256 hex digest"
            )
        if not isinstance(self.status, ClientDecisionReplayClaimStatus):
            raise ClientDecisionSecurityValidationError(
                "replay claim status must be ClientDecisionReplayClaimStatus"
            )


class ClientDecisionReplayClaimPort(Protocol):
    """Durable atomic replay-claim boundary; implementations must be fail-closed."""

    def claim(
        self,
        key: ClientDecisionReplayKey,
        fingerprint: str,
    ) -> Result[ClientDecisionReplayClaim, ClientDecisionSecurityError]: ...


@dataclass(frozen=True, slots=True)
class VerifiedClientDecision:
    """Only successful output consumable by the Client Execution Agent."""

    decision: CoreTradeDecision
    attestation: DecisionSecurityAttestation
    envelope_id: ClientDecisionEnvelopeId
    replay_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.decision, CoreTradeDecision):
            raise ClientDecisionSecurityValidationError(
                "verified client decision requires CoreTradeDecision"
            )
        if not isinstance(self.attestation, DecisionSecurityAttestation):
            raise ClientDecisionSecurityValidationError(
                "verified client decision requires DecisionSecurityAttestation"
            )
        if self.attestation.status is not DecisionSecurityStatus.VERIFIED:
            raise ClientDecisionSecurityValidationError(
                "verified client decision requires VERIFIED attestation"
            )
        if not isinstance(self.envelope_id, ClientDecisionEnvelopeId):
            raise ClientDecisionSecurityValidationError(
                "verified client decision envelope_id must be ClientDecisionEnvelopeId"
            )
        if (
            not isinstance(self.replay_fingerprint, str)
            or len(self.replay_fingerprint) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.replay_fingerprint
            )
        ):
            raise ClientDecisionSecurityValidationError(
                "verified client decision replay_fingerprint must be SHA-256 hex"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.decision.logical_values(),
            self.attestation.logical_values(),
            self.envelope_id.logical_values(),
            self.replay_fingerprint,
        )


_SUPPORTED_PROTOCOL = "qore.client-decision.v1"


def protected_payload_digest(payload: ProtectedDecisionPayload) -> str:
    """Hash the canonical protected-payload metadata without exposing protected bytes."""

    if not isinstance(payload, ProtectedDecisionPayload):
        raise ClientDecisionSecurityValidationError(
            "protected payload digest requires ProtectedDecisionPayload"
        )
    canonical = "\x1f".join(str(value) for value in payload.logical_values())
    return sha256(canonical.encode("utf-8")).hexdigest()


def client_decision_replay_fingerprint(envelope: ClientDecisionEnvelope) -> str:
    """Deterministic secret-free replay fingerprint over the protected envelope."""

    if not isinstance(envelope, ClientDecisionEnvelope):
        raise ClientDecisionSecurityValidationError(
            "replay fingerprint requires ClientDecisionEnvelope"
        )
    values = (
        str(envelope.envelope_id.value),
        envelope.protocol_version.value,
        envelope.protection_profile.value,
        str(envelope.decision_id.value),
        str(envelope.account_id.value),
        str(envelope.runtime_ref.value),
        str(envelope.entitlement_ref.value),
        envelope.issued_at.isoformat(),
        envelope.expires_at.isoformat(),
        envelope.nonce.value.hex(),
        str(envelope.key_id.value),
        str(envelope.key_version.value),
        protected_payload_digest(envelope.protected_payload),
    )
    return sha256("\x1f".join(values).encode("utf-8")).hexdigest()


def _verification_failure(message: str) -> Failure[ClientDecisionSecurityError]:
    return Failure(ClientDecisionSecurityVerificationError(message))


def verify_client_decision_envelope(
    envelope: ClientDecisionEnvelope,
    binding: ClientTradingAccountBinding,
    key_source: DecisionKeyStatusSource,
    crypto_verifier: DecisionCryptoVerifier,
    replay_port: ClientDecisionReplayClaimPort,
    *,
    evidence_ref: DecisionSecurityEvidenceReference,
    evaluated_at: datetime,
) -> Result[VerifiedClientDecision, ClientDecisionSecurityError]:
    """Verify, decrypt and atomically replay-claim one account-bound Core Decision.

    The function performs no broker IO, no retry, no key-material resolution and no fallback crypto.
    A failure never returns a VERIFIED attestation.
    """

    if not isinstance(envelope, ClientDecisionEnvelope):
        return Failure(
            ClientDecisionSecurityValidationError(
                "envelope must be ClientDecisionEnvelope"
            )
        )
    if not isinstance(binding, ClientTradingAccountBinding):
        return Failure(
            ClientDecisionSecurityValidationError(
                "binding must be ClientTradingAccountBinding"
            )
        )
    if not isinstance(evidence_ref, DecisionSecurityEvidenceReference):
        return Failure(
            ClientDecisionSecurityValidationError(
                "evidence_ref must be DecisionSecurityEvidenceReference"
            )
        )
    try:
        _validate_timestamp(evaluated_at, field_name="decision evaluated_at")
    except ClientDecisionSecurityError as error:
        return Failure(error)

    if envelope.protocol_version.value != _SUPPORTED_PROTOCOL:
        return _verification_failure("unsupported decision protocol version")
    if envelope.protection_profile is not DecisionProtectionProfile.SIGNED_ENCRYPTED:
        return _verification_failure("unsupported decision protection profile")

    if (
        envelope.account_id != binding.account_id
        or envelope.runtime_ref != binding.runtime_ref
        or envelope.entitlement_ref != binding.product_entitlement_ref
    ):
        return _verification_failure(
            "decision envelope account/runtime/entitlement binding mismatch"
        )

    if envelope.issued_at > evaluated_at:
        return _verification_failure("decision envelope issued_at is in the future")
    if evaluated_at >= envelope.expires_at:
        return _verification_failure("decision envelope is expired")

    key_result = key_source.resolve(
        envelope.key_id,
        envelope.key_version,
        evaluated_at=evaluated_at,
    )
    if isinstance(key_result, Failure):
        return Failure(key_result.error)
    key = key_result.value
    if key.key_id != envelope.key_id or key.version != envelope.key_version:
        return _verification_failure("decision key resolution binding mismatch")
    if key.status not in (DecisionKeyStatus.ACTIVE, DecisionKeyStatus.VERIFY_ONLY):
        return _verification_failure("decision key is not authorized for verification")
    if evaluated_at < key.effective_at:
        return _verification_failure("decision key is not yet effective")
    if key.expires_at is not None and evaluated_at >= key.expires_at:
        return _verification_failure("decision key is expired")

    crypto_result = crypto_verifier.verify_and_decrypt(envelope, key)
    if isinstance(crypto_result, Failure):
        return Failure(crypto_result.error)
    cryptographic = crypto_result.value
    expected_payload_digest = protected_payload_digest(envelope.protected_payload)
    if cryptographic.protected_payload_digest != expected_payload_digest:
        return _verification_failure("cryptographic protected-payload digest mismatch")

    decision = cryptographic.decision
    if decision.decision.decision_id != envelope.decision_id:
        return _verification_failure("decrypted Core Decision identity mismatch")
    if decision.expires_at != envelope.expires_at:
        return _verification_failure("decrypted Core Decision expiry mismatch")
    if decision.decision.timestamp > envelope.issued_at:
        return _verification_failure("Core Decision timestamp is after envelope issuance")

    replay_key = ClientDecisionReplayKey(
        account_id=envelope.account_id,
        decision_id=envelope.decision_id,
    )
    fingerprint = client_decision_replay_fingerprint(envelope)
    replay_result = replay_port.claim(replay_key, fingerprint)
    if isinstance(replay_result, Failure):
        return Failure(replay_result.error)
    replay_claim = replay_result.value
    if replay_claim.key != replay_key or replay_claim.fingerprint != fingerprint:
        return _verification_failure("replay claim binding mismatch")
    if replay_claim.status is ClientDecisionReplayClaimStatus.DUPLICATE:
        return _verification_failure("decision replay duplicate rejected")
    if replay_claim.status is ClientDecisionReplayClaimStatus.CONFLICT:
        return _verification_failure("decision replay conflict rejected")
    if replay_claim.status is not ClientDecisionReplayClaimStatus.ACQUIRED:
        return _verification_failure("decision replay state is unresolved")

    try:
        attestation = DecisionSecurityAttestation(
            decision_id=envelope.decision_id,
            account_id=envelope.account_id,
            runtime_ref=envelope.runtime_ref,
            status=DecisionSecurityStatus.VERIFIED,
            evidence_ref=evidence_ref,
            verified_at=evaluated_at,
        )
        return Success(
            VerifiedClientDecision(
                decision=decision,
                attestation=attestation,
                envelope_id=envelope.envelope_id,
                replay_fingerprint=fingerprint,
            )
        )
    except ClientDecisionSecurityError as error:
        return Failure(error)
