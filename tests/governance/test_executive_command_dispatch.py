from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_command_dispatch import (
    ExecutiveCommandDispatchBlockedError,
    ExecutiveCommandDispatcher,
    ExecutiveCommandDispatchReason,
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
from qore.governance.executive_ports import (
    ExecutiveControlReceipt,
    ExecutiveControlReceiptStatus,
    ExecutiveEvidenceRef,
    ExecutivePortError,
    ExecutivePortValidationError,
    ExecutiveReceiptId,
    build_executive_control_receipt,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 2, 30, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("44000000-0000-0000-0000-000000000001"))


def _authorized() -> AuthorizedExecutiveControlIntent:
    grant = ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("44000000-0000-0000-0000-000000000002")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v1"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=10),
        reason="mission04 command dispatch",
    )
    intent = ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("44000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
        reason="CEO requests governed pause",
    )
    return AuthorizedExecutiveControlIntent(
        intent=intent,
        grant=grant,
        authorized_at=_NOW + timedelta(minutes=2),
    )


def _receipt(
    authorized: AuthorizedExecutiveControlIntent,
    *,
    status: ExecutiveControlReceiptStatus = ExecutiveControlReceiptStatus.APPLIED,
    reason_code: str = "governance.applied",
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = (
        ExecutiveEvidenceRef("audit:control/44000000"),
    ),
) -> ExecutiveControlReceipt:
    result = build_executive_control_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(
            UUID("44000000-0000-0000-0000-000000000004")
        ),
        received_at=_NOW + timedelta(minutes=2, seconds=1),
        completed_at=_NOW + timedelta(minutes=2, seconds=2),
        status=status,
        reason_code=reason_code,
        evidence_refs=evidence_refs,
    )
    assert isinstance(result, Success)
    return result.value


class _FakeCommandPort:
    def __init__(
        self,
        *,
        receipt: ExecutiveControlReceipt | None = None,
        error: ExecutivePortError | None = None,
    ) -> None:
        self.receipt = receipt
        self.error = error
        self.requests: list[AuthorizedExecutiveControlIntent] = []

    def apply(
        self,
        request: AuthorizedExecutiveControlIntent,
    ) -> Result[ExecutiveControlReceipt, ExecutivePortError]:
        self.requests.append(request)
        if self.error is not None:
            return Failure(self.error)
        if self.receipt is None:
            return Failure(ExecutivePortValidationError("receipt unavailable"))
        return Success(self.receipt)


def _blocked_reason(result: object) -> ExecutiveCommandDispatchReason:
    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveCommandDispatchBlockedError)
    return result.error.reason


def test_dispatch_calls_command_port_exactly_once_and_preserves_exact_receipt() -> None:
    authorized = _authorized()
    receipt = _receipt(authorized)
    port = _FakeCommandPort(receipt=receipt)

    result = ExecutiveCommandDispatcher(port).dispatch(authorized)

    assert isinstance(result, Success)
    assert result.value is receipt
    assert port.requests == [authorized]


def test_valid_downstream_blocked_and_failed_statuses_remain_receipt_outcomes() -> None:
    authorized = _authorized()

    for status in (
        ExecutiveControlReceiptStatus.BLOCKED,
        ExecutiveControlReceiptStatus.FAILED,
        ExecutiveControlReceiptStatus.NO_CHANGE,
    ):
        receipt = _receipt(
            authorized,
            status=status,
            reason_code=f"governance.{status.value}",
        )
        result = ExecutiveCommandDispatcher(
            _FakeCommandPort(receipt=receipt)
        ).dispatch(authorized)

        assert isinstance(result, Success)
        assert result.value.status is status


def test_downstream_failure_is_sanitized_and_never_retried() -> None:
    authorized = _authorized()
    port = _FakeCommandPort(
        error=ExecutivePortValidationError("database password=private token=abc")
    )

    result = ExecutiveCommandDispatcher(port).dispatch(authorized)

    assert _blocked_reason(result) is ExecutiveCommandDispatchReason.DOWNSTREAM_FAILED
    assert len(port.requests) == 1
    assert isinstance(result, Failure)
    assert "password" not in str(result.error).lower()
    assert "token" not in str(result.error).lower()


def test_receipt_identity_mismatch_fails_closed_without_second_call() -> None:
    authorized = _authorized()
    valid = _receipt(authorized)
    mismatched = replace(valid, principal_id=ExecutivePrincipalId("ceo.other"))
    port = _FakeCommandPort(receipt=mismatched)

    result = ExecutiveCommandDispatcher(port).dispatch(authorized)

    assert _blocked_reason(result) is ExecutiveCommandDispatchReason.RECEIPT_MISMATCH
    assert len(port.requests) == 1


def test_receipt_received_before_authorization_fails_closed() -> None:
    authorized = _authorized()
    valid = _receipt(authorized)
    early = replace(
        valid,
        received_at=authorized.authorized_at - timedelta(microseconds=1),
        completed_at=authorized.authorized_at,
    )

    result = ExecutiveCommandDispatcher(
        _FakeCommandPort(receipt=early)
    ).dispatch(authorized)

    assert _blocked_reason(result) is ExecutiveCommandDispatchReason.RECEIPT_MISMATCH


def test_secret_like_receipt_reason_or_evidence_is_rejected() -> None:
    authorized = _authorized()
    unsafe_reason = _receipt(authorized, reason_code="token")
    unsafe_evidence = _receipt(
        authorized,
        evidence_refs=(ExecutiveEvidenceRef("audit:token/private"),),
    )

    reason_result = ExecutiveCommandDispatcher(
        _FakeCommandPort(receipt=unsafe_reason)
    ).dispatch(authorized)
    evidence_result = ExecutiveCommandDispatcher(
        _FakeCommandPort(receipt=unsafe_evidence)
    ).dispatch(authorized)

    assert _blocked_reason(reason_result) is ExecutiveCommandDispatchReason.RECEIPT_UNSAFE
    assert (
        _blocked_reason(evidence_result)
        is ExecutiveCommandDispatchReason.RECEIPT_UNSAFE
    )
