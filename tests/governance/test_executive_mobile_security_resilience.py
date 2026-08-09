from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_authentication import (
    AuthenticatedExecutivePrincipal,
    ExecutiveAuthenticationAssertionId,
    ExecutiveAuthenticationContextCode,
    ExecutiveAuthenticationMethodCode,
    ExecutiveIdentityBoundaryRef,
)
from qore.governance.executive_client_session import (
    ExecutiveClientDeviceRef,
    ExecutiveClientSession,
    ExecutiveClientSessionBinding,
    ExecutiveClientSessionId,
    ExecutiveClientSessionStatus,
)
from qore.governance.executive_client_surface import (
    ExecutiveClientPlatform,
    ExecutiveClientSurface,
    ExecutiveClientSurfaceId,
    ExecutiveClientVersion,
    build_executive_client_surface,
)
from qore.governance.executive_control import (
    AuthorizedExecutiveReadRequest,
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveControlAction,
    ExecutiveGrantId,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadRequest,
    ExecutiveReadRequestId,
    ExecutiveReadScope,
)
from qore.governance.executive_control_plane_resilience import (
    ExecutiveControlPlaneRecoveryRequirement,
)
from qore.governance.executive_governance_ux import ExecutiveGovernanceUxPhase
from qore.governance.executive_mobile_security_resilience import (
    ExecutiveMobileConnectivityObservation,
    ExecutiveMobileConnectivityStatus,
    ExecutiveMobileGovernanceActivity,
    ExecutiveMobileSecretBoundaryAssertion,
    ExecutiveMobileSecretBoundaryRef,
    ExecutiveMobileSecretBoundaryStatus,
    ExecutiveMobileSecurityAssessmentId,
    ExecutiveMobileSecurityDisposition,
    ExecutiveMobileSecurityReason,
    ExecutiveMobileSecurityResilienceValidationError,
    assess_executive_mobile_security,
)
from qore.governance.executive_ports import (
    ExecutiveReadDelivery,
    ExecutiveReadReceiptStatus,
    ExecutiveReceiptId,
    build_executive_read_delivery,
    build_executive_read_receipt,
)
from qore.governance.executive_read_models import (
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveSourceFreshness,
)
from qore.governance.executive_state_sync import (
    ExecutiveClientStateSnapshot,
    ExecutiveClientStateSnapshotId,
    ExecutiveClientStateStatus,
    ExecutiveClientStateVersion,
    ExecutiveClientStateView,
    build_executive_client_absent_state,
    evaluate_executive_client_state_snapshot,
)
from qore.governance.executive_transport_envelope import ExecutiveTransportMessageKind
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 20, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("63000000-0000-0000-0000-000000000001"))
_SURFACE_ID = ExecutiveClientSurfaceId(
    UUID("63000000-0000-0000-0000-000000000002")
)
_ASSERTION_ID = ExecutiveAuthenticationAssertionId(
    UUID("63000000-0000-0000-0000-000000000003")
)


@dataclass(frozen=True, slots=True)
class _GovernanceProjection:
    metadata: ExecutiveProjectionMetadata

    def logical_values(self) -> tuple[object, ...]:
        return (self.metadata.logical_values(),)


def _surface(
    platform: ExecutiveClientPlatform = ExecutiveClientPlatform.IOS,
) -> ExecutiveClientSurface:
    result = build_executive_client_surface(
        surface_id=_SURFACE_ID,
        platform=platform,
        client_version=ExecutiveClientVersion("mobile-security.v1"),
        allowed_message_kinds=(
            ExecutiveTransportMessageKind.CONTROL,
            ExecutiveTransportMessageKind.READ,
        ),
    )
    assert isinstance(result, Success)
    return result.value


def _binding(
    *,
    platform: ExecutiveClientPlatform = ExecutiveClientPlatform.IOS,
    expires_at: datetime | None = None,
) -> ExecutiveClientSessionBinding:
    surface = _surface(platform)
    assertion = AuthenticatedExecutivePrincipal(
        assertion_id=_ASSERTION_ID,
        principal_id=_PRINCIPAL,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef("identity:mobile"),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        correlation_id=_CORRELATION,
    )
    session = ExecutiveClientSession(
        session_id=ExecutiveClientSessionId(
            UUID("63000000-0000-0000-0000-000000000004")
        ),
        surface_id=surface.surface_id,
        device_ref=ExecutiveClientDeviceRef("device:mobile-primary"),
        principal_id=_PRINCIPAL,
        authentication_assertion_id=_ASSERTION_ID,
        status=ExecutiveClientSessionStatus.ACTIVE,
        established_at=_NOW + timedelta(seconds=1),
        expires_at=expires_at or _NOW + timedelta(minutes=20),
        correlation_id=_CORRELATION,
    )
    return ExecutiveClientSessionBinding(
        session=session,
        surface=surface,
        authenticated_principal=assertion,
        evaluated_at=_NOW + timedelta(minutes=2),
    )


def _secret(
    status: ExecutiveMobileSecretBoundaryStatus = ExecutiveMobileSecretBoundaryStatus.AVAILABLE,
) -> ExecutiveMobileSecretBoundaryAssertion:
    return ExecutiveMobileSecretBoundaryAssertion(
        surface_id=_SURFACE_ID,
        boundary_ref=ExecutiveMobileSecretBoundaryRef("secure-store:mobile-primary"),
        status=status,
        observed_at=_NOW + timedelta(minutes=2),
    )


def _connectivity(
    status: ExecutiveMobileConnectivityStatus = ExecutiveMobileConnectivityStatus.ONLINE,
) -> ExecutiveMobileConnectivityObservation:
    return ExecutiveMobileConnectivityObservation(
        surface_id=_SURFACE_ID,
        status=status,
        observed_at=_NOW + timedelta(minutes=2),
    )


def _authorized_governance_read() -> AuthorizedExecutiveReadRequest:
    grant = ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID(int=5)),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v5"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=20),
        reason="mobile governance freshness",
    )
    request = ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(UUID(int=6)),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.GOVERNANCE,
        requested_at=_NOW + timedelta(seconds=1),
        correlation_id=_CORRELATION,
    )
    return AuthorizedExecutiveReadRequest(
        request=request,
        grant=grant,
        authorized_at=_NOW + timedelta(seconds=2),
    )


def _governance_delivery() -> ExecutiveReadDelivery:
    authorized = _authorized_governance_read()
    projection = _GovernanceProjection(
        metadata=ExecutiveProjectionMetadata(
            projection_id=ExecutiveProjectionId(UUID(int=7)),
            projection_version=ExecutiveProjectionVersion("governance.v1"),
            scope=ExecutiveReadScope.GOVERNANCE,
            source_observed_at=_NOW,
            projected_at=_NOW + timedelta(seconds=3),
            freshness=ExecutiveSourceFreshness.FRESH,
        )
    )
    receipt_result = build_executive_read_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(UUID(int=8)),
        received_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=4),
        status=ExecutiveReadReceiptStatus.SERVED,
        reason_code="read.served",
    )
    assert isinstance(receipt_result, Success)
    delivery_result = build_executive_read_delivery(
        authorized,
        projection=projection,
        receipt=receipt_result.value,
    )
    assert isinstance(delivery_result, Success)
    return delivery_result.value


def _current_governance_state() -> ExecutiveClientStateView:
    snapshot = ExecutiveClientStateSnapshot(
        snapshot_id=ExecutiveClientStateSnapshotId(UUID(int=9)),
        version=ExecutiveClientStateVersion(3),
        delivery=_governance_delivery(),
        received_at=_NOW + timedelta(seconds=5),
        fresh_until=_NOW + timedelta(minutes=10),
    )
    result = evaluate_executive_client_state_snapshot(
        snapshot,
        evaluated_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(result, Success)
    return result.value


def _absent_governance_state(
    status: ExecutiveClientStateStatus,
) -> ExecutiveClientStateView:
    result = build_executive_client_absent_state(
        status=status,
        scope=ExecutiveReadScope.GOVERNANCE,
        observed_at=_NOW + timedelta(minutes=2),
        reason_code=f"governance.{status.value}",
    )
    assert isinstance(result, Success)
    return result.value


def test_mobile_ready_requires_current_session_secret_connectivity_and_state() -> None:
    result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=10)),
        session_binding=_binding(),
        secret_boundary=_secret(),
        connectivity=_connectivity(),
        governance_state=_current_governance_state(),
        assessed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Success)
    assessment = result.value
    assert assessment.disposition is ExecutiveMobileSecurityDisposition.READY
    assert assessment.reason is ExecutiveMobileSecurityReason.READY
    assert assessment.read_request_eligible is True
    assert assessment.control_request_eligible is True
    assert assessment.automatic_retry_allowed is False
    assert assessment.automatic_redispatch_allowed is False
    assert assessment.logical_values() == assessment.logical_values()


@pytest.mark.parametrize(
    ("state_status", "reason"),
    (
        (
            ExecutiveClientStateStatus.UNAVAILABLE,
            ExecutiveMobileSecurityReason.GOVERNANCE_UNAVAILABLE,
        ),
        (
            ExecutiveClientStateStatus.UNKNOWN,
            ExecutiveMobileSecurityReason.GOVERNANCE_UNKNOWN,
        ),
    ),
)
def test_missing_governance_state_is_read_only_not_command_ready(
    state_status: ExecutiveClientStateStatus,
    reason: ExecutiveMobileSecurityReason,
) -> None:
    result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=11)),
        session_binding=_binding(platform=ExecutiveClientPlatform.ANDROID),
        secret_boundary=_secret(),
        connectivity=_connectivity(),
        governance_state=_absent_governance_state(state_status),
        assessed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Success)
    assert result.value.disposition is ExecutiveMobileSecurityDisposition.READ_ONLY
    assert result.value.reason is reason
    assert result.value.read_request_eligible is True
    assert result.value.control_request_eligible is False


def test_offline_mobile_is_local_read_only_and_cannot_issue_requests() -> None:
    result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=12)),
        session_binding=_binding(),
        secret_boundary=_secret(),
        connectivity=_connectivity(ExecutiveMobileConnectivityStatus.OFFLINE),
        governance_state=_current_governance_state(),
        assessed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Success)
    assert result.value.disposition is ExecutiveMobileSecurityDisposition.READ_ONLY
    assert result.value.reason is ExecutiveMobileSecurityReason.OFFLINE
    assert result.value.read_request_eligible is False
    assert result.value.control_request_eligible is False


def test_unavailable_secret_boundary_blocks_mobile_requests() -> None:
    result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=13)),
        session_binding=_binding(),
        secret_boundary=_secret(ExecutiveMobileSecretBoundaryStatus.UNAVAILABLE),
        connectivity=_connectivity(),
        governance_state=_current_governance_state(),
        assessed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Success)
    assert result.value.disposition is ExecutiveMobileSecurityDisposition.BLOCKED
    assert result.value.reason is ExecutiveMobileSecurityReason.SECURE_BOUNDARY_UNAVAILABLE
    assert result.value.read_request_eligible is False
    assert result.value.control_request_eligible is False


def test_expired_session_fails_closed_without_mutating_session() -> None:
    binding = _binding(expires_at=_NOW + timedelta(minutes=2, seconds=30))
    result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=14)),
        session_binding=binding,
        secret_boundary=_secret(),
        connectivity=_connectivity(),
        governance_state=_current_governance_state(),
        assessed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Success)
    assert result.value.session_current is False
    assert result.value.disposition is ExecutiveMobileSecurityDisposition.BLOCKED
    assert result.value.reason is ExecutiveMobileSecurityReason.SESSION_INVALID
    assert binding.session.status is ExecutiveClientSessionStatus.ACTIVE


def test_stale_snapshot_is_re_evaluated_at_assessment_time() -> None:
    current = _current_governance_state()
    assert current.snapshot is not None
    result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=15)),
        session_binding=_binding(),
        secret_boundary=_secret(),
        connectivity=_connectivity(),
        governance_state=current,
        assessed_at=current.snapshot.fresh_until + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.governance_state.status is ExecutiveClientStateStatus.STALE
    assert result.value.reason is ExecutiveMobileSecurityReason.GOVERNANCE_STALE
    assert result.value.control_request_eligible is False


def test_unknown_governance_outcome_requires_receipt_verification_and_no_redispatch() -> None:
    base_result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=16)),
        session_binding=_binding(),
        secret_boundary=_secret(),
        connectivity=_connectivity(),
        governance_state=_current_governance_state(),
        assessed_at=_NOW + timedelta(minutes=3),
    )
    assert isinstance(base_result, Success)
    activity = ExecutiveMobileGovernanceActivity(
        phase=ExecutiveGovernanceUxPhase.OUTCOME_UNKNOWN,
        intent_id=ExecutiveIntentId(UUID(int=17)),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v5"),
        correlation_id=_CORRELATION,
        observed_at=_NOW + timedelta(minutes=2, seconds=30),
    )
    assessment = replace(
        base_result.value,
        disposition=ExecutiveMobileSecurityDisposition.RECOVERY_REQUIRED,
        reason=ExecutiveMobileSecurityReason.OUTCOME_UNKNOWN,
        governance_activity=activity,
        recovery_requirement=ExecutiveControlPlaneRecoveryRequirement.VERIFY_CONTROL_RECEIPT,
    )

    assert assessment.control_request_eligible is False
    assert assessment.automatic_retry_allowed is False
    assert assessment.automatic_redispatch_allowed is False
    assert (
        assessment.recovery_requirement
        is ExecutiveControlPlaneRecoveryRequirement.VERIFY_CONTROL_RECEIPT
    )


def test_pending_governance_activity_blocks_new_control_request() -> None:
    base_result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=18)),
        session_binding=_binding(),
        secret_boundary=_secret(),
        connectivity=_connectivity(),
        governance_state=_current_governance_state(),
        assessed_at=_NOW + timedelta(minutes=3),
    )
    assert isinstance(base_result, Success)
    activity = ExecutiveMobileGovernanceActivity(
        phase=ExecutiveGovernanceUxPhase.PENDING,
        intent_id=ExecutiveIntentId(UUID(int=19)),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v5"),
        correlation_id=_CORRELATION,
        observed_at=_NOW + timedelta(minutes=2, seconds=30),
    )
    assessment = replace(
        base_result.value,
        disposition=ExecutiveMobileSecurityDisposition.BLOCKED,
        reason=ExecutiveMobileSecurityReason.COMMAND_PENDING,
        governance_activity=activity,
    )

    assert assessment.control_request_eligible is False
    assert assessment.read_request_eligible is True


def test_secure_boundary_reference_rejects_secret_material() -> None:
    with pytest.raises(ExecutiveMobileSecurityResilienceValidationError):
        ExecutiveMobileSecretBoundaryRef("secure-store:token=abc")


def test_desktop_surface_is_rejected_by_mobile_security_assessment() -> None:
    result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=20)),
        session_binding=_binding(platform=ExecutiveClientPlatform.DESKTOP),
        secret_boundary=_secret(),
        connectivity=_connectivity(),
        governance_state=_current_governance_state(),
        assessed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Failure)


def test_mobile_security_contract_has_no_native_secret_or_execution_surface() -> None:
    result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=21)),
        session_binding=_binding(),
        secret_boundary=_secret(),
        connectivity=_connectivity(),
        governance_state=_current_governance_state(),
        assessed_at=_NOW + timedelta(minutes=3),
    )
    assert isinstance(result, Success)
    assessment = result.value

    assert not hasattr(assessment, "token")
    assert not hasattr(assessment, "password")
    assert not hasattr(assessment, "keychain")
    assert not hasattr(assessment, "keystore")
    assert not hasattr(assessment, "retry")
    assert not hasattr(assessment, "redispatch")
    assert not hasattr(assessment, "submit_order")
    assert not hasattr(assessment, "buy")
    assert not hasattr(assessment, "sell")
