from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.client_trial_licensing as licensing
import qore.infrastructure.hosting_commercial_suspension as suspension

_NOW = datetime(2026, 8, 10, 0, 0, tzinfo=UTC)
_ACCOUNT = accounts.TradingAccountId(UUID("52000000-0000-0000-0000-000000000003"))
_RUNTIME = accounts.ExecutionRuntimeReference(
    UUID("52000000-0000-0000-0000-000000000004")
)
_ENTITLEMENT = accounts.ProductEntitlementReference(
    UUID("52000000-0000-0000-0000-000000000005")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"52000000-0000-0000-0000-{suffix:012d}")


def _evaluate(
    payment: licensing.CommercialPaymentStanding,
    *,
    open_positions: int,
) -> suspension.HostingCommercialSuspensionSnapshot:
    return suspension.evaluate_hosting_commercial_suspension(
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        entitlement_ref=_ENTITLEMENT,
        payment_standing=payment,
        open_positions=open_positions,
        evaluated_at=_NOW,
        evidence_ref=suspension.HostingCommercialEvidenceReference(_uuid(10)),
    )


def test_current_hosting_payment_keeps_runtime_commercially_active() -> None:
    snapshot = _evaluate(
        licensing.CommercialPaymentStanding.CURRENT,
        open_positions=0,
    )

    assert snapshot.state is suspension.HostingCommercialState.ACTIVE
    assert snapshot.disposition is (
        suspension.HostingRuntimeCommercialDisposition.KEEP_ACTIVE
    )
    assert snapshot.allows_new_trades is True
    assert snapshot.preserve_authorized_position_lifecycle is False


def test_payment_failure_with_open_position_enters_safe_pending_suspension() -> None:
    snapshot = _evaluate(
        licensing.CommercialPaymentStanding.PAYMENT_FAILED,
        open_positions=1,
    )

    assert snapshot.state is suspension.HostingCommercialState.SUSPEND_PENDING_FLAT
    assert snapshot.disposition is (
        suspension.HostingRuntimeCommercialDisposition.PRESERVE_POSITION_LIFECYCLE
    )
    assert snapshot.allows_new_trades is False
    assert snapshot.preserve_authorized_position_lifecycle is True
    assert not hasattr(snapshot, "close_position")
    assert not hasattr(snapshot, "liquidate")


def test_payment_failure_when_flat_allows_runtime_stop_but_not_trade_close() -> None:
    snapshot = _evaluate(
        licensing.CommercialPaymentStanding.PAYMENT_FAILED,
        open_positions=0,
    )

    assert snapshot.state is suspension.HostingCommercialState.SUSPENDED
    assert snapshot.disposition is (
        suspension.HostingRuntimeCommercialDisposition.MAY_STOP_WHEN_FLAT
    )
    assert snapshot.allows_new_trades is False
    assert snapshot.preserve_authorized_position_lifecycle is False
    assert not hasattr(snapshot, "stop_runtime")


def test_unknown_payment_fails_closed_and_preserves_open_position_lifecycle() -> None:
    snapshot = _evaluate(
        licensing.CommercialPaymentStanding.UNKNOWN,
        open_positions=2,
    )

    assert snapshot.state is suspension.HostingCommercialState.UNKNOWN
    assert snapshot.disposition is (
        suspension.HostingRuntimeCommercialDisposition.PRESERVE_POSITION_LIFECYCLE
    )
    assert snapshot.allows_new_trades is False
    assert snapshot.preserve_authorized_position_lifecycle is True


def test_unknown_payment_when_flat_never_becomes_active() -> None:
    snapshot = _evaluate(
        licensing.CommercialPaymentStanding.UNKNOWN,
        open_positions=0,
    )

    assert snapshot.state is suspension.HostingCommercialState.UNKNOWN
    assert snapshot.disposition is (
        suspension.HostingRuntimeCommercialDisposition.MAY_STOP_WHEN_FLAT
    )
    assert snapshot.allows_new_trades is False


def test_open_positions_must_be_non_negative_real_integer() -> None:
    for invalid in (-1, True):
        with pytest.raises(suspension.HostingCommercialSuspensionValidationError):
            suspension.evaluate_hosting_commercial_suspension(
                account_id=_ACCOUNT,
                runtime_ref=_RUNTIME,
                entitlement_ref=_ENTITLEMENT,
                payment_standing=licensing.CommercialPaymentStanding.CURRENT,
                open_positions=invalid,
                evaluated_at=_NOW,
                evidence_ref=suspension.HostingCommercialEvidenceReference(_uuid(11)),
            )


def test_snapshot_is_immutable() -> None:
    snapshot = _evaluate(
        licensing.CommercialPaymentStanding.CURRENT,
        open_positions=0,
    )
    attribute_name = "open_positions"

    with pytest.raises(FrozenInstanceError):
        setattr(snapshot, attribute_name, 1)


def test_commercial_suspension_has_no_billing_widget_or_trading_authority() -> None:
    snapshot = _evaluate(
        licensing.CommercialPaymentStanding.PAYMENT_FAILED,
        open_positions=1,
    )
    prohibited = (
        "broker",
        "close_position",
        "liquidate",
        "mark_paid",
        "redispatch",
        "retry",
        "set_risk",
        "submit_order",
        "suspend_widget",
    )

    for name in prohibited:
        assert not hasattr(snapshot, name)
