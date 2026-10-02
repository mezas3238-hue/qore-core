from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Event
from types import SimpleNamespace

import pytest

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
    CTraderDemoFreePositionError,
    CTraderDemoFreePositionService,
    DemoPositionLabelClass,
    classify_position_label,
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
                SimpleNamespace(trader=SimpleNamespace(balance=10_000_000, moneyDigits=2))
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
    service = CTraderDemoFreePositionService(client=FakeClient(), configuration=_configuration())
    snapshot = service.account_snapshot(observed_at=NOW)

    assert snapshot.balance == Decimal("100000.00")
    assert snapshot.gross_unrealized_pnl == Decimal("25.00")
    assert snapshot.net_unrealized_pnl == Decimal("23.00")
    assert snapshot.equity == Decimal("100023.00")


def test_position_labels_have_explicit_non_trader_taxonomy() -> None:
    trader = classify_position_label("QORE:R38_EURUSD")
    calibration = classify_position_label("QORE:CIBO-CAL:XAUUSD:probe")
    test = classify_position_label("QORE:CIBO-T16:US500:BUY:probe")
    external = classify_position_label("manual-position")
    invalid = classify_position_label("QORE:NOT-A-QORE-IDENTITY")

    assert trader.classification is DemoPositionLabelClass.KNOWN_TRADER
    assert trader.trader_id is TraderLineage.R38_EURUSD
    assert calibration.classification is DemoPositionLabelClass.KNOWN_SYSTEM
    assert test.classification is DemoPositionLabelClass.KNOWN_TEST
    assert external.classification is DemoPositionLabelClass.EXTERNAL
    assert invalid.classification is DemoPositionLabelClass.UNKNOWN_INVALID


class AccountCaptureClient(FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.last_request_completed_at = NOW

    def request(self, *args, **kwargs):
        result = super().request(*args, **kwargs)
        self.last_request_completed_at = datetime.now(UTC)
        return result


def test_account_snapshot_timestamp_follows_broker_reads() -> None:
    client = AccountCaptureClient()
    service = CTraderDemoFreePositionService(
        client=client,
        configuration=_configuration(),
    )

    snapshot = service.account_snapshot()

    assert snapshot.observed_at >= client.last_request_completed_at


class ConcurrentAccountClient(FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.trader_started = Event()
        self.pnl_started = Event()

    def request(self, message_name, fields, *, client_msg_id, timeout_seconds):
        if message_name == "ProtoOATraderReq":
            self.trader_started.set()
            if not self.pnl_started.wait(timeout=0.5):
                raise AssertionError("account requests executed serially")
        elif message_name == "ProtoOAGetPositionUnrealizedPnLReq":
            self.pnl_started.set()
            if not self.trader_started.wait(timeout=0.5):
                raise AssertionError("account requests executed serially")
        return super().request(
            message_name,
            fields,
            client_msg_id=client_msg_id,
            timeout_seconds=timeout_seconds,
        )


def test_account_snapshot_reads_balance_and_pnl_concurrently() -> None:
    client = ConcurrentAccountClient()
    service = CTraderDemoFreePositionService(
        client=client,
        configuration=_configuration(),
    )

    snapshot = service.account_snapshot(observed_at=NOW)

    assert snapshot.equity == Decimal("100023.00")
    assert client.trader_started.is_set()
    assert client.pnl_started.is_set()


class LabelReconcileClient(FakeClient):
    def __init__(self, labels: tuple[str, ...]) -> None:
        super().__init__()
        self._labels = labels

    def request(self, message_name, fields, *, client_msg_id, timeout_seconds):
        if message_name != "ProtoOAReconcileReq":
            return super().request(
                message_name,
                fields,
                client_msg_id=client_msg_id,
                timeout_seconds=timeout_seconds,
            )
        positions = tuple(
            SimpleNamespace(
                positionId=700 + index,
                price=1.1001,
                stopLoss=1.095,
                takeProfit=1.11,
                tradeData=SimpleNamespace(
                    symbolId=1,
                    volume=500000,
                    tradeSide=1,
                    openTimestamp=int(NOW.timestamp() * 1000),
                    label=label,
                    comment="qore:test",
                ),
            )
            for index, label in enumerate(self._labels)
        )
        return Success(SimpleNamespace(position=positions))


def test_positions_exclude_system_test_and_external_labels() -> None:
    client = LabelReconcileClient(
        (
            "QORE:CIBO-CAL:XAUUSD:probe",
            "QORE:CIBO-T16:US500:BUY:probe",
            "manual-position",
            "QORE:R38_EURUSD",
        )
    )
    service = CTraderDemoFreePositionService(
        client=client,
        configuration=_configuration(),
    )

    positions = service.positions()

    assert [item.position_id for item in positions] == [703]
    assert positions[0].trader_id is TraderLineage.R38_EURUSD


def test_positions_fail_closed_for_unknown_qore_identity() -> None:
    service = CTraderDemoFreePositionService(
        client=LabelReconcileClient(("QORE:NOT-A-QORE-IDENTITY",)),
        configuration=_configuration(),
    )

    with pytest.raises(
        CTraderDemoFreePositionError,
        match="unknown QORE position label",
    ):
        service.positions()