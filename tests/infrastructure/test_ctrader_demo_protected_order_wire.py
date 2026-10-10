from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_codec import (
    build_ctrader_demo_order_create_plan,
)
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoExecutionValidationError,
)
from qore.infrastructure.ctrader_open_api_client import CTraderOpenApiClientError
from qore.infrastructure.ctrader_open_api_transport import CTraderOpenApiExecutionTransport
from qore.infrastructure.execution_boundary import (
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderPrice,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.pretrade_safety import (
    AuthorizedOrderIntent,
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
    PreTradeAuthorization,
    PreTradeAuthorizationId,
    PreTradeDecision,
    PreTradePolicyId,
)
from qore.infrastructure.transport import ExternalTransportTimeout
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 9, 7, 3, 0, tzinfo=UTC)
_ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="424242",
    environment=MarketRuntimeEnvironment.DEMO,
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("54000000-0000-0000-0000-000000000001"))
)


def _configuration() -> CTraderDemoRuntimeConfiguration:
    return CTraderDemoRuntimeConfiguration(
        provider_key="ctrader-demo",
        environment=MarketRuntimeEnvironment.DEMO,
        endpoint=ProviderEndpoint(host="demo.ctraderapi.com", port=5035),
        account=_ACCOUNT,
        symbol_mappings=(
            CTraderSymbolMapping(
                instrument=ExecutionInstrument("EURUSD"),
                symbol_id=1234,
                symbol_name="EURUSD",
                digits=5,
                volume_step=Decimal("1"),
                min_volume_units=1,
                max_volume_units=1_000_000,
                step_volume_units=1,
            ),
        ),
        capabilities=(
            CTraderDemoCapability.ACCOUNT,
            CTraderDemoCapability.ORDERS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        limits=CTraderDemoOperationalLimits(order_requests_per_second=1),
        secret_requirements=ctrader_demo_secret_requirements(),
    )


def _submission(*, order_type: OrderType = OrderType.LIMIT) -> ExecutionSubmission:
    intent = OrderIntent(
        intent_id=OrderIntentId(UUID("54000000-0000-0000-0000-000000000010")),
        idempotency_key=ExecutionIdempotencyKey(
            UUID("54000000-0000-0000-0000-000000000011")
        ),
        instrument=ExecutionInstrument("EURUSD"),
        side=OrderSide.BUY,
        order_type=order_type,
        quantity=OrderQuantity(Decimal("1")),
        created_at=_NOW,
        metadata=_METADATA,
        limit_price=OrderPrice(Decimal("1.10000")) if order_type is OrderType.LIMIT else None,
        stop_loss=OrderPrice(Decimal("1.09500")),
        take_profit=OrderPrice(Decimal("1.11000")),
    )
    authorization = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(
            UUID("54000000-0000-0000-0000-000000000012")
        ),
        policy_id=PreTradePolicyId("ctrader.demo.pretrade"),
        intent_id=intent.intent_id,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(minutes=1),
        reason="protected DEMO order approved",
    )
    return ExecutionSubmission(
        request_id=ExecutionRequestId(UUID("54000000-0000-0000-0000-000000000013")),
        receipt_id=ExecutionReceiptId(UUID("54000000-0000-0000-0000-000000000014")),
        authorized_intent=AuthorizedOrderIntent(
            intent=intent,
            authorization=authorization,
            switch=ExecutionSafetySwitchSnapshot(
                state=ExecutionSwitchState.ENABLED,
                observed_at=_NOW + timedelta(seconds=2),
                reason="DEMO execution enabled",
            ),
            authorized_at=_NOW + timedelta(seconds=3),
        ),
        submitted_at=_NOW + timedelta(seconds=4),
    )


def test_limit_plan_carries_exact_absolute_stop_and_take_profit() -> None:
    built = build_ctrader_demo_order_create_plan(_configuration(), _submission())

    assert isinstance(built, Success)
    assert built.value.stop_loss == "1.09500"
    assert built.value.take_profit == "1.11000"
    assert '"stopLoss":"1.09500"' in built.value.body_json
    assert '"takeProfit":"1.11000"' in built.value.body_json


def test_protected_market_order_fails_closed_before_provider_io() -> None:
    built = build_ctrader_demo_order_create_plan(
        _configuration(),
        _submission(order_type=OrderType.MARKET),
    )

    assert isinstance(built, Failure)
    assert isinstance(built.error, CTraderDemoExecutionValidationError)
    assert "protected MARKET" in str(built.error)


class _Client:
    def __init__(self) -> None:
        self.fields: dict[str, object] | None = None

    @property
    def is_ready(self) -> bool:
        return True

    @property
    def account_id(self) -> int:
        return 424242

    def connect_and_authenticate(self) -> Result[None, CTraderOpenApiClientError]:
        return Success(None)

    def request(
        self,
        message_name: str,
        fields: Mapping[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Result[object, CTraderOpenApiClientError]:
        del client_msg_id, timeout_seconds
        assert message_name == "ProtoOANewOrderReq"
        self.fields = dict(fields)
        return Success(
            SimpleNamespace(
                executionType=2,
                order=SimpleNamespace(
                    orderId=70001,
                    utcLastUpdateTimestamp=int(_NOW.timestamp() * 1000),
                    tradeData=SimpleNamespace(symbolId=1234),
                ),
            )
        )

    def wait_for_event(
        self,
        message_name: str,
        *,
        timeout_seconds: float,
        predicate: Callable[[object], bool] | None = None,
    ) -> Result[object, CTraderOpenApiClientError]:
        del message_name, timeout_seconds, predicate
        raise AssertionError("unexpected cTrader event wait")

    def close(self) -> None:
        return None


def test_open_api_transport_sends_limit_protections_on_creation() -> None:
    plan = build_ctrader_demo_order_create_plan(_configuration(), _submission())
    assert isinstance(plan, Success)
    client = _Client()
    transport = CTraderOpenApiExecutionTransport(
        configuration=_configuration(),
        client=client,
        clock=lambda: _NOW,
    )

    result = transport.submit_order(plan.value, metadata=_METADATA)

    assert isinstance(result, Success)
    assert client.fields is not None
    assert client.fields["limitPrice"] == 1.1
    assert client.fields["stopLoss"] == 1.095
    assert client.fields["takeProfit"] == 1.11


class _DiscoveryClient(_Client):
    def __init__(self, *, orders: tuple[object, ...], has_more: bool) -> None:
        super().__init__()
        self.orders = orders
        self.has_more = has_more
        self.message_name: str | None = None

    def request(
        self,
        message_name: str,
        fields: Mapping[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Result[object, CTraderOpenApiClientError]:
        del fields, client_msg_id, timeout_seconds
        self.message_name = message_name
        return Success(SimpleNamespace(order=self.orders, hasMore=self.has_more))


def _discovered_order(client_order_id: str, *, order_id: int = 70001) -> object:
    return SimpleNamespace(
        clientOrderId=client_order_id,
        orderId=order_id,
        orderStatus=1,
        orderType=2,
        limitPrice=1.1,
        stopLoss=1.095,
        takeProfit=1.11,
        utcLastUpdateTimestamp=int(_NOW.timestamp() * 1000),
        tradeData=SimpleNamespace(
            symbolId=1234,
            tradeSide=1,
            volume=1,
            openTimestamp=int(_NOW.timestamp() * 1000),
        ),
    )


def test_open_api_transport_discovers_exact_client_order_id_without_create() -> None:
    plan = build_ctrader_demo_order_create_plan(_configuration(), _submission())
    assert isinstance(plan, Success)
    client = _DiscoveryClient(
        orders=(_discovered_order(plan.value.client_msg_id),),
        has_more=False,
    )
    transport = CTraderOpenApiExecutionTransport(
        configuration=_configuration(),
        client=client,
        clock=lambda: _NOW + timedelta(seconds=10),
    )

    result = transport.discover_order(
        plan.value,
        from_timestamp=_NOW - timedelta(minutes=1),
        to_timestamp=_NOW + timedelta(minutes=1),
        metadata=_METADATA,
    )

    assert isinstance(result, Success)
    assert result.value.status_code == 200
    assert b'"orderId":"70001"' in result.value.payload
    assert client.message_name == "ProtoOAOrderListReq"


def test_open_api_transport_contains_incomplete_discovery_scope() -> None:
    plan = build_ctrader_demo_order_create_plan(_configuration(), _submission())
    assert isinstance(plan, Success)
    client = _DiscoveryClient(orders=(), has_more=True)
    transport = CTraderOpenApiExecutionTransport(
        configuration=_configuration(),
        client=client,
        clock=lambda: _NOW + timedelta(seconds=10),
    )

    result = transport.discover_order(
        plan.value,
        from_timestamp=_NOW - timedelta(minutes=1),
        to_timestamp=_NOW + timedelta(minutes=1),
        metadata=_METADATA,
    )

    assert isinstance(result, Success)
    assert result.value.status_code == 409
