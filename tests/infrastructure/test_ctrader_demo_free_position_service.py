from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.ctrader_demo_free_position_service import (
    CTraderDemoFreePositionService,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import ExecutionInstrument
from qore.infrastructure.transport import ExternalTransportTimeout
from qore.kernel.result import Success

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="424242",
    environment=MarketRuntimeEnvironment.DEMO,
)
def _configuration() -> CTraderDemoRuntimeConfiguration:
    return CTraderDemoRuntimeConfiguration(
        provider_key="ctrader-demo",
        environment=MarketRuntimeEnvironment.DEMO,
        endpoint=ProviderEndpoint(host="demo.ctraderapi.com", port=5035),
        account=ACCOUNT,
        symbol_mappings=(
            CTraderSymbolMapping(
                instrument=ExecutionInstrument("EURUSD"),
                symbol_id=1,
                symbol_name="EURUSD",
                digits=5,
                volume_step=Decimal("0.01"),
                min_volume_units=100,
                max_volume_units=100_000_000,
                step_volume_units=100,
            ),
        ),
        capabilities=(
            CTraderDemoCapability.ACCOUNT,
            CTraderDemoCapability.CANDLES,
            CTraderDemoCapability.ORDERS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        limits=CTraderDemoOperationalLimits(order_requests_per_second=1),
        secret_requirements=ctrader_demo_secret_requirements(),
    )


class FakeClient:
    def __init__(self) -> None:
        self._ready = True
        self.calls: list[tuple[str, dict[str, object]]] = []

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def account_id(self) -> int:
        return 424242
    def connect_and_authenticate(self):
        self._ready = True
        return Success(None)

    def request(self, message_name, fields, *, client_msg_id, timeout_seconds):
        del client_msg_id, timeout_seconds
        self.calls.append((message_name, dict(fields)))
        if message_name == "ProtoOATraderReq":
            return Success(
                SimpleNamespace(
                    trader=SimpleNamespace(balance=10_000_000, moneyDigits=2)
                )
            )
        if message_name == "ProtoOAGetPositionUnrealizedPnLReq":
            return Success(
                SimpleNamespace(
                    moneyDigits=2,
                    positionUnrealizedPnL=(
                        SimpleNamespace(
                            positionId=700,
                            grossUnrealizedPnL=2500,
                            netUnrealizedPnL=2300,
                        ),
                    ),
                )
            )
        if message_name == "ProtoOAReconcileReq":
            return Success(
                SimpleNamespace(
                    position=(
                        SimpleNamespace(
                            positionId=700,
                            price=1.1001,
                            stopLoss=1.095,
                            takeProfit=1.11,
                            tradeData=SimpleNamespace(
                                symbolId=1,
                                volume=500000,
                                tradeSide=1,
                                openTimestamp=int(NOW.timestamp() * 1000),
                                label="QORE:R38_EURUSD",
                                comment="qore:test",
                            ),
                        ),
                    )
                )
            )
        if message_name == "ProtoOAAmendPositionSLTPReq":
            return Success(SimpleNamespace(executionType=2))
        if message_name == "ProtoOAClosePositionReq":
            return Success(SimpleNamespace(executionType=2))
        if message_name == "ProtoOADealListReq":
            detail = SimpleNamespace(
                grossProfit=2500,
                swap=-100,
                commission=-200,
                balance=10_002_200,
                moneyDigits=2,
                pnlConversionFee=0,
            )
            deal = SimpleNamespace(
                dealId=900,
                orderId=800,
                positionId=700,
                volume=500000,
                filledVolume=500000,
                symbolId=1,
                executionTimestamp=int((NOW + timedelta(minutes=5)).timestamp() * 1000),
                executionPrice=1.1025,
                tradeSide=2,
                commission=-200,
                moneyDigits=2,
                closePositionDetail=detail,
                HasField=lambda name: name == "closePositionDetail",
            )
            return Success(SimpleNamespace(deal=(deal,)))
        raise AssertionError(message_name)


def test_account_snapshot_uses_realized_balance_plus_net_unrealized() -> None:
    service = CTraderDemoFreePositionService(
        client=FakeClient(), configuration=_configuration()
    )
    snapshot = service.account_snapshot(observed_at=NOW)

    assert snapshot.balance == Decimal("100000.00")
    assert snapshot.gross_unrealized_pnl == Decimal("25.00")
    assert snapshot.net_unrealized_pnl == Decimal("23.00")
    assert snapshot.equity == Decimal("100023.00")
