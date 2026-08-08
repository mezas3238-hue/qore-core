from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from re import fullmatch
from uuid import UUID

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveProjectionMetadata,
    ExecutiveReadModelValidationError,
)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveReadModelValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveReadModelValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise ExecutiveReadModelValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    return value


def _validated_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(not isinstance(item, str) for item in values):
        raise ExecutiveReadModelValidationError(
            f"{field_name} must be an immutable tuple of canonical strings"
        )
    normalized = tuple(_validate_code(item, field_name=field_name) for item in values)
    if len(set(normalized)) != len(normalized):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validated_evidence_refs(
    values: tuple[ExecutiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[ExecutiveEvidenceRef, ...]:
    if not isinstance(values, tuple) or not values or any(
        not isinstance(item, ExecutiveEvidenceRef) for item in values
    ):
        raise ExecutiveReadModelValidationError(
            f"{field_name} must be a non-empty immutable tuple of ExecutiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceGrantRef:
    """Opaque identity of one executive authority grant projection."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "governance grant ref requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernancePrincipalRef:
    """Stable executive principal identity projected independently of control internals."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="governance principal ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceAuthorityVersionRef:
    """Stable authority-policy version reference in the Governance read surface."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="governance authority version")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceActionCode:
    """Projected governance action capability without exposing internal enums directly."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="governance action code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceReadScopeCode:
    """Projected executive read capability without exposing internal enums directly."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="governance read scope code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceAuthoritySummary:
    """Evidence-backed projection of one explicit executive authority grant."""

    grant_ref: ExecutiveGovernanceGrantRef
    principal_ref: ExecutiveGovernancePrincipalRef
    authority_version: ExecutiveGovernanceAuthorityVersionRef
    issued_at: datetime
    expires_at: datetime
    allowed_actions: tuple[ExecutiveGovernanceActionCode, ...]
    allowed_read_scopes: tuple[ExecutiveGovernanceReadScopeCode, ...]
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.grant_ref, ExecutiveGovernanceGrantRef):
            raise ExecutiveReadModelValidationError(
                "governance authority summary requires ExecutiveGovernanceGrantRef"
            )
        if not isinstance(self.principal_ref, ExecutiveGovernancePrincipalRef):
            raise ExecutiveReadModelValidationError(
                "governance authority summary requires ExecutiveGovernancePrincipalRef"
            )
        if not isinstance(
            self.authority_version,
            ExecutiveGovernanceAuthorityVersionRef,
        ):
            raise ExecutiveReadModelValidationError(
                "governance authority summary requires ExecutiveGovernanceAuthorityVersionRef"
            )
        _validate_timestamp(self.issued_at, field_name="governance authority issued_at")
        _validate_timestamp(self.expires_at, field_name="governance authority expires_at")
        if self.expires_at <= self.issued_at:
            raise ExecutiveReadModelValidationError(
                "governance authority expiry must be after issue time"
            )
        if not isinstance(self.allowed_actions, tuple) or any(
            not isinstance(item, ExecutiveGovernanceActionCode)
            for item in self.allowed_actions
        ):
            raise ExecutiveReadModelValidationError(
                "governance allowed actions must be an immutable tuple of action codes"
            )
        if not isinstance(self.allowed_read_scopes, tuple) or any(
            not isinstance(item, ExecutiveGovernanceReadScopeCode)
            for item in self.allowed_read_scopes
        ):
            raise ExecutiveReadModelValidationError(
                "governance read scopes must be an immutable tuple of read scope codes"
            )
        if not self.allowed_actions and not self.allowed_read_scopes:
            raise ExecutiveReadModelValidationError(
                "governance authority summary must expose at least one capability"
            )
        if len(set(self.allowed_actions)) != len(self.allowed_actions):
            raise ExecutiveReadModelValidationError(
                "governance allowed actions must not contain duplicates"
            )
        if len(set(self.allowed_read_scopes)) != len(self.allowed_read_scopes):
            raise ExecutiveReadModelValidationError(
                "governance read scopes must not contain duplicates"
            )
        object.__setattr__(
            self,
            "allowed_actions",
            tuple(sorted(self.allowed_actions, key=lambda item: item.value)),
        )
        object.__setattr__(
            self,
            "allowed_read_scopes",
            tuple(sorted(self.allowed_read_scopes, key=lambda item: item.value)),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="governance authority reason codes"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="governance authority evidence refs",
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.grant_ref.logical_values(),
            self.principal_ref.logical_values(),
            self.authority_version.logical_values(),
            self.issued_at.isoformat(),
            self.expires_at.isoformat(),
            tuple(item.logical_values() for item in self.allowed_actions),
            tuple(item.logical_values() for item in self.allowed_read_scopes),
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceReceiptRef:
    """Opaque identity of one projected executive control receipt."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "governance receipt ref requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceIntentRef:
    """Opaque identity of the governance intent bound to a control receipt."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "governance intent ref requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceCorrelationRef:
    """Explicit correlation identity retained for executive audit reconstruction."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "governance correlation ref requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceReceiptStatusCode:
    """Stable projected receipt status code, independent of internal receipt enum layout."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="governance receipt status code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceControlReceiptSummary:
    """Audit-backed result of one executive governance command."""

    receipt_ref: ExecutiveGovernanceReceiptRef
    intent_ref: ExecutiveGovernanceIntentRef
    principal_ref: ExecutiveGovernancePrincipalRef
    action: ExecutiveGovernanceActionCode
    authority_version: ExecutiveGovernanceAuthorityVersionRef
    correlation_ref: ExecutiveGovernanceCorrelationRef
    received_at: datetime
    completed_at: datetime
    status: ExecutiveGovernanceReceiptStatusCode
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.receipt_ref, ExecutiveGovernanceReceiptRef):
            raise ExecutiveReadModelValidationError(
                "governance receipt summary requires ExecutiveGovernanceReceiptRef"
            )
        if not isinstance(self.intent_ref, ExecutiveGovernanceIntentRef):
            raise ExecutiveReadModelValidationError(
                "governance receipt summary requires ExecutiveGovernanceIntentRef"
            )
        if self.receipt_ref.value == self.intent_ref.value:
            raise ExecutiveReadModelValidationError(
                "governance receipt and intent identities must differ"
            )
        if not isinstance(self.principal_ref, ExecutiveGovernancePrincipalRef):
            raise ExecutiveReadModelValidationError(
                "governance receipt summary requires ExecutiveGovernancePrincipalRef"
            )
        if not isinstance(self.action, ExecutiveGovernanceActionCode):
            raise ExecutiveReadModelValidationError(
                "governance receipt summary requires ExecutiveGovernanceActionCode"
            )
        if not isinstance(
            self.authority_version,
            ExecutiveGovernanceAuthorityVersionRef,
        ):
            raise ExecutiveReadModelValidationError(
                "governance receipt summary requires ExecutiveGovernanceAuthorityVersionRef"
            )
        if not isinstance(self.correlation_ref, ExecutiveGovernanceCorrelationRef):
            raise ExecutiveReadModelValidationError(
                "governance receipt summary requires ExecutiveGovernanceCorrelationRef"
            )
        _validate_timestamp(self.received_at, field_name="governance receipt received_at")
        _validate_timestamp(self.completed_at, field_name="governance receipt completed_at")
        if self.completed_at < self.received_at:
            raise ExecutiveReadModelValidationError(
                "governance receipt completion must not predate receipt"
            )
        if not isinstance(self.status, ExecutiveGovernanceReceiptStatusCode):
            raise ExecutiveReadModelValidationError(
                "governance receipt summary requires ExecutiveGovernanceReceiptStatusCode"
            )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="governance receipt reason codes"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="governance receipt evidence refs",
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.receipt_ref.logical_values(),
            self.intent_ref.logical_values(),
            self.principal_ref.logical_values(),
            self.action.logical_values(),
            self.authority_version.logical_values(),
            self.correlation_ref.logical_values(),
            self.received_at.isoformat(),
            self.completed_at.isoformat(),
            self.status.logical_values(),
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceReadModel:
    """Stable GOVERNANCE projection from canonical authority and receipt evidence."""

    metadata: ExecutiveProjectionMetadata
    attention: ExecutiveAttentionLevel
    authorities: tuple[ExecutiveGovernanceAuthoritySummary, ...]
    control_receipts: tuple[ExecutiveGovernanceControlReceiptSummary, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "governance read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.GOVERNANCE:
            raise ExecutiveReadModelValidationError(
                "governance projection requires GOVERNANCE scope"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "governance projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.authorities, tuple) or any(
            not isinstance(item, ExecutiveGovernanceAuthoritySummary)
            for item in self.authorities
        ):
            raise ExecutiveReadModelValidationError(
                "governance authorities must be an immutable tuple of summaries"
            )
        grant_ids = tuple(item.grant_ref.value for item in self.authorities)
        if len(set(grant_ids)) != len(grant_ids):
            raise ExecutiveReadModelValidationError(
                "governance projection must not contain duplicate grant refs"
            )
        object.__setattr__(
            self,
            "authorities",
            tuple(sorted(self.authorities, key=lambda item: str(item.grant_ref.value))),
        )
        if not isinstance(self.control_receipts, tuple) or any(
            not isinstance(item, ExecutiveGovernanceControlReceiptSummary)
            for item in self.control_receipts
        ):
            raise ExecutiveReadModelValidationError(
                "governance receipts must be an immutable tuple of summaries"
            )
        receipt_ids = tuple(item.receipt_ref.value for item in self.control_receipts)
        if len(set(receipt_ids)) != len(receipt_ids):
            raise ExecutiveReadModelValidationError(
                "governance projection must not contain duplicate receipt refs"
            )
        object.__setattr__(
            self,
            "control_receipts",
            tuple(
                sorted(
                    self.control_receipts,
                    key=lambda item: (item.completed_at, str(item.receipt_ref.value)),
                )
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.attention.value,
            tuple(item.logical_values() for item in self.authorities),
            tuple(item.logical_values() for item in self.control_receipts),
        )
