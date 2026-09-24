from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import CiboRiskRequest, TraderLineage
from qore.infrastructure.ctrader_demo_allocation_only import (
    CTraderDemoAllocationError,
    CTraderDemoBrokerContract,
    DemoAllocationAuthorization,
    DemoCapitalAllocationBook,
    allocation_fence_values,
    authorize_allocation_only,
    build_allocation_only_submission,
    equal_active_trader_allocations,
)
from qore.infrastructure.order_intent import OrderType

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def _request(
    trader: TraderLineage = TraderLineage.R38_EURUSD,
    *,
    request_id: str = "request-1",
    volume: Decimal = Decimal("0.05"),
    entry_type: str = "market",
) -> CiboRiskRequest:
    return CiboRiskRequest(
        request_id=request_id,
        trader_id=trader,
        signal_fingerprint=("a" if request_id == "request-1" else "b") * 64,
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type=entry_type,
        intended_entry=Decimal("1.10000"),
        stop_loss=Decimal("1.09500"),
        take_profit=Decimal("1.11000"),
        requested_volume=volume,
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        stop_loss_per_volume=Decimal("500"),
        margin_per_volume=Decimal("1000"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        strategy_requested_risk_usd=Decimal("25"),
    )


def _book() -> DemoCapitalAllocationBook:
    return DemoCapitalAllocationBook(
        total_capital=Decimal("100000"),
        allocations={
            TraderLineage.R38_EURUSD: Decimal("50000"),
            TraderLineage.R43_GBPUSD: Decimal("50000"),
        },
    )


def test_allocation_only_preserves_cibo_requested_volume_exactly() -> None:
    request = _request(volume=Decimal("0.37"))
    approved = authorize_allocation_only(request, book=_book(), now=NOW)

    assert approved.assigned_capital == Decimal("50000")
    assert approved.authorized_volume == Decimal("0.37")
    assert approved.authorized_volume == request.requested_volume


def test_other_trader_activity_never_reduces_the_request() -> None:
    first = authorize_allocation_only(_request(), book=_book(), now=NOW)
    second_request = _request(
        trader=TraderLineage.R43_GBPUSD,
        request_id="request-2",
        volume=Decimal("0.91"),
    )
    second = authorize_allocation_only(second_request, book=_book(), now=NOW)

    assert first.authorized_volume == Decimal("0.05")
    assert second.authorized_volume == Decimal("0.91")


def test_equal_book_assigns_all_active_traders() -> None:
    book = equal_active_trader_allocations(Decimal("70000"))

    assert book.capital_for(TraderLineage.VT08_FOREX) == Decimal("10000")
    assert book.capital_for(TraderLineage.VT31_NAS100) == Decimal("10000")


def test_expired_cibo_request_is_still_fail_closed() -> None:
    request = _request()
    with pytest.raises(CTraderDemoAllocationError, match="expired"):
        authorize_allocation_only(
            request,
            book=_book(),
            now=request.expires_at + timedelta(microseconds=1),
        )


def test_contract_mismatch_is_converted_without_distorting_exposure() -> None:
    contract = CTraderDemoBrokerContract(
        qore_symbol="NAS100",
        provider_symbol="NAS100",
        source_contract_size_units=Decimal("10"),
        ctrader_lot_size_units=Decimal("1"),
    )

    assert contract.source_to_ctrader_lot_ratio == Decimal("10")


def test_nas100_source_lot_converts_to_equivalent_ctrader_units() -> None:
    request = _request(
        trader=TraderLineage.VT31_NAS100,
        volume=Decimal("1"),
        entry_type="limit",
    )
    object.__setattr__(request, "qore_symbol", "NAS100")
    object.__setattr__(request, "provider_symbol", "NDX100")
    approved = DemoAllocationAuthorization(
        request=request,
        assigned_capital=Decimal("50000"),
        authorized_volume=request.requested_volume,
        policy_id="ctrader.demo.allocation-only.v1",
        authorization_fingerprint="f" * 64,
        authorized_at=NOW,
    )
    contract = CTraderDemoBrokerContract(
        qore_symbol="NAS100",
        provider_symbol="NAS100",
        source_contract_size_units=Decimal("10"),
        ctrader_lot_size_units=Decimal("1"),
    )
    submission = build_allocation_only_submission(
        approved,
        contract=contract,
        submitted_at=NOW + timedelta(seconds=1),
    )

    assert submission.authorized_intent.intent.quantity.value == Decimal("10")


def test_market_submission_converts_lots_to_ctrader_units_and_keeps_cibo_geometry() -> None:
    request = _request(volume=Decimal("0.05"))
    approved = authorize_allocation_only(request, book=_book(), now=NOW)
    contract = CTraderDemoBrokerContract(
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        source_contract_size_units=Decimal("100000"),
        ctrader_lot_size_units=Decimal("100000"),
    )
    submission = build_allocation_only_submission(
        approved,
        contract=contract,
        submitted_at=NOW + timedelta(seconds=1),
    )
    intent = submission.authorized_intent.intent

    assert intent.order_type is OrderType.MARKET
    assert intent.quantity.value == Decimal("5000.00")
    assert intent.limit_price is None
    assert intent.stop_loss is not None
    assert intent.stop_loss.value == Decimal("1.09500")
    assert intent.take_profit is not None
    assert intent.take_profit.value == Decimal("1.11000")
    assert intent.metadata.attributes["ctrader_reference_entry"] == "1.10000"
    assert intent.metadata.attributes["demo_policy"] == "allocation-only"


def test_limit_submission_retains_exact_entry() -> None:
    request = _request(entry_type="limit")
    approved = authorize_allocation_only(request, book=_book(), now=NOW)
    contract = CTraderDemoBrokerContract(
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        source_contract_size_units=Decimal("100000"),
        ctrader_lot_size_units=Decimal("100000"),
    )
    submission = build_allocation_only_submission(
        approved,
        contract=contract,
        submitted_at=NOW + timedelta(seconds=1),
    )
    intent = submission.authorized_intent.intent

    assert intent.order_type is OrderType.LIMIT
    assert intent.limit_price is not None
    assert intent.limit_price.value == Decimal("1.10000")


def test_allocator_fence_is_non_secret_and_stable_for_authorization() -> None:
    approved = authorize_allocation_only(_request(), book=_book(), now=NOW)

    authorization_id, fingerprint, reservation_id = allocation_fence_values(approved)

    assert authorization_id.startswith("allocation:R38_EURUSD:")
    assert reservation_id == authorization_id
    assert fingerprint == approved.authorization_fingerprint
