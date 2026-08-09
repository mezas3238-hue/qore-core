from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_control import (
    AuthorizedExecutiveReadRequest,
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveControlAction,
    ExecutiveGrantId,
    ExecutivePrincipalId,
    ExecutiveReadRequest,
    ExecutiveReadRequestId,
    ExecutiveReadScope,
)
from qore.governance.executive_ports import (
    ExecutiveEvidenceRef,
    ExecutivePortError,
    ExecutivePortValidationError,
    ExecutiveReadDelivery,
    ExecutiveReadReceiptStatus,
    ExecutiveReceiptId,
    build_executive_read_delivery,
    build_executive_read_receipt,
)
from qore.governance.executive_query_dispatch import (
    ExecutiveQueryDispatchBlockedError,
    ExecutiveQueryDispatcher,
    ExecutiveQueryDispatchReason,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 3, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("45000000-0000-0000-0000-000000000001"))
_REQUEST_UUID = UUID("45000000-0000-0000-0000-000000000002")


@dataclass(frozen=True, slots=True)
class _ProjectionMetadata:
    scope: ExecutiveReadScope
    projected_at: datetime


@dataclass(frozen=True, slots=True)
class _Projection:
    metadata: _ProjectionMetadata
    value: str

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.scope.value,
            self.metadata.projected_at.isoformat(),
            self.value,
        )


def _authorized(
    *,
    request_id: UUID = _REQUEST_UUID,
) -> AuthorizedExecutiveReadRequest:
    grant = ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("45000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v1"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=10),
        reason="mission04 query dispatch",
    )
    request = ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(request_id),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.GOVERNANCE,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
    )
    return AuthorizedExecutiveReadRequest(
        request=request,
        grant=grant,
        authorized_at=_NOW + timedelta(minutes=2),
    )


def _delivery(
    authorized: AuthorizedExecutiveReadRequest,
    *,
    reason_code: str = "read.served",
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = (
        ExecutiveEvidenceRef("audit:read/45000000"),
    ),
) -> ExecutiveReadDelivery:
    receipt_result = build_executive_read_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(
            UUID("45000000-0000-0000-0000-000000000004")
        ),
        received_at=_NOW + timedelta(minutes=2, seconds=1),
        completed_at=_NOW + timedelta(minutes=2, seconds=3),
        status=ExecutiveReadReceiptStatus.SERVED,
        reason_code=reason_code,
        evidence_refs=evidence_refs,
    )
    assert isinstance(receipt_result, Success)
    projection = _Projection(
        metadata=_ProjectionMetadata(
            scope=ExecutiveReadScope.GOVERNANCE,
            projected_at=_NOW + timedelta(minutes=2, seconds=2),
        ),
        value="governance-state",
    )
    delivery_result = build_executive_read_delivery(
        authorized,
        projection=projection,
        receipt=receipt_result.value,
    )
    assert isinstance(delivery_result, Success)
    return delivery_result.value


class _FakeQueryPort:
    def __init__(
        self,
        *,
        delivery: ExecutiveReadDelivery | None = None,
        error: ExecutivePortError | None = None,
    ) -> None:
        self.delivery = delivery
        self.error = error
        self.requests: list[AuthorizedExecutiveReadRequest] = []

    def read(
        self,
        request: AuthorizedExecutiveReadRequest,
    ) -> Result[ExecutiveReadDelivery, ExecutivePortError]:
        self.requests.append(request)
        if self.error is not None:
            return Failure(self.error)
        if self.delivery is None:
            return Failure(ExecutivePortValidationError("delivery unavailable"))
        return Success(self.delivery)


def _blocked_reason(result: object) -> ExecutiveQueryDispatchReason:
    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveQueryDispatchBlockedError)
    return result.error.reason


def test_dispatch_calls_query_port_exactly_once_and_preserves_delivery() -> None:
    authorized = _authorized()
    delivery = _delivery(authorized)
    port = _FakeQueryPort(delivery=delivery)

    result = ExecutiveQueryDispatcher(port).dispatch(authorized)

    assert isinstance(result, Success)
    assert result.value is delivery
    assert port.requests == [authorized]


def test_downstream_failure_is_sanitized_and_never_retried() -> None:
    authorized = _authorized()
    port = _FakeQueryPort(
        error=ExecutivePortValidationError("storage password=private token=abc")
    )

    result = ExecutiveQueryDispatcher(port).dispatch(authorized)

    assert _blocked_reason(result) is ExecutiveQueryDispatchReason.DOWNSTREAM_FAILED
    assert len(port.requests) == 1
    assert isinstance(result, Failure)
    assert "password" not in str(result.error).lower()
    assert "token" not in str(result.error).lower()


def test_delivery_for_different_authorization_fails_closed() -> None:
    authorized = _authorized()
    other_authorized = _authorized(
        request_id=UUID("45000000-0000-0000-0000-000000000009")
    )
    port = _FakeQueryPort(delivery=_delivery(other_authorized))

    result = ExecutiveQueryDispatcher(port).dispatch(authorized)

    assert _blocked_reason(result) is ExecutiveQueryDispatchReason.DELIVERY_MISMATCH
    assert len(port.requests) == 1


def test_secret_like_receipt_reason_or_evidence_is_rejected() -> None:
    authorized = _authorized()
    unsafe_reason = _delivery(authorized, reason_code="token")
    unsafe_evidence = _delivery(
        authorized,
        evidence_refs=(ExecutiveEvidenceRef("audit:secret/private"),),
    )

    reason_result = ExecutiveQueryDispatcher(
        _FakeQueryPort(delivery=unsafe_reason)
    ).dispatch(authorized)
    evidence_result = ExecutiveQueryDispatcher(
        _FakeQueryPort(delivery=unsafe_evidence)
    ).dispatch(authorized)

    assert _blocked_reason(reason_result) is ExecutiveQueryDispatchReason.RECEIPT_UNSAFE
    assert (
        _blocked_reason(evidence_result)
        is ExecutiveQueryDispatchReason.RECEIPT_UNSAFE
    )
