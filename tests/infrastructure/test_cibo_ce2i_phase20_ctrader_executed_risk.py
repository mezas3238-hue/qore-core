from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.account_wide_risk import (
    CiboRiskRequest,
    TraderLineage,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_ctrader_executed_risk import (
    build_ctrader_phase20_executed_risk,
)
from qore.infrastructure.ctrader_demo_allocation_only import (
    CTraderDemoBrokerContract,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoFillObservation,
    CTraderDemoFillReconciliation,
    CTraderDemoFillReconciliationStatus,
)
from qore.infrastructure.execution_boundary import ExecutionReceiptId
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderSide,
)

NOW = datetime(2026, 9, 27, 17, 30, tzinfo=UTC)
ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="demo-forward",
    environment=MarketRuntimeEnvironment.DEMO,
)
RECEIPT = ExecutionReceiptId(
    UUID("32000000-0000-0000-4000-000000000001")
)
KEY = ExecutionIdempotencyKey(
    UUID("32000000-0000-0000-1000-000000000001")
)


def _request() -> CiboRiskRequest:
    return CiboRiskRequest(
        request_id="request-1",
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="fill-risk-vt31",
        qore_symbol="NAS100",
        provider_symbol="NAS100",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        requested_volume=Decimal("1"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("10"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
    )


def _contract() -> CTraderDemoBrokerContract:
    return CTraderDemoBrokerContract(
        qore_symbol="NAS100",
        provider_symbol="NAS100",
        source_contract_size_units=Decimal("100"),
        ctrader_lot_size_units=Decimal("100"),
    )


def _fill(
    *,
    fill_ref: str,
    quantity: str,
    cumulative: str,
    price: str,
    complete: bool,
    offset_ms: int,
) -> CTraderDemoFillObservation:
    return CTraderDemoFillObservation(
        receipt_id=RECEIPT,
        idempotency_key=KEY,
        account=ACCOUNT,
        instrument=ExecutionInstrument("NAS100"),
        side=OrderSide.BUY,
        provider_order_ref="70001",
        fill_ref=fill_ref,
        fill_quantity=Decimal(quantity),
        cumulative_quantity=Decimal(cumulative),
        fill_price=Decimal(price),
        provider_timestamp=NOW + timedelta(milliseconds=offset_ms),
        received_at=NOW + timedelta(milliseconds=offset_ms + 1),
        is_complete=complete,
    )


def _reconciliation(
    status: CTraderDemoFillReconciliationStatus = (
        CTraderDemoFillReconciliationStatus.MATCHED
    ),
) -> CTraderDemoFillReconciliation:
    return CTraderDemoFillReconciliation(
        status=status,
        reconciled_at=NOW + timedelta(seconds=1),
        requested_quantity=Decimal("100"),
        filled_quantity=(
            Decimal("100")
            if status is CTraderDemoFillReconciliationStatus.MATCHED
            else Decimal("50")
        ),
        issues=(),
    )


def test_ctrader_executed_risk_uses_weighted_fill_slippage() -> None:
    evidence = build_ctrader_phase20_executed_risk(
        decision_evidence_sha256="sha256:" + "a" * 64,
        position_id=77,
        request=_request(),
        contract=_contract(),
        fills=(
            _fill(
                fill_ref="90001",
                quantity="50",
                cumulative="50",
                price="100.1",
                complete=False,
                offset_ms=100,
            ),
            _fill(
                fill_ref="90002",
                quantity="50",
                cumulative="100",
                price="100.2",
                complete=True,
                offset_ms=200,
            ),
        ),
        reconciliation=_reconciliation(),
    )

    assert evidence.position_id == 77
    assert evidence.signal_fingerprint == "fill-risk-vt31"
    assert evidence.executed_initial_stop_risk_usd == Decimal("11.50")
    assert evidence.fill_evidence_refs == ("90001", "90002")
    assert evidence.fill_reconciled is True
    assert evidence.mutation_outcome_known is True


def test_ctrader_executed_risk_rejects_partial_reconciliation() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="MATCHED fill reconciliation",
    ):
        build_ctrader_phase20_executed_risk(
            decision_evidence_sha256="sha256:" + "a" * 64,
            position_id=77,
            request=_request(),
            contract=_contract(),
            fills=(
                _fill(
                    fill_ref="90001",
                    quantity="50",
                    cumulative="50",
                    price="100.1",
                    complete=False,
                    offset_ms=100,
                ),
            ),
            reconciliation=_reconciliation(
                CTraderDemoFillReconciliationStatus.PARTIAL
            ),
        )


def test_ctrader_executed_risk_rejects_nonterminal_fill() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="terminal fill must be marked complete",
    ):
        build_ctrader_phase20_executed_risk(
            decision_evidence_sha256="sha256:" + "a" * 64,
            position_id=77,
            request=_request(),
            contract=_contract(),
            fills=(
                _fill(
                    fill_ref="90001",
                    quantity="100",
                    cumulative="100",
                    price="100.1",
                    complete=False,
                    offset_ms=100,
                ),
            ),
            reconciliation=_reconciliation(),
        )


def test_ctrader_executed_risk_rejects_fill_through_stop() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="crossed structural stop",
    ):
        build_ctrader_phase20_executed_risk(
            decision_evidence_sha256="sha256:" + "a" * 64,
            position_id=77,
            request=_request(),
            contract=_contract(),
            fills=(
                _fill(
                    fill_ref="90001",
                    quantity="100",
                    cumulative="100",
                    price="98.9",
                    complete=True,
                    offset_ms=100,
                ),
            ),
            reconciliation=_reconciliation(),
        )
