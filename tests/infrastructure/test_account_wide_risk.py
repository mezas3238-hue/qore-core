from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    CiboRiskRequest,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.fundednext_stellar_instant import (
    StellarInstantAccountSnapshot,
    evaluate_stellar_instant_budget,
)

_NOW = datetime(2026, 9, 13, 18, 0, tzinfo=UTC)


def _snapshot(qore_headroom: str = "25") -> AccountRiskSnapshot:
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
        qore_authorizable_headroom=Decimal(qore_headroom),
        provider_budget=provider,
        reconciled_at=_NOW,
    )


def _request(
    request_id: str,
    trader: TraderLineage,
    signal: str,
    *,
    volume: str = "1",
    step: str = "1",
    minimum: str = "1",
) -> CiboRiskRequest:
    return CiboRiskRequest(
        request_id=request_id,
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol="GBPUSD" if trader is TraderLineage.VT08_FOREX else "NAS100",
        provider_symbol="GBPUSD" if trader is TraderLineage.VT08_FOREX else "NDX100",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        requested_volume=Decimal(volume),
        volume_step=Decimal(step),
        minimum_volume=Decimal(minimum),
        stop_loss_per_volume=Decimal("20"),
        margin_per_volume=Decimal("50"),
        requested_at=_NOW,
        expires_at=_NOW + timedelta(minutes=2),
    )


def test_forex_and_index_cannot_double_spend_same_headroom() -> None:
    engine = AccountWideRiskEngine()
    snapshot = _snapshot("25")
    forex = engine.authorize(
        _request("r1", TraderLineage.VT08_FOREX, "fx-signal"),
        snapshot,
        now=_NOW,
    )
    index = engine.authorize(
        _request("r2", TraderLineage.VT08_INDEX, "index-signal"),
        snapshot,
        now=_NOW,
    )
    assert forex.decision is RiskDecision.ALLOW
    assert forex.monetary_stop_loss == Decimal("20")
    assert index.decision is RiskDecision.REJECT
    assert engine.active_reserved_stop_risk() == Decimal("20")


def test_request_reduces_to_remaining_account_wide_budget() -> None:
    engine = AccountWideRiskEngine()
    auth = engine.authorize(
        _request(
            "r1",
            TraderLineage.VT08_INDEX,
            "index-signal",
            volume="2",
            step="0.1",
            minimum="0.1",
        ),
        _snapshot("25"),
        now=_NOW,
    )
    assert auth.decision is RiskDecision.REDUCE
    assert auth.authorized_volume == Decimal("1.2")
    assert auth.monetary_stop_loss == Decimal("24.0")


def test_duplicate_signal_is_idempotent_and_does_not_reserve_twice() -> None:
    engine = AccountWideRiskEngine()
    request = _request("r1", TraderLineage.VT08_FOREX, "same-signal")
    first = engine.authorize(request, _snapshot("25"), now=_NOW)
    second = engine.authorize(request, _snapshot("25"), now=_NOW)
    assert second.authorization_id == first.authorization_id
    assert engine.active_reserved_stop_risk() == Decimal("20")


def test_cancel_releases_reservation_for_other_trader() -> None:
    engine = AccountWideRiskEngine()
    first = engine.authorize(
        _request("r1", TraderLineage.VT08_FOREX, "fx"),
        _snapshot("25"),
        now=_NOW,
    )
    engine.cancel(first.authorization_id)
    second = engine.authorize(
        _request("r2", TraderLineage.VT08_INDEX, "idx"),
        _snapshot("25"),
        now=_NOW,
    )
    assert second.decision is RiskDecision.ALLOW


def test_expired_reservation_releases_budget() -> None:
    engine = AccountWideRiskEngine()
    first = engine.authorize(
        _request("r1", TraderLineage.VT08_FOREX, "fx"),
        _snapshot("25"),
        now=_NOW,
    )
    assert first.decision is RiskDecision.ALLOW
    engine.expire(now=_NOW + timedelta(minutes=3))
    assert engine.active_reserved_stop_risk() == 0
    second = engine.authorize(
        _request("r2", TraderLineage.VT08_INDEX, "idx"),
        _snapshot("25"),
        now=_NOW,
    )
    assert second.decision is RiskDecision.ALLOW


def test_partial_then_full_fill_remains_reserved_until_reconciliation() -> None:
    engine = AccountWideRiskEngine()
    auth = engine.authorize(
        _request(
            "r1",
            TraderLineage.VT08_FOREX,
            "fx",
            volume="1",
            step="0.1",
            minimum="0.1",
        ),
        _snapshot("25"),
        now=_NOW,
    )
    engine.record_partial_fill(auth.authorization_id, filled_volume=Decimal("0.4"))
    assert engine.active_reserved_stop_risk() == Decimal("20.0")
    engine.record_full_fill(auth.authorization_id)
    assert engine.active_reserved_stop_risk() == Decimal("20.0")
    engine.reconcile_fill(auth.authorization_id)
    assert engine.active_reserved_stop_risk() == 0
