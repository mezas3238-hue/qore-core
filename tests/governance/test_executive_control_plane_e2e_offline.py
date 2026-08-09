from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_audit_evidence import (
    ExecutiveAuditEvidenceError,
    ExecutiveAuditEvidenceOutcome,
    ExecutiveAuditEvidencePort,
    ExecutiveAuditEvidenceRecord,
    ExecutiveAuditEvidenceRecordId,
    build_executive_authentication_audit_record,
    build_executive_authority_audit_record,
    build_executive_control_dispatch_audit_record,
    build_executive_governance_mutation_audit_record,
    build_executive_read_dispatch_audit_record,
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
from qore.governance.executive_command_dispatch import ExecutiveCommandDispatcher
from qore.governance.executive_control import (
    AuthorizedExecutiveControlIntent,
    AuthorizedExecutiveReadRequest,
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveControlAction,
    ExecutiveControlIntent,
    ExecutiveGrantId,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadRequest,
    ExecutiveReadRequestId,
    ExecutiveReadScope,
)
from qore.governance.executive_governance_mutation import (
    ExecutiveGovernanceMutationError,
    ExecutiveGovernanceMutationId,
    ExecutiveGovernanceMutationReceipt,
    ExecutiveGovernanceMutationRequest,
    ExecutiveGovernanceMutationStatus,
    build_executive_governance_mutation_receipt,
)
from qore.governance.executive_governance_state import (
    ExecutiveGovernanceStateSnapshot,
    ExecutiveGovernanceStateSnapshotId,
    ExecutiveGovernanceStateVersion,
    ExecutiveNewTradingState,
    ExecutiveSystemRunState,
)
from qore.governance.executive_ports import (
    ExecutiveControlReceipt,
    ExecutiveControlReceiptStatus,
    ExecutiveEvidenceRef,
    ExecutivePortError,
    ExecutivePortValidationError,
    ExecutiveReadDelivery,
    ExecutiveReadReceiptStatus,
    ExecutiveReceiptId,
    build_executive_control_receipt,
    build_executive_read_delivery,
    build_executive_read_receipt,
)
from qore.governance.executive_query_dispatch import ExecutiveQueryDispatcher
from qore.governance.executive_replay_idempotency import (
    ExecutiveReplayClaimPort,
    ExecutiveReplayClaimReceipt,
    ExecutiveReplayClaimRequest,
    ExecutiveReplayClaimStatus,
    ExecutiveReplayProtectionError,
    ExecutiveReplayProtector,
    build_executive_control_replay_claim,
    build_executive_replay_claim_receipt,
)
from qore.governance.executive_request_guard import ExecutiveRequestGuard
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 10, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("52000000-0000-0000-0000-000000000001"))
_SOURCE_RECEIPT_ID = ExecutiveReceiptId(
    UUID("52000000-0000-0000-0000-000000000020")
)


def _grant() -> ExecutiveAuthorityGrant:
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("52000000-0000-0000-0000-000000000002")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v4"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        reason="mission04 offline e2e",
    )


def _assertion() -> AuthenticatedExecutivePrincipal:
    return AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(
            UUID("52000000-0000-0000-0000-000000000003")
        ),
        principal_id=_PRINCIPAL,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef("identity:offline-fixture"),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        correlation_id=_CORRELATION,
    )


def _authority_request() -> ExecutiveAuthorityStateRequest:
    return ExecutiveAuthorityStateRequest(
        request_id=ExecutiveAuthorityStateRequestId(
            UUID("52000000-0000-0000-0000-000000000004")
        ),
        principal_id=_PRINCIPAL,
        requested_at=_NOW + timedelta(minutes=2),
        correlation_id=_CORRELATION,
    )


def _authority_snapshot(
    *,
    status: ExecutiveAuthorityStateStatus = ExecutiveAuthorityStateStatus.ACTIVE,
) -> ExecutiveAuthorityStateSnapshot:
    return ExecutiveAuthorityStateSnapshot(
        request_id=_authority_request().request_id,
        principal_id=_PRINCIPAL,
        status=status,
        observed_at=_NOW + timedelta(minutes=2, seconds=1),
        evidence_ref=ExecutiveAuthorityStateEvidenceRef("authority:offline/current"),
        grant=_grant() if status is ExecutiveAuthorityStateStatus.ACTIVE else None,
    )


def _control_intent() -> ExecutiveControlIntent:
    return ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("52000000-0000-0000-0000-000000000005")),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
        reason="CEO requests governed pause",
    )


def _read_request() -> ExecutiveReadRequest:
    return ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(
            UUID("52000000-0000-0000-0000-000000000006")
        ),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.GOVERNANCE,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
    )


def _governance_state(
    *,
    snapshot_id: UUID,
    version: str,
    observed_at: datetime,
    system_state: ExecutiveSystemRunState,
) -> ExecutiveGovernanceStateSnapshot:
    return ExecutiveGovernanceStateSnapshot(
        snapshot_id=ExecutiveGovernanceStateSnapshotId(snapshot_id),
        state_version=ExecutiveGovernanceStateVersion(version),
        observed_at=observed_at,
        system_run_state=system_state,
        new_trading_state=ExecutiveNewTradingState.PERMITTED,
        market_restrictions=(),
        account_restrictions=(),
    )


class _FakeAuthoritySource:
    def __init__(self, snapshot: ExecutiveAuthorityStateSnapshot) -> None:
        self.snapshot = snapshot
        self.requests: list[ExecutiveAuthorityStateRequest] = []

    def read_current(
        self,
        request: ExecutiveAuthorityStateRequest,
    ) -> Result[ExecutiveAuthorityStateSnapshot, ExecutiveAuthorityStateError]:
        self.requests.append(request)
        return Success(self.snapshot)


class _FakeReplayClaimPort(ExecutiveReplayClaimPort):
    def __init__(self) -> None:
        self.requests: list[ExecutiveReplayClaimRequest] = []

    def claim(
        self,
        request: ExecutiveReplayClaimRequest,
    ) -> Result[ExecutiveReplayClaimReceipt, ExecutiveReplayProtectionError]:
        self.requests.append(request)
        return build_executive_replay_claim_receipt(
            request,
            observed_fingerprint=request.fingerprint,
            completed_at=request.requested_at + timedelta(microseconds=1),
            status=ExecutiveReplayClaimStatus.ACQUIRED,
        )


class _FakeMutationPort:
    def __init__(self) -> None:
        self.requests: list[ExecutiveGovernanceMutationRequest] = []

    def compare_and_set(
        self,
        request: ExecutiveGovernanceMutationRequest,
    ) -> Result[ExecutiveGovernanceMutationReceipt, ExecutiveGovernanceMutationError]:
        self.requests.append(request)
        return build_executive_governance_mutation_receipt(
            request,
            observed_snapshot_id=request.next_state.snapshot_id,
            observed_state_version=request.next_state.state_version,
            completed_at=request.requested_at + timedelta(seconds=1),
            status=ExecutiveGovernanceMutationStatus.APPLIED,
        )


class _FakeGovernedCommandPort:
    def __init__(
        self,
        mutation_port: _FakeMutationPort,
        expected_state: ExecutiveGovernanceStateSnapshot,
        next_state: ExecutiveGovernanceStateSnapshot,
    ) -> None:
        self.mutation_port = mutation_port
        self.expected_state = expected_state
        self.next_state = next_state
        self.requests: list[AuthorizedExecutiveControlIntent] = []
        self.mutation_request: ExecutiveGovernanceMutationRequest | None = None
        self.mutation_receipt: ExecutiveGovernanceMutationReceipt | None = None

    def apply(
        self,
        request: AuthorizedExecutiveControlIntent,
    ) -> Result[ExecutiveControlReceipt, ExecutivePortError]:
        self.requests.append(request)
        mutation_request = ExecutiveGovernanceMutationRequest(
            mutation_id=ExecutiveGovernanceMutationId(
                UUID("52000000-0000-0000-0000-000000000021")
            ),
            authorized=request,
            expected_state=self.expected_state,
            next_state=self.next_state,
            source_receipt_id=_SOURCE_RECEIPT_ID,
            requested_at=_NOW + timedelta(minutes=4),
        )
        self.mutation_request = mutation_request
        mutation_result = self.mutation_port.compare_and_set(mutation_request)
        if isinstance(mutation_result, Failure):
            return Failure(ExecutivePortValidationError("governance mutation failed"))
        self.mutation_receipt = mutation_result.value
        return build_executive_control_receipt(
            request,
            receipt_id=_SOURCE_RECEIPT_ID,
            received_at=_NOW + timedelta(minutes=4),
            completed_at=_NOW + timedelta(minutes=5),
            status=ExecutiveControlReceiptStatus.APPLIED,
            reason_code="governance.applied",
            evidence_refs=(ExecutiveEvidenceRef("audit:control/offline-e2e"),),
        )


@dataclass(frozen=True, slots=True)
class _ProjectionMetadata:
    scope: ExecutiveReadScope
    projected_at: datetime


@dataclass(frozen=True, slots=True)
class _Projection:
    metadata: _ProjectionMetadata
    value: str

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.scope.value,
            self.metadata.projected_at.isoformat(),
            self.value,
        )


class _FakeQueryPort:
    def __init__(self) -> None:
        self.requests: list[AuthorizedExecutiveReadRequest] = []

    def read(
        self,
        request: AuthorizedExecutiveReadRequest,
    ) -> Result[ExecutiveReadDelivery, ExecutivePortError]:
        self.requests.append(request)
        receipt_result = build_executive_read_receipt(
            request,
            receipt_id=ExecutiveReceiptId(
                UUID("52000000-0000-0000-0000-000000000030")
            ),
            received_at=_NOW + timedelta(minutes=3, seconds=1),
            completed_at=_NOW + timedelta(minutes=3, seconds=3),
            status=ExecutiveReadReceiptStatus.SERVED,
            reason_code="read.served",
            evidence_refs=(ExecutiveEvidenceRef("audit:read/offline-e2e"),),
        )
        if isinstance(receipt_result, Failure):
            return receipt_result
        delivery_result = build_executive_read_delivery(
            request,
            projection=_Projection(
                metadata=_ProjectionMetadata(
                    scope=ExecutiveReadScope.GOVERNANCE,
                    projected_at=_NOW + timedelta(minutes=3, seconds=2),
                ),
                value="governance-state",
            ),
            receipt=receipt_result.value,
        )
        if isinstance(delivery_result, Failure):
            return delivery_result
        return Success(delivery_result.value)


class _FakeAuditSink(ExecutiveAuditEvidencePort):
    def __init__(self) -> None:
        self.records: list[ExecutiveAuditEvidenceRecord] = []

    def append(
        self,
        record: ExecutiveAuditEvidenceRecord,
    ) -> Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError]:
        self.records.append(record)
        return Success(record)


def _append_success(
    sink: _FakeAuditSink,
    result: Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError],
) -> ExecutiveAuditEvidenceRecord:
    assert isinstance(result, Success)
    appended = sink.append(result.value)
    assert isinstance(appended, Success)
    return appended.value


def test_control_e2e_auth_guard_replay_dispatch_mutation_receipt_and_audit() -> None:
    assertion = _assertion()
    authority_request = _authority_request()
    authority_snapshot = _authority_snapshot()
    authority_source = _FakeAuthoritySource(authority_snapshot)
    authorized_result = ExecutiveRequestGuard(authority_source).authorize_control(
        assertion,
        _control_intent(),
        authority_request=authority_request,
        evaluated_at=_NOW + timedelta(minutes=3),
    )
    assert isinstance(authorized_result, Success)
    authorized = authorized_result.value

    replay_request_result = build_executive_control_replay_claim(
        authorized,
        requested_at=_NOW + timedelta(minutes=3, seconds=1),
    )
    assert isinstance(replay_request_result, Success)
    replay_port = _FakeReplayClaimPort()
    replay_result = ExecutiveReplayProtector(replay_port).protect(
        replay_request_result.value
    )
    assert isinstance(replay_result, Success)

    expected_state = _governance_state(
        snapshot_id=UUID("52000000-0000-0000-0000-000000000010"),
        version="state.v1",
        observed_at=_NOW + timedelta(minutes=3),
        system_state=ExecutiveSystemRunState.ACTIVE,
    )
    next_state = _governance_state(
        snapshot_id=UUID("52000000-0000-0000-0000-000000000011"),
        version="state.v2",
        observed_at=_NOW + timedelta(minutes=4),
        system_state=ExecutiveSystemRunState.PAUSED,
    )
    mutation_port = _FakeMutationPort()
    command_port = _FakeGovernedCommandPort(mutation_port, expected_state, next_state)
    dispatch_result = ExecutiveCommandDispatcher(command_port).dispatch(authorized)
    assert isinstance(dispatch_result, Success)
    control_receipt = dispatch_result.value
    assert control_receipt.status is ExecutiveControlReceiptStatus.APPLIED
    assert len(authority_source.requests) == 1
    assert len(replay_port.requests) == 1
    assert len(command_port.requests) == 1
    assert len(mutation_port.requests) == 1
    assert command_port.mutation_request is not None
    assert command_port.mutation_receipt is not None

    audit = _FakeAuditSink()
    auth_record = _append_success(
        audit,
        build_executive_authentication_audit_record(
            assertion,
            record_id=ExecutiveAuditEvidenceRecordId(
                UUID("52000000-0000-0000-0000-000000000040")
            ),
            outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
            occurred_at=_NOW + timedelta(minutes=3),
            reason_code="authentication.succeeded",
        ),
    )
    authority_record = _append_success(
        audit,
        build_executive_authority_audit_record(
            assertion,
            authority_request,
            snapshot=authority_snapshot,
            record_id=ExecutiveAuditEvidenceRecordId(
                UUID("52000000-0000-0000-0000-000000000041")
            ),
            outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
            occurred_at=_NOW + timedelta(minutes=3),
            reason_code="authority.active",
        ),
    )
    command_record = _append_success(
        audit,
        build_executive_control_dispatch_audit_record(
            assertion,
            authorized,
            receipt=control_receipt,
            record_id=ExecutiveAuditEvidenceRecordId(
                UUID("52000000-0000-0000-0000-000000000042")
            ),
            outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
            occurred_at=_NOW + timedelta(minutes=6),
            reason_code="command.applied",
        ),
    )
    mutation_record = _append_success(
        audit,
        build_executive_governance_mutation_audit_record(
            assertion,
            command_port.mutation_request,
            receipt=command_port.mutation_receipt,
            control_receipt=control_receipt,
            record_id=ExecutiveAuditEvidenceRecordId(
                UUID("52000000-0000-0000-0000-000000000043")
            ),
            outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
            occurred_at=_NOW + timedelta(minutes=6),
            reason_code="governance.mutation.applied",
        ),
    )

    assert [record.stage.value for record in audit.records] == [
        "authentication",
        "authority",
        "command-dispatch",
        "governance-mutation",
    ]
    assert auth_record.correlation_id == _CORRELATION
    assert authority_record.authority_version == _grant().authority_version
    assert command_record.authority_version == _grant().authority_version
    assert mutation_record.authority_version == _grant().authority_version
    assert all(record.principal_id == _PRINCIPAL for record in audit.records)


def test_read_e2e_auth_guard_query_delivery_and_audit() -> None:
    assertion = _assertion()
    authority_request = _authority_request()
    authority_snapshot = _authority_snapshot()
    authority_source = _FakeAuthoritySource(authority_snapshot)
    authorized_result = ExecutiveRequestGuard(authority_source).authorize_read(
        assertion,
        _read_request(),
        authority_request=authority_request,
        evaluated_at=_NOW + timedelta(minutes=3),
    )
    assert isinstance(authorized_result, Success)
    authorized = authorized_result.value

    query_port = _FakeQueryPort()
    delivery_result = ExecutiveQueryDispatcher(query_port).dispatch(authorized)
    assert isinstance(delivery_result, Success)
    delivery = delivery_result.value
    assert delivery.authorized_request == authorized
    assert len(authority_source.requests) == 1
    assert len(query_port.requests) == 1

    audit = _FakeAuditSink()
    read_record = _append_success(
        audit,
        build_executive_read_dispatch_audit_record(
            assertion,
            authorized,
            delivery=delivery,
            record_id=ExecutiveAuditEvidenceRecordId(
                UUID("52000000-0000-0000-0000-000000000050")
            ),
            outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
            occurred_at=_NOW + timedelta(minutes=4),
            reason_code="query.served",
        ),
    )

    assert read_record.stage.value == "query-dispatch"
    assert read_record.correlation_id == _CORRELATION
    assert read_record.authority_version == _grant().authority_version
    assert read_record.evidence_refs == (
        ExecutiveEvidenceRef("audit:read/offline-e2e"),
    )


def test_unknown_authority_is_auditable_no_action_and_stops_before_dispatch() -> None:
    assertion = _assertion()
    authority_request = _authority_request()
    unknown_snapshot = _authority_snapshot(status=ExecutiveAuthorityStateStatus.UNKNOWN)
    authority_source = _FakeAuthoritySource(unknown_snapshot)

    result = ExecutiveRequestGuard(authority_source).authorize_control(
        assertion,
        _control_intent(),
        authority_request=authority_request,
        evaluated_at=_NOW + timedelta(minutes=3),
    )
    assert isinstance(result, Failure)
    assert len(authority_source.requests) == 1

    audit = _FakeAuditSink()
    blocked_record = _append_success(
        audit,
        build_executive_authority_audit_record(
            assertion,
            authority_request,
            snapshot=unknown_snapshot,
            record_id=ExecutiveAuditEvidenceRecordId(
                UUID("52000000-0000-0000-0000-000000000060")
            ),
            outcome=ExecutiveAuditEvidenceOutcome.BLOCKED,
            occurred_at=_NOW + timedelta(minutes=3),
            reason_code="authority.unknown",
        ),
    )

    assert blocked_record.outcome is ExecutiveAuditEvidenceOutcome.BLOCKED
    assert blocked_record.authority_version is None
    assert blocked_record.correlation_id == _CORRELATION
    assert blocked_record.principal_id == _PRINCIPAL
