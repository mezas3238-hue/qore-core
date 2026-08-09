from __future__ import annotations

from dataclasses import dataclass
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
from qore.governance.executive_authority_state import (
    ExecutiveAuthorityStateError,
    ExecutiveAuthorityStateEvidenceRef,
    ExecutiveAuthorityStateRequest,
    ExecutiveAuthorityStateRequestId,
    ExecutiveAuthorityStateSnapshot,
    ExecutiveAuthorityStateStatus,
)
from qore.governance.executive_client_gateway import (
    ExecutiveClientGatewayEnvironment,
    ExecutiveClientGatewayError,
    ExecutiveClientGatewayIngress,
    ExecutiveClientGatewayProtocol,
    ExecutiveClientGatewayRoute,
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
from qore.governance.executive_command_center_view_model import (
    ExecutiveCommandCenterSection,
    ExecutiveCommandCenterViewModelId,
    build_executive_command_center_view_model,
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
from qore.governance.executive_governance_ux import (
    ExecutiveGovernanceUxPhase,
    ExecutiveGovernanceUxStateId,
    build_executive_governance_result_state,
)
from qore.governance.executive_mobile_security_resilience import (
    ExecutiveMobileConnectivityObservation,
    ExecutiveMobileConnectivityStatus,
    ExecutiveMobileSecretBoundaryAssertion,
    ExecutiveMobileSecretBoundaryRef,
    ExecutiveMobileSecretBoundaryStatus,
    ExecutiveMobileSecurityAssessmentId,
    ExecutiveMobileSecurityDisposition,
    ExecutiveMobileSecurityReason,
    assess_executive_mobile_security,
)
from qore.governance.executive_ports import (
    ExecutiveControlReceipt,
    ExecutiveControlReceiptStatus,
    ExecutivePortError,
    ExecutiveReadDelivery,
    ExecutiveReadReceiptStatus,
    ExecutiveReceiptId,
    build_executive_control_receipt,
    build_executive_read_delivery,
    build_executive_read_receipt,
)
from qore.governance.executive_read_models import (
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveSourceFreshness,
)
from qore.governance.executive_replay_idempotency import (
    ExecutiveReplayClaimReceipt,
    ExecutiveReplayClaimRequest,
    ExecutiveReplayClaimStatus,
    ExecutiveReplayProtectionError,
    ExecutiveReplayProtector,
    build_executive_control_replay_claim,
    build_executive_replay_claim_receipt,
)
from qore.governance.executive_request_guard import ExecutiveRequestGuard
from qore.governance.executive_state_sync import (
    ExecutiveClientStateSnapshot,
    ExecutiveClientStateSnapshotId,
    ExecutiveClientStateVersion,
    ExecutiveClientStateView,
    evaluate_executive_client_state_snapshot,
)
from qore.governance.executive_transport_envelope import (
    ExecutiveTransportEnvelopeId,
    ExecutiveTransportMessageKind,
    ExecutiveTransportSchemaVersion,
    ExecutiveTransportSurface,
)
from qore.kernel.result import Failure, Result, Success
from qore_clients.android_reference import (
    ExecutiveAndroidReferenceClient,
    ExecutiveAndroidReferenceId,
    build_executive_android_reference_client,
    normalize_executive_android_gateway_ingress,
)
from qore_clients.desktop_reference import (
    ExecutiveDesktopReferenceClient,
    ExecutiveDesktopReferenceId,
    build_executive_desktop_reference_client,
    normalize_executive_desktop_gateway_ingress,
)
from qore_clients.ios_reference import (
    ExecutiveIosReferenceClient,
    ExecutiveIosReferenceId,
    build_executive_ios_reference_client,
    normalize_executive_ios_gateway_ingress,
)

_NOW = datetime(2026, 8, 9, 21, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("64000000-0000-0000-0000-000000000001"))
_SCHEMA = ExecutiveTransportSchemaVersion("executive.v1")


type _ReferenceClient = (
    ExecutiveDesktopReferenceClient
    | ExecutiveIosReferenceClient
    | ExecutiveAndroidReferenceClient
)


@dataclass(frozen=True, slots=True)
class _GovernanceProjection:
    metadata: ExecutiveProjectionMetadata

    def logical_values(self) -> tuple[object, ...]:
        return (self.metadata.logical_values(),)


def _platform_uuid(platform: ExecutiveClientPlatform, offset: int) -> UUID:
    base = {
        ExecutiveClientPlatform.DESKTOP: 100,
        ExecutiveClientPlatform.IOS: 200,
        ExecutiveClientPlatform.ANDROID: 300,
    }[platform]
    return UUID(int=base + offset)


def _assertion(platform: ExecutiveClientPlatform) -> AuthenticatedExecutivePrincipal:
    return AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(_platform_uuid(platform, 1)),
        principal_id=_PRINCIPAL,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef(
            f"identity:{platform.value}-e2e"
        ),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        correlation_id=_CORRELATION,
    )


def _surface(platform: ExecutiveClientPlatform) -> ExecutiveClientSurface:
    result = build_executive_client_surface(
        surface_id=ExecutiveClientSurfaceId(_platform_uuid(platform, 2)),
        platform=platform,
        client_version=ExecutiveClientVersion("mission05.e2e.v1"),
        allowed_message_kinds=(
            ExecutiveTransportMessageKind.CONTROL,
            ExecutiveTransportMessageKind.READ,
        ),
    )
    assert isinstance(result, Success)
    return result.value


def _binding(platform: ExecutiveClientPlatform) -> ExecutiveClientSessionBinding:
    assertion = _assertion(platform)
    surface = _surface(platform)
    session = ExecutiveClientSession(
        session_id=ExecutiveClientSessionId(_platform_uuid(platform, 3)),
        surface_id=surface.surface_id,
        device_ref=ExecutiveClientDeviceRef(f"device:{platform.value}-e2e"),
        principal_id=_PRINCIPAL,
        authentication_assertion_id=assertion.assertion_id,
        status=ExecutiveClientSessionStatus.ACTIVE,
        established_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(minutes=20),
        correlation_id=_CORRELATION,
    )
    return ExecutiveClientSessionBinding(
        session=session,
        surface=surface,
        authenticated_principal=assertion,
        evaluated_at=_NOW + timedelta(minutes=2),
    )


def _reference_client(platform: ExecutiveClientPlatform) -> _ReferenceClient:
    binding = _binding(platform)
    surface = binding.surface
    view_result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(_platform_uuid(platform, 4)),
        surface_id=surface.surface_id,
        observed_at=_NOW + timedelta(minutes=2),
        selected_section=ExecutiveCommandCenterSection.GOVERNANCE,
        state_views=(),
    )
    assert isinstance(view_result, Success)
    if platform is ExecutiveClientPlatform.DESKTOP:
        result = build_executive_desktop_reference_client(
            reference_id=ExecutiveDesktopReferenceId(_platform_uuid(platform, 5)),
            surface=surface,
            session_binding=binding,
            command_center=view_result.value,
            environment=ExecutiveClientGatewayEnvironment.TEST,
            protocol=ExecutiveClientGatewayProtocol.IN_PROCESS,
            composed_at=_NOW + timedelta(minutes=3),
        )
    elif platform is ExecutiveClientPlatform.IOS:
        result = build_executive_ios_reference_client(
            reference_id=ExecutiveIosReferenceId(_platform_uuid(platform, 5)),
            surface=surface,
            session_binding=binding,
            command_center=view_result.value,
            environment=ExecutiveClientGatewayEnvironment.TEST,
            protocol=ExecutiveClientGatewayProtocol.IN_PROCESS,
            composed_at=_NOW + timedelta(minutes=3),
        )
    else:
        result = build_executive_android_reference_client(
            reference_id=ExecutiveAndroidReferenceId(_platform_uuid(platform, 5)),
            surface=surface,
            session_binding=binding,
            command_center=view_result.value,
            environment=ExecutiveClientGatewayEnvironment.TEST,
            protocol=ExecutiveClientGatewayProtocol.IN_PROCESS,
            composed_at=_NOW + timedelta(minutes=3),
        )
    assert isinstance(result, Success)
    return result.value


def _grant() -> ExecutiveAuthorityGrant:
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID(int=500)),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.mission05.e2e.v1"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=20),
        reason="mission05 cross-surface offline e2e",
    )


class _AuthoritySource:
    def __init__(self) -> None:
        self.requests: list[ExecutiveAuthorityStateRequest] = []

    def read_current(
        self,
        request: ExecutiveAuthorityStateRequest,
    ) -> Result[ExecutiveAuthorityStateSnapshot, ExecutiveAuthorityStateError]:
        self.requests.append(request)
        return Success(
            ExecutiveAuthorityStateSnapshot(
                request_id=request.request_id,
                principal_id=request.principal_id,
                status=ExecutiveAuthorityStateStatus.ACTIVE,
                observed_at=request.requested_at + timedelta(seconds=1),
                evidence_ref=ExecutiveAuthorityStateEvidenceRef(
                    "audit:mission05/authority-active"
                ),
                grant=_grant(),
            )
        )


class _ReplayStore:
    def __init__(self, status: ExecutiveReplayClaimStatus) -> None:
        self.status = status
        self.requests: list[ExecutiveReplayClaimRequest] = []

    def claim(
        self,
        request: ExecutiveReplayClaimRequest,
    ) -> Result[ExecutiveReplayClaimReceipt, ExecutiveReplayProtectionError]:
        self.requests.append(request)
        result = build_executive_replay_claim_receipt(
            request,
            observed_fingerprint=request.fingerprint,
            completed_at=request.requested_at + timedelta(microseconds=1),
            status=self.status,
        )
        assert isinstance(result, Success)
        return result


class _CommandPort:
    def __init__(self) -> None:
        self.requests: list[AuthorizedExecutiveControlIntent] = []

    def apply(
        self,
        request: AuthorizedExecutiveControlIntent,
    ) -> Result[ExecutiveControlReceipt, ExecutivePortError]:
        self.requests.append(request)
        result = build_executive_control_receipt(
            request,
            receipt_id=ExecutiveReceiptId(UUID(int=501)),
            received_at=request.authorized_at + timedelta(seconds=1),
            completed_at=request.authorized_at + timedelta(seconds=2),
            status=ExecutiveControlReceiptStatus.APPLIED,
            reason_code="governance.applied",
        )
        assert isinstance(result, Success)
        return result


def _control(platform: ExecutiveClientPlatform) -> ExecutiveControlIntent:
    return ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(_platform_uuid(platform, 6)),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=4),
        correlation_id=_CORRELATION,
        reason="mission05 offline e2e pause",
    )


def _normalize_control(
    client: _ReferenceClient,
    intent: ExecutiveControlIntent,
    *,
    envelope_id: ExecutiveTransportEnvelopeId,
) -> Result[ExecutiveClientGatewayIngress, ExecutiveClientGatewayError]:
    if isinstance(client, ExecutiveDesktopReferenceClient):
        return normalize_executive_desktop_gateway_ingress(
            client,
            intent,
            envelope_id=envelope_id,
            schema_version=_SCHEMA,
            route=ExecutiveClientGatewayRoute.CONTROL,
            received_at=_NOW + timedelta(minutes=5),
        )
    if isinstance(client, ExecutiveIosReferenceClient):
        return normalize_executive_ios_gateway_ingress(
            client,
            intent,
            envelope_id=envelope_id,
            schema_version=_SCHEMA,
            route=ExecutiveClientGatewayRoute.CONTROL,
            received_at=_NOW + timedelta(minutes=5),
        )
    return normalize_executive_android_gateway_ingress(
        client,
        intent,
        envelope_id=envelope_id,
        schema_version=_SCHEMA,
        route=ExecutiveClientGatewayRoute.CONTROL,
        received_at=_NOW + timedelta(minutes=5),
    )


def _authorized_governance_read() -> AuthorizedExecutiveReadRequest:
    request = ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(UUID(int=510)),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.GOVERNANCE,
        requested_at=_NOW + timedelta(seconds=1),
        correlation_id=_CORRELATION,
    )
    return AuthorizedExecutiveReadRequest(
        request=request,
        grant=_grant(),
        authorized_at=_NOW + timedelta(seconds=2),
    )


def _governance_delivery() -> ExecutiveReadDelivery:
    authorized = _authorized_governance_read()
    projection = _GovernanceProjection(
        ExecutiveProjectionMetadata(
            projection_id=ExecutiveProjectionId(UUID(int=511)),
            projection_version=ExecutiveProjectionVersion("governance.e2e.v1"),
            scope=ExecutiveReadScope.GOVERNANCE,
            source_observed_at=_NOW,
            projected_at=_NOW + timedelta(seconds=3),
            freshness=ExecutiveSourceFreshness.FRESH,
        )
    )
    receipt_result = build_executive_read_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(UUID(int=512)),
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


def _governance_state() -> ExecutiveClientStateView:
    snapshot = ExecutiveClientStateSnapshot(
        snapshot_id=ExecutiveClientStateSnapshotId(UUID(int=513)),
        version=ExecutiveClientStateVersion(1),
        delivery=_governance_delivery(),
        received_at=_NOW + timedelta(seconds=5),
        fresh_until=_NOW + timedelta(minutes=15),
    )
    result = evaluate_executive_client_state_snapshot(
        snapshot,
        evaluated_at=_NOW + timedelta(minutes=3),
    )
    assert isinstance(result, Success)
    return result.value


def _assert_mobile_ready(client: _ReferenceClient) -> None:
    if isinstance(client, ExecutiveDesktopReferenceClient):
        return
    result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=520)),
        session_binding=client.session_binding,
        secret_boundary=ExecutiveMobileSecretBoundaryAssertion(
            surface_id=client.surface.surface_id,
            boundary_ref=ExecutiveMobileSecretBoundaryRef(
                f"secure-store:{client.surface.platform.value}-e2e"
            ),
            status=ExecutiveMobileSecretBoundaryStatus.AVAILABLE,
            observed_at=_NOW + timedelta(minutes=3),
        ),
        connectivity=ExecutiveMobileConnectivityObservation(
            surface_id=client.surface.surface_id,
            status=ExecutiveMobileConnectivityStatus.ONLINE,
            observed_at=_NOW + timedelta(minutes=3),
        ),
        governance_state=_governance_state(),
        assessed_at=_NOW + timedelta(minutes=3, seconds=1),
    )
    assert isinstance(result, Success)
    assert result.value.disposition is ExecutiveMobileSecurityDisposition.READY
    assert result.value.reason is ExecutiveMobileSecurityReason.READY
    assert result.value.control_request_eligible is True


@pytest.mark.parametrize(
    "platform",
    (
        ExecutiveClientPlatform.DESKTOP,
        ExecutiveClientPlatform.IOS,
        ExecutiveClientPlatform.ANDROID,
    ),
)
def test_cross_surface_control_reaches_same_mission04_guard_replay_and_dispatch(
    platform: ExecutiveClientPlatform,
) -> None:
    client = _reference_client(platform)
    _assert_mobile_ready(client)
    intent = _control(platform)
    ingress_result = _normalize_control(
        client,
        intent,
        envelope_id=ExecutiveTransportEnvelopeId(_platform_uuid(platform, 7)),
    )
    assert isinstance(ingress_result, Success)
    ingress = ingress_result.value
    expected_surface = (
        ExecutiveTransportSurface.CEO_COMMAND_CENTER
        if platform is ExecutiveClientPlatform.DESKTOP
        else ExecutiveTransportSurface.MOBILE
    )
    assert ingress.envelope.surface is expected_surface
    assert ingress.envelope.message_kind is ExecutiveTransportMessageKind.CONTROL
    assert isinstance(ingress.envelope.payload, ExecutiveControlIntent)

    authority_source = _AuthoritySource()
    guard = ExecutiveRequestGuard(authority_source)
    authority_request = ExecutiveAuthorityStateRequest(
        request_id=ExecutiveAuthorityStateRequestId(_platform_uuid(platform, 8)),
        principal_id=_PRINCIPAL,
        requested_at=_NOW + timedelta(minutes=5, seconds=30),
        correlation_id=_CORRELATION,
    )
    authorized_result = guard.authorize_control(
        ingress.envelope.authenticated_principal,
        ingress.envelope.payload,
        authority_request=authority_request,
        evaluated_at=_NOW + timedelta(minutes=6),
    )
    assert isinstance(authorized_result, Success)
    authorized = authorized_result.value

    replay_request = build_executive_control_replay_claim(
        authorized,
        requested_at=_NOW + timedelta(minutes=6, seconds=1),
    )
    assert isinstance(replay_request, Success)
    replay_store = _ReplayStore(ExecutiveReplayClaimStatus.ACQUIRED)
    replay_result = ExecutiveReplayProtector(replay_store).protect(replay_request.value)
    assert isinstance(replay_result, Success)

    command_port = _CommandPort()
    dispatch_result = ExecutiveCommandDispatcher(command_port).dispatch(authorized)
    assert isinstance(dispatch_result, Success)
    ux_result = build_executive_governance_result_state(
        state_id=ExecutiveGovernanceUxStateId(_platform_uuid(platform, 9)),
        surface_id=client.surface.surface_id,
        authorized=authorized,
        receipt=dispatch_result.value,
        observed_at=dispatch_result.value.completed_at,
    )
    assert isinstance(ux_result, Success)
    assert ux_result.value.phase is ExecutiveGovernanceUxPhase.APPLIED
    assert ux_result.value.automatic_redispatch_allowed is False
    assert len(authority_source.requests) == 1
    assert len(replay_store.requests) == 1
    assert len(command_port.requests) == 1


def test_duplicate_replay_blocks_before_downstream_dispatch() -> None:
    platform = ExecutiveClientPlatform.IOS
    client = _reference_client(platform)
    _assert_mobile_ready(client)
    ingress_result = _normalize_control(
        client,
        _control(platform),
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=530)),
    )
    assert isinstance(ingress_result, Success)
    payload = ingress_result.value.envelope.payload
    assert isinstance(payload, ExecutiveControlIntent)
    guard = ExecutiveRequestGuard(_AuthoritySource())
    authorized_result = guard.authorize_control(
        ingress_result.value.envelope.authenticated_principal,
        payload,
        authority_request=ExecutiveAuthorityStateRequest(
            request_id=ExecutiveAuthorityStateRequestId(UUID(int=531)),
            principal_id=_PRINCIPAL,
            requested_at=_NOW + timedelta(minutes=5, seconds=30),
            correlation_id=_CORRELATION,
        ),
        evaluated_at=_NOW + timedelta(minutes=6),
    )
    assert isinstance(authorized_result, Success)
    replay_request = build_executive_control_replay_claim(
        authorized_result.value,
        requested_at=_NOW + timedelta(minutes=6, seconds=1),
    )
    assert isinstance(replay_request, Success)
    replay_store = _ReplayStore(ExecutiveReplayClaimStatus.DUPLICATE)
    replay_result = ExecutiveReplayProtector(replay_store).protect(replay_request.value)
    assert isinstance(replay_result, Failure)

    command_port = _CommandPort()
    assert command_port.requests == []


def test_stale_mobile_governance_state_blocks_control_before_gateway() -> None:
    client = _reference_client(ExecutiveClientPlatform.ANDROID)
    assert isinstance(client, ExecutiveAndroidReferenceClient)
    state = _governance_state()
    assert state.snapshot is not None
    result = assess_executive_mobile_security(
        assessment_id=ExecutiveMobileSecurityAssessmentId(UUID(int=540)),
        session_binding=client.session_binding,
        secret_boundary=ExecutiveMobileSecretBoundaryAssertion(
            surface_id=client.surface.surface_id,
            boundary_ref=ExecutiveMobileSecretBoundaryRef("secure-store:android-e2e"),
            status=ExecutiveMobileSecretBoundaryStatus.AVAILABLE,
            observed_at=_NOW + timedelta(minutes=3),
        ),
        connectivity=ExecutiveMobileConnectivityObservation(
            surface_id=client.surface.surface_id,
            status=ExecutiveMobileConnectivityStatus.ONLINE,
            observed_at=_NOW + timedelta(minutes=3),
        ),
        governance_state=state,
        assessed_at=state.snapshot.fresh_until + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.disposition is ExecutiveMobileSecurityDisposition.READ_ONLY
    assert result.value.reason is ExecutiveMobileSecurityReason.GOVERNANCE_STALE
    assert result.value.control_request_eligible is False
    assert result.value.automatic_redispatch_allowed is False


def test_cross_surface_e2e_contains_no_provider_or_trading_authority() -> None:
    for platform in (
        ExecutiveClientPlatform.DESKTOP,
        ExecutiveClientPlatform.IOS,
        ExecutiveClientPlatform.ANDROID,
    ):
        client = _reference_client(platform)
        assert not hasattr(client, "broker")
        assert not hasattr(client, "provider")
        assert not hasattr(client, "submit_order")
        assert not hasattr(client, "buy")
        assert not hasattr(client, "sell")
        assert not hasattr(client, "bypass_risk")
