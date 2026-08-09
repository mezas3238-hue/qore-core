from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.events import CorrelationId
from qore.governance.executive_audit_evidence import (
    ExecutiveAuditEvidenceOutcome,
    ExecutiveAuditEvidenceRecordId,
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
from qore.governance.executive_command_dispatch import ExecutiveCommandDispatcher
from qore.governance.executive_control import (
    AuthorizedExecutiveControlIntent,
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveControlAction,
    ExecutiveControlIntent,
    ExecutiveControlTarget,
    ExecutiveControlTargetKind,
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
    ExecutiveReplayBlockReason,
    ExecutiveReplayBlockedError,
    ExecutiveReplayClaimPort,
    ExecutiveReplayClaimReceipt,
    ExecutiveReplayClaimRequest,
    ExecutiveReplayClaimStatus,
    ExecutiveReplayFingerprint,
    ExecutiveReplayKey,
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


def _core() -> CoreApplication:
    result = bootstrap(Configuration(application_name="qore-mission04-closure"))
    assert isinstance(result, Success)
    return result.value


def _assertion(*, expires_at: datetime | None = None) -> AuthenticatedExecutivePrincipal:
    return AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(
            UUID("53000000-0000-0000-0000-000000000002")
        ),
        principal_id=_PRINCIPAL,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef("identity:closure-fixture"),
        issued_at=_NOW,
        expires_at=expires_at or _NOW + timedelta(minutes=30),
        correlation_id=_CORRELATION,
    )


def _grant(
    *actions: ExecutiveControlAction,
) -> ExecutiveAuthorityGrant:
    selected_actions = actions or (ExecutiveControlAction.PAUSE_SYSTEM,)
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("53000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v6"),
        allowed_actions=selected_actions,
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        reason="mission04 closure readiness",
    )


def _authority_request() -> ExecutiveAuthorityStateRequest:
    return ExecutiveAuthorityStateRequest(
        request_id=ExecutiveAuthorityStateRequestId(
            UUID("53000000-0000-0000-0000-000000000004")
        ),
        principal_id=_PRINCIPAL,
        requested_at=_NOW + timedelta(minutes=1, seconds=30),
        correlation_id=_CORRELATION,
    )


def _authority_snapshot(
    grant: ExecutiveAuthorityGrant,
    *,
    status: ExecutiveAuthorityStateStatus = ExecutiveAuthorityStateStatus.ACTIVE,
) -> ExecutiveAuthorityStateSnapshot:
    return ExecutiveAuthorityStateSnapshot(
        request_id=_authority_request().request_id,
        principal_id=_PRINCIPAL,
        status=status,
        observed_at=_NOW + timedelta(minutes=1, seconds=45),
        evidence_ref=ExecutiveAuthorityStateEvidenceRef(
            f"audit:authority/{status.value}"
        ),
        grant=grant,
        invalidated_at=(
            _NOW + timedelta(minutes=1, seconds=40)
            if status
            in {
                ExecutiveAuthorityStateStatus.REVOKED,
                ExecutiveAuthorityStateStatus.SUPERSEDED,
            }
            else None
        ),
        superseding_version=(
            ExecutiveAuthorityVersion("authority.v7")
            if status is ExecutiveAuthorityStateStatus.SUPERSEDED
            else None
        ),
    )


def _intent(
    action: ExecutiveControlAction = ExecutiveControlAction.PAUSE_SYSTEM,
    *,
    intent_id: UUID = UUID("53000000-0000-0000-0000-000000000005"),
    target: ExecutiveControlTarget | None = None,
) -> ExecutiveControlIntent:
    return ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(intent_id),
        principal_id=_PRINCIPAL,
        action=action,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
        reason="CEO governed closure fixture",
        target=target,
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
        status: ExecutiveControlReceiptStatus = ExecutiveControlReceiptStatus.APPLIED,
        error: ExecutivePortError | None = None,
    ) -> None:
        self.status = status
        self.error = error
        self.requests: list[AuthorizedExecutiveControlIntent] = []

    def apply(
        self,
        request: AuthorizedExecutiveControlIntent,
    ) -> Result[ExecutiveControlReceipt, ExecutivePortError]:
        self.requests.append(request)
        if self.error is not None:
            return Failure(self.error)
        reason_code = {
            ExecutiveControlReceiptStatus.APPLIED: "governance.applied",
            ExecutiveControlReceiptStatus.NO_CHANGE: "governance.no_change",
            ExecutiveControlReceiptStatus.BLOCKED: "governance.blocked",
            ExecutiveControlReceiptStatus.FAILED: "governance.failed",
        }[self.status]
        return build_executive_control_receipt(
            request,
            receipt_id=ExecutiveReceiptId(
                UUID("53000000-0000-0000-0000-000000000006")
            ),
            received_at=_NOW + timedelta(minutes=2, seconds=1),
            completed_at=_NOW + timedelta(minutes=2, seconds=2),
            status=self.status,
            reason_code=reason_code,
            evidence_refs=(ExecutiveEvidenceRef("audit:closure/command"),),
        )


class _StatefulReplayStore(ExecutiveReplayClaimPort):
    def __init__(self) -> None:
        self.requests: list[ExecutiveReplayClaimRequest] = []
        self.claimed: dict[ExecutiveReplayKey, ExecutiveReplayFingerprint] = {}

    def claim(
        self,
        request: ExecutiveReplayClaimRequest,
    ) -> Result[ExecutiveReplayClaimReceipt, ExecutiveReplayProtectionError]:
        self.requests.append(request)
        observed = self.claimed.get(request.key)
        if observed is None:
            self.claimed[request.key] = request.fingerprint
            observed = request.fingerprint
            status = ExecutiveReplayClaimStatus.ACQUIRED
        elif observed == request.fingerprint:
            status = ExecutiveReplayClaimStatus.DUPLICATE
        else:
            status = ExecutiveReplayClaimStatus.CONFLICT
        return build_executive_replay_claim_receipt(
            request,
            observed_fingerprint=observed,
            completed_at=request.requested_at + timedelta(microseconds=1),
            status=status,
        )


def _authorized(
    action: ExecutiveControlAction,
    *,
    intent_id: UUID = UUID("53000000-0000-0000-0000-000000000005"),
    grant: ExecutiveAuthorityGrant | None = None,
) -> AuthorizedExecutiveControlIntent:
    selected_grant = grant or _grant(action)
    return AuthorizedExecutiveControlIntent(
        intent=_intent(action, intent_id=intent_id),
        grant=selected_grant,
        authorized_at=_NOW + timedelta(minutes=2),
    )


def test_unauthenticated_request_stops_before_authority_and_dispatch() -> None:
    source = _AuthoritySource(_authority_snapshot(_grant()))
    command = _CommandPort()

    result = ExecutiveRequestGuard(source).authorize_control(
        cast(AuthenticatedExecutivePrincipal, object()),
        _intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=2),
    )

    assert isinstance(result, Failure)
    assert source.requests == []
    assert command.requests == []


def test_expired_authentication_stops_before_authority_and_dispatch() -> None:
    source = _AuthoritySource(_authority_snapshot(_grant()))
    command = _CommandPort()

    result = ExecutiveRequestGuard(source).authorize_control(
        _assertion(expires_at=_NOW + timedelta(minutes=1)),
        _intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveRequestGuardBlockedError)
    assert result.error.reason is ExecutiveRequestGuardReason.AUTHENTICATION_INVALID
    assert source.requests == []
    assert command.requests == []


def test_revoked_authority_stops_before_dispatch() -> None:
    grant = _grant()
    source = _AuthoritySource(
        _authority_snapshot(grant, status=ExecutiveAuthorityStateStatus.REVOKED)
    )
    command = _CommandPort()

    result = ExecutiveRequestGuard(source).authorize_control(
        _assertion(),
        _intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveRequestGuardBlockedError)
    assert result.error.reason is ExecutiveRequestGuardReason.AUTHORITY_NOT_ACTIVE
    assert source.requests == [_authority_request()]
    assert command.requests == []


def test_scoped_control_preserves_exact_target_and_calls_downstream_once() -> None:
    target = ExecutiveControlTarget(
        kind=ExecutiveControlTargetKind.MARKET,
        value="market:eurusd",
    )
    grant = _grant(ExecutiveControlAction.RESTRICT_MARKET)
    source = _AuthoritySource(_authority_snapshot(grant))
    intent = _intent(ExecutiveControlAction.RESTRICT_MARKET, target=target)
    authorized = ExecutiveRequestGuard(source).authorize_control(
        _assertion(),
        intent,
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(authorized, Success)
    port = _CommandPort()

    dispatched = ExecutiveCommandDispatcher(port).dispatch(authorized.value)

    assert isinstance(dispatched, Success)
    assert port.requests == [authorized.value]
    assert dispatched.value.target == target


def test_exact_duplicate_and_modified_replay_are_deterministic_and_fail_closed() -> None:
    intent_id = UUID("53000000-0000-0000-0000-000000000010")
    grant = _grant(
        ExecutiveControlAction.PAUSE_SYSTEM,
        ExecutiveControlAction.RESUME_SYSTEM,
    )
    original = _authorized(
        ExecutiveControlAction.PAUSE_SYSTEM,
        intent_id=intent_id,
        grant=grant,
    )
    modified = _authorized(
        ExecutiveControlAction.RESUME_SYSTEM,
        intent_id=intent_id,
        grant=grant,
    )
    original_claim = build_executive_control_replay_claim(
        original,
        requested_at=_NOW + timedelta(minutes=2, seconds=1),
    )
    modified_claim = build_executive_control_replay_claim(
        modified,
        requested_at=_NOW + timedelta(minutes=2, seconds=1),
    )
    assert isinstance(original_claim, Success)
    assert isinstance(modified_claim, Success)
    assert original_claim.value.key == modified_claim.value.key
    assert original_claim.value.fingerprint != modified_claim.value.fingerprint

    store = _StatefulReplayStore()
    protector = ExecutiveReplayProtector(store)
    first = protector.protect(original_claim.value)
    duplicate = protector.protect(original_claim.value)
    conflict = protector.protect(modified_claim.value)

    assert isinstance(first, Success)
    assert isinstance(duplicate, Failure)
    assert isinstance(duplicate.error, ExecutiveReplayBlockedError)
    assert duplicate.error.reason is ExecutiveReplayBlockReason.DUPLICATE
    assert isinstance(conflict, Failure)
    assert isinstance(conflict.error, ExecutiveReplayBlockedError)
    assert conflict.error.reason is ExecutiveReplayBlockReason.CONFLICT
    assert store.requests == [
        original_claim.value,
        original_claim.value,
        modified_claim.value,
    ]


def test_no_change_command_is_durable_no_action_evidence() -> None:
    assertion = _assertion()
    grant = _grant()
    source = _AuthoritySource(_authority_snapshot(grant))
    authorized = ExecutiveRequestGuard(source).authorize_control(
        assertion,
        _intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(authorized, Success)
    port = _CommandPort(status=ExecutiveControlReceiptStatus.NO_CHANGE)
    receipt = ExecutiveCommandDispatcher(port).dispatch(authorized.value)
    assert isinstance(receipt, Success)

    audit = build_executive_control_dispatch_audit_record(
        assertion,
        authorized.value,
        receipt=receipt.value,
        record_id=ExecutiveAuditEvidenceRecordId(
            UUID("53000000-0000-0000-0000-000000000011")
        ),
        outcome=ExecutiveAuditEvidenceOutcome.NO_ACTION,
        occurred_at=_NOW + timedelta(minutes=2, seconds=3),
        reason_code="command.no_action",
    )

    assert isinstance(audit, Success)
    assert audit.value.outcome is ExecutiveAuditEvidenceOutcome.NO_ACTION
    assert port.requests == [authorized.value]


def test_ambiguous_downstream_failure_is_contained_without_repeat() -> None:
    authorized = _authorized(ExecutiveControlAction.PAUSE_SYSTEM)
    port = _CommandPort(
        error=ExecutivePortValidationError("downstream unavailable")
    )

    dispatched = ExecutiveCommandDispatcher(port).dispatch(authorized)
    recovery = plan_executive_control_plane_recovery(
        ExecutiveControlPlaneOperation.COMMAND_DISPATCH,
        ExecutiveControlPlaneFailureKind.AMBIGUOUS_OUTCOME,
        recovery_id=ExecutiveControlPlaneRecoveryId(
            UUID("53000000-0000-0000-0000-000000000012")
        ),
        correlation_id=_CORRELATION,
        failed_at=_NOW + timedelta(minutes=2, seconds=2),
        planned_at=_NOW + timedelta(minutes=2, seconds=3),
    )

    assert isinstance(dispatched, Failure)
    assert port.requests == [authorized]
    assert isinstance(recovery, Success)
    assert (
        recovery.value.requirement
        is ExecutiveControlPlaneRecoveryRequirement.VERIFY_CONTROL_RECEIPT
    )
    assert recovery.value.automatic_retry_allowed is False
    assert recovery.value.automatic_redispatch_allowed is False


def test_external_control_plane_composition_preserves_core_runtime_identity() -> None:
    core = _core()
    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    grant = _grant()
    source = _AuthoritySource(_authority_snapshot(grant))
    authorized = ExecutiveRequestGuard(source).authorize_control(
        _assertion(),
        _intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(authorized, Success)
    claim = build_executive_control_replay_claim(
        authorized.value,
        requested_at=_NOW + timedelta(minutes=2, seconds=1),
    )
    assert isinstance(claim, Success)
    assert isinstance(
        ExecutiveReplayProtector(_StatefulReplayStore()).protect(claim.value),
        Success,
    )

    assert core.event_bus is event_bus
    assert core.runtime_plan == runtime_plan
    assert core.runtime_snapshot() == runtime_snapshot
    assert core.runtime_health() == runtime_health
