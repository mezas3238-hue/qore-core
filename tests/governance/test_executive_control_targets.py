from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_control import (
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveControlAction,
    ExecutiveControlIntent,
    ExecutiveControlTarget,
    ExecutiveControlTargetKind,
    ExecutiveControlValidationError,
    ExecutiveGrantId,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadScope,
    authorize_executive_control_intent,
)
from qore.governance.executive_ports import (
    ExecutiveControlReceipt,
    ExecutiveControlReceiptStatus,
    ExecutivePortValidationError,
    ExecutiveReceiptId,
    build_executive_control_receipt,
)
from qore.kernel.result import Success

_NOW = datetime(2026, 8, 8, 22, 30, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("32000000-0000-0000-0000-000000000001"))


def _grant(action: ExecutiveControlAction) -> ExecutiveAuthorityGrant:
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("32000000-0000-0000-0000-000000000002")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("executive.v2"),
        allowed_actions=(action,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=15),
        reason="authenticated CEO governance authority",
    )


def _intent(
    action: ExecutiveControlAction,
    target: ExecutiveControlTarget | None,
) -> ExecutiveControlIntent:
    return ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("32000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        action=action,
        requested_at=_NOW + timedelta(seconds=1),
        correlation_id=_CORRELATION,
        reason="scoped executive governance request",
        target=target,
    )


def test_restrict_market_requires_market_target() -> None:
    target = ExecutiveControlTarget(
        kind=ExecutiveControlTargetKind.MARKET,
        value="market:eur_usd",
    )

    intent = _intent(ExecutiveControlAction.RESTRICT_MARKET, target)

    assert intent.target == target
    assert target.logical_values() == ("market", "market:eur_usd")

    with pytest.raises(ExecutiveControlValidationError):
        _intent(ExecutiveControlAction.RESTRICT_MARKET, None)

    with pytest.raises(ExecutiveControlValidationError):
        _intent(
            ExecutiveControlAction.RESTRICT_MARKET,
            ExecutiveControlTarget(
                kind=ExecutiveControlTargetKind.ACCOUNT,
                value="proprietary-account:alpha",
            ),
        )


def test_restrict_account_requires_account_target() -> None:
    target = ExecutiveControlTarget(
        kind=ExecutiveControlTargetKind.ACCOUNT,
        value="proprietary-account:alpha",
    )

    intent = _intent(ExecutiveControlAction.RESTRICT_ACCOUNT, target)

    assert intent.target == target

    with pytest.raises(ExecutiveControlValidationError):
        _intent(
            ExecutiveControlAction.RESTRICT_ACCOUNT,
            ExecutiveControlTarget(
                kind=ExecutiveControlTargetKind.MARKET,
                value="market:gbp_usd",
            ),
        )


def test_restore_restriction_targets_restriction_identity() -> None:
    target = ExecutiveControlTarget(
        kind=ExecutiveControlTargetKind.RESTRICTION,
        value="restriction:32000000-0000-0000-0000-000000000010",
    )

    intent = _intent(ExecutiveControlAction.RESTORE_RESTRICTION, target)

    assert intent.target == target


def test_global_control_actions_reject_targets() -> None:
    target = ExecutiveControlTarget(
        kind=ExecutiveControlTargetKind.MARKET,
        value="market:eur_usd",
    )

    with pytest.raises(ExecutiveControlValidationError):
        _intent(ExecutiveControlAction.PAUSE_SYSTEM, target)

    pause = _intent(ExecutiveControlAction.PAUSE_SYSTEM, None)
    assert pause.target is None


def test_target_value_is_canonical_and_secret_safe() -> None:
    with pytest.raises(ExecutiveControlValidationError):
        ExecutiveControlTarget(
            kind=ExecutiveControlTargetKind.MARKET,
            value="EUR_USD",
        )

    with pytest.raises(ExecutiveControlValidationError):
        ExecutiveControlTarget(
            kind=ExecutiveControlTargetKind.ACCOUNT,
            value="token=secret",
        )


def test_authorization_and_receipt_preserve_exact_target() -> None:
    target = ExecutiveControlTarget(
        kind=ExecutiveControlTargetKind.MARKET,
        value="market:eur_usd",
    )
    intent = _intent(ExecutiveControlAction.RESTRICT_MARKET, target)
    authorization = authorize_executive_control_intent(
        intent,
        grant=_grant(ExecutiveControlAction.RESTRICT_MARKET),
        evaluated_at=_NOW + timedelta(seconds=2),
    )
    assert isinstance(authorization, Success)

    receipt_result = build_executive_control_receipt(
        authorization.value,
        receipt_id=ExecutiveReceiptId(
            UUID("32000000-0000-0000-0000-000000000004")
        ),
        received_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=4),
        status=ExecutiveControlReceiptStatus.APPLIED,
        reason_code="governance.restriction_applied",
    )

    assert isinstance(receipt_result, Success)
    assert receipt_result.value.target == target
    assert "market:eur_usd" in repr(receipt_result.value.logical_values())


def test_control_receipt_fails_closed_on_target_action_mismatch() -> None:
    with pytest.raises(ExecutivePortValidationError):
        ExecutiveControlReceipt(
            receipt_id=ExecutiveReceiptId(
                UUID("32000000-0000-0000-0000-000000000005")
            ),
            intent_id=ExecutiveIntentId(
                UUID("32000000-0000-0000-0000-000000000006")
            ),
            principal_id=_PRINCIPAL,
            action=ExecutiveControlAction.RESTRICT_MARKET,
            authority_version=ExecutiveAuthorityVersion("executive.v2"),
            correlation_id=_CORRELATION,
            received_at=_NOW + timedelta(seconds=3),
            completed_at=_NOW + timedelta(seconds=4),
            status=ExecutiveControlReceiptStatus.APPLIED,
            reason_code="governance.applied",
            evidence_refs=(),
            target=ExecutiveControlTarget(
                kind=ExecutiveControlTargetKind.ACCOUNT,
                value="proprietary-account:alpha",
            ),
        )
