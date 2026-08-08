from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_control import (
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveAuthorizationBlockedError,
    ExecutiveControlAction,
    ExecutiveControlIntent,
    ExecutiveControlValidationError,
    ExecutiveGrantId,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadRequest,
    ExecutiveReadRequestId,
    ExecutiveReadScope,
    authorize_executive_control_intent,
    authorize_executive_read_request,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 20, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION_ID = CorrelationId(UUID("27000000-0000-0000-0000-000000000001"))


def _grant(
    *,
    principal_id: ExecutivePrincipalId = _PRINCIPAL,
    allowed_actions: tuple[ExecutiveControlAction, ...] = (
        ExecutiveControlAction.PAUSE_SYSTEM,
        ExecutiveControlAction.HALT_NEW_TRADING,
    ),
    allowed_read_scopes: tuple[ExecutiveReadScope, ...] = (
        ExecutiveReadScope.SYSTEM_HEALTH,
        ExecutiveReadScope.CIBO_STATE,
        ExecutiveReadScope.CEO_ACCOUNTS,
        ExecutiveReadScope.CORPORATE_PROFIT_VAULT,
    ),
    expires_at: datetime | None = None,
) -> ExecutiveAuthorityGrant:
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(
            UUID("27000000-0000-0000-0000-000000000002")
        ),
        principal_id=principal_id,
        authority_version=ExecutiveAuthorityVersion("executive.v1"),
        allowed_actions=allowed_actions,
        allowed_read_scopes=allowed_read_scopes,
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=15) if expires_at is None else expires_at,
        reason="CEO authenticated executive control window",
    )


def _intent(
    *,
    principal_id: ExecutivePrincipalId = _PRINCIPAL,
    action: ExecutiveControlAction = ExecutiveControlAction.PAUSE_SYSTEM,
    requested_at: datetime | None = None,
) -> ExecutiveControlIntent:
    return ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(
            UUID("27000000-0000-0000-0000-000000000003")
        ),
        principal_id=principal_id,
        action=action,
        requested_at=_NOW + timedelta(seconds=1)
        if requested_at is None
        else requested_at,
        correlation_id=_CORRELATION_ID,
        reason="CEO requested controlled governance action",
    )


def _read_request(
    *,
    principal_id: ExecutivePrincipalId = _PRINCIPAL,
    scope: ExecutiveReadScope = ExecutiveReadScope.SYSTEM_HEALTH,
) -> ExecutiveReadRequest:
    return ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(
            UUID("27000000-0000-0000-0000-000000000004")
        ),
        principal_id=principal_id,
        scope=scope,
        requested_at=_NOW + timedelta(seconds=1),
        correlation_id=_CORRELATION_ID,
    )


def test_allowed_governance_action_is_authorized_with_exact_grant() -> None:
    grant = _grant()
    intent = _intent()

    result = authorize_executive_control_intent(
        intent,
        grant=grant,
        evaluated_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Success)
    assert result.value.intent == intent
    assert result.value.grant == grant
    assert result.value.authorized_at == _NOW + timedelta(seconds=2)


def test_action_outside_grant_fails_closed() -> None:
    result = authorize_executive_control_intent(
        _intent(action=ExecutiveControlAction.UPDATE_GOVERNANCE_POLICY),
        grant=_grant(),
        evaluated_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveAuthorizationBlockedError)


def test_principal_mismatch_fails_closed() -> None:
    result = authorize_executive_control_intent(
        _intent(principal_id=ExecutivePrincipalId("ceo.secondary")),
        grant=_grant(),
        evaluated_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveAuthorizationBlockedError)


def test_expired_grant_fails_closed() -> None:
    result = authorize_executive_control_intent(
        _intent(),
        grant=_grant(expires_at=_NOW + timedelta(seconds=2)),
        evaluated_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveAuthorizationBlockedError)


def test_intent_cannot_predate_authority_grant() -> None:
    result = authorize_executive_control_intent(
        _intent(requested_at=_NOW - timedelta(seconds=1)),
        grant=_grant(),
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveAuthorizationBlockedError)


def test_direct_trading_actions_are_not_part_of_executive_allowlist() -> None:
    values = {item.value for item in ExecutiveControlAction}

    assert "buy" not in values
    assert "sell" not in values
    assert "submit-order" not in values
    assert "cancel-order" not in values
    assert "force-trade" not in values
    assert "close-position" not in values

    with pytest.raises(ValueError):
        ExecutiveControlAction("force-trade")


def test_grant_canonicalizes_capabilities_for_deterministic_evidence() -> None:
    grant = _grant(
        allowed_actions=(
            ExecutiveControlAction.RESTRICT_MARKET,
            ExecutiveControlAction.HALT_NEW_TRADING,
            ExecutiveControlAction.PAUSE_SYSTEM,
        ),
        allowed_read_scopes=(
            ExecutiveReadScope.CORPORATE_PROFIT_VAULT,
            ExecutiveReadScope.AUDIT,
            ExecutiveReadScope.CEO_ACCOUNTS,
        ),
    )

    assert tuple(item.value for item in grant.allowed_actions) == (
        "halt-new-trading",
        "pause-system",
        "restrict-market",
    )
    assert tuple(item.value for item in grant.allowed_read_scopes) == (
        "audit",
        "ceo-accounts",
        "corporate-profit-vault",
    )


def test_duplicate_authority_capability_is_rejected() -> None:
    with pytest.raises(ExecutiveControlValidationError):
        _grant(
            allowed_actions=(
                ExecutiveControlAction.PAUSE_SYSTEM,
                ExecutiveControlAction.PAUSE_SYSTEM,
            )
        )


def test_secret_like_reason_is_rejected() -> None:
    with pytest.raises(ExecutiveControlValidationError):
        ExecutiveControlIntent(
            intent_id=ExecutiveIntentId(
                UUID("27000000-0000-0000-0000-000000000005")
            ),
            principal_id=_PRINCIPAL,
            action=ExecutiveControlAction.PAUSE_SYSTEM,
            requested_at=_NOW,
            correlation_id=_CORRELATION_ID,
            reason="token=do-not-store-this",
        )


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ExecutiveControlValidationError):
        ExecutiveReadRequest(
            request_id=ExecutiveReadRequestId(
                UUID("27000000-0000-0000-0000-000000000006")
            ),
            principal_id=_PRINCIPAL,
            scope=ExecutiveReadScope.SYSTEM_HEALTH,
            requested_at=datetime(2026, 8, 8, 20, 0),
            correlation_id=_CORRELATION_ID,
        )


def test_allowed_read_scope_is_authorized() -> None:
    request = _read_request(scope=ExecutiveReadScope.CORPORATE_PROFIT_VAULT)
    grant = _grant()

    result = authorize_executive_read_request(
        request,
        grant=grant,
        evaluated_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Success)
    assert result.value.request == request
    assert result.value.grant == grant


def test_ungranted_read_scope_fails_closed() -> None:
    result = authorize_executive_read_request(
        _read_request(scope=ExecutiveReadScope.TRADE_FORENSICS),
        grant=_grant(),
        evaluated_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveAuthorizationBlockedError)


def test_ceo_accounts_and_profit_vault_are_distinct_read_scopes() -> None:
    scope_values = {
        ExecutiveReadScope.CEO_ACCOUNTS.value,
        ExecutiveReadScope.CORPORATE_PROFIT_VAULT.value,
    }

    assert scope_values == {"ceo-accounts", "corporate-profit-vault"}


def test_authorized_values_are_deterministic_and_include_authority_version() -> None:
    result = authorize_executive_control_intent(
        _intent(),
        grant=_grant(),
        evaluated_at=_NOW + timedelta(seconds=2),
    )
    assert isinstance(result, Success)

    values = result.value.logical_values()

    assert values == result.value.logical_values()
    assert "executive.v1" in repr(values)
    assert "token=" not in repr(values).lower()
