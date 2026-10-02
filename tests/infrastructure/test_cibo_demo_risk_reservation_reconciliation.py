from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    CiboRiskRequest,
    ReservationState,
    TraderLineage,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_shadow_risk import (
    CiboDemoCapabilitySolvencyBudget,
)
from qore.infrastructure.cibo_demo_risk_reservation_reconciliation import (
    confirmed_fill_authorization_ids,
    reconcile_demo_risk_reservations,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoAttemptState,
)
from qore.infrastructure.ctrader_demo_mutation_ledger import (
    CTraderDemoMutationLedgerRecord,
)
from qore.infrastructure.ctrader_demo_trade_registry import (
    DemoTradeRegistryEntry,
)

NOW = datetime(2026, 10, 2, 15, 0, tzinfo=UTC)


def _snapshot() -> AccountRiskSnapshot:
    return AccountRiskSnapshot(
        account_binding_id="ctrader-demo-risk-reconcile",
        equity=Decimal("1000"),
        margin_used=Decimal("0"),
        free_margin=Decimal("1000"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("1000"),
        provider_budget=CiboDemoCapabilitySolvencyBudget(
            provider_headroom=Decimal("1000"),
            max_risk_at_any_time=Decimal("1000"),
            active_mll=Decimal("0"),
            hard_breach=False,
        ),
        reconciled_at=NOW,
    )


def _request(signal: str = "risk-reconcile-signal") -> CiboRiskRequest:
    return CiboRiskRequest(
        request_id=f"request-{signal}",
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint=signal,
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profit=Decimal("1.12"),
        requested_volume=Decimal("1"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        requested_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )


def _entry(
    authorization_id: str,
    *,
    signal: str = "risk-reconcile-signal",
    position_id: int | None = 42,
    closed_at: str | None = None,
) -> DemoTradeRegistryEntry:
    return DemoTradeRegistryEntry(
        trader=TraderLineage.R38_EURUSD.value,
        signal_fingerprint=signal,
        request_id=f"request-{signal}",
        client_order_id=f"client-{signal}",
        provider_order_ref="7001",
        qore_symbol="EURUSD",
        requested_volume="1",
        requested_stop_risk="10",
        submitted_at=NOW.isoformat(),
        expires_at=(NOW + timedelta(minutes=5)).isoformat(),
        position_id=position_id,
        receipt_id=f"receipt-{signal}",
        idempotency_key=f"idempotency-{signal}",
        authorized_source_volume="1",
        risk_authorization_id=authorization_id,
        source_contract_size_units="100",
        closed_at=closed_at,
    )


def _mutation(
    authorization_id: str,
    *,
    signal: str = "risk-reconcile-signal",
) -> CTraderDemoMutationLedgerRecord:
    return CTraderDemoMutationLedgerRecord(
        idempotency_key=f"idempotency-{signal}",
        receipt_id=f"receipt-{signal}",
        submission_digest="sha256:" + "a" * 64,
        client_order_id=f"client-{signal}",
        state=CTraderDemoAttemptState.DEFINITIVE_OUTCOME,
        transitioned_at=NOW + timedelta(seconds=2),
        provider_order_ref="7001",
        cumulative_quantity="100",
        is_complete=True,
        risk_authorization_id=authorization_id,
        risk_authorization_fingerprint="b" * 64,
        risk_reservation_id=authorization_id,
    )


def test_exact_provider_fill_releases_internal_shadow_once_open_risk_is_visible() -> None:
    risk = AccountWideRiskEngine()
    auth = risk.authorize(_request(), _snapshot(), now=NOW)
    entry = _entry(auth.authorization_id)
    confirmed = confirmed_fill_authorization_ids(
        registry_entries=(entry,),
        mutation_records=(_mutation(auth.authorization_id),),
    )

    report = reconcile_demo_risk_reservations(
        risk=risk,
        registry_entries=(entry,),
        confirmed_fill_authorization_ids=confirmed,
        terminal_settlement_keys=frozenset(),
        broker_open_position_ids=frozenset({42}),
        provider_order_status=lambda _: 2,
        observed_at=NOW + timedelta(seconds=5),
    )

    assert report.open_fill_reconciled == 1
    assert report.blockers == ()
    assert risk.active_reserved_stop_risk() == 0
    reservation = risk.reservation_for(auth.authorization_id)
    assert reservation is not None
    assert reservation.state is ReservationState.RELEASED


def test_terminal_unfilled_provider_order_cancels_internal_reservation() -> None:
    risk = AccountWideRiskEngine()
    auth = risk.authorize(_request(), _snapshot(), now=NOW)
    entry = _entry(auth.authorization_id, position_id=None)

    report = reconcile_demo_risk_reservations(
        risk=risk,
        registry_entries=(entry,),
        confirmed_fill_authorization_ids=frozenset(),
        terminal_settlement_keys=frozenset(),
        broker_open_position_ids=frozenset(),
        provider_order_status=lambda _: 4,
        observed_at=NOW + timedelta(seconds=5),
    )

    assert report.terminal_order_cancelled == 1
    assert risk.active_reserved_stop_risk() == 0


def test_terminal_settlement_releases_shadow_only_with_exact_fill_lineage() -> None:
    risk = AccountWideRiskEngine()
    auth = risk.authorize(_request(), _snapshot(), now=NOW)
    entry = _entry(
        auth.authorization_id,
        closed_at=(NOW + timedelta(minutes=2)).isoformat(),
    )
    confirmed = confirmed_fill_authorization_ids(
        registry_entries=(entry,),
        mutation_records=(_mutation(auth.authorization_id),),
    )

    report = reconcile_demo_risk_reservations(
        risk=risk,
        registry_entries=(entry,),
        confirmed_fill_authorization_ids=confirmed,
        terminal_settlement_keys=frozenset(
            {(entry.signal_fingerprint, 42)}
        ),
        broker_open_position_ids=frozenset(),
        provider_order_status=lambda _: 2,
        observed_at=NOW + timedelta(minutes=3),
    )

    assert report.terminal_settlement_released == 1
    assert risk.active_reserved_stop_risk() == 0


def test_missing_registry_binding_stays_reserved_and_blocks_boot_clearance() -> None:
    risk = AccountWideRiskEngine()
    auth = risk.authorize(_request(), _snapshot(), now=NOW)

    report = reconcile_demo_risk_reservations(
        risk=risk,
        registry_entries=(),
        confirmed_fill_authorization_ids=frozenset(),
        terminal_settlement_keys=frozenset(),
        broker_open_position_ids=frozenset(),
        provider_order_status=lambda _: 2,
        observed_at=NOW + timedelta(seconds=5),
    )

    assert report.safe_to_clear_boot_fence is False
    assert report.blockers
    assert risk.active_reserved_stop_risk() == Decimal("10")
    reservation = risk.reservation_for(auth.authorization_id)
    assert reservation is not None
    assert reservation.state is ReservationState.RESERVED
