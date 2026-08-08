from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
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
from qore.governance.executive_ports import (
    ExecutiveControlCommandPort,
    ExecutiveControlReceipt,
    ExecutiveControlReceiptStatus,
    ExecutiveEvidenceRef,
    ExecutivePortError,
    ExecutivePortValidationError,
    ExecutiveReadQueryPort,
    ExecutiveReadReceipt,
    ExecutiveReadReceiptStatus,
    ExecutiveReceiptId,
    build_executive_control_receipt,
    build_executive_read_receipt,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 20, 30, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("28000000-0000-0000-0000-000000000001"))


def _grant() -> ExecutiveAuthorityGrant:
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("28000000-0000-0000-0000-000000000002")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("executive.v1"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.SYSTEM_HEALTH,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=10),
        reason="authenticated CEO authority window",
    )


def _authorized_control() -> AuthorizedExecutiveControlIntent:
    return AuthorizedExecutiveControlIntent(
        intent=ExecutiveControlIntent(
            intent_id=ExecutiveIntentId(
                UUID("28000000-0000-0000-0000-000000000003")
            ),
            principal_id=_PRINCIPAL,
            action=ExecutiveControlAction.PAUSE_SYSTEM,
            requested_at=_NOW + timedelta(seconds=1),
            correlation_id=_CORRELATION,
            reason="controlled CEO pause request",
        ),
        grant=_grant(),
        authorized_at=_NOW + timedelta(seconds=2),
    )


def _authorized_read() -> AuthorizedExecutiveReadRequest:
    return AuthorizedExecutiveReadRequest(
        request=ExecutiveReadRequest(
            request_id=ExecutiveReadRequestId(
                UUID("28000000-0000-0000-0000-000000000004")
            ),
            principal_id=_PRINCIPAL,
            scope=ExecutiveReadScope.SYSTEM_HEALTH,
            requested_at=_NOW + timedelta(seconds=1),
            correlation_id=_CORRELATION,
        ),
        grant=_grant(),
        authorized_at=_NOW + timedelta(seconds=2),
    )


def test_control_receipt_derives_identity_from_authorized_intent() -> None:
    authorized = _authorized_control()

    result = build_executive_control_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(
            UUID("28000000-0000-0000-0000-000000000005")
        ),
        received_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=4),
        status=ExecutiveControlReceiptStatus.APPLIED,
        reason_code="governance.applied",
        evidence_refs=(ExecutiveEvidenceRef("audit:control/001"),),
    )

    assert isinstance(result, Success)
    receipt = result.value
    assert receipt.intent_id == authorized.intent.intent_id
    assert receipt.principal_id == authorized.intent.principal_id
    assert receipt.action == authorized.intent.action
    assert receipt.authority_version == authorized.grant.authority_version
    assert receipt.correlation_id == authorized.intent.correlation_id


def test_control_receipt_cannot_predate_authorization() -> None:
    result = build_executive_control_receipt(
        _authorized_control(),
        receipt_id=ExecutiveReceiptId(
            UUID("28000000-0000-0000-0000-000000000006")
        ),
        received_at=_NOW + timedelta(seconds=1),
        completed_at=_NOW + timedelta(seconds=3),
        status=ExecutiveControlReceiptStatus.APPLIED,
        reason_code="governance.applied",
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutivePortValidationError)


def test_receipt_completion_cannot_predate_receipt_time() -> None:
    result = build_executive_control_receipt(
        _authorized_control(),
        receipt_id=ExecutiveReceiptId(
            UUID("28000000-0000-0000-0000-000000000007")
        ),
        received_at=_NOW + timedelta(seconds=4),
        completed_at=_NOW + timedelta(seconds=3),
        status=ExecutiveControlReceiptStatus.FAILED,
        reason_code="governance.failed",
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutivePortValidationError)


def test_evidence_refs_are_stable_and_deduplicated() -> None:
    result = build_executive_control_receipt(
        _authorized_control(),
        receipt_id=ExecutiveReceiptId(
            UUID("28000000-0000-0000-0000-000000000008")
        ),
        received_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=4),
        status=ExecutiveControlReceiptStatus.NO_CHANGE,
        reason_code="governance.no_change",
        evidence_refs=(
            ExecutiveEvidenceRef("audit:z/002"),
            ExecutiveEvidenceRef("audit:a/001"),
        ),
    )

    assert isinstance(result, Success)
    assert tuple(item.value for item in result.value.evidence_refs) == (
        "audit:a/001",
        "audit:z/002",
    )

    with pytest.raises(ExecutivePortValidationError):
        ExecutiveControlReceipt(
            receipt_id=ExecutiveReceiptId(
                UUID("28000000-0000-0000-0000-000000000009")
            ),
            intent_id=_authorized_control().intent.intent_id,
            principal_id=_PRINCIPAL,
            action=ExecutiveControlAction.PAUSE_SYSTEM,
            authority_version=ExecutiveAuthorityVersion("executive.v1"),
            correlation_id=_CORRELATION,
            received_at=_NOW + timedelta(seconds=3),
            completed_at=_NOW + timedelta(seconds=4),
            status=ExecutiveControlReceiptStatus.APPLIED,
            reason_code="governance.applied",
            evidence_refs=(
                ExecutiveEvidenceRef("audit:duplicate/001"),
                ExecutiveEvidenceRef("audit:duplicate/001"),
            ),
        )


def test_reason_code_is_canonical_and_cannot_carry_secret_material() -> None:
    result = build_executive_control_receipt(
        _authorized_control(),
        receipt_id=ExecutiveReceiptId(
            UUID("28000000-0000-0000-0000-000000000010")
        ),
        received_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=4),
        status=ExecutiveControlReceiptStatus.BLOCKED,
        reason_code="token=secret",
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutivePortValidationError)


def test_read_receipt_derives_scope_and_authority_from_authorized_request() -> None:
    authorized = _authorized_read()

    result = build_executive_read_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(
            UUID("28000000-0000-0000-0000-000000000011")
        ),
        received_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=4),
        status=ExecutiveReadReceiptStatus.SERVED,
        reason_code="read.served",
        evidence_refs=(ExecutiveEvidenceRef("audit:read/001"),),
    )

    assert isinstance(result, Success)
    receipt = result.value
    assert receipt.request_id == authorized.request.request_id
    assert receipt.principal_id == authorized.request.principal_id
    assert receipt.scope == ExecutiveReadScope.SYSTEM_HEALTH
    assert receipt.authority_version == authorized.grant.authority_version
    assert receipt.correlation_id == authorized.request.correlation_id


def test_receipts_are_audit_metadata_not_read_model_payloads() -> None:
    control = build_executive_control_receipt(
        _authorized_control(),
        receipt_id=ExecutiveReceiptId(
            UUID("28000000-0000-0000-0000-000000000012")
        ),
        received_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=4),
        status=ExecutiveControlReceiptStatus.APPLIED,
        reason_code="governance.applied",
    )
    read = build_executive_read_receipt(
        _authorized_read(),
        receipt_id=ExecutiveReceiptId(
            UUID("28000000-0000-0000-0000-000000000013")
        ),
        received_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=4),
        status=ExecutiveReadReceiptStatus.SERVED,
        reason_code="read.served",
    )

    assert isinstance(control, Success)
    assert isinstance(read, Success)
    assert not hasattr(control.value, "order")
    assert not hasattr(control.value, "broker")
    assert not hasattr(read.value, "balance")
    assert not hasattr(read.value, "profit_vault_payload")


class _ControlPort:
    def apply(
        self,
        request: AuthorizedExecutiveControlIntent,
    ) -> Result[ExecutiveControlReceipt, ExecutivePortError]:
        return build_executive_control_receipt(
            request,
            receipt_id=ExecutiveReceiptId(
                UUID("28000000-0000-0000-0000-000000000014")
            ),
            received_at=_NOW + timedelta(seconds=3),
            completed_at=_NOW + timedelta(seconds=4),
            status=ExecutiveControlReceiptStatus.APPLIED,
            reason_code="governance.applied",
        )


class _ReadPort:
    def read(
        self,
        request: AuthorizedExecutiveReadRequest,
    ) -> Result[ExecutiveReadReceipt, ExecutivePortError]:
        return build_executive_read_receipt(
            request,
            receipt_id=ExecutiveReceiptId(
                UUID("28000000-0000-0000-0000-000000000015")
            ),
            received_at=_NOW + timedelta(seconds=3),
            completed_at=_NOW + timedelta(seconds=4),
            status=ExecutiveReadReceiptStatus.SERVED,
            reason_code="read.served",
        )


def _accept_control_port(port: ExecutiveControlCommandPort) -> None:
    assert callable(port.apply)


def _accept_read_port(port: ExecutiveReadQueryPort) -> None:
    assert callable(port.read)


def test_protocols_expose_only_authorized_command_and_read_surfaces() -> None:
    control = _ControlPort()
    read = _ReadPort()

    _accept_control_port(control)
    _accept_read_port(read)

    assert callable(control.apply)
    assert callable(read.read)
    assert not hasattr(control, "submit_order")
    assert not hasattr(control, "cancel_order")
    assert not hasattr(read, "execute")


def test_receipt_logical_values_are_deterministic() -> None:
    result = build_executive_read_receipt(
        _authorized_read(),
        receipt_id=ExecutiveReceiptId(
            UUID("28000000-0000-0000-0000-000000000016")
        ),
        received_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=4),
        status=ExecutiveReadReceiptStatus.SERVED,
        reason_code="read.served",
        evidence_refs=(ExecutiveEvidenceRef("audit:read/002"),),
    )

    assert isinstance(result, Success)
    values = result.value.logical_values()
    assert values == result.value.logical_values()
    assert "executive.v1" in repr(values)
    assert "secret" not in repr(values).lower()
