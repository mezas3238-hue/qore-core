from __future__ import annotations

import json
from datetime import timedelta

from test_ctrader_demo_execution_gateway import (
    _ACCOUNT,
    _NOW,
    _configuration,
    _create_response,
    _FakeExecutionTransport,
    _fill_payload,
    _gateway,
    _submission,
)

from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoExecutionConflictError,
    CTraderDemoFillReconciliationStatus,
)
from qore.infrastructure.ctrader_demo_execution_gateway import CTraderDemoExecutionGateway
from qore.infrastructure.execution_boundary import ExecutionSubmission
from qore.kernel.result import Failure, Success


def _submitted_gateway() -> tuple[CTraderDemoExecutionGateway, ExecutionSubmission]:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission),
    )
    gateway = _gateway(transport=transport)
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Success)
    return gateway, submission


def test_same_deal_event_then_query_updates_projection_without_double_count() -> None:
    gateway, submission = _submitted_gateway()

    event = gateway.observe_fill(
        submission,
        _fill_payload(
            fill_ref="deal-1",
            filled_volume=4,
            cumulative_volume=4,
            is_complete=False,
            timestamp="2026-08-08T23:30:06+00:00",
        ),
        received_at=_NOW + timedelta(seconds=7),
    )
    query = gateway.observe_fill(
        submission,
        _fill_payload(
            fill_ref="deal-1",
            filled_volume=4,
            cumulative_volume=10,
            is_complete=True,
            timestamp="2026-08-08T23:30:07+00:00",
        ),
        received_at=_NOW + timedelta(seconds=8),
    )
    reconciled = gateway.reconcile_fills(
        submission.receipt_id,
        reconciled_at=_NOW + timedelta(seconds=9),
    )

    assert isinstance(event, Success)
    assert isinstance(query, Success)
    assert isinstance(reconciled, Success)
    assert reconciled.value.status is CTraderDemoFillReconciliationStatus.MATCHED
    assert reconciled.value.filled_quantity == submission.authorized_intent.intent.quantity.value


def test_same_deal_late_projection_cannot_regress_authoritative_cumulative() -> None:
    gateway, submission = _submitted_gateway()

    complete = gateway.observe_fill(
        submission,
        _fill_payload(
            fill_ref="deal-1",
            filled_volume=4,
            cumulative_volume=10,
            is_complete=True,
        ),
        received_at=_NOW + timedelta(seconds=7),
    )
    late = gateway.observe_fill(
        submission,
        _fill_payload(
            fill_ref="deal-1",
            filled_volume=4,
            cumulative_volume=4,
            is_complete=False,
        ),
        received_at=_NOW + timedelta(seconds=8),
    )
    reconciled = gateway.reconcile_fills(
        submission.receipt_id,
        reconciled_at=_NOW + timedelta(seconds=9),
    )

    assert isinstance(complete, Success)
    assert isinstance(late, Success)
    assert isinstance(reconciled, Success)
    assert reconciled.value.status is CTraderDemoFillReconciliationStatus.MATCHED


def test_same_deal_reference_with_changed_price_is_a_real_conflict() -> None:
    gateway, submission = _submitted_gateway()
    first = gateway.observe_fill(
        submission,
        _fill_payload(fill_ref="deal-1", cumulative_volume=4),
        received_at=_NOW + timedelta(seconds=7),
    )
    assert isinstance(first, Success)

    changed = json.loads(_fill_payload(fill_ref="deal-1", cumulative_volume=4))
    changed["price"] = "1.23457"
    conflict = gateway.observe_fill(
        submission,
        json.dumps(changed).encode("utf-8"),
        received_at=_NOW + timedelta(seconds=8),
    )

    assert isinstance(conflict, Failure)
    assert isinstance(conflict.error, CTraderDemoExecutionConflictError)
