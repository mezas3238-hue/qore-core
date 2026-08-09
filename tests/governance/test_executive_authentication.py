from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_authentication import (
    AuthenticatedExecutivePrincipal,
    ExecutiveAuthenticationAssertionId,
    ExecutiveAuthenticationBlockedError,
    ExecutiveAuthenticationContextCode,
    ExecutiveAuthenticationMethodCode,
    ExecutiveAuthenticationValidationError,
    ExecutiveIdentityBoundaryRef,
    evaluate_authenticated_executive_principal,
)
from qore.governance.executive_control import ExecutivePrincipalId
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 30, tzinfo=UTC)


def _assertion(
    *,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> AuthenticatedExecutivePrincipal:
    issued = issued_at or _NOW
    return AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(
            UUID("41000000-0000-0000-0000-000000000001")
        ),
        principal_id=ExecutivePrincipalId("ceo.primary"),
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef("identity:primary"),
        issued_at=issued,
        expires_at=expires_at or issued + timedelta(minutes=10),
        correlation_id=CorrelationId(
            UUID("41000000-0000-0000-0000-000000000002")
        ),
    )


def test_current_assertion_evaluates_successfully_and_deterministically() -> None:
    assertion = _assertion()

    result = evaluate_authenticated_executive_principal(
        assertion,
        evaluated_at=_NOW + timedelta(minutes=1),
    )

    assert isinstance(result, Success)
    assert result.value is assertion
    assert assertion.logical_values() == assertion.logical_values()
    values = repr(assertion.logical_values()).lower()
    assert "password" not in values
    assert "bearer " not in values
    assert "token" not in values


def test_assertion_is_valid_at_exact_issue_and_expiry_boundaries() -> None:
    assertion = _assertion()

    at_issue = evaluate_authenticated_executive_principal(
        assertion,
        evaluated_at=assertion.issued_at,
    )
    at_expiry = evaluate_authenticated_executive_principal(
        assertion,
        evaluated_at=assertion.expires_at,
    )

    assert isinstance(at_issue, Success)
    assert isinstance(at_expiry, Success)


def test_future_and_expired_assertions_fail_closed() -> None:
    assertion = _assertion()

    future = evaluate_authenticated_executive_principal(
        assertion,
        evaluated_at=assertion.issued_at - timedelta(microseconds=1),
    )
    expired = evaluate_authenticated_executive_principal(
        assertion,
        evaluated_at=assertion.expires_at + timedelta(microseconds=1),
    )

    assert isinstance(future, Failure)
    assert isinstance(expired, Failure)
    assert isinstance(future.error, ExecutiveAuthenticationBlockedError)
    assert isinstance(expired.error, ExecutiveAuthenticationBlockedError)


def test_assertion_requires_explicit_aware_chronology() -> None:
    naive = datetime(2026, 8, 9, 0, 30)

    with pytest.raises(ExecutiveAuthenticationValidationError):
        _assertion(issued_at=naive)

    with pytest.raises(ExecutiveAuthenticationValidationError):
        _assertion(expires_at=_NOW)

    result = evaluate_authenticated_executive_principal(
        _assertion(),
        evaluated_at=naive,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveAuthenticationValidationError)


def test_public_authentication_codes_reject_secret_like_material() -> None:
    with pytest.raises(ExecutiveAuthenticationValidationError):
        ExecutiveAuthenticationMethodCode("bearer-token")

    with pytest.raises(ExecutiveAuthenticationValidationError):
        ExecutiveAuthenticationContextCode("password")

    with pytest.raises(ExecutiveAuthenticationValidationError):
        ExecutiveIdentityBoundaryRef("identity:client_secret")


def test_assertion_types_fail_closed_without_coercion() -> None:
    with pytest.raises(ExecutiveAuthenticationValidationError):
        ExecutiveAuthenticationAssertionId(cast(UUID, "assertion-1"))

    assertion = _assertion()
    with pytest.raises(ExecutiveAuthenticationValidationError):
        AuthenticatedExecutivePrincipal(
            assertion_id=assertion.assertion_id,
            principal_id=cast(ExecutivePrincipalId, "ceo.primary"),
            method=assertion.method,
            context=assertion.context,
            identity_boundary_ref=assertion.identity_boundary_ref,
            issued_at=assertion.issued_at,
            expires_at=assertion.expires_at,
            correlation_id=assertion.correlation_id,
        )


def test_assertion_is_immutable_and_carries_no_authentication_secret_field() -> None:
    assertion = _assertion()

    with pytest.raises(FrozenInstanceError):
        assertion.expires_at = assertion.expires_at + timedelta(minutes=1)

    assert not hasattr(assertion, "password")
    assert not hasattr(assertion, "token")
    assert not hasattr(assertion, "credential")
    assert not hasattr(assertion, "biometric")
