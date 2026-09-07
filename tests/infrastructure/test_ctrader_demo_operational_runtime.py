from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.ctrader_demo_operational_runtime import (
    CTraderDemoOperationalRuntime,
    CTraderDemoOperationalRuntimeValidationError,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiClientError,
    CTraderOpenApiCredentials,
)
from qore.infrastructure.execution_boundary import (
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionSubmission,
)
from qore.infrastructure.market_data import Instrument, MarketDataSnapshotId, QuoteRequest
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
    MarketTestEnvironmentAuthorization,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
    PortName,
    SourceId,
)
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
from qore.kernel.result import Result, Success

_NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)
_ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="424242",
    environment=MarketRuntimeEnvironment.DEMO,
)
_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("52000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("52000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo"),
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("52000000-0000-0000-0000-000000000003"))
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


def _credentials(*, account_id: int = 424242) -> CTraderOpenApiCredentials:
    return CTraderOpenApiCredentials(
        client_id="client-id",
        client_secret="client-secret",
        access_token="access-token",
        refresh_token="refresh-token",
        ctid_trader_account_id=account_id,
    )


def _authorization() -> MarketTestEnvironmentAuthorization:
    return MarketTestEnvironmentAuthorization(
        account=_ACCOUNT,
        policy_id="ctrader.demo.environment",
        authorized_at=_NOW,
    )


def _submission() -> ExecutionSubmission:
    intent = OrderIntent(
        intent_id=OrderIntentId(UUID("52000000-0000-0000-0000-000000000010")),
        idempotency_key=ExecutionIdempotencyKey(UUID("52000000-0000-0000-0000-000000000011")),
        instrument=ExecutionInstrument("EURUSD"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("10")),
        created_at=_NOW + timedelta(seconds=1),
        metadata=_METADATA,
    )
    authorization = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(UUID("52000000-0000-0000-0000-000000000012")),
        policy_id=PreTradePolicyId("ctrader.demo.pretrade"),
        intent_id=intent.intent_id,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=_NOW + timedelta(seconds=2),
        expires_at=_NOW + timedelta(minutes=1),
        reason="bounded demo execution approved",
    )
    return ExecutionSubmission(
        request_id=ExecutionRequestId(UUID("52000000-0000-0000-0000-000000000013")),
        receipt_id=ExecutionReceiptId(UUID("52000000-0000-0000-0000-000000000014")),
        authorized_intent=AuthorizedOrderIntent(
            intent=intent,
            authorization=authorization,
            switch=ExecutionSafetySwitchSnapshot(
                state=ExecutionSwitchState.ENABLED,
                observed_at=_NOW + timedelta(seconds=3),
                reason="demo execution switch enabled",
            ),
            authorized_at=_NOW + timedelta(seconds=4),
        ),
        submitted_at=_NOW + timedelta(seconds=5),
    )


class _FakeOpenApiClient:
    def __init__(self) -> None:
        self.ready = False
        self.closed = False
        self.requests: list[str] = []

    @property
    def is_ready(self) -> bool:
        return self.ready

    @property
    def account_id(self) -> int:
        return 424242

    def connect_and_authenticate(self) -> Result[None, CTraderOpenApiClientError]:
        self.ready = True
        return Success(None)

    def request(
        self,
        message_name: str,
        fields: Mapping[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Result[object, CTraderOpenApiClientError]:
        del fields, client_msg_id, timeout_seconds
        self.requests.append(message_name)
        if message_name == "ProtoOANewOrderReq":
            order = SimpleNamespace(
                orderId=70001,
                executedVolume=10,
                utcLastUpdateTimestamp=int((_NOW + timedelta(seconds=6)).timestamp() * 1000),
                tradeData=SimpleNamespace(symbolId=1234),
            )
            deal = SimpleNamespace(
                dealId=90001,
                symbolId=1234,
                filledVolume=10,
                executionPrice=1.10005,
                executionTimestamp=int((_NOW + timedelta(seconds=6)).timestamp() * 1000),
            )
            return Success(SimpleNamespace(executionType=3, order=order, deal=deal))
        if message_name == "ProtoOASubscribeSpotsReq":
            return Success(SimpleNamespace(ctidTraderAccountId=424242))
        if message_name == "ProtoOASymbolsListReq":
            return Success(
                SimpleNamespace(
                    ctidTraderAccountId=424242,
                    symbol=(SimpleNamespace(symbolId=1234, symbolName="EURUSD", enabled=True),),
                )
            )
        if message_name == "ProtoOASymbolByIdReq":
            return Success(
                SimpleNamespace(
                    ctidTraderAccountId=424242,
                    symbol=(
                        SimpleNamespace(
                            symbolId=1234,
                            digits=5,
                            minVolume=1,
                            maxVolume=1_000_000,
                            stepVolume=1,
                        ),
                    ),
                )
            )
        raise AssertionError(f"unexpected request: {message_name}")

    def wait_for_event(
        self,
        message_name: str,
        *,
        timeout_seconds: float,
        predicate: Callable[[object], bool] | None = None,
    ) -> Result[object, CTraderOpenApiClientError]:
        del timeout_seconds
        assert message_name == "ProtoOASpotEvent"
        event = SimpleNamespace(
            symbolId=1234,
            bid=110000,
            ask=110010,
            timestamp=int((_NOW + timedelta(seconds=7)).timestamp() * 1000),
        )
        assert predicate is not None and predicate(event)
        return Success(event)

    def close(self) -> None:
        self.closed = True


def _runtime(client: _FakeOpenApiClient) -> CTraderDemoOperationalRuntime:
    return CTraderDemoOperationalRuntime(
        configuration=_configuration(),
        credentials=_credentials(),
        environment_authorization=_authorization(),
        market_data_descriptor=_DESCRIPTOR,
        client=client,
        clock=lambda: _NOW + timedelta(seconds=7),
    )


def test_credentials_never_reveal_secret_material() -> None:
    rendered = repr(_credentials())
    assert "client-secret" not in rendered
    assert "access-token" not in rendered
    assert "refresh-token" not in rendered
    assert rendered.count("<redacted>") == 4


def test_runtime_connects_reads_quote_and_executes_only_authorized_demo_submission() -> None:
    client = _FakeOpenApiClient()
    runtime = _runtime(client)

    health = runtime.connect(checked_at=_NOW, metadata=_METADATA)
    quote = runtime.market_data.read_quote(
        QuoteRequest(instrument=Instrument("EURUSD")),
        snapshot_id=MarketDataSnapshotId(UUID("52000000-0000-0000-0000-000000000020")),
        metadata=_METADATA,
    )
    executed = runtime.submit_authorized(_submission())

    assert isinstance(health, Success)
    assert health.value.availability is PortAvailability.AVAILABLE
    assert isinstance(quote, Success)
    assert quote.value.bid == 1.1
    assert quote.value.ask == 1.1001
    assert isinstance(executed, Success)
    assert executed.value.provider_order_ref == "70001"
    assert len(executed.value.fills) == 1
    assert executed.value.fills[0].is_complete is True
    assert client.requests == [
        "ProtoOASymbolsListReq",
        "ProtoOASymbolByIdReq",
        "ProtoOASubscribeSpotsReq",
        "ProtoOASymbolsListReq",
        "ProtoOASymbolByIdReq",
        "ProtoOANewOrderReq",
    ]

    runtime.close()
    assert client.closed is True


def test_runtime_rejects_mismatched_credential_account_before_network_access() -> None:
    with pytest.raises(CTraderDemoOperationalRuntimeValidationError):
        CTraderDemoOperationalRuntime(
            configuration=_configuration(),
            credentials=_credentials(account_id=999999),
            environment_authorization=_authorization(),
            market_data_descriptor=_DESCRIPTOR,
            client=_FakeOpenApiClient(),
        )
