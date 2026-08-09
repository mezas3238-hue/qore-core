from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_client_surface import ExecutiveClientSurfaceId
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
    ExecutiveReadDelivery,
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
from qore.governance.executive_state_sync import (
    ExecutiveClientStateSnapshot,
    ExecutiveClientStateSnapshotId,
    ExecutiveClientStateStatus,
    ExecutiveClientStateVersion,
    ExecutiveClientStateView,
    ExecutiveClientSubscription,
    ExecutiveClientSubscriptionId,
    ExecutiveClientSubscriptionUpdate,
    ExecutiveStateSyncValidationError,
    build_executive_client_absent_state,
    evaluate_executive_client_state_snapshot,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 11, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("54000000-0000-0000-0000-000000000001"))


def _grant() -> ExecutiveAuthorityGrant:
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("54000000-0000-0000-0000-000000000002")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("executive.v1"),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.SYSTEM_HEALTH,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=20),
        reason="authorized executive read window",
    )


def _authorized_read() -> AuthorizedExecutiveReadRequest:
    return AuthorizedExecutiveReadRequest(
        request=ExecutiveReadRequest(
            request_id=ExecutiveReadRequestId(
                UUID("54000000-0000-0000-0000-000000000003")
            ),
            principal_id=_PRINCIPAL,
            scope=ExecutiveReadScope.SYSTEM_HEALTH,
            requested_at=_NOW + timedelta(seconds=1),
            correlation_id=_CORRELATION,
        ),
        grant=_grant(),
        authorized_at=_NOW + timedelta(seconds=2),
    )


def _projection() -> ExecutiveSystemHealthReadModel:
    return ExecutiveSystemHealthReadModel(
        metadata=ExecutiveProjectionMetadata(
            projection_id=ExecutiveProjectionId(
                UUID("54000000-0000-0000-0000-000000000004")
            ),
            projection_version=ExecutiveProjectionVersion("system-health.v1"),
            scope=ExecutiveReadScope.SYSTEM_HEALTH,
            source_observed_at=_NOW,
            projected_at=_NOW + timedelta(seconds=3),
            freshness=ExecutiveSourceFreshness.FRESH,
            evidence_refs=(ExecutiveEvidenceRef("audit:sync/projection-001"),),
        ),
        health=ExecutiveSystemHealthState.HEALTHY,
        readiness=ExecutiveReadinessState.READY,
        attention=ExecutiveAttentionLevel.INFORMATION,
        reason_codes=("system.healthy",),
        components=(),
    )


def _delivery() -> ExecutiveReadDelivery:
    authorized = _authorized_read()
    receipt = build_executive_read_receipt(
        authorized,
        receipt_id=ExecutiveReceiptId(
            UUID("54000000-0000-0000-0000-000000000005")
        ),
        received_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=4),
        status=ExecutiveReadReceiptStatus.SERVED,
        reason_code="read.served",
    )
    assert isinstance(receipt, Success)
    delivery = build_executive_read_delivery(
        authorized,
        projection=_projection(),
        receipt=receipt.value,
    )
    assert isinstance(delivery, Success)
    return delivery.value


def _snapshot() -> ExecutiveClientStateSnapshot:
    return ExecutiveClientStateSnapshot(
        snapshot_id=ExecutiveClientStateSnapshotId(
            UUID("54000000-0000-0000-0000-000000000006")
        ),
        version=ExecutiveClientStateVersion(7),
        delivery=_delivery(),
        received_at=_NOW + timedelta(seconds=5),
        fresh_until=_NOW + timedelta(seconds=15),
    )


def test_snapshot_evaluates_current_then_stale_without_guessing() -> None:
    snapshot = _snapshot()
    current = evaluate_executive_client_state_snapshot(
        snapshot,
        evaluated_at=snapshot.fresh_until,
    )
    stale = evaluate_executive_client_state_snapshot(
        snapshot,
        evaluated_at=snapshot.fresh_until + timedelta(microseconds=1),
    )

    assert isinstance(current, Success)
    assert current.value.status is ExecutiveClientStateStatus.CURRENT
    assert current.value.snapshot is snapshot
    assert isinstance(stale, Success)
    assert stale.value.status is ExecutiveClientStateStatus.STALE
    assert stale.value.snapshot is snapshot
    assert current.value.logical_values() == current.value.logical_values()


def test_absent_state_is_explicitly_unavailable_or_unknown() -> None:
    unavailable = build_executive_client_absent_state(
        status=ExecutiveClientStateStatus.UNAVAILABLE,
        scope=ExecutiveReadScope.SYSTEM_HEALTH,
        observed_at=_NOW + timedelta(seconds=20),
        reason_code="source.unavailable",
    )
    unknown = build_executive_client_absent_state(
        status=ExecutiveClientStateStatus.UNKNOWN,
        scope=ExecutiveReadScope.SYSTEM_HEALTH,
        observed_at=_NOW + timedelta(seconds=20),
        reason_code="source.unknown",
    )

    assert isinstance(unavailable, Success)
    assert unavailable.value.snapshot is None
    assert isinstance(unknown, Success)
    assert unknown.value.snapshot is None


def test_absent_builder_rejects_current_or_stale_status() -> None:
    for status in (
        ExecutiveClientStateStatus.CURRENT,
        ExecutiveClientStateStatus.STALE,
    ):
        result = build_executive_client_absent_state(
            status=status,
            scope=ExecutiveReadScope.SYSTEM_HEALTH,
            observed_at=_NOW,
            reason_code="source.invalid",
        )
        assert isinstance(result, Failure)


def test_state_version_is_strict_positive_int_not_bool() -> None:
    with pytest.raises(ExecutiveStateSyncValidationError):
        ExecutiveClientStateVersion(0)
    with pytest.raises(ExecutiveStateSyncValidationError):
        ExecutiveClientStateVersion(cast(int, True))
    with pytest.raises(ExecutiveStateSyncValidationError):
        ExecutiveClientStateVersion(cast(int, "7"))


def test_subscription_update_binds_exact_read_scope_only() -> None:
    subscription = ExecutiveClientSubscription(
        subscription_id=ExecutiveClientSubscriptionId(
            UUID("54000000-0000-0000-0000-000000000007")
        ),
        surface_id=ExecutiveClientSurfaceId(
            UUID("54000000-0000-0000-0000-000000000008")
        ),
        scope=ExecutiveReadScope.SYSTEM_HEALTH,
        created_at=_NOW,
    )
    update = ExecutiveClientSubscriptionUpdate(
        subscription=subscription,
        snapshot=_snapshot(),
        delivered_at=_NOW + timedelta(seconds=6),
    )

    assert update.snapshot.scope is subscription.scope
    assert not hasattr(subscription, "command")
    assert not hasattr(subscription, "authority")
    assert not hasattr(update, "execute")

    wrong_scope = ExecutiveClientSubscription(
        subscription_id=ExecutiveClientSubscriptionId(UUID(int=9)),
        surface_id=subscription.surface_id,
        scope=ExecutiveReadScope.GOVERNANCE,
        created_at=_NOW,
    )
    with pytest.raises(ExecutiveStateSyncValidationError):
        ExecutiveClientSubscriptionUpdate(
            subscription=wrong_scope,
            snapshot=_snapshot(),
            delivered_at=_NOW + timedelta(seconds=6),
        )


def test_subscription_delivery_and_snapshot_chronology_fail_closed() -> None:
    snapshot = _snapshot()
    subscription = ExecutiveClientSubscription(
        subscription_id=ExecutiveClientSubscriptionId(UUID(int=10)),
        surface_id=ExecutiveClientSurfaceId(UUID(int=11)),
        scope=ExecutiveReadScope.SYSTEM_HEALTH,
        created_at=_NOW,
    )
    with pytest.raises(ExecutiveStateSyncValidationError):
        ExecutiveClientSubscriptionUpdate(
            subscription=subscription,
            snapshot=snapshot,
            delivered_at=snapshot.received_at - timedelta(microseconds=1),
        )
    with pytest.raises(ExecutiveStateSyncValidationError):
        ExecutiveClientStateSnapshot(
            snapshot_id=ExecutiveClientStateSnapshotId(UUID(int=12)),
            version=ExecutiveClientStateVersion(1),
            delivery=_delivery(),
            received_at=_NOW + timedelta(seconds=5),
            fresh_until=_NOW + timedelta(seconds=4),
        )


def test_manual_current_or_stale_misclassification_fails_closed() -> None:
    snapshot = _snapshot()
    with pytest.raises(ExecutiveStateSyncValidationError):
        ExecutiveClientStateView(
            status=ExecutiveClientStateStatus.CURRENT,
            scope=snapshot.scope,
            observed_at=snapshot.fresh_until + timedelta(microseconds=1),
            reason_code="snapshot.current",
            snapshot=snapshot,
        )
    with pytest.raises(ExecutiveStateSyncValidationError):
        ExecutiveClientStateView(
            status=ExecutiveClientStateStatus.STALE,
            scope=snapshot.scope,
            observed_at=snapshot.fresh_until,
            reason_code="snapshot.stale",
            snapshot=snapshot,
        )
