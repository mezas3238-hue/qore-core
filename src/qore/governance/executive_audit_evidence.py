from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from typing import Protocol
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_authentication import AuthenticatedExecutivePrincipal
from qore.governance.executive_authority_state import (
    ExecutiveAuthorityStateRequest,
    ExecutiveAuthorityStateSnapshot,
)
from qore.governance.executive_control import (
    AuthorizedExecutiveControlIntent,
    AuthorizedExecutiveReadRequest,
    ExecutiveAuthorityVersion,
    ExecutivePrincipalId,
)
from qore.governance.executive_governance_mutation import (
    ExecutiveGovernanceMutationReceipt,
    ExecutiveGovernanceMutationRequest,
    ExecutiveGovernanceMutationStatus,
)
from qore.governance.executive_ports import (
    ExecutiveControlReceipt,
    ExecutiveControlReceiptStatus,
    ExecutiveEvidenceRef,
    ExecutiveReadDelivery,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


class ExecutiveAuditEvidenceError(DomainError):
    """Base error for durable executive audit-evidence contracts."""

    __slots__ = ()


class ExecutiveAuditEvidenceValidationError(ExecutiveAuditEvidenceError):
    """An executive audit-evidence value violates a deterministic invariant."""

    __slots__ = ()


class ExecutiveAuditEvidenceUnavailableError(ExecutiveAuditEvidenceError):
    """A concrete durable audit boundary is unavailable."""

    __slots__ = ()


class ExecutiveAuditEvidenceStage(StrEnum):
    AUTHENTICATION = "authentication"
    AUTHORITY = "authority"
    AUTHORIZATION = "authorization"
    COMMAND_DISPATCH = "command-dispatch"
    QUERY_DISPATCH = "query-dispatch"
    GOVERNANCE_MUTATION = "governance-mutation"


class ExecutiveAuditEvidenceOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    NO_ACTION = "no-action"
    BLOCKED = "blocked"
    FAILED = "failed"


class ExecutiveAuditSourceKind(StrEnum):
    AUTHENTICATION_ASSERTION = "authentication-assertion"
    AUTHORITY_STATE_REQUEST = "authority-state-request"
    AUTHORITY_STATE_EVIDENCE = "authority-state-evidence"
    AUTHORIZED_CONTROL_INTENT = "authorized-control-intent"
    AUTHORIZED_READ_REQUEST = "authorized-read-request"
    CONTROL_RECEIPT = "control-receipt"
    READ_DELIVERY = "read-delivery"
    READ_RECEIPT = "read-receipt"
    GOVERNANCE_MUTATION = "governance-mutation"
    GOVERNANCE_MUTATION_RECEIPT = "governance-mutation-receipt"
    GOVERNANCE_EXPECTED_SNAPSHOT = "governance-expected-snapshot"
    GOVERNANCE_REQUESTED_SNAPSHOT = "governance-requested-snapshot"
    GOVERNANCE_OBSERVED_SNAPSHOT = "governance-observed-snapshot"


def _contains_sensitive_material(value: str) -> bool:
    normalized = value.lower()
    return any(part in normalized for part in _SENSITIVE_PARTS)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveAuditEvidenceValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveAuditEvidenceValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_reason_code(value: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise ExecutiveAuditEvidenceValidationError(
            "executive audit reason code must use canonical lowercase syntax"
        )
    if _contains_sensitive_material(value):
        raise ExecutiveAuditEvidenceValidationError(
            "executive audit reason code must not contain sensitive material"
        )
    return value


def _validate_source_value(value: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z0-9][a-z0-9._:/-]*", value) is None:
        raise ExecutiveAuditEvidenceValidationError(
            "executive audit source reference must use canonical lowercase syntax"
        )
    if _contains_sensitive_material(value):
        raise ExecutiveAuditEvidenceValidationError(
            "executive audit source reference must not contain sensitive material"
        )
    return value


def _validated_evidence_refs(
    values: tuple[ExecutiveEvidenceRef, ...],
) -> tuple[ExecutiveEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, ExecutiveEvidenceRef) for item in values
    ):
        raise ExecutiveAuditEvidenceValidationError(
            "executive audit evidence refs must be a tuple of ExecutiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise ExecutiveAuditEvidenceValidationError(
            "executive audit evidence refs must not contain duplicates"
        )
    for item in values:
        if _contains_sensitive_material(item.value):
            raise ExecutiveAuditEvidenceValidationError(
                "executive audit evidence refs must not contain sensitive material"
            )
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class ExecutiveAuditEvidenceRecordId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveAuditEvidenceValidationError(
                "executive audit record id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveAuditSourceRef:
    kind: ExecutiveAuditSourceKind
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ExecutiveAuditSourceKind):
            raise ExecutiveAuditEvidenceValidationError(
                "executive audit source ref requires ExecutiveAuditSourceKind"
            )
        object.__setattr__(self, "value", _validate_source_value(self.value))

    def logical_values(self) -> tuple[str, str]:
        return (self.kind.value, self.value)


@dataclass(frozen=True, slots=True)
class ExecutiveAuditEvidenceRecord:
    """Immutable secret-free evidence index for one executive control-plane stage."""

    record_id: ExecutiveAuditEvidenceRecordId
    stage: ExecutiveAuditEvidenceStage
    outcome: ExecutiveAuditEvidenceOutcome
    principal_id: ExecutivePrincipalId
    correlation_id: CorrelationId
    occurred_at: datetime
    reason_code: str
    source_refs: tuple[ExecutiveAuditSourceRef, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = ()
    authority_version: ExecutiveAuthorityVersion | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, ExecutiveAuditEvidenceRecordId):
            raise ExecutiveAuditEvidenceValidationError(
                "executive audit record requires ExecutiveAuditEvidenceRecordId"
            )
        if not isinstance(self.stage, ExecutiveAuditEvidenceStage):
            raise ExecutiveAuditEvidenceValidationError(
                "executive audit record requires ExecutiveAuditEvidenceStage"
            )
        if not isinstance(self.outcome, ExecutiveAuditEvidenceOutcome):
            raise ExecutiveAuditEvidenceValidationError(
                "executive audit record requires ExecutiveAuditEvidenceOutcome"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveAuditEvidenceValidationError(
                "executive audit record requires ExecutivePrincipalId"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveAuditEvidenceValidationError(
                "executive audit record requires CorrelationId"
            )
        _validate_timestamp(self.occurred_at, field_name="occurred_at")
        object.__setattr__(self, "reason_code", _validate_reason_code(self.reason_code))
        if not isinstance(self.source_refs, tuple) or any(
            not isinstance(item, ExecutiveAuditSourceRef) for item in self.source_refs
        ):
            raise ExecutiveAuditEvidenceValidationError(
                "executive audit source refs must be a tuple of ExecutiveAuditSourceRef"
            )
        if not self.source_refs:
            raise ExecutiveAuditEvidenceValidationError(
                "executive audit source refs must not be empty"
            )
        if len(set(self.source_refs)) != len(self.source_refs):
            raise ExecutiveAuditEvidenceValidationError(
                "executive audit source refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "source_refs",
            tuple(sorted(self.source_refs, key=lambda item: item.logical_values())),
        )
        object.__setattr__(self, "evidence_refs", _validated_evidence_refs(self.evidence_refs))
        if self.authority_version is not None and not isinstance(
            self.authority_version,
            ExecutiveAuthorityVersion,
        ):
            raise ExecutiveAuditEvidenceValidationError(
                "authority version must be ExecutiveAuthorityVersion or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.stage.value,
            self.outcome.value,
            self.principal_id.logical_values(),
            str(self.correlation_id.value),
            (
                self.authority_version.logical_values()
                if self.authority_version is not None
                else None
            ),
            self.occurred_at.isoformat(),
            self.reason_code,
            tuple(item.logical_values() for item in self.source_refs),
            tuple(item.logical_values() for item in self.evidence_refs),
        )


class ExecutiveAuditEvidencePort(Protocol):
    """Persistence-neutral append boundary for executive audit evidence."""

    def append(
        self,
        record: ExecutiveAuditEvidenceRecord,
    ) -> Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError]: ...


def _source_ref(kind: ExecutiveAuditSourceKind, value: object) -> ExecutiveAuditSourceRef:
    if isinstance(value, UUID):
        rendered = str(value)
    elif isinstance(value, str):
        rendered = value
    else:
        raise ExecutiveAuditEvidenceValidationError(
            "executive audit source identity must be UUID or canonical string"
        )
    return ExecutiveAuditSourceRef(kind=kind, value=rendered)


def _merge_evidence_refs(
    *groups: tuple[ExecutiveEvidenceRef, ...],
) -> tuple[ExecutiveEvidenceRef, ...]:
    merged = tuple(item for group in groups for item in group)
    if len(set(merged)) != len(merged):
        merged = tuple(dict.fromkeys(merged))
    return _validated_evidence_refs(merged)


def _build_record(
    *,
    record_id: ExecutiveAuditEvidenceRecordId,
    stage: ExecutiveAuditEvidenceStage,
    outcome: ExecutiveAuditEvidenceOutcome,
    principal_id: ExecutivePrincipalId,
    correlation_id: CorrelationId,
    occurred_at: datetime,
    reason_code: str,
    source_refs: tuple[ExecutiveAuditSourceRef, ...],
    evidence_refs: tuple[ExecutiveEvidenceRef, ...],
    authority_version: ExecutiveAuthorityVersion | None,
) -> Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError]:
    try:
        return Success(
            ExecutiveAuditEvidenceRecord(
                record_id=record_id,
                stage=stage,
                outcome=outcome,
                principal_id=principal_id,
                correlation_id=correlation_id,
                occurred_at=occurred_at,
                reason_code=reason_code,
                source_refs=source_refs,
                evidence_refs=evidence_refs,
                authority_version=authority_version,
            )
        )
    except ExecutiveAuditEvidenceError as error:
        return Failure(error)


def build_executive_authentication_audit_record(
    assertion: AuthenticatedExecutivePrincipal,
    *,
    record_id: ExecutiveAuditEvidenceRecordId,
    outcome: ExecutiveAuditEvidenceOutcome,
    occurred_at: datetime,
    reason_code: str,
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = (),
) -> Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError]:
    if not isinstance(assertion, AuthenticatedExecutivePrincipal):
        return Failure(
            ExecutiveAuditEvidenceValidationError(
                "authentication audit requires AuthenticatedExecutivePrincipal"
            )
        )
    try:
        _validate_timestamp(occurred_at, field_name="occurred_at")
        if occurred_at < assertion.issued_at:
            raise ExecutiveAuditEvidenceValidationError(
                "authentication audit cannot predate assertion issue"
            )
        refs = (
            _source_ref(
                ExecutiveAuditSourceKind.AUTHENTICATION_ASSERTION,
                assertion.assertion_id.value,
            ),
        )
        return _build_record(
            record_id=record_id,
            stage=ExecutiveAuditEvidenceStage.AUTHENTICATION,
            outcome=outcome,
            principal_id=assertion.principal_id,
            correlation_id=assertion.correlation_id,
            occurred_at=occurred_at,
            reason_code=reason_code,
            source_refs=refs,
            evidence_refs=evidence_refs,
            authority_version=None,
        )
    except ExecutiveAuditEvidenceError as error:
        return Failure(error)


def build_executive_authority_audit_record(
    assertion: AuthenticatedExecutivePrincipal,
    request: ExecutiveAuthorityStateRequest,
    *,
    snapshot: ExecutiveAuthorityStateSnapshot | None,
    record_id: ExecutiveAuditEvidenceRecordId,
    outcome: ExecutiveAuditEvidenceOutcome,
    occurred_at: datetime,
    reason_code: str,
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = (),
) -> Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError]:
    if not isinstance(assertion, AuthenticatedExecutivePrincipal):
        return Failure(
            ExecutiveAuditEvidenceValidationError(
                "authority audit requires AuthenticatedExecutivePrincipal"
            )
        )
    if not isinstance(request, ExecutiveAuthorityStateRequest):
        return Failure(
            ExecutiveAuditEvidenceValidationError(
                "authority audit requires ExecutiveAuthorityStateRequest"
            )
        )
    try:
        _validate_timestamp(occurred_at, field_name="occurred_at")
        if request.principal_id != assertion.principal_id:
            raise ExecutiveAuditEvidenceValidationError(
                "authority audit principal must match authentication assertion"
            )
        if request.correlation_id != assertion.correlation_id:
            raise ExecutiveAuditEvidenceValidationError(
                "authority audit correlation must match authentication assertion"
            )
        if request.requested_at < assertion.issued_at:
            raise ExecutiveAuditEvidenceValidationError(
                "authority audit request cannot predate authentication assertion"
            )
        if occurred_at < request.requested_at:
            raise ExecutiveAuditEvidenceValidationError(
                "authority audit cannot predate authority request"
            )
        refs = [
            _source_ref(
                ExecutiveAuditSourceKind.AUTHENTICATION_ASSERTION,
                assertion.assertion_id.value,
            ),
            _source_ref(
                ExecutiveAuditSourceKind.AUTHORITY_STATE_REQUEST,
                request.request_id.value,
            ),
        ]
        authority_version: ExecutiveAuthorityVersion | None = None
        combined_evidence = evidence_refs
        if snapshot is None:
            if outcome not in {
                ExecutiveAuditEvidenceOutcome.BLOCKED,
                ExecutiveAuditEvidenceOutcome.FAILED,
            }:
                raise ExecutiveAuditEvidenceValidationError(
                    "authority audit without snapshot must be blocked or failed"
                )
        else:
            if not isinstance(snapshot, ExecutiveAuthorityStateSnapshot):
                raise ExecutiveAuditEvidenceValidationError(
                    "authority audit snapshot must be ExecutiveAuthorityStateSnapshot or None"
                )
            if snapshot.request_id != request.request_id:
                raise ExecutiveAuditEvidenceValidationError(
                    "authority audit snapshot request id must match request"
                )
            if snapshot.principal_id != request.principal_id:
                raise ExecutiveAuditEvidenceValidationError(
                    "authority audit snapshot principal must match request"
                )
            if snapshot.observed_at < request.requested_at or snapshot.observed_at > occurred_at:
                raise ExecutiveAuditEvidenceValidationError(
                    "authority audit snapshot chronology is invalid"
                )
            refs.append(
                _source_ref(
                    ExecutiveAuditSourceKind.AUTHORITY_STATE_EVIDENCE,
                    snapshot.evidence_ref.value,
                )
            )
            combined_evidence = _merge_evidence_refs(
                evidence_refs,
                (ExecutiveEvidenceRef(snapshot.evidence_ref.value),),
            )
            if snapshot.active_grant is not None:
                authority_version = snapshot.active_grant.authority_version
                if outcome is not ExecutiveAuditEvidenceOutcome.SUCCEEDED:
                    raise ExecutiveAuditEvidenceValidationError(
                        "active authority snapshot must audit as succeeded"
                    )
            elif outcome is ExecutiveAuditEvidenceOutcome.SUCCEEDED:
                raise ExecutiveAuditEvidenceValidationError(
                    "non-active authority snapshot cannot audit as succeeded"
                )
        return _build_record(
            record_id=record_id,
            stage=ExecutiveAuditEvidenceStage.AUTHORITY,
            outcome=outcome,
            principal_id=assertion.principal_id,
            correlation_id=assertion.correlation_id,
            occurred_at=occurred_at,
            reason_code=reason_code,
            source_refs=tuple(refs),
            evidence_refs=combined_evidence,
            authority_version=authority_version,
        )
    except ExecutiveAuditEvidenceError as error:
        return Failure(error)


def _validate_authorized_control_binding(
    assertion: AuthenticatedExecutivePrincipal,
    authorized: AuthorizedExecutiveControlIntent,
) -> None:
    if authorized.intent.principal_id != assertion.principal_id:
        raise ExecutiveAuditEvidenceValidationError(
            "control audit principal must match authentication assertion"
        )
    if authorized.intent.correlation_id != assertion.correlation_id:
        raise ExecutiveAuditEvidenceValidationError(
            "control audit correlation must match authentication assertion"
        )


def _control_outcome(status: ExecutiveControlReceiptStatus) -> ExecutiveAuditEvidenceOutcome:
    if status is ExecutiveControlReceiptStatus.APPLIED:
        return ExecutiveAuditEvidenceOutcome.SUCCEEDED
    if status is ExecutiveControlReceiptStatus.NO_CHANGE:
        return ExecutiveAuditEvidenceOutcome.NO_ACTION
    if status is ExecutiveControlReceiptStatus.BLOCKED:
        return ExecutiveAuditEvidenceOutcome.BLOCKED
    return ExecutiveAuditEvidenceOutcome.FAILED


def build_executive_control_dispatch_audit_record(
    assertion: AuthenticatedExecutivePrincipal,
    authorized: AuthorizedExecutiveControlIntent,
    *,
    receipt: ExecutiveControlReceipt | None,
    record_id: ExecutiveAuditEvidenceRecordId,
    outcome: ExecutiveAuditEvidenceOutcome,
    occurred_at: datetime,
    reason_code: str,
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = (),
) -> Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError]:
    if not isinstance(assertion, AuthenticatedExecutivePrincipal):
        return Failure(
            ExecutiveAuditEvidenceValidationError(
                "control dispatch audit requires AuthenticatedExecutivePrincipal"
            )
        )
    if not isinstance(authorized, AuthorizedExecutiveControlIntent):
        return Failure(
            ExecutiveAuditEvidenceValidationError(
                "control dispatch audit requires AuthorizedExecutiveControlIntent"
            )
        )
    try:
        _validate_timestamp(occurred_at, field_name="occurred_at")
        _validate_authorized_control_binding(assertion, authorized)
        if occurred_at < authorized.authorized_at:
            raise ExecutiveAuditEvidenceValidationError(
                "control dispatch audit cannot predate authorization"
            )
        refs = [
            _source_ref(
                ExecutiveAuditSourceKind.AUTHENTICATION_ASSERTION,
                assertion.assertion_id.value,
            ),
            _source_ref(
                ExecutiveAuditSourceKind.AUTHORIZED_CONTROL_INTENT,
                authorized.intent.intent_id.value,
            ),
        ]
        combined_evidence = evidence_refs
        if receipt is None:
            if outcome not in {
                ExecutiveAuditEvidenceOutcome.BLOCKED,
                ExecutiveAuditEvidenceOutcome.FAILED,
            }:
                raise ExecutiveAuditEvidenceValidationError(
                    "control audit without receipt must be blocked or failed"
                )
        else:
            if not isinstance(receipt, ExecutiveControlReceipt):
                raise ExecutiveAuditEvidenceValidationError(
                    "control audit receipt must be ExecutiveControlReceipt or None"
                )
            intent = authorized.intent
            grant = authorized.grant
            if (
                receipt.intent_id != intent.intent_id
                or receipt.principal_id != intent.principal_id
                or receipt.action is not intent.action
                or receipt.target != intent.target
                or receipt.authority_version != grant.authority_version
                or receipt.correlation_id != intent.correlation_id
            ):
                raise ExecutiveAuditEvidenceValidationError(
                    "control audit receipt must match exact authorization"
                )
            if receipt.received_at < authorized.authorized_at:
                raise ExecutiveAuditEvidenceValidationError(
                    "control audit receipt cannot predate authorization"
                )
            if receipt.completed_at > occurred_at:
                raise ExecutiveAuditEvidenceValidationError(
                    "control audit cannot predate receipt completion"
                )
            if _control_outcome(receipt.status) is not outcome:
                raise ExecutiveAuditEvidenceValidationError(
                    "control audit outcome must match receipt status"
                )
            refs.append(
                _source_ref(
                    ExecutiveAuditSourceKind.CONTROL_RECEIPT,
                    receipt.receipt_id.value,
                )
            )
            combined_evidence = _merge_evidence_refs(evidence_refs, receipt.evidence_refs)
        return _build_record(
            record_id=record_id,
            stage=ExecutiveAuditEvidenceStage.COMMAND_DISPATCH,
            outcome=outcome,
            principal_id=assertion.principal_id,
            correlation_id=assertion.correlation_id,
            occurred_at=occurred_at,
            reason_code=reason_code,
            source_refs=tuple(refs),
            evidence_refs=combined_evidence,
            authority_version=authorized.grant.authority_version,
        )
    except ExecutiveAuditEvidenceError as error:
        return Failure(error)


def _validate_authorized_read_binding(
    assertion: AuthenticatedExecutivePrincipal,
    authorized: AuthorizedExecutiveReadRequest,
) -> None:
    if authorized.request.principal_id != assertion.principal_id:
        raise ExecutiveAuditEvidenceValidationError(
            "read audit principal must match authentication assertion"
        )
    if authorized.request.correlation_id != assertion.correlation_id:
        raise ExecutiveAuditEvidenceValidationError(
            "read audit correlation must match authentication assertion"
        )


def build_executive_read_dispatch_audit_record(
    assertion: AuthenticatedExecutivePrincipal,
    authorized: AuthorizedExecutiveReadRequest,
    *,
    delivery: ExecutiveReadDelivery | None,
    record_id: ExecutiveAuditEvidenceRecordId,
    outcome: ExecutiveAuditEvidenceOutcome,
    occurred_at: datetime,
    reason_code: str,
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = (),
) -> Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError]:
    if not isinstance(assertion, AuthenticatedExecutivePrincipal):
        return Failure(
            ExecutiveAuditEvidenceValidationError(
                "read dispatch audit requires AuthenticatedExecutivePrincipal"
            )
        )
    if not isinstance(authorized, AuthorizedExecutiveReadRequest):
        return Failure(
            ExecutiveAuditEvidenceValidationError(
                "read dispatch audit requires AuthorizedExecutiveReadRequest"
            )
        )
    try:
        _validate_timestamp(occurred_at, field_name="occurred_at")
        _validate_authorized_read_binding(assertion, authorized)
        if occurred_at < authorized.authorized_at:
            raise ExecutiveAuditEvidenceValidationError(
                "read dispatch audit cannot predate authorization"
            )
        refs = [
            _source_ref(
                ExecutiveAuditSourceKind.AUTHENTICATION_ASSERTION,
                assertion.assertion_id.value,
            ),
            _source_ref(
                ExecutiveAuditSourceKind.AUTHORIZED_READ_REQUEST,
                authorized.request.request_id.value,
            ),
        ]
        combined_evidence = evidence_refs
        if delivery is None:
            if outcome not in {
                ExecutiveAuditEvidenceOutcome.BLOCKED,
                ExecutiveAuditEvidenceOutcome.FAILED,
            }:
                raise ExecutiveAuditEvidenceValidationError(
                    "read audit without delivery must be blocked or failed"
                )
        else:
            if not isinstance(delivery, ExecutiveReadDelivery):
                raise ExecutiveAuditEvidenceValidationError(
                    "read audit delivery must be ExecutiveReadDelivery or None"
                )
            if delivery.authorized_request != authorized:
                raise ExecutiveAuditEvidenceValidationError(
                    "read audit delivery must match exact authorization"
                )
            if delivery.receipt.completed_at > occurred_at:
                raise ExecutiveAuditEvidenceValidationError(
                    "read audit cannot predate delivery receipt completion"
                )
            if outcome is not ExecutiveAuditEvidenceOutcome.SUCCEEDED:
                raise ExecutiveAuditEvidenceValidationError(
                    "served read delivery must audit as succeeded"
                )
            refs.extend(
                (
                    _source_ref(
                        ExecutiveAuditSourceKind.READ_DELIVERY,
                        delivery.receipt.receipt_id.value,
                    ),
                    _source_ref(
                        ExecutiveAuditSourceKind.READ_RECEIPT,
                        delivery.receipt.receipt_id.value,
                    ),
                )
            )
            combined_evidence = _merge_evidence_refs(
                evidence_refs,
                delivery.receipt.evidence_refs,
            )
        return _build_record(
            record_id=record_id,
            stage=ExecutiveAuditEvidenceStage.QUERY_DISPATCH,
            outcome=outcome,
            principal_id=assertion.principal_id,
            correlation_id=assertion.correlation_id,
            occurred_at=occurred_at,
            reason_code=reason_code,
            source_refs=tuple(refs),
            evidence_refs=combined_evidence,
            authority_version=authorized.grant.authority_version,
        )
    except ExecutiveAuditEvidenceError as error:
        return Failure(error)


def build_executive_governance_mutation_audit_record(
    assertion: AuthenticatedExecutivePrincipal,
    request: ExecutiveGovernanceMutationRequest,
    *,
    receipt: ExecutiveGovernanceMutationReceipt | None,
    control_receipt: ExecutiveControlReceipt | None,
    record_id: ExecutiveAuditEvidenceRecordId,
    outcome: ExecutiveAuditEvidenceOutcome,
    occurred_at: datetime,
    reason_code: str,
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = (),
) -> Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError]:
    if not isinstance(assertion, AuthenticatedExecutivePrincipal):
        return Failure(
            ExecutiveAuditEvidenceValidationError(
                "mutation audit requires AuthenticatedExecutivePrincipal"
            )
        )
    if not isinstance(request, ExecutiveGovernanceMutationRequest):
        return Failure(
            ExecutiveAuditEvidenceValidationError(
                "mutation audit requires ExecutiveGovernanceMutationRequest"
            )
        )
    try:
        _validate_timestamp(occurred_at, field_name="occurred_at")
        _validate_authorized_control_binding(assertion, request.authorized)
        if occurred_at < request.requested_at:
            raise ExecutiveAuditEvidenceValidationError(
                "mutation audit cannot predate mutation request"
            )
        refs = [
            _source_ref(
                ExecutiveAuditSourceKind.AUTHENTICATION_ASSERTION,
                assertion.assertion_id.value,
            ),
            _source_ref(
                ExecutiveAuditSourceKind.AUTHORIZED_CONTROL_INTENT,
                request.authorized.intent.intent_id.value,
            ),
            _source_ref(
                ExecutiveAuditSourceKind.CONTROL_RECEIPT,
                request.source_receipt_id.value,
            ),
            _source_ref(
                ExecutiveAuditSourceKind.GOVERNANCE_MUTATION,
                request.mutation_id.value,
            ),
            _source_ref(
                ExecutiveAuditSourceKind.GOVERNANCE_EXPECTED_SNAPSHOT,
                request.expected_state.snapshot_id.value,
            ),
            _source_ref(
                ExecutiveAuditSourceKind.GOVERNANCE_REQUESTED_SNAPSHOT,
                request.next_state.snapshot_id.value,
            ),
        ]
        combined_evidence = evidence_refs
        if control_receipt is not None:
            if not isinstance(control_receipt, ExecutiveControlReceipt):
                raise ExecutiveAuditEvidenceValidationError(
                    "mutation audit control receipt must be ExecutiveControlReceipt or None"
                )
            if control_receipt.receipt_id != request.source_receipt_id:
                raise ExecutiveAuditEvidenceValidationError(
                    "mutation audit control receipt id must match source receipt"
                )
            authorized = request.authorized
            intent = authorized.intent
            grant = authorized.grant
            if (
                control_receipt.intent_id != intent.intent_id
                or control_receipt.principal_id != intent.principal_id
                or control_receipt.action is not intent.action
                or control_receipt.target != intent.target
                or control_receipt.authority_version != grant.authority_version
                or control_receipt.correlation_id != intent.correlation_id
            ):
                raise ExecutiveAuditEvidenceValidationError(
                    "mutation audit control receipt must match authorization"
                )
            if control_receipt.completed_at > occurred_at:
                raise ExecutiveAuditEvidenceValidationError(
                    "mutation audit cannot predate control receipt completion"
                )
            combined_evidence = _merge_evidence_refs(
                combined_evidence,
                control_receipt.evidence_refs,
            )
        if receipt is None:
            if outcome not in {
                ExecutiveAuditEvidenceOutcome.BLOCKED,
                ExecutiveAuditEvidenceOutcome.FAILED,
            }:
                raise ExecutiveAuditEvidenceValidationError(
                    "mutation audit without receipt must be blocked or failed"
                )
        else:
            if not isinstance(receipt, ExecutiveGovernanceMutationReceipt):
                raise ExecutiveAuditEvidenceValidationError(
                    "mutation audit receipt must be ExecutiveGovernanceMutationReceipt or None"
                )
            if (
                receipt.mutation_id != request.mutation_id
                or receipt.source_receipt_id != request.source_receipt_id
                or receipt.expected_snapshot_id != request.expected_state.snapshot_id
                or receipt.expected_state_version != request.expected_state.state_version
                or receipt.requested_snapshot_id != request.next_state.snapshot_id
                or receipt.requested_state_version != request.next_state.state_version
            ):
                raise ExecutiveAuditEvidenceValidationError(
                    "mutation audit receipt must match exact mutation request"
                )
            if receipt.completed_at > occurred_at:
                raise ExecutiveAuditEvidenceValidationError(
                    "mutation audit cannot predate mutation receipt completion"
                )
            expected_outcome = (
                ExecutiveAuditEvidenceOutcome.SUCCEEDED
                if receipt.status is ExecutiveGovernanceMutationStatus.APPLIED
                else ExecutiveAuditEvidenceOutcome.BLOCKED
            )
            if outcome is not expected_outcome:
                raise ExecutiveAuditEvidenceValidationError(
                    "mutation audit outcome must match mutation receipt status"
                )
            refs.extend(
                (
                    _source_ref(
                        ExecutiveAuditSourceKind.GOVERNANCE_MUTATION_RECEIPT,
                        receipt.mutation_id.value,
                    ),
                    _source_ref(
                        ExecutiveAuditSourceKind.GOVERNANCE_OBSERVED_SNAPSHOT,
                        receipt.observed_snapshot_id.value,
                    ),
                )
            )
        return _build_record(
            record_id=record_id,
            stage=ExecutiveAuditEvidenceStage.GOVERNANCE_MUTATION,
            outcome=outcome,
            principal_id=assertion.principal_id,
            correlation_id=assertion.correlation_id,
            occurred_at=occurred_at,
            reason_code=reason_code,
            source_refs=tuple(refs),
            evidence_refs=combined_evidence,
            authority_version=request.authorized.grant.authority_version,
        )
    except ExecutiveAuditEvidenceError as error:
        return Failure(error)
