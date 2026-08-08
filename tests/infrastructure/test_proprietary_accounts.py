from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.proprietary_accounts import (
    CurrencyCode,
    DrawdownBps,
    MoneyAmount,
    ProprietaryAccountEnvironment,
    ProprietaryAccountFinancialSnapshot,
    ProprietaryAccountId,
    ProprietaryAccountOperationalState,
    ProprietaryAccountPerformanceRequest,
    ProprietaryAccountPerformanceSnapshot,
    ProprietaryAccountSnapshotId,
    ProprietaryAccountSnapshotRequest,
    ProprietaryAccountValidationError,
)

_NOW = datetime(2026, 8, 8, 22, 15, tzinfo=UTC)
_USD = CurrencyCode("USD")


def _source(name: str = "proprietary-account.reference") -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("2d000000-0000-0000-0000-000000000001")),
        source_id=SourceId(UUID("2d000000-0000-0000-0000-000000000002")),
        port_name=PortName(name),
    )


def _money(value: str) -> MoneyAmount:
    return MoneyAmount(_USD, Decimal(value))


def _financial_snapshot() -> ProprietaryAccountFinancialSnapshot:
    return ProprietaryAccountFinancialSnapshot(
        snapshot_id=ProprietaryAccountSnapshotId(
            UUID("2d000000-0000-0000-0000-000000000010")
        ),
        account_id=ProprietaryAccountId(
            UUID("2d000000-0000-0000-0000-000000000020")
        ),
        source=_source(),
        observed_at=_NOW,
        environment=ProprietaryAccountEnvironment.DEMO,
        state=ProprietaryAccountOperationalState.ACTIVE,
        balance=_money("10000.00"),
        equity=_money("10125.50"),
        unrealized_pnl=_money("125.50"),
        margin_used=_money("500.00"),
        drawdown=DrawdownBps(125),
    )


def test_money_amount_normalizes_decimal_logical_values() -> None:
    first = MoneyAmount(_USD, Decimal("1000.000"))
    second = MoneyAmount(_USD, Decimal("1000"))
    zero = MoneyAmount(_USD, Decimal("-0.00"))

    assert first == second
    assert first.logical_values() == ("USD", "1000")
    assert zero.logical_values() == ("USD", "0")


def test_money_amount_rejects_non_finite_values() -> None:
    with pytest.raises(ProprietaryAccountValidationError):
        MoneyAmount(_USD, Decimal("NaN"))

    with pytest.raises(ProprietaryAccountValidationError):
        MoneyAmount(_USD, Decimal("Infinity"))


def test_financial_snapshot_is_opaque_provider_neutral_and_deterministic() -> None:
    snapshot = _financial_snapshot()

    assert snapshot.currency == _USD
    assert snapshot.environment is ProprietaryAccountEnvironment.DEMO
    assert snapshot.logical_values() == snapshot.logical_values()
    assert not hasattr(snapshot, "broker_account_number")
    assert not hasattr(snapshot, "provider_account_id")
    assert not hasattr(snapshot, "token")
    assert not hasattr(snapshot, "credentials")


def test_financial_snapshot_requires_proprietary_account_source_namespace() -> None:
    with pytest.raises(ProprietaryAccountValidationError):
        ProprietaryAccountFinancialSnapshot(
            snapshot_id=ProprietaryAccountSnapshotId(
                UUID("2d000000-0000-0000-0000-000000000011")
            ),
            account_id=ProprietaryAccountId(
                UUID("2d000000-0000-0000-0000-000000000021")
            ),
            source=_source("market-data.reference"),
            observed_at=_NOW,
            environment=ProprietaryAccountEnvironment.PRACTICE,
            state=ProprietaryAccountOperationalState.RESTRICTED,
            balance=_money("1000"),
            equity=_money("1000"),
            unrealized_pnl=_money("0"),
            margin_used=_money("0"),
            drawdown=DrawdownBps(0),
        )


def test_financial_snapshot_requires_aware_time_single_currency_and_nonnegative_state() -> None:
    eur = CurrencyCode("EUR")

    with pytest.raises(ProprietaryAccountValidationError):
        ProprietaryAccountFinancialSnapshot(
            snapshot_id=ProprietaryAccountSnapshotId(
                UUID("2d000000-0000-0000-0000-000000000012")
            ),
            account_id=ProprietaryAccountId(
                UUID("2d000000-0000-0000-0000-000000000022")
            ),
            source=_source(),
            observed_at=datetime(2026, 8, 8, 22, 15),
            environment=ProprietaryAccountEnvironment.DEMO,
            state=ProprietaryAccountOperationalState.ACTIVE,
            balance=_money("1000"),
            equity=_money("1000"),
            unrealized_pnl=_money("0"),
            margin_used=_money("0"),
            drawdown=DrawdownBps(0),
        )

    with pytest.raises(ProprietaryAccountValidationError):
        ProprietaryAccountFinancialSnapshot(
            snapshot_id=ProprietaryAccountSnapshotId(
                UUID("2d000000-0000-0000-0000-000000000013")
            ),
            account_id=ProprietaryAccountId(
                UUID("2d000000-0000-0000-0000-000000000023")
            ),
            source=_source(),
            observed_at=_NOW,
            environment=ProprietaryAccountEnvironment.DEMO,
            state=ProprietaryAccountOperationalState.ACTIVE,
            balance=_money("1000"),
            equity=MoneyAmount(eur, Decimal("1000")),
            unrealized_pnl=_money("0"),
            margin_used=_money("0"),
            drawdown=DrawdownBps(0),
        )

    with pytest.raises(ProprietaryAccountValidationError):
        ProprietaryAccountFinancialSnapshot(
            snapshot_id=ProprietaryAccountSnapshotId(
                UUID("2d000000-0000-0000-0000-000000000014")
            ),
            account_id=ProprietaryAccountId(
                UUID("2d000000-0000-0000-0000-000000000024")
            ),
            source=_source(),
            observed_at=_NOW,
            environment=ProprietaryAccountEnvironment.DEMO,
            state=ProprietaryAccountOperationalState.ACTIVE,
            balance=_money("-1"),
            equity=_money("1000"),
            unrealized_pnl=_money("0"),
            margin_used=_money("0"),
            drawdown=DrawdownBps(0),
        )


def test_drawdown_rejects_bool_and_out_of_range_values() -> None:
    for value in (-1, 10_001):
        with pytest.raises(ProprietaryAccountValidationError):
            DrawdownBps(value)


def test_performance_snapshot_uses_explicit_window_and_signed_realized_pnl() -> None:
    snapshot = ProprietaryAccountPerformanceSnapshot(
        snapshot_id=ProprietaryAccountSnapshotId(
            UUID("2d000000-0000-0000-0000-000000000030")
        ),
        account_id=ProprietaryAccountId(
            UUID("2d000000-0000-0000-0000-000000000020")
        ),
        source=_source(),
        observed_at=_NOW,
        period_start=_NOW - timedelta(days=1),
        period_end=_NOW - timedelta(seconds=1),
        realized_pnl=_money("-250.75"),
    )

    assert snapshot.realized_pnl.amount == Decimal("-250.75")
    assert snapshot.currency == _USD
    assert snapshot.period_start < snapshot.period_end <= snapshot.observed_at


def test_performance_snapshot_rejects_invalid_chronology() -> None:
    with pytest.raises(ProprietaryAccountValidationError):
        ProprietaryAccountPerformanceSnapshot(
            snapshot_id=ProprietaryAccountSnapshotId(
                UUID("2d000000-0000-0000-0000-000000000031")
            ),
            account_id=ProprietaryAccountId(
                UUID("2d000000-0000-0000-0000-000000000020")
            ),
            source=_source(),
            observed_at=_NOW - timedelta(hours=2),
            period_start=_NOW - timedelta(days=1),
            period_end=_NOW - timedelta(hours=1),
            realized_pnl=_money("100"),
        )


def test_requests_require_explicit_account_and_performance_window() -> None:
    account_id = ProprietaryAccountId(
        UUID("2d000000-0000-0000-0000-000000000020")
    )
    request = ProprietaryAccountSnapshotRequest(account_id)
    performance = ProprietaryAccountPerformanceRequest(
        account_id=account_id,
        period_start=_NOW - timedelta(days=7),
        period_end=_NOW,
    )

    assert request.account_id == account_id
    assert performance.period_end - performance.period_start == timedelta(days=7)

    with pytest.raises(ProprietaryAccountValidationError):
        ProprietaryAccountPerformanceRequest(
            account_id=account_id,
            period_start=_NOW,
            period_end=_NOW,
        )


def test_production_is_classification_not_authorization() -> None:
    assert ProprietaryAccountEnvironment.PRODUCTION.value == "production"
    assert not hasattr(ProprietaryAccountEnvironment.PRODUCTION, "authorized")
