from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.events import CorrelationId
from qore.governance.cibo_executive_dialogue import (
    CiboExecutiveDialogueTurnId,
    CiboExecutiveJudgmentState,
    CiboExecutivePromptRef,
    CiboExecutiveQuestion,
    build_cibo_executive_answer,
)
from qore.governance.cibo_widget import (
    CiboWidgetMode,
    CiboWidgetStateId,
    build_cibo_widget_state,
)
from qore.governance.executive_authentication import (
    AuthenticatedExecutivePrincipal,
    ExecutiveAuthenticationAssertionId,
    ExecutiveAuthenticationContextCode,
    ExecutiveAuthenticationMethodCode,
    ExecutiveIdentityBoundaryRef,
)
from qore.governance.executive_client_gateway import (
    ExecutiveClientGatewayEnvironment,
    ExecutiveClientGatewayProtocol,
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
from qore.governance.executive_governance_ux import (
    ExecutiveGovernanceUxPhase,
    ExecutiveGovernanceUxStateId,
    build_executive_governance_result_state,
)
from qore.governance.executive_notifications import (
    ExecutiveInterruptionMode,
    ExecutiveNotification,
    ExecutiveNotificationId,
    ExecutiveNotificationOrigin,
    ExecutiveNotificationPolicy,
    ExecutiveNotificationRule,
    evaluate_executive_notification,
)
from qore.governance.executive_ports import (
    ExecutiveControlReceiptStatus,
    ExecutiveEvidenceRef,
    ExecutiveReceiptId,
    build_executive_control_receipt,
)
from qore.governance.executive_read_models import ExecutiveAttentionLevel
from qore.governance.executive_state_sync import (
    ExecutiveClientStateStatus,
    ExecutiveClientSubscription,
    ExecutiveClientSubscriptionId,
)
from qore.governance.executive_transport_envelope import (
    ExecutiveTransportMessageKind,
    ExecutiveTransportSurface,
)
from qore.kernel.result import Success
from qore_clients.android_reference import (
    ExecutiveAndroidReferenceClient,
    ExecutiveAndroidReferenceId,
    build_executive_android_reference_client,
)
from qore_clients.desktop_reference import (
    ExecutiveDesktopReferenceClient,
    ExecutiveDesktopReferenceId,
    build_executive_desktop_reference_client,
)
from qore_clients.ios_reference import (
    ExecutiveIosReferenceClient,
    ExecutiveIosReferenceId,
    build_executive_ios_reference_client,
)

_NOW = datetime(2026, 8, 9, 22, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("65000000-0000-0000-0000-000000000001"))


type _ReferenceClient = (
    ExecutiveDesktopReferenceClient
    | ExecutiveIosReferenceClient
    | ExecutiveAndroidReferenceClient
)


def _core() -> CoreApplication:
    result = bootstrap(Configuration(application_name="qore-mission05-closure"))
    assert isinstance(result, Success)
    return result.value


def _platform_uuid(platform: ExecutiveClientPlatform, offset: int) -> UUID:
    base = {
        ExecutiveClientPlatform.DESKTOP: 1000,
        ExecutiveClientPlatform.IOS: 2000,
        ExecutiveClientPlatform.ANDROID: 3000,
    }[platform]
    return UUID(int=base + offset)


def _surface(platform: ExecutiveClientPlatform) -> ExecutiveClientSurface:
    result = build_executive_client_surface(
        surface_id=ExecutiveClientSurfaceId(_platform_uuid(platform, 1)),
        platform=platform,
        client_version=ExecutiveClientVersion("mission05.closure.v1"),
        allowed_message_kinds=(
            ExecutiveTransportMessageKind.CONTROL,
            ExecutiveTransportMessageKind.READ,
        ),
    )
    assert isinstance(result, Success)
    return result.value


def _binding(platform: ExecutiveClientPlatform) -> ExecutiveClientSessionBinding:
    surface = _surface(platform)
    assertion = AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(_platform_uuid(platform, 2)),
        principal_id=_PRINCIPAL,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef(
            f"identity:{platform.value}-closure"
        ),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        correlation_id=_CORRELATION,
    )
    session = ExecutiveClientSession(
        session_id=ExecutiveClientSessionId(_platform_uuid(platform, 3)),
        surface_id=surface.surface_id,
        device_ref=ExecutiveClientDeviceRef(f"device:{platform.value}-closure"),
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
    view_result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(_platform_uuid(platform, 4)),
        surface_id=binding.surface.surface_id,
        observed_at=_NOW + timedelta(minutes=2),
        selected_section=ExecutiveCommandCenterSection.HOME,
        state_views=(),
    )
    assert isinstance(view_result, Success)
    if platform is ExecutiveClientPlatform.DESKTOP:
        desktop_result = build_executive_desktop_reference_client(
            reference_id=ExecutiveDesktopReferenceId(_platform_uuid(platform, 5)),
            surface=binding.surface,
            session_binding=binding,
            command_center=view_result.value,
            environment=ExecutiveClientGatewayEnvironment.TEST,
            protocol=ExecutiveClientGatewayProtocol.IN_PROCESS,
            composed_at=_NOW + timedelta(minutes=3),
        )
        assert isinstance(desktop_result, Success)
        return desktop_result.value
    if platform is ExecutiveClientPlatform.IOS:
        ios_result = build_executive_ios_reference_client(
            reference_id=ExecutiveIosReferenceId(_platform_uuid(platform, 5)),
            surface=binding.surface,
            session_binding=binding,
            command_center=view_result.value,
            environment=ExecutiveClientGatewayEnvironment.TEST,
            protocol=ExecutiveClientGatewayProtocol.IN_PROCESS,
            composed_at=_NOW + timedelta(minutes=3),
        )
        assert isinstance(ios_result, Success)
        return ios_result.value
    android_result = build_executive_android_reference_client(
        reference_id=ExecutiveAndroidReferenceId(_platform_uuid(platform, 5)),
        surface=binding.surface,
        session_binding=binding,
        command_center=view_result.value,
        environment=ExecutiveClientGatewayEnvironment.TEST,
        protocol=ExecutiveClientGatewayProtocol.IN_PROCESS,
        composed_at=_NOW + timedelta(minutes=3),
    )
    assert isinstance(android_result, Success)
    return android_result.value


def _notification_policy() -> ExecutiveNotificationPolicy:
    return ExecutiveNotificationPolicy(
        rules=(
            ExecutiveNotificationRule(
                ExecutiveAttentionLevel.INFORMATION,
                ExecutiveInterruptionMode.PASSIVE,
                False,
                False,
            ),
            ExecutiveNotificationRule(
                ExecutiveAttentionLevel.ATTENTION,
                ExecutiveInterruptionMode.AMBIENT,
                False,
                False,
            ),
            ExecutiveNotificationRule(
                ExecutiveAttentionLevel.IMPORTANT,
                ExecutiveInterruptionMode.PROMINENT,
                True,
                False,
            ),
            ExecutiveNotificationRule(
                ExecutiveAttentionLevel.DECISION_REQUIRED,
                ExecutiveInterruptionMode.DECISION,
                True,
                True,
            ),
            ExecutiveNotificationRule(
                ExecutiveAttentionLevel.CRITICAL,
                ExecutiveInterruptionMode.CRITICAL,
                True,
                True,
            ),
        )
    )


def _authorized_control() -> AuthorizedExecutiveControlIntent:
    grant = ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID(int=4001)),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.mission05.closure.v1"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=20),
        reason="mission05 closure no-action evidence",
    )
    intent = ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID(int=4002)),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
        reason="mission05 closure governed pause",
    )
    return AuthorizedExecutiveControlIntent(
        intent=intent,
        grant=grant,
        authorized_at=_NOW + timedelta(minutes=2),
    )


def test_reference_clients_share_authority_and_no_production_gateway() -> None:
    clients = tuple(
        _reference_client(platform)
        for platform in (
            ExecutiveClientPlatform.DESKTOP,
            ExecutiveClientPlatform.IOS,
            ExecutiveClientPlatform.ANDROID,
        )
    )

    assert clients[0].surface.transport_surface is ExecutiveTransportSurface.CEO_COMMAND_CENTER
    assert clients[1].surface.transport_surface is ExecutiveTransportSurface.MOBILE
    assert clients[2].surface.transport_surface is ExecutiveTransportSurface.MOBILE
    assert all(client.session_binding.session.principal_id == _PRINCIPAL for client in clients)
    assert all(client.automatic_redispatch_allowed is False for client in clients)
    assert all(client.__class__.__module__.startswith("qore_clients.") for client in clients)
    assert "production" not in {item.value for item in ExecutiveClientGatewayEnvironment}

    for client in clients:
        assert not hasattr(client, "core")
        assert not hasattr(client, "broker")
        assert not hasattr(client, "provider")
        assert not hasattr(client, "credential")
        assert not hasattr(client, "submit_order")
        assert not hasattr(client, "buy")
        assert not hasattr(client, "sell")
        assert not hasattr(client, "bypass_risk")


def test_notification_dialogue_widget_are_evidence_backed_non_authoritative() -> None:
    notification = ExecutiveNotification(
        notification_id=ExecutiveNotificationId(UUID(int=4101)),
        origin=ExecutiveNotificationOrigin.RISK,
        level=ExecutiveAttentionLevel.CRITICAL,
        subject_code="risk.capital_protection",
        reason_codes=("risk.threshold",),
        observed_at=_NOW,
        evidence_refs=(ExecutiveEvidenceRef("audit:mission05/notification"),),
    )
    notification_result = evaluate_executive_notification(
        notification,
        _notification_policy(),
        evaluated_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(notification_result, Success)

    question = CiboExecutiveQuestion(
        turn_id=CiboExecutiveDialogueTurnId(UUID(int=4102)),
        principal_id=_PRINCIPAL,
        prompt_ref=CiboExecutivePromptRef("prompt:mission05/closure"),
        requested_scope=ExecutiveReadScope.GOVERNANCE,
        asked_at=_NOW,
        correlation_id=_CORRELATION,
    )
    answer_result = build_cibo_executive_answer(
        question,
        judgment_state=CiboExecutiveJudgmentState.CONCERNED,
        summary_code="governance.attention",
        reason_codes=("risk.threshold",),
        evidence_refs=(ExecutiveEvidenceRef("audit:mission05/cibo"),),
        answered_at=_NOW + timedelta(seconds=1),
        navigation_scope=ExecutiveReadScope.GOVERNANCE,
    )
    assert isinstance(answer_result, Success)
    widget_result = build_cibo_widget_state(
        state_id=CiboWidgetStateId(UUID(int=4103)),
        surface_id=ExecutiveClientSurfaceId(UUID(int=4104)),
        mode=CiboWidgetMode.EVIDENCE_REVIEW,
        observed_at=_NOW + timedelta(seconds=2),
        answer=answer_result.value,
        notification=notification_result.value,
    )
    assert isinstance(widget_result, Success)

    assert answer_result.value.evidence_refs
    presentation_values = (
        notification,
        notification_result.value,
        answer_result.value,
        widget_result.value,
    )
    for value in presentation_values:
        assert not hasattr(value, "dispatch")
        assert not hasattr(value, "execute")
        assert not hasattr(value, "submit_order")
        assert not hasattr(value, "buy")
        assert not hasattr(value, "sell")
        assert not hasattr(value, "bypass_risk")


def test_no_change_receipt_is_no_action_and_never_redispatchable() -> None:
    authorized = _authorized_control()
    receipt_result = build_executive_control_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(UUID(int=4201)),
        received_at=_NOW + timedelta(minutes=2, seconds=1),
        completed_at=_NOW + timedelta(minutes=2, seconds=2),
        status=ExecutiveControlReceiptStatus.NO_CHANGE,
        reason_code="governance.no_change",
    )
    assert isinstance(receipt_result, Success)
    ux_result = build_executive_governance_result_state(
        state_id=ExecutiveGovernanceUxStateId(UUID(int=4202)),
        surface_id=ExecutiveClientSurfaceId(UUID(int=4203)),
        authorized=authorized,
        receipt=receipt_result.value,
        observed_at=receipt_result.value.completed_at,
    )

    assert isinstance(ux_result, Success)
    assert ux_result.value.phase is ExecutiveGovernanceUxPhase.NO_ACTION
    assert ux_result.value.is_confirmed_applied is False
    assert ux_result.value.automatic_redispatch_allowed is False


def test_subscription_is_presentation_only_and_freshness_vocabulary_is_closed() -> None:
    subscription = ExecutiveClientSubscription(
        subscription_id=ExecutiveClientSubscriptionId(UUID(int=4301)),
        surface_id=ExecutiveClientSurfaceId(UUID(int=4302)),
        scope=ExecutiveReadScope.GOVERNANCE,
        created_at=_NOW,
    )

    assert {item.value for item in ExecutiveClientStateStatus} == {
        "current",
        "stale",
        "unavailable",
        "unknown",
    }
    assert not hasattr(subscription, "command")
    assert not hasattr(subscription, "authority")
    assert not hasattr(subscription, "dispatch")
    assert not hasattr(subscription, "execute")


def test_external_reference_composition_preserves_core_runtime_identity() -> None:
    core = _core()
    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    clients = tuple(
        _reference_client(platform)
        for platform in (
            ExecutiveClientPlatform.DESKTOP,
            ExecutiveClientPlatform.IOS,
            ExecutiveClientPlatform.ANDROID,
        )
    )
    assert len(clients) == 3

    assert core.event_bus is event_bus
    assert core.runtime_plan == runtime_plan
    assert core.runtime_snapshot() == runtime_snapshot
    assert core.runtime_health() == runtime_health
