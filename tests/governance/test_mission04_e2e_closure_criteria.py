from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from qore.core.event_bus import EventBus
from qore.core.runtime_health import evaluate_runtime_health
from qore.core.runtime_plan import RuntimePlan
from qore.core.runtime_state import RuntimeSnapshot, RuntimeStatus
from qore.domain.events import CorrelationId
from qore.governance.executive_audit_evidence import (
    ExecutiveAuditEvidenceError,
    ExecutiveAuditEvidenceOutcome,
    ExecutiveAuditEvidenceRecord,
    ExecutiveAuditEvidenceRecordId,
    ExecutiveAuditEvidenceStage,
    ExecutiveAuditEvidencePort,
    build_executive_authority_audit_record,
    build_executive_control_dispatch_audit_record,
)
from qore.governance.executive_authentication import (
    AuthenticatedExecutivePrincipal,
    ExecutiveAuthenticationAssertionId,
    ExecutiveAuthenticationContextCode,
    ExecutiveAuthenticationMethodCode,
    ExecutiveIdentityBoundaryRef,
)
from qore.governance.executive_authority_state import (
    ExecutiveAuthorityStateError,
    ExecutiveAuthorityStateEvidenceRef,
    ExecutiveAuthorityStateRequest,
    ExecutiveAuthorityStateRequestId,
    ExecutiveAuthorityStateSnapshot,
    ExecutiveAuthorityStateStatus,
)
from qore.governance.executive_command_dispatch import (
    ExecutiveCommandDispatchBlockedError,
    ExecutiveCommandDispatchReason,
    ExecutiveCommandDispatcher,
)
from qore.governance.executive_control import (
    AuthorizedExecutiveControlIntent,
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveControlAction,
    ExecutiveControlIntent,
    ExecutiveGrantId,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadScope,
)
from qore.governance.executive_control_plane_resilience import (
    ExecutiveControlPlaneFailureKind,
    ExecutiveControlPlaneOperation,
    ExecutiveControlPlaneRecoveryId,
    ExecutiveControlPlaneRecoveryRequirement,
    plan_executive_control_plane_recovery,
)
from qore.governance.executive_ports import (
    ExecutiveControlReceipt,
    ExecutiveControlReceiptStatus,
    ExecutiveEvidenceRef,
    ExecutivePortError,
    ExecutivePortValidationError,
    ExecutiveReceiptId,
    build_executive_control_receipt,
)
from qore.governance.executive_replay_idempotency import (
    ExecutiveReplayBlockedError,
    ExecutiveReplayBlockReason,
    ExecutiveReplayClaimReceipt,
    ExecutiveReplayClaimRequest,
    ExecutiveReplayClaimStatus,
    ExecutiveReplayFingerprint,
    ExecutiveReplayProtectionError,
    ExecutiveReplayProtector,
    build_executive_control_replay_claim,
    build_executive_replay_claim_receipt,
)
from qore.governance.executive_request_guard import (
    ExecutiveRequestGuard,
    ExecutiveRequestGuardBlockedError,
    ExecutiveRequestGuardReason,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 11, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("53000000-0000-0000-0000-000000000001"))


def _assertion(*, expires_at: datetime | None = None) -> AuthenticatedExecutivePrincipal:
    return AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(
            UUID("53000000-0000-0000-0000-000000000002")
        ),
        principal_id=_PRINCIPAL,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef("identity:primary"),
        issued_at=_NOW,
        expires_at=expires_at or _NOW + timedelta(minutes=10),
        correlation_id=_CORRELATION,
    )


def _grant() -> ExecutiveAuthorityGrant:
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("53000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v6"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=10),
        reason="mission04 closure e2e authority",
    )


def _intent() -> ExecutiveControlIntent:
    return ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("53000000-0000-0000-0000-000000000004")),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
        reason="CEO requests governed pause",
    )


def _authority_request() -> ExecutiveAuthorityStateRequest:
    return ExecutiveAuthorityStateRequest(
        request_id=ExecutiveAuthorityStateRequestId(
            UUID("53000000-0000-0000-0000-000000000005")
        ),
        principal_id=_PRINCIPAL,
        requested_at=_NOW + timedelta(minutes=1, seconds=15),
        correlation_id=_CORRELATION,
    )


def _authority_snapshot(status: ExecutiveAuthorityStateStatus) -> ExecutiveAuthorityStateSnapshot:
    request = _authority_request()
    if status is ExecutiveAuthorityStateStatus.UNKNOWN:
        return ExecutiveAuthorityStateSnapshot(
            request_id=request.request_id,
            principal_id=_PRINCIPAL,
            status=status,
            observed_at=_NOW + timedelta(minutes=1, seconds=30),
            evidence_ref=ExecutiveAuthorityStateEvidenceRef("audit:authority/unknown"),
        )
    if status is ExecutiveAuthorityStateStatus.REVOKED:
        return ExecutiveAuthorityStateSnapshot(
            request_id=request.request_id,
            principal_id=_PRINCIPAL,
            status=status,
            observed_at=_NOW + timedelta(minutes=1, seconds=30),
            evidence_ref=ExecutiveAuthorityStateEvidenceRef("audit:authority/revoked"),
            grant=_grant(),
            invalidated_at=_NOW + timedelta(minutes=1, seconds=20),
        )
    return ExecutiveAuthorityStateSnapshot(
        request_id=request.request_id,
        principal_id=_PRINCIPAL,
        status=ExecutiveAuthorityStateStatus.ACTIVE,
        observed_at=_NOW + timedelta(minutes=1, seconds=30),
        evidence_ref=ExecutiveAuthorityStateEvidenceRef("audit:authority/active"),
        grant=_grant(),
    )


class _AuthoritySource:
    def __init__(self, snapshot: ExecutiveAuthorityStateSnapshot) -> None:
        self.snapshot = snapshot
        self.requests: list[ExecutiveAuthorityStateRequest] = []

    def read_current(
        self,
        request: ExecutiveAuthorityStateRequest,
    ) -> Result[ExecutiveAuthorityStateSnapshot, ExecutiveAuthorityStateError]:
        self.requests.append(request)
        return Success(self.snapshot)


class _CommandPort:
    def __init__(
        self,
        *,
        receipt_status: ExecutiveControlReceiptStatus = ExecutiveControlReceiptStatus.APPLIED,
        error: ExecutivePortError | None = None,
    ) -> None:
        self.receipt_status = receipt_status
        self.error = error
        self.requests: list[AuthorizedExecutiveControlIntent] = []

    def apply(
        self,
        request: AuthorizedExecutiveControlIntent,
    ) -> Result[ExecutiveControlReceipt, ExecutivePortError]:
        self.requests.append(request)
        if self.error is not None:
            return Failure(self.error)
        built = build_executive_control_receipt(
            request,
            receipt_id=ExecutiveReceiptId(
                UUID("53000000-0000-0000-0000-000000000006")
            ),
            received_at=_NOW + timedelta(minutes=2, seconds=1),
            completed_at=_NOW + timedelta(minutes=2, seconds=2),
            status=self.receipt_status,
            reason_code=f"governance.{self.receipt_status.value}",
            evidence_refs=(ExecutiveEvidenceRef("audit:control/result"),),
        )
        assert isinstance(built, Success)
        return Success(built.value)


class _ReplayPort:
    def __init__(
        self,
        status: ExecutiveReplayClaimStatus,
        *,
        conflicting_fingerprint: ExecutiveReplayFingerprint | None = None,
    ) -> None:
        self.status = status
        self.conflicting_fingerprint = conflicting_fingerprint
        self.requests: list[ExecutiveReplayClaimRequest] = []

    def claim(
        self,
        request: ExecutiveReplayClaimRequest,
    ) -> Result[ExecutiveReplayClaimReceipt, ExecutiveReplayProtectionError]:
        self.requests.append(request)
        observed = self.conflicting_fingerprint or request.fingerprint
        built = build_executive_replay_claim_receipt(
            request,
            observed_fingerprint=observed,
            completed_at=request.requested_at + timedelta(microseconds=1),
            status=self.status,
        )
        assert isinstance(built, Success)
        return Success(built.value)


class _AuditSink:
    def __init__(self) -> None:
        self.records: list[ExecutiveAuditEvidenceRecord] = []

    def append(
        self,
        record: ExecutiveAuditEvidenceRecord,
    ) -> Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError]:
        self.records.append(record)
        return Success(record)


def _authorized() -> AuthorizedExecutiveControlIntent:
    source = _AuthoritySource(_authority_snapshot(ExecutiveAuthorityStateStatus.ACTIVE))
    result = ExecutiveRequestGuard(source).authorize_control(
        _assertion(),
        _intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(result, Success)
    return result.value


def test_unauthenticated_request_fails_before_authority_or_dispatch() -> None:
    authority_source = _AuthoritySource(
        _authority_snapshot(ExecutiveAuthorityStateStatus.ACTIVE)
    )
    command_port = _CommandPort()

    result = ExecutiveRequestGuard(authority_source).authorize_control(
        cast(AuthenticatedExecutivePrincipal, object()),
        _intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=2),
    )

    assert isinstance(result, Failure)
    assert authority_source.requests == []
    assert command_port.requests == []


def test_expired_authentication_fails_before_authority_or_dispatch() -> None:
    authority_source = _AuthoritySource(
        _authority_snapshot(ExecutiveAuthorityStateStatus.ACTIVE)
    )
    command_port = _CommandPort()
    expired = _assertion(expires_at=_NOW + timedelta(minutes=1, seconds=30))

    result = ExecutiveRequestGuard(authority_source).authorize_control(
        expired,
        _intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveRequestGuardBlockedError)
    assert result.error.reason is ExecutiveRequestGuardReason.AUTHENTICATION_INVALID
    assert authority_source.requests == []
    assert command_port.requests == []


def test_revoked_and_unknown_authority_fail_closed_before_dispatch_and_are_auditable() -> None:
    audit_sink_impl = _AuditSink()
    audit_sink: ExecutiveAuditEvidencePort = audit_sink_impl

    for index, status in enumerate(
        (ExecutiveAuthorityStateStatus.REVOKED, ExecutiveAuthorityStateStatus.UNKNOWN),
        start=20,
    ):
        snapshot = _authority_snapshot(status)
        source = _AuthoritySource(snapshot)
        command_port = _CommandPort()
        guarded = ExecutiveRequestGuard(source).authorize_control(
            _assertion(),
            _intent(),
            authority_request=_authority_request(),
            evaluated_at=_NOW + timedelta(minutes=2),
        )

        assert isinstance(guarded, Failure)
        assert isinstance(guarded.error, ExecutiveRequestGuardBlockedError)
        assert guarded.error.reason is ExecutiveRequestGuardReason.AUTHORITY_NOT_ACTIVE
        assert command_port.requests == []

        audit = build_executive_authority_audit_record(
            _assertion(),
            _authority_request(),
            snapshot=snapshot,
            record_id=ExecutiveAuditEvidenceRecordId(UUID(int=index)),
            outcome=ExecutiveAuditEvidenceOutcome.BLOCKED,
            occurred_at=_NOW + timedelta(minutes=2),
            reason_code="authority.not_active",
        )
        assert isinstance(audit, Success)
        assert isinstance(audit_sink.append(audit.value), Success)

    assert len(audit_sink_impl.records) == 2
    assert all(
        record.stage is ExecutiveAuditEvidenceStage.AUTHORITY
        and record.outcome is ExecutiveAuditEvidenceOutcome.BLOCKED
        for record in audit_sink_impl.records
    )


def test_exact_duplicate_replay_is_deterministically_blocked_without_redispatch() -> None:
    authorized = _authorized()
    claim = build_executive_control_replay_claim(
        authorized,
        requested_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(claim, Success)
    replay_port = _ReplayPort(ExecutiveReplayClaimStatus.DUPLICATE)
    command_port = _CommandPort()

    result = ExecutiveReplayProtector(replay_port).protect(claim.value)

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveReplayBlockedError)
    assert result.error.reason is ExecutiveReplayBlockReason.DUPLICATE
    assert replay_port.requests == [claim.value]
    assert command_port.requests == []


def test_modified_replay_conflict_fails_closed_without_dispatch() -> None:
    authorized = _authorized()
    claim = build_executive_control_replay_claim(
        authorized,
        requested_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(claim, Success)
    replay_port = _ReplayPort(
        ExecutiveReplayClaimStatus.CONFLICT,
        conflicting_fingerprint=ExecutiveReplayFingerprint(("intent:conflict",)),
    )
    command_port = _CommandPort()

    result = ExecutiveReplayProtector(replay_port).protect(claim.value)

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveReplayBlockedError)
    assert result.error.reason is ExecutiveReplayBlockReason.CONFLICT
    assert replay_port.requests == [claim.value]
    assert command_port.requests == []


def test_no_action_command_outcome_is_emitted_as_durable_no_action_audit() -> None:
    authorized = _authorized()
    command_port = _CommandPort(receipt_status=ExecutiveControlReceiptStatus.NO_CHANGE)
    dispatched = ExecutiveCommandDispatcher(command_port).dispatch(authorized)
    assert isinstance(dispatched, Success)

    audit = build_executive_control_dispatch_audit_record(
        _assertion(),
        authorized,
        receipt=dispatched.value,
        record_id=ExecutiveAuditEvidenceRecordId(UUID(int=30)),
        outcome=ExecutiveAuditEvidenceOutcome.NO_ACTION,
        occurred_at=_NOW + timedelta(minutes=2, seconds=3),
        reason_code="dispatch.no_action",
    )
    assert isinstance(audit, Success)
    sink_impl = _AuditSink()
    sink: ExecutiveAuditEvidencePort = sink_impl
    appended = sink.append(audit.value)

    assert isinstance(appended, Success)
    assert command_port.requests == [authorized]
    assert sink_impl.records == [audit.value]
    assert audit.value.outcome is ExecutiveAuditEvidenceOutcome.NO_ACTION


def test_ambiguous_downstream_failure_is_contained_without_automatic_repeat() -> None:
    authorized = _authorized()
    command_port = _CommandPort(
        error=ExecutivePortValidationError("ambiguous downstream outcome")
    )
    dispatched = ExecutiveCommandDispatcher(command_port).dispatch(authorized)

    assert isinstance(dispatched, Failure)
    assert isinstance(dispatched.error, ExecutiveCommandDispatchBlockedError)
    assert dispatched.error.reason is ExecutiveCommandDispatchReason.DOWNSTREAM_FAILED
    assert command_port.requests == [authorized]

    recovery = plan_executive_control_plane_recovery(
        ExecutiveControlPlaneOperation.COMMAND_DISPATCH,
        ExecutiveControlPlaneFailureKind.AMBIGUOUS_OUTCOME,
        recovery_id=ExecutiveControlPlaneRecoveryId(UUID(int=40)),
        correlation_id=_CORRELATION,
        failed_at=_NOW + timedelta(minutes=2, seconds=2),
        planned_at=_NOW + timedelta(minutes=2, seconds=3),
    )
    assert isinstance(recovery, Success)
    assert (
        recovery.value.requirement
        is ExecutiveControlPlaneRecoveryRequirement.VERIFY_CONTROL_RECEIPT
    )
    assert not recovery.value.automatic_retry_allowed
    assert not recovery.value.automatic_redispatch_allowed
    assert command_port.requests == [authorized]


def test_external_control_plane_composition_preserves_core_runtime_identity() -> None:
    event_bus = EventBus()
    runtime_plan = RuntimePlan()
    runtime_snapshot = RuntimeSnapshot(
        context=None,
        status=RuntimeStatus.STOPPED,
        components=(),
        active_component_names=(),
        residual_component_names=(),
    )
    runtime_health = evaluate_runtime_health(runtime_snapshot)
    event_bus_identity = id(event_bus)
    runtime_plan_before = runtime_plan
    runtime_snapshot_before = runtime_snapshot
    runtime_health_before = runtime_health

    source = _AuthoritySource(_authority_snapshot(ExecutiveAuthorityStateStatus.ACTIVE))
    guarded = ExecutiveRequestGuard(source).authorize_control(
        _assertion(),
        _intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=2),
    )

    assert isinstance(guarded, Success)
    assert id(event_bus) == event_bus_identity
    assert runtime_plan is runtime_plan_before
    assert runtime_plan == RuntimePlan()
    assert runtime_snapshot is runtime_snapshot_before
    assert runtime_snapshot == RuntimeSnapshot(
        context=None,
        status=RuntimeStatus.STOPPED,
        components=(),
        active_component_names=(),
        residual_component_names=(),
    )
    assert runtime_health is runtime_health_before
    assert runtime_health == evaluate_runtime_health(runtime_snapshot)
