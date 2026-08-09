from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from typing import cast
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
from qore.governance.executive_control import (
    ExecutiveControlAction,
    ExecutiveControlIntent,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadRequest,
    ExecutiveReadRequestId,
    ExecutiveReadScope,
)
from qore.governance.executive_transport_envelope import (
    ExecutiveTransportEnvelope,
    ExecutiveTransportEnvelopeId,
    ExecutiveTransportEnvelopeValidationError,
    ExecutiveTransportMessageKind,
    ExecutiveTransportSchemaVersion,
    ExecutiveTransportSurface,
    build_executive_control_transport_envelope,
    build_executive_read_transport_envelope,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 7, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("49000000-0000-0000-0000-000000000001"))
_SCHEMA = ExecutiveTransportSchemaVersion("executive.v1")


def _assertion() -> AuthenticatedExecutivePrincipal:
    return AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(
            UUID("49000000-0000-0000-0000-000000000002")
        ),
        principal_id=_PRINCIPAL,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef("identity:primary"),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=20),
        correlation_id=_CORRELATION,
    )


def _intent() -> ExecutiveControlIntent:
    return ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("49000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
        reason="CEO governed pause",
    )


def _read() -> ExecutiveReadRequest:
    return ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(
            UUID("49000000-0000-0000-0000-000000000004")
        ),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.GOVERNANCE,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
    )


def test_control_envelope_is_transport_neutral_immutable_and_deterministic() -> None:
    result = build_executive_control_transport_envelope(
        _assertion(),
        _intent(),
        envelope_id=ExecutiveTransportEnvelopeId(
            UUID("49000000-0000-0000-0000-000000000005")
        ),
        schema_version=_SCHEMA,
        surface=ExecutiveTransportSurface.MOBILE,
        received_at=_NOW + timedelta(minutes=2),
    )

    assert isinstance(result, Success)
    envelope = result.value
    assert envelope.message_kind is ExecutiveTransportMessageKind.CONTROL
    assert envelope.surface is ExecutiveTransportSurface.MOBILE
    assert envelope.logical_values() == envelope.logical_values()
    assert not hasattr(envelope, "headers")
    assert not hasattr(envelope, "token")
    assert not hasattr(envelope, "metadata")
    with pytest.raises(FrozenInstanceError):
        envelope.__setattr__("surface", ExecutiveTransportSurface.API)


def test_read_envelope_uses_same_normalized_contract_for_internal_surface() -> None:
    result = build_executive_read_transport_envelope(
        _assertion(),
        _read(),
        envelope_id=ExecutiveTransportEnvelopeId(
            UUID("49000000-0000-0000-0000-000000000006")
        ),
        schema_version=_SCHEMA,
        surface=ExecutiveTransportSurface.INTERNAL_SERVICE,
        received_at=_NOW + timedelta(minutes=2),
    )

    assert isinstance(result, Success)
    assert result.value.message_kind is ExecutiveTransportMessageKind.READ
    assert result.value.payload is not None


def test_envelope_rejects_kind_principal_or_correlation_mismatch() -> None:
    assertion = _assertion()
    intent = _intent()
    with pytest.raises(ExecutiveTransportEnvelopeValidationError):
        ExecutiveTransportEnvelope(
            envelope_id=ExecutiveTransportEnvelopeId(UUID(int=7)),
            schema_version=_SCHEMA,
            surface=ExecutiveTransportSurface.API,
            message_kind=ExecutiveTransportMessageKind.READ,
            authenticated_principal=assertion,
            payload=intent,
            received_at=_NOW + timedelta(minutes=2),
        )

    wrong_principal = replace(intent, principal_id=ExecutivePrincipalId("ceo.other"))
    wrong_correlation = replace(intent, correlation_id=CorrelationId(UUID(int=9)))
    for invalid in (wrong_principal, wrong_correlation):
        result = build_executive_control_transport_envelope(
            assertion,
            invalid,
            envelope_id=ExecutiveTransportEnvelopeId(UUID(int=10)),
            schema_version=_SCHEMA,
            surface=ExecutiveTransportSurface.API,
            received_at=_NOW + timedelta(minutes=2),
        )
        assert isinstance(result, Failure)


def test_envelope_requires_explicit_aware_valid_chronology() -> None:
    assertion = _assertion()
    intent = _intent()
    naive = datetime(2026, 8, 9, 7, 2)

    naive_result = build_executive_control_transport_envelope(
        assertion,
        intent,
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=11)),
        schema_version=_SCHEMA,
        surface=ExecutiveTransportSurface.API,
        received_at=naive,
    )
    early_result = build_executive_control_transport_envelope(
        assertion,
        intent,
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=12)),
        schema_version=_SCHEMA,
        surface=ExecutiveTransportSurface.API,
        received_at=intent.requested_at - timedelta(microseconds=1),
    )
    expired_result = build_executive_control_transport_envelope(
        assertion,
        intent,
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=13)),
        schema_version=_SCHEMA,
        surface=ExecutiveTransportSurface.API,
        received_at=assertion.expires_at + timedelta(microseconds=1),
    )

    assert isinstance(naive_result, Failure)
    assert isinstance(early_result, Failure)
    assert isinstance(expired_result, Failure)


def test_payload_must_be_created_inside_authentication_window() -> None:
    assertion = _assertion()
    before = replace(_intent(), requested_at=assertion.issued_at - timedelta(microseconds=1))
    after = replace(_intent(), requested_at=assertion.expires_at + timedelta(microseconds=1))

    for invalid in (before, after):
        result = build_executive_control_transport_envelope(
            assertion,
            invalid,
            envelope_id=ExecutiveTransportEnvelopeId(UUID(int=14)),
            schema_version=_SCHEMA,
            surface=ExecutiveTransportSurface.CEO_COMMAND_CENTER,
            received_at=assertion.expires_at,
        )
        assert isinstance(result, Failure)


def test_identity_and_schema_types_fail_closed_without_coercion() -> None:
    with pytest.raises(ExecutiveTransportEnvelopeValidationError):
        ExecutiveTransportEnvelopeId(cast(UUID, "envelope"))
    with pytest.raises(ExecutiveTransportEnvelopeValidationError):
        ExecutiveTransportSchemaVersion("Executive V1")
