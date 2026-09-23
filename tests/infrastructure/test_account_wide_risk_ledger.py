from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskError,
    CiboRiskRequest,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.fundednext_stellar_instant import (
    StellarInstantAccountSnapshot,
    evaluate_stellar_instant_budget,
)

_NOW = datetime(2026, 9, 14, 4, 0, tzinfo=UTC)


def _snapshot(*, reconciled_at: datetime = _NOW) -> AccountRiskSnapshot:
    provider = evaluate_stellar_instant_budget(
        StellarInstantAccountSnapshot(
            initial_balance=Decimal("2000"),
            balance=Decimal("2000"),
            equity=Decimal("2000"),
            highest_closed_balance=Decimal("2000"),
            previous_active_mll=Decimal("1880"),
        )
    )
    return AccountRiskSnapshot(
        account_binding_id="fn-si-opaque-001",
        equity=Decimal("2000"),
        margin_used=Decimal("0"),
        free_margin=Decimal("500"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("25"),
        provider_budget=provider,
        reconciled_at=reconciled_at,
    )


def _request(signal: str) -> CiboRiskRequest:
    return CiboRiskRequest(
        request_id=f"request-{signal}",
        trader_id=TraderLineage.VT08_FOREX,
        signal_fingerprint=signal,
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD.a",
        side="long",
        entry_type="market",
        intended_entry=Decimal("1.2500"),
        stop_loss=Decimal("1.2450"),
        take_profit=Decimal("1.2600"),
        requested_volume=Decimal("0.1"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        stop_loss_per_volume=Decimal("200"),
        margin_per_volume=Decimal("50"),
        requested_at=_NOW,
        expires_at=_NOW + timedelta(minutes=2),
    )


def test_restart_restores_risk_and_blocks_until_fresh_reconciliation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "account-wide-risk.json"
    first = DurableAccountWideRiskEngine(DurableAccountWideRiskLedger(path))
    authorized = first.authorize(_request("same"), _snapshot(), now=_NOW)
    assert authorized.decision is RiskDecision.ALLOW
    assert first.active_reserved_stop_risk() == Decimal("20.0")

    restarted = DurableAccountWideRiskEngine(DurableAccountWideRiskLedger(path))
    assert restarted.recovery_required is True
    assert restarted.active_reserved_stop_risk() == Decimal("20.0")
    with pytest.raises(AccountWideRiskError, match="restart-reconciliation-required"):
        restarted.authorize(_request("other"), _snapshot(), now=_NOW)

    restarted.complete_boot_reconciliation(_snapshot(), now=_NOW)
    assert restarted.recovery_required is False
    duplicate = restarted.authorize(_request("same"), _snapshot(), now=_NOW)
    assert duplicate.authorization_id == authorized.authorization_id
    assert restarted.active_reserved_stop_risk() == Decimal("20.0")


def test_stale_boot_snapshot_cannot_unlock_risk(tmp_path: Path) -> None:
    path = tmp_path / "account-wide-risk.json"
    first = DurableAccountWideRiskEngine(DurableAccountWideRiskLedger(path))
    first.authorize(_request("same"), _snapshot(), now=_NOW)
    restarted = DurableAccountWideRiskEngine(DurableAccountWideRiskLedger(path))
    with pytest.raises(AccountWideRiskError, match="snapshot is stale"):
        restarted.complete_boot_reconciliation(
            _snapshot(reconciled_at=_NOW - timedelta(minutes=1)),
            now=_NOW,
        )
    assert restarted.recovery_required is True


def test_full_fill_and_reconcile_are_durable(tmp_path: Path) -> None:
    path = tmp_path / "account-wide-risk.json"
    engine = DurableAccountWideRiskEngine(DurableAccountWideRiskLedger(path))
    authorization = engine.authorize(_request("same"), _snapshot(), now=_NOW)
    engine.record_full_fill(authorization.authorization_id)

    restarted = DurableAccountWideRiskEngine(DurableAccountWideRiskLedger(path))
    assert restarted.active_reserved_stop_risk() == Decimal("20.0")
    restarted.complete_boot_reconciliation(_snapshot(), now=_NOW)
    restarted.reconcile_fill(authorization.authorization_id)
    assert restarted.active_reserved_stop_risk() == 0

    clean = DurableAccountWideRiskEngine(DurableAccountWideRiskLedger(path))
    assert clean.recovery_required is False
    assert clean.active_reserved_stop_risk() == 0


def test_stale_boot_snapshot_can_be_recovered_by_fresh_refresh(tmp_path: Path) -> None:
    path = tmp_path / "account-wide-risk.json"
    first = DurableAccountWideRiskEngine(DurableAccountWideRiskLedger(path))
    first.authorize(_request("same"), _snapshot(), now=_NOW)

    restarted = DurableAccountWideRiskEngine(DurableAccountWideRiskLedger(path))
    with pytest.raises(AccountWideRiskError, match="snapshot is stale"):
        restarted.complete_boot_reconciliation(
            _snapshot(reconciled_at=_NOW - timedelta(minutes=1)),
            now=_NOW,
        )
    assert restarted.recovery_required is True

    restarted.complete_boot_reconciliation(_snapshot(reconciled_at=_NOW), now=_NOW)
    assert restarted.recovery_required is False
    authorization = restarted.authorize(_request("fresh-after-recovery"), _snapshot(), now=_NOW)
    assert authorization.decision is not RiskDecision.REJECT
