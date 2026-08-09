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
    ExecutiveAuditEvidenceStage,
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
    ExecutiveAuthorityStateSource,
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
from qore.governance.executive_control_plane_observability import (
    ExecutiveControlPlaneObservabilityError,
    ExecutiveControlPlaneObservabilityPort,
    ExecutiveControlPlaneObservation,
    ExecutiveControlPlaneObservationId,
    ExecutiveControlPlaneObservationStage,
    build_executive_audit_append_observation,
    build_executive_control_plane_observation,
)
from qore.governance.executive_governance_mutation import (
    ExecutiveGovernanceMutationError,
    ExecutiveGovernanceMutationId,
    ExecutiveGovernanceMutationPort,
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
    ExecutiveControlCommandPort,
    ExecutiveControlReceipt,
    ExecutiveControlReceiptStatus,
    ExecutiveEvidenceRef,
    ExecutivePortError,
    ExecutiveReadDelivery,
    ExecutiveReadProjection,
    ExecutiveReadQueryPort,
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
from qore.governance.executive_request_guard import (
    ExecutiveRequestGuard,
    ExecutiveRequestGuardBlockedError,
    ExecutiveRequestGuardReason,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 10, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("52000000-0000-0000-0000-000000000001"))


def _assertion() -> AuthenticatedExecutivePrincipal:
    return AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(
            UUID("52000000-0000-0000-0000-000000000002")
        ),
        principal_id=_PRINCIPAL,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef("identity:primary"),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        correlation_id=_CORRELATION,
    )


def _grant() -> ExecutiveAuthorityGrant:
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("52000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v5"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        reason="mission04 offline e2e authority",
    )


def _authority_request() -> ExecutiveAuthorityStateRequest:
    return ExecutiveAuthorityStateRequest(
        request_id=ExecutiveAuthorityStateRequestId(
            UUID("52000000-0000-0000-0000-000000000004")
        ),
        principal_id=_PRINCIPAL,
        requested_at=_NOW + timedelta(minutes=1, seconds=30),
        correlation_id=_CORRELATION,
    )


def _active_authority_snapshot() -> ExecutiveAuthorityStateSnapshot:
    request = _authority_request()
    return ExecutiveAuthorityStateSnapshot(
        request_id=request.request_id,
        principal_id=_PRINCIPAL,
        status=ExecutiveAuthorityStateStatus.ACTIVE,
        observed_at=_NOW + timedelta(minutes=1, seconds=45),
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


class _ReplayClaimStore:
    def __init__(self) -> None:
        self.requests: list[ExecutiveReplayClaimRequest] = []

    def claim(
        self,
        request: ExecutiveReplayClaimRequest,
    ) -> Result[ExecutiveReplayClaimReceipt, ExecutiveReplayProtectionError]:
        self.requests.append(request)
        built = build_executive_replay_claim_receipt(
            request,
            observed_fingerprint=request.fingerprint,
            completed_at=request.requested_at + timedelta(microseconds=1),
            status=ExecutiveReplayClaimStatus.ACQUIRED,
        )
        assert isinstance(built, Success)
        return Success(built.value)


class _CommandPort:
    def __init__(self) -> None:
        self.requests: list[AuthorizedExecutiveControlIntent] = []

    def apply(
        self,
        request: AuthorizedExecutiveControlIntent,
    ) -> Result[ExecutiveControlReceipt, ExecutivePortError]:
        self.requests.append(request)
        built = build_executive_control_receipt(
            request,
            receipt_id=ExecutiveReceiptId(
                UUID("52000000-0000-0000-0000-000000000005")
            ),
            received_at=_NOW + timedelta(minutes=2, seconds=1),
            completed_at=_NOW + timedelta(minutes=2, seconds=2),
            status=ExecutiveControlReceiptStatus.APPLIED,
            reason_code="governance.applied",
            evidence_refs=(ExecutiveEvidenceRef("audit:control/applied"),),
        )
        assert isinstance(built, Success)
        return Success(built.value)


class _MutationPort:
    def __init__(self) -> None:
        self.requests: list[ExecutiveGovernanceMutationRequest] = []

    def compare_and_set(
        self,
        request: ExecutiveGovernanceMutationRequest,
    ) -> Result[ExecutiveGovernanceMutationReceipt, ExecutiveGovernanceMutationError]:
        self.requests.append(request)
        built = build_executive_governance_mutation_receipt(
            request,
            observed_snapshot_id=request.next_state.snapshot_id,
            observed_state_version=request.next_state.state_version,
            completed_at=_NOW + timedelta(minutes=2, seconds=5),
            status=ExecutiveGovernanceMutationStatus.APPLIED,
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


class _ObservabilitySink:
    def __init__(self) -> None:
        self.observations: list[ExecutiveControlPlaneObservation] = []

    def emit(
        self,
        observation: ExecutiveControlPlaneObservation,
    ) -> Result[ExecutiveControlPlaneObservation, ExecutiveControlPlaneObservabilityError]:
        self.observations.append(observation)
        return Success(observation)


@dataclass(frozen=True, slots=True)
class _ProjectionMetadata:
    scope: ExecutiveReadScope
    projected_at: datetime


@dataclass(frozen=True, slots=True)
class _GovernanceProjection:
    metadata: _ProjectionMetadata
    state_version: str

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.scope.value,
            self.metadata.projected_at.isoformat(),
            self.state_version,
        )


class _ReadPort:
    def __init__(self) -> None:
        self.requests: list[AuthorizedExecutiveReadRequest] = []

    def read(
        self,
        request: AuthorizedExecutiveReadRequest,
    ) -> Result[ExecutiveReadDelivery, ExecutivePortError]:
        self.requests.append(request)
        receipt = build_executive_read_receipt(
            request,
            receipt_id=ExecutiveReceiptId(
                UUID("52000000-0000-0000-0000-000000000006")
            ),
            received_at=_NOW + timedelta(minutes=2, seconds=1),
            completed_at=_NOW + timedelta(minutes=2, seconds=3),
            status=ExecutiveReadReceiptStatus.SERVED,
            reason_code="read.served",
            evidence_refs=(ExecutiveEvidenceRef("audit:read/served"),),
        )
        assert isinstance(receipt, Success)
        projection: ExecutiveReadProjection = _GovernanceProjection(
            metadata=_ProjectionMetadata(
                scope=ExecutiveReadScope.GOVERNANCE,
                projected_at=_NOW + timedelta(minutes=2, seconds=2),
            ),
            state_version="state.v2",
        )
        delivery = build_executive_read_delivery(
            request,
            projection=projection,
            receipt=receipt.value,
        )
        assert isinstance(delivery, Success)
        return Success(delivery.value)


def _control_intent() -> ExecutiveControlIntent:
    return ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("52000000-0000-0000-0000-000000000007")),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
        reason="CEO requests governed offline pause",
    )


def _read_request() -> ExecutiveReadRequest:
    return ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(
            UUID("52000000-0000-0000-0000-000000000008")
        ),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.GOVERNANCE,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
    )


def _governance_state(
    *,
    snapshot_id: str,
    version: str,
    observed_at: datetime,
    state: ExecutiveSystemRunState,
) -> ExecutiveGovernanceStateSnapshot:
    return ExecutiveGovernanceStateSnapshot(
        snapshot_id=ExecutiveGovernanceStateSnapshotId(UUID(snapshot_id)),
        state_version=ExecutiveGovernanceStateVersion(version),
        observed_at=observed_at,
        system_run_state=state,
        new_trading_state=ExecutiveNewTradingState.PERMITTED,
        market_restrictions=(),
        account_restrictions=(),
    )


def test_command_mutation_chain_composes_offline_with_exact_audit_evidence() -> None:
    assertion = _assertion()
    authority_request = _authority_request()
    authority_source_impl = _AuthoritySource(_active_authority_snapshot())
    authority_source: ExecutiveAuthorityStateSource = authority_source_impl
    guard = ExecutiveRequestGuard(authority_source)

    authorized = guard.authorize_control(
        assertion,
        _control_intent(),
        authority_request=authority_request,
        evaluated_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(authorized, Success)

    replay_request = build_executive_control_replay_claim(
        authorized.value,
        requested_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(replay_request, Success)
    replay_store_impl = _ReplayClaimStore()
    replay_store: ExecutiveReplayClaimPort = replay_store_impl
    replay = ExecutiveReplayProtector(replay_store).protect(replay_request.value)
    assert isinstance(replay, Success)

    command_impl = _CommandPort()
    command_port: ExecutiveControlCommandPort = command_impl
    command = ExecutiveCommandDispatcher(command_port).dispatch(authorized.value)
    assert isinstance(command, Success)

    expected = _governance_state(
        snapshot_id="52000000-0000-0000-0000-000000000009",
        version="state.v1",
        observed_at=_NOW + timedelta(minutes=2, seconds=2),
        state=ExecutiveSystemRunState.ACTIVE,
    )
    next_state = _governance_state(
        snapshot_id="52000000-0000-0000-0000-000000000010",
        version="state.v2",
        observed_at=_NOW + timedelta(minutes=2, seconds=3),
        state=ExecutiveSystemRunState.PAUSED,
    )
    mutation_request = ExecutiveGovernanceMutationRequest(
        mutation_id=ExecutiveGovernanceMutationId(
            UUID("52000000-0000-0000-0000-000000000011")
        ),
        authorized=authorized.value,
        expected_state=expected,
        next_state=next_state,
        source_receipt_id=command.value.receipt_id,
        requested_at=_NOW + timedelta(minutes=2, seconds=3),
    )
    mutation_impl = _MutationPort()
    mutation_port: ExecutiveGovernanceMutationPort = mutation_impl
    mutation = mutation_port.compare_and_set(mutation_request)
    assert isinstance(mutation, Success)

    audit_impl = _AuditSink()
    audit_port: ExecutiveAuditEvidencePort = audit_impl
    auth_audit = build_executive_authentication_audit_record(
        assertion,
        record_id=ExecutiveAuditEvidenceRecordId(UUID(int=100)),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(seconds=1),
        reason_code="authentication.accepted",
    )
    authority_audit = build_executive_authority_audit_record(
        assertion,
        authority_request,
        snapshot=_active_authority_snapshot(),
        record_id=ExecutiveAuditEvidenceRecordId(UUID(int=101)),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(minutes=1, seconds=46),
        reason_code="authority.active",
    )
    dispatch_audit = build_executive_control_dispatch_audit_record(
        assertion,
        authorized.value,
        receipt=command.value,
        record_id=ExecutiveAuditEvidenceRecordId(UUID(int=102)),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(minutes=2, seconds=3),
        reason_code="dispatch.completed",
    )
    mutation_audit = build_executive_governance_mutation_audit_record(
        assertion,
        mutation_request,
        receipt=mutation.value,
        control_receipt=command.value,
        record_id=ExecutiveAuditEvidenceRecordId(UUID(int=103)),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(minutes=2, seconds=6),
        reason_code="governance.mutation_applied",
    )
    for result in (auth_audit, authority_audit, dispatch_audit, mutation_audit):
        assert isinstance(result, Success)
        appended = audit_port.append(result.value)
        assert isinstance(appended, Success)

    observation_impl = _ObservabilitySink()
    observation_port: ExecutiveControlPlaneObservabilityPort = observation_impl
    for index, record in enumerate(audit_impl.records, start=200):
        built = build_executive_control_plane_observation(
            record,
            observation_id=ExecutiveControlPlaneObservationId(UUID(int=index)),
            observed_at=record.occurred_at + timedelta(microseconds=1),
        )
        assert isinstance(built, Success)
        emitted = observation_port.emit(built.value)
        assert isinstance(emitted, Success)
    audit_observation = build_executive_audit_append_observation(
        audit_impl.records[-1],
        observation_id=ExecutiveControlPlaneObservationId(UUID(int=204)),
        observed_at=_NOW + timedelta(minutes=2, seconds=7),
    )
    assert isinstance(audit_observation, Success)
    assert isinstance(observation_port.emit(audit_observation.value), Success)

    assert authority_source_impl.requests == [authority_request]
    assert replay_store_impl.requests == [replay_request.value]
    assert command_impl.requests == [authorized.value]
    assert mutation_impl.requests == [mutation_request]
    assert [record.stage for record in audit_impl.records] == [
        ExecutiveAuditEvidenceStage.AUTHENTICATION,
        ExecutiveAuditEvidenceStage.AUTHORITY,
        ExecutiveAuditEvidenceStage.COMMAND_DISPATCH,
        ExecutiveAuditEvidenceStage.GOVERNANCE_MUTATION,
    ]
    assert observation_impl.observations[-1].stage is ExecutiveControlPlaneObservationStage.AUDIT


def test_read_chain_composes_offline_from_guard_to_delivery_and_audit() -> None:
    assertion = _assertion()
    authority_request = _authority_request()
    authority_source_impl = _AuthoritySource(_active_authority_snapshot())
    guard = ExecutiveRequestGuard(authority_source_impl)

    authorized = guard.authorize_read(
        assertion,
        _read_request(),
        authority_request=authority_request,
        evaluated_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(authorized, Success)

    read_impl = _ReadPort()
    read_port: ExecutiveReadQueryPort = read_impl
    delivery = ExecutiveQueryDispatcher(read_port).dispatch(authorized.value)
    assert isinstance(delivery, Success)

    audit = build_executive_read_dispatch_audit_record(
        assertion,
        authorized.value,
        delivery=delivery.value,
        record_id=ExecutiveAuditEvidenceRecordId(UUID(int=300)),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(minutes=2, seconds=4),
        reason_code="read.served",
    )
    assert isinstance(audit, Success)
    audit_sink_impl = _AuditSink()
    audit_sink: ExecutiveAuditEvidencePort = audit_sink_impl
    appended = audit_sink.append(audit.value)

    assert isinstance(appended, Success)
    assert read_impl.requests == [authorized.value]
    assert delivery.value.authorized_request == authorized.value
    assert audit.value.stage is ExecutiveAuditEvidenceStage.QUERY_DISPATCH
    assert audit.value.correlation_id == _CORRELATION


def test_unknown_authority_fails_closed_before_dispatch_and_remains_auditable() -> None:
    assertion = _assertion()
    authority_request = _authority_request()
    unknown = ExecutiveAuthorityStateSnapshot(
        request_id=authority_request.request_id,
        principal_id=_PRINCIPAL,
        status=ExecutiveAuthorityStateStatus.UNKNOWN,
        observed_at=_NOW + timedelta(minutes=1, seconds=45),
        evidence_ref=ExecutiveAuthorityStateEvidenceRef("audit:authority/unknown"),
    )
    authority_source_impl = _AuthoritySource(unknown)
    result = ExecutiveRequestGuard(authority_source_impl).authorize_control(
        assertion,
        _control_intent(),
        authority_request=authority_request,
        evaluated_at=_NOW + timedelta(minutes=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveRequestGuardBlockedError)
    assert result.error.reason is ExecutiveRequestGuardReason.AUTHORITY_NOT_ACTIVE

    audit = build_executive_authority_audit_record(
        assertion,
        authority_request,
        snapshot=unknown,
        record_id=ExecutiveAuditEvidenceRecordId(UUID(int=400)),
        outcome=ExecutiveAuditEvidenceOutcome.BLOCKED,
        occurred_at=_NOW + timedelta(minutes=2),
        reason_code="authority.not_active",
    )
    assert isinstance(audit, Success)
    assert audit.value.outcome is ExecutiveAuditEvidenceOutcome.BLOCKED
    assert audit.value.authority_version is None
