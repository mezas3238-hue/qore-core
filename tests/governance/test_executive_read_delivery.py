from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_control import (
    AuthorizedExecutiveReadRequest,
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveGrantId,
    ExecutivePrincipalId,
    ExecutiveReadRequest,
    ExecutiveReadRequestId,
    ExecutiveReadScope,
)
from qore.governance.executive_ports import (
    ExecutiveEvidenceRef,
    ExecutivePortError,
    ExecutiveReadDelivery,
    ExecutiveReadQueryPort,
    ExecutiveReadReceipt,
    ExecutiveReadReceiptStatus,
    ExecutiveReceiptId,
    build_executive_read_delivery,
    build_executive_read_receipt,
)
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveReadinessState,
    ExecutiveSourceFreshness,
    ExecutiveSystemHealthReadModel,
    ExecutiveSystemHealthState,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 23, 55, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("35000000-0000-0000-0000-000000000001"))


def _authorized_read(
    scope: ExecutiveReadScope = ExecutiveReadScope.SYSTEM_HEALTH,
) -> AuthorizedExecutiveReadRequest:
    grant = ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("35000000-0000-0000-0000-000000000002")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("executive.v3"),
        allowed_actions=(),
        allowed_read_scopes=(scope,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=10),
        reason="authenticated executive read authority",
    )
    return AuthorizedExecutiveReadRequest(
        request=ExecutiveReadRequest(
            request_id=ExecutiveReadRequestId(
                UUID("35000000-0000-0000-0000-000000000003")
            ),
            principal_id=_PRINCIPAL,
            scope=scope,
            requested_at=_NOW + timedelta(seconds=1),
            correlation_id=_CORRELATION,
        ),
        grant=grant,
        authorized_at=_NOW + timedelta(seconds=2),
    )


def _projection(
    *,
    projected_at: datetime = _NOW + timedelta(seconds=3),
) -> ExecutiveSystemHealthReadModel:
    return ExecutiveSystemHealthReadModel(
        metadata=ExecutiveProjectionMetadata(
            projection_id=ExecutiveProjectionId(
                UUID("35000000-0000-0000-0000-000000000004")
            ),
            projection_version=ExecutiveProjectionVersion("system-health.v1"),
            scope=ExecutiveReadScope.SYSTEM_HEALTH,
            source_observed_at=_NOW,
            projected_at=projected_at,
            freshness=ExecutiveSourceFreshness.FRESH,
            evidence_refs=(ExecutiveEvidenceRef("evidence:health/root-001"),),
        ),
        health=ExecutiveSystemHealthState.HEALTHY,
        readiness=ExecutiveReadinessState.READY,
        attention=ExecutiveAttentionLevel.INFORMATION,
        reason_codes=("system.healthy",),
        components=(),
    )


def _receipt(
    authorized: AuthorizedExecutiveReadRequest,
    *,
    status: ExecutiveReadReceiptStatus = ExecutiveReadReceiptStatus.SERVED,
    completed_at: datetime = _NOW + timedelta(seconds=5),
) -> ExecutiveReadReceipt:
    result = build_executive_read_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(
            UUID("35000000-0000-0000-0000-000000000005")
        ),
        received_at=_NOW + timedelta(seconds=4),
        completed_at=completed_at,
        status=status,
        reason_code="read.served" if status is ExecutiveReadReceiptStatus.SERVED else "read.failed",
        evidence_refs=(ExecutiveEvidenceRef("audit:read/delivery-001"),),
    )
    assert isinstance(result, Success)
    return result.value


def test_read_delivery_binds_real_projection_to_exact_authorization_and_receipt() -> None:
    authorized = _authorized_read()
    projection = _projection()
    receipt = _receipt(authorized)

    result = build_executive_read_delivery(
        authorized,
        projection=projection,
        receipt=receipt,
    )

    assert isinstance(result, Success)
    delivery = result.value
    assert delivery.authorized_request == authorized
    assert delivery.projection == projection
    assert delivery.receipt == receipt
    assert delivery.logical_values() == delivery.logical_values()


def test_read_delivery_rejects_projection_scope_mismatch() -> None:
    authorized = _authorized_read(ExecutiveReadScope.CIBO_STATE)
    receipt = _receipt(authorized)

    result = build_executive_read_delivery(
        authorized,
        projection=_projection(),
        receipt=receipt,
    )

    assert isinstance(result, Failure)


def test_read_delivery_rejects_non_served_receipt() -> None:
    authorized = _authorized_read()

    result = build_executive_read_delivery(
        authorized,
        projection=_projection(),
        receipt=_receipt(authorized, status=ExecutiveReadReceiptStatus.FAILED),
    )

    assert isinstance(result, Failure)


def test_read_delivery_rejects_projection_after_receipt_completion() -> None:
    authorized = _authorized_read()
    receipt = _receipt(
        authorized,
        completed_at=_NOW + timedelta(seconds=5),
    )

    result = build_executive_read_delivery(
        authorized,
        projection=_projection(projected_at=_NOW + timedelta(seconds=6)),
        receipt=receipt,
    )

    assert isinstance(result, Failure)


def test_read_delivery_rejects_receipt_identity_mismatch() -> None:
    authorized = _authorized_read()
    receipt = ExecutiveReadReceipt(
        receipt_id=ExecutiveReceiptId(
            UUID("35000000-0000-0000-0000-000000000006")
        ),
        request_id=ExecutiveReadRequestId(
            UUID("35000000-0000-0000-0000-000000000099")
        ),
        principal_id=authorized.request.principal_id,
        scope=authorized.request.scope,
        authority_version=authorized.grant.authority_version,
        correlation_id=authorized.request.correlation_id,
        received_at=_NOW + timedelta(seconds=4),
        completed_at=_NOW + timedelta(seconds=5),
        status=ExecutiveReadReceiptStatus.SERVED,
        reason_code="read.served",
        evidence_refs=(),
    )

    result = build_executive_read_delivery(
        authorized,
        projection=_projection(),
        receipt=receipt,
    )

    assert isinstance(result, Failure)


class _ReadPort:
    def read(
        self,
        request: AuthorizedExecutiveReadRequest,
    ) -> Result[ExecutiveReadDelivery, ExecutivePortError]:
        receipt = _receipt(request)
        return build_executive_read_delivery(
            request,
            projection=_projection(),
            receipt=receipt,
        )


def _accept_read_port(port: ExecutiveReadQueryPort) -> None:
    result = port.read(_authorized_read())
    assert isinstance(result, Success)
    assert isinstance(result.value, ExecutiveReadDelivery)


def test_query_port_returns_delivery_not_receipt_only() -> None:
    port = _ReadPort()

    _accept_read_port(port)
    result = port.read(_authorized_read())

    assert isinstance(result, Success)
    assert isinstance(result.value, ExecutiveReadDelivery)
    assert not isinstance(result.value, ExecutiveReadReceipt)
    assert not hasattr(port, "execute")
    assert not hasattr(port, "submit_order")
