from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_audit_evidence import (
    ExecutiveAuditEvidenceError,
    ExecutiveAuditEvidenceOutcome,
    ExecutiveAuditEvidencePort,
    ExecutiveAuditEvidenceRecord,
    ExecutiveAuditEvidenceRecordId,
    ExecutiveAuditEvidenceStage,
    ExecutiveAuditEvidenceValidationError,
    ExecutiveAuditSourceKind,
    ExecutiveAuditSourceRef,
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
    ExecutiveAuthorityStateEvidenceRef,
    ExecutiveAuthorityStateRequest,
    ExecutiveAuthorityStateRequestId,
    ExecutiveAuthorityStateSnapshot,
    ExecutiveAuthorityStateStatus,
)
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
    ExecutiveGovernanceMutationId,
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
    ExecutiveReadDelivery,
    ExecutiveReadProjection,
    ExecutiveReadReceiptStatus,
    ExecutiveReceiptId,
    build_executive_control_receipt,
    build_executive_read_delivery,
    build_executive_read_receipt,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 5, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("47000000-0000-0000-0000-000000000001"))


def _record_id(value: int = 90) -> ExecutiveAuditEvidenceRecordId:
    return ExecutiveAuditEvidenceRecordId(
        UUID(f"47000000-0000-0000-0000-{value:012d}")
    )


def _assertion() -> AuthenticatedExecutivePrincipal:
    return AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(
            UUID("47000000-0000-0000-0000-000000000002")
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
        grant_id=ExecutiveGrantId(UUID("47000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v2"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        reason="mission04 audit evidence",
    )


def _authority_request() -> ExecutiveAuthorityStateRequest:
    return ExecutiveAuthorityStateRequest(
        request_id=ExecutiveAuthorityStateRequestId(
            UUID("47000000-0000-0000-0000-000000000004")
        ),
        principal_id=_PRINCIPAL,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
    )


def _authority_snapshot() -> ExecutiveAuthorityStateSnapshot:
    request = _authority_request()
    return ExecutiveAuthorityStateSnapshot(
        request_id=request.request_id,
        principal_id=_PRINCIPAL,
        status=ExecutiveAuthorityStateStatus.ACTIVE,
        observed_at=_NOW + timedelta(minutes=2),
        evidence_ref=ExecutiveAuthorityStateEvidenceRef("audit:authority/current"),
        grant=_grant(),
    )


def _authorized_control() -> AuthorizedExecutiveControlIntent:
    intent = ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("47000000-0000-0000-0000-000000000005")),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=2),
        correlation_id=_CORRELATION,
        reason="CEO requests governed pause",
    )
    return AuthorizedExecutiveControlIntent(
        intent=intent,
        grant=_grant(),
        authorized_at=_NOW + timedelta(minutes=3),
    )


def _control_receipt(
    authorized: AuthorizedExecutiveControlIntent,
    *,
    status: ExecutiveControlReceiptStatus = ExecutiveControlReceiptStatus.APPLIED,
) -> ExecutiveControlReceipt:
    result = build_executive_control_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(
            UUID("47000000-0000-0000-0000-000000000006")
        ),
        received_at=_NOW + timedelta(minutes=3, seconds=1),
        completed_at=_NOW + timedelta(minutes=3, seconds=2),
        status=status,
        reason_code=f"governance.{status.value}",
        evidence_refs=(ExecutiveEvidenceRef("audit:control/receipt"),),
    )
    assert isinstance(result, Success)
    return result.value


def _authorized_read() -> AuthorizedExecutiveReadRequest:
    request = ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(
            UUID("47000000-0000-0000-0000-000000000007")
        ),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.GOVERNANCE,
        requested_at=_NOW + timedelta(minutes=2),
        correlation_id=_CORRELATION,
    )
    return AuthorizedExecutiveReadRequest(
        request=request,
        grant=_grant(),
        authorized_at=_NOW + timedelta(minutes=3),
    )


@dataclass(frozen=True, slots=True)
class _ProjectionMetadata:
    scope: ExecutiveReadScope
    projected_at: datetime


@dataclass(frozen=True, slots=True)
class _Projection:
    metadata: _ProjectionMetadata

    def logical_values(self) -> tuple[object, ...]:
        return (self.metadata.scope.value, self.metadata.projected_at.isoformat())


def _read_delivery(authorized: AuthorizedExecutiveReadRequest) -> ExecutiveReadDelivery:
    receipt_result = build_executive_read_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(
            UUID("47000000-0000-0000-0000-000000000008")
        ),
        received_at=_NOW + timedelta(minutes=3, seconds=1),
        completed_at=_NOW + timedelta(minutes=3, seconds=3),
        status=ExecutiveReadReceiptStatus.SERVED,
        reason_code="read.served",
        evidence_refs=(ExecutiveEvidenceRef("audit:read/receipt"),),
    )
    assert isinstance(receipt_result, Success)
    projection: ExecutiveReadProjection = _Projection(
        metadata=_ProjectionMetadata(
            scope=ExecutiveReadScope.GOVERNANCE,
            projected_at=_NOW + timedelta(minutes=3, seconds=2),
        )
    )
    delivery_result = build_executive_read_delivery(
        authorized,
        projection=projection,
        receipt=receipt_result.value,
    )
    assert isinstance(delivery_result, Success)
    return delivery_result.value


def _state(
    *,
    snapshot_id: UUID,
    version: str,
    observed_at: datetime,
    system: ExecutiveSystemRunState,
) -> ExecutiveGovernanceStateSnapshot:
    return ExecutiveGovernanceStateSnapshot(
        snapshot_id=ExecutiveGovernanceStateSnapshotId(snapshot_id),
        state_version=ExecutiveGovernanceStateVersion(version),
        observed_at=observed_at,
        system_run_state=system,
        new_trading_state=ExecutiveNewTradingState.PERMITTED,
        market_restrictions=(),
        account_restrictions=(),
    )


def _mutation_request() -> ExecutiveGovernanceMutationRequest:
    authorized = _authorized_control()
    expected = _state(
        snapshot_id=UUID("47000000-0000-0000-0000-000000000010"),
        version="state.v1",
        observed_at=_NOW + timedelta(minutes=3),
        system=ExecutiveSystemRunState.ACTIVE,
    )
    next_state = _state(
        snapshot_id=UUID("47000000-0000-0000-0000-000000000011"),
        version="state.v2",
        observed_at=_NOW + timedelta(minutes=4),
        system=ExecutiveSystemRunState.PAUSED,
    )
    return ExecutiveGovernanceMutationRequest(
        mutation_id=ExecutiveGovernanceMutationId(
            UUID("47000000-0000-0000-0000-000000000012")
        ),
        authorized=authorized,
        expected_state=expected,
        next_state=next_state,
        source_receipt_id=ExecutiveReceiptId(
            UUID("47000000-0000-0000-0000-000000000006")
        ),
        requested_at=_NOW + timedelta(minutes=3, seconds=1),
    )


class _FakeAuditSink:
    def __init__(self) -> None:
        self.records: list[ExecutiveAuditEvidenceRecord] = []

    def append(
        self,
        record: ExecutiveAuditEvidenceRecord,
    ) -> Result[ExecutiveAuditEvidenceRecord, ExecutiveAuditEvidenceError]:
        self.records.append(record)
        return Success(record)


def test_record_is_immutable_deterministic_and_secret_free() -> None:
    record = ExecutiveAuditEvidenceRecord(
        record_id=_record_id(),
        stage=ExecutiveAuditEvidenceStage.AUTHENTICATION,
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        principal_id=_PRINCIPAL,
        correlation_id=_CORRELATION,
        occurred_at=_NOW + timedelta(minutes=1),
        reason_code="authentication.accepted",
        source_refs=(
            ExecutiveAuditSourceRef(
                ExecutiveAuditSourceKind.AUTHORITY_STATE_REQUEST,
                "47000000-0000-0000-0000-000000000004",
            ),
            ExecutiveAuditSourceRef(
                ExecutiveAuditSourceKind.AUTHENTICATION_ASSERTION,
                "47000000-0000-0000-0000-000000000002",
            ),
        ),
        evidence_refs=(
            ExecutiveEvidenceRef("audit:z"),
            ExecutiveEvidenceRef("audit:a"),
        ),
    )

    assert record.source_refs[0].kind is ExecutiveAuditSourceKind.AUTHENTICATION_ASSERTION
    assert tuple(item.value for item in record.evidence_refs) == ("audit:a", "audit:z")
    assert record.logical_values() == record.logical_values()
    assert "password" not in repr(record.logical_values()).lower()
    assert "token" not in repr(record.logical_values()).lower()
    with pytest.raises(FrozenInstanceError):
        record.__setattr__("reason_code", "changed")


def test_record_rejects_unsafe_or_ambiguous_values() -> None:
    source = ExecutiveAuditSourceRef(
        ExecutiveAuditSourceKind.AUTHENTICATION_ASSERTION,
        "47000000-0000-0000-0000-000000000002",
    )
    with pytest.raises(ExecutiveAuditEvidenceValidationError):
        ExecutiveAuditEvidenceRecordId(cast(UUID, "not-a-uuid"))
    with pytest.raises(ExecutiveAuditEvidenceValidationError):
        ExecutiveAuditSourceRef(
            ExecutiveAuditSourceKind.AUTHENTICATION_ASSERTION,
            "identity:token/private",
        )
    with pytest.raises(ExecutiveAuditEvidenceValidationError):
        ExecutiveAuditEvidenceRecord(
            record_id=_record_id(),
            stage=ExecutiveAuditEvidenceStage.AUTHENTICATION,
            outcome=ExecutiveAuditEvidenceOutcome.FAILED,
            principal_id=_PRINCIPAL,
            correlation_id=_CORRELATION,
            occurred_at=datetime(2026, 8, 9, 5, 1),
            reason_code="authentication.failed",
            source_refs=(source,),
        )
    with pytest.raises(ExecutiveAuditEvidenceValidationError):
        ExecutiveAuditEvidenceRecord(
            record_id=_record_id(),
            stage=ExecutiveAuditEvidenceStage.AUTHENTICATION,
            outcome=ExecutiveAuditEvidenceOutcome.FAILED,
            principal_id=_PRINCIPAL,
            correlation_id=_CORRELATION,
            occurred_at=_NOW,
            reason_code="token",
            source_refs=(source,),
        )
    with pytest.raises(ExecutiveAuditEvidenceValidationError):
        ExecutiveAuditEvidenceRecord(
            record_id=_record_id(),
            stage=ExecutiveAuditEvidenceStage.AUTHENTICATION,
            outcome=ExecutiveAuditEvidenceOutcome.FAILED,
            principal_id=_PRINCIPAL,
            correlation_id=_CORRELATION,
            occurred_at=_NOW,
            reason_code="authentication.failed",
            source_refs=(source, source),
        )


def test_authentication_builder_links_exact_assertion() -> None:
    assertion = _assertion()
    result = build_executive_authentication_audit_record(
        assertion,
        record_id=_record_id(91),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(seconds=1),
        reason_code="authentication.accepted",
    )

    assert isinstance(result, Success)
    record = result.value
    assert record.principal_id == assertion.principal_id
    assert record.correlation_id == assertion.correlation_id
    assert record.authority_version is None
    assert record.source_refs == (
        ExecutiveAuditSourceRef(
            ExecutiveAuditSourceKind.AUTHENTICATION_ASSERTION,
            str(assertion.assertion_id.value),
        ),
    )


def test_authentication_builder_rejects_pre_assertion_audit_time() -> None:
    result = build_executive_authentication_audit_record(
        _assertion(),
        record_id=_record_id(92),
        outcome=ExecutiveAuditEvidenceOutcome.BLOCKED,
        occurred_at=_NOW - timedelta(microseconds=1),
        reason_code="authentication.blocked",
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveAuditEvidenceValidationError)


def test_authority_builder_links_current_state_and_authority_version() -> None:
    result = build_executive_authority_audit_record(
        _assertion(),
        _authority_request(),
        snapshot=_authority_snapshot(),
        record_id=_record_id(93),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(minutes=2, seconds=1),
        reason_code="authority.active",
        evidence_refs=(ExecutiveEvidenceRef("audit:authority/request"),),
    )

    assert isinstance(result, Success)
    record = result.value
    assert record.stage is ExecutiveAuditEvidenceStage.AUTHORITY
    assert record.authority_version == ExecutiveAuthorityVersion("authority.v2")
    assert {item.value for item in record.evidence_refs} == {
        "audit:authority/current",
        "audit:authority/request",
    }
    assert any(
        item.kind is ExecutiveAuditSourceKind.AUTHORITY_STATE_EVIDENCE
        for item in record.source_refs
    )


def test_authority_builder_fails_closed_on_missing_or_mismatched_state() -> None:
    missing = build_executive_authority_audit_record(
        _assertion(),
        _authority_request(),
        snapshot=None,
        record_id=_record_id(94),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(minutes=2),
        reason_code="authority.active",
    )
    wrong_request = replace(
        _authority_request(),
        request_id=ExecutiveAuthorityStateRequestId(
            UUID("47000000-0000-0000-0000-000000000099")
        ),
    )
    mismatched = build_executive_authority_audit_record(
        _assertion(),
        wrong_request,
        snapshot=_authority_snapshot(),
        record_id=_record_id(95),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(minutes=2, seconds=1),
        reason_code="authority.active",
    )

    assert isinstance(missing, Failure)
    assert isinstance(mismatched, Failure)


@pytest.mark.parametrize(
    ("status", "outcome"),
    [
        (ExecutiveControlReceiptStatus.APPLIED, ExecutiveAuditEvidenceOutcome.SUCCEEDED),
        (ExecutiveControlReceiptStatus.NO_CHANGE, ExecutiveAuditEvidenceOutcome.NO_ACTION),
        (ExecutiveControlReceiptStatus.BLOCKED, ExecutiveAuditEvidenceOutcome.BLOCKED),
        (ExecutiveControlReceiptStatus.FAILED, ExecutiveAuditEvidenceOutcome.FAILED),
    ],
)
def test_control_dispatch_builder_preserves_all_receipt_outcomes(
    status: ExecutiveControlReceiptStatus,
    outcome: ExecutiveAuditEvidenceOutcome,
) -> None:
    authorized = _authorized_control()
    receipt = _control_receipt(authorized, status=status)

    result = build_executive_control_dispatch_audit_record(
        _assertion(),
        authorized,
        receipt=receipt,
        record_id=_record_id(96),
        outcome=outcome,
        occurred_at=_NOW + timedelta(minutes=4),
        reason_code="dispatch.completed",
    )

    assert isinstance(result, Success)
    assert result.value.outcome is outcome
    assert result.value.authority_version == authorized.grant.authority_version
    assert ExecutiveEvidenceRef("audit:control/receipt") in result.value.evidence_refs
    assert any(
        item.kind is ExecutiveAuditSourceKind.CONTROL_RECEIPT
        for item in result.value.source_refs
    )


def test_control_dispatch_without_receipt_can_only_be_blocked_or_failed() -> None:
    authorized = _authorized_control()
    invalid = build_executive_control_dispatch_audit_record(
        _assertion(),
        authorized,
        receipt=None,
        record_id=_record_id(97),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(minutes=4),
        reason_code="dispatch.completed",
    )
    failed = build_executive_control_dispatch_audit_record(
        _assertion(),
        authorized,
        receipt=None,
        record_id=_record_id(98),
        outcome=ExecutiveAuditEvidenceOutcome.FAILED,
        occurred_at=_NOW + timedelta(minutes=4),
        reason_code="dispatch.downstream_failed",
    )

    assert isinstance(invalid, Failure)
    assert isinstance(failed, Success)


def test_read_dispatch_builder_links_delivery_without_storing_projection_payload() -> None:
    authorized = _authorized_read()
    delivery = _read_delivery(authorized)

    result = build_executive_read_dispatch_audit_record(
        _assertion(),
        authorized,
        delivery=delivery,
        record_id=_record_id(99),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(minutes=4),
        reason_code="read.served",
    )

    assert isinstance(result, Success)
    kinds = {item.kind for item in result.value.source_refs}
    assert ExecutiveAuditSourceKind.READ_DELIVERY in kinds
    assert ExecutiveAuditSourceKind.READ_RECEIPT in kinds
    assert ExecutiveEvidenceRef("audit:read/receipt") in result.value.evidence_refs
    assert not hasattr(result.value, "projection")


def test_read_dispatch_without_delivery_fails_closed_for_success() -> None:
    result = build_executive_read_dispatch_audit_record(
        _assertion(),
        _authorized_read(),
        delivery=None,
        record_id=_record_id(100),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(minutes=4),
        reason_code="read.served",
    )

    assert isinstance(result, Failure)


def test_governance_mutation_builder_links_request_receipt_and_snapshots() -> None:
    request = _mutation_request()
    mutation_result = build_executive_governance_mutation_receipt(
        request,
        observed_snapshot_id=request.next_state.snapshot_id,
        observed_state_version=request.next_state.state_version,
        completed_at=_NOW + timedelta(minutes=4, seconds=1),
        status=ExecutiveGovernanceMutationStatus.APPLIED,
    )
    assert isinstance(mutation_result, Success)
    control_receipt = _control_receipt(request.authorized)

    result = build_executive_governance_mutation_audit_record(
        _assertion(),
        request,
        receipt=mutation_result.value,
        control_receipt=control_receipt,
        record_id=_record_id(101),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(minutes=5),
        reason_code="governance.mutation_applied",
    )

    assert isinstance(result, Success)
    kinds = {item.kind for item in result.value.source_refs}
    assert ExecutiveAuditSourceKind.GOVERNANCE_MUTATION in kinds
    assert ExecutiveAuditSourceKind.GOVERNANCE_MUTATION_RECEIPT in kinds
    assert ExecutiveAuditSourceKind.GOVERNANCE_EXPECTED_SNAPSHOT in kinds
    assert ExecutiveAuditSourceKind.GOVERNANCE_REQUESTED_SNAPSHOT in kinds
    assert ExecutiveAuditSourceKind.GOVERNANCE_OBSERVED_SNAPSHOT in kinds
    assert ExecutiveEvidenceRef("audit:control/receipt") in result.value.evidence_refs


def test_governance_mutation_conflict_is_auditable_as_blocked() -> None:
    request = _mutation_request()
    conflict_result = build_executive_governance_mutation_receipt(
        request,
        observed_snapshot_id=ExecutiveGovernanceStateSnapshotId(
            UUID("47000000-0000-0000-0000-000000000013")
        ),
        observed_state_version=ExecutiveGovernanceStateVersion("state.v3"),
        completed_at=_NOW + timedelta(minutes=4, seconds=1),
        status=ExecutiveGovernanceMutationStatus.CONFLICT,
    )
    assert isinstance(conflict_result, Success)

    result = build_executive_governance_mutation_audit_record(
        _assertion(),
        request,
        receipt=conflict_result.value,
        control_receipt=None,
        record_id=_record_id(102),
        outcome=ExecutiveAuditEvidenceOutcome.BLOCKED,
        occurred_at=_NOW + timedelta(minutes=5),
        reason_code="governance.mutation_conflict",
    )

    assert isinstance(result, Success)
    assert result.value.outcome is ExecutiveAuditEvidenceOutcome.BLOCKED


def test_audit_port_is_structural_and_append_only_at_the_boundary() -> None:
    result = build_executive_authentication_audit_record(
        _assertion(),
        record_id=_record_id(103),
        outcome=ExecutiveAuditEvidenceOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(seconds=1),
        reason_code="authentication.accepted",
    )
    assert isinstance(result, Success)
    sink: ExecutiveAuditEvidencePort = _FakeAuditSink()

    appended = sink.append(result.value)

    assert isinstance(appended, Success)
    assert appended.value is result.value
