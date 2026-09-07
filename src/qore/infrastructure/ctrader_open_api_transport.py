from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from threading import Lock

from qore.infrastructure.ctrader_demo_execution_codec import (
    CTraderOrderCancelPlan,
    CTraderOrderCreatePlan,
)
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoRuntimeConfiguration,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiMessageClientBoundary,
)
from qore.infrastructure.execution_boundary import ExecutionBoundaryError
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.transport import ExternalTransportResponse
from qore.kernel.result import Failure, Result, Success

_EXECUTION_STATUSES = {
    2: "accepted",
    3: "filled",
    5: "cancelled",
    6: "expired",
    7: "rejected",
    11: "partially_filled",
}
_ORDER_STATUSES = {
    1: "accepted",
    2: "filled",
    3: "rejected",
    4: "expired",
    5: "cancelled",
}
_ORDER_TYPES = {"market": 1, "limit": 2}
_TRADE_SIDES = {"buy": 1, "sell": 2}


class CTraderOpenApiTransportError(ExecutionBoundaryError):
    """Sanitized cTrader Protobuf transport failure."""

    __slots__ = ()


class CTraderOpenApiTransportValidationError(CTraderOpenApiTransportError):
    """A native provider message violates its exact QORE binding."""

    __slots__ = ()


def _timestamp(value: object, fallback: datetime) -> datetime:
    if type(value) is int and value > 0:
        try:
            return datetime.fromtimestamp(value / 1000, tz=UTC)
        except (OverflowError, OSError, ValueError):
            pass
    return fallback


def _json_response(payload: dict[str, object], received_at: datetime) -> ExternalTransportResponse:
    return ExternalTransportResponse(
        status_code=200,
        received_at=received_at,
        payload=json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8"),
    )


def _required_int(value: object, *, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise CTraderOpenApiTransportValidationError(f"cTrader {field_name} must be a positive int")
    return value


def _configured_account_id(configuration: CTraderDemoRuntimeConfiguration) -> int:
    try:
        account_id = int(configuration.account.account_ref)
    except ValueError as error:
        raise CTraderOpenApiTransportValidationError(
            "cTrader DEMO account_ref must be numeric"
        ) from error
    return _required_int(account_id, field_name="configured account id")


class CTraderOpenApiExecutionTransport:
    """Concrete Protobuf/TLS implementation of the cTrader execution transport port."""

    __slots__ = (
        "_client",
        "_clock",
        "_configuration",
        "_fill_payloads",
        "_lock",
    )

    def __init__(
        self,
        *,
        configuration: CTraderDemoRuntimeConfiguration,
        client: CTraderOpenApiMessageClientBoundary,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
            raise CTraderOpenApiTransportValidationError(
                "configuration must be CTraderDemoRuntimeConfiguration"
            )
        if client.account_id != _configured_account_id(configuration):
            raise CTraderOpenApiTransportValidationError(
                "native client account must match cTrader DEMO configuration"
            )
        self._configuration = configuration
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = Lock()
        self._fill_payloads: dict[str, list[bytes]] = {}

    @property
    def configuration(self) -> CTraderDemoRuntimeConfiguration:
        return self._configuration

    def _ready(self) -> Result[None, ExecutionBoundaryError]:
        if self._client.is_ready:
            return Success(None)
        connected = self._client.connect_and_authenticate()
        if isinstance(connected, Failure):
            return Failure(CTraderOpenApiTransportError(str(connected.error)))
        if not self._client.is_ready:
            return Failure(
                CTraderOpenApiTransportError(
                    "cTrader client did not enter authenticated DEMO state"
                )
            )
        return Success(None)

    def _execution_payload(
        self,
        event: object,
        *,
        client_msg_id: str,
        expected_symbol_id: int,
        received_at: datetime,
    ) -> dict[str, object]:
        execution_type = getattr(event, "executionType", None)
        if type(execution_type) is not int:
            raise CTraderOpenApiTransportValidationError(
                "cTrader execution event type must be an int"
            )
        status = _EXECUTION_STATUSES.get(execution_type)
        if status is None:
            raise CTraderOpenApiTransportValidationError("unsupported cTrader execution event type")
        order = getattr(event, "order", None)
        if order is None:
            raise CTraderOpenApiTransportValidationError(
                "cTrader execution event is missing order evidence"
            )
        order_id = _required_int(getattr(order, "orderId", None), field_name="orderId")
        trade_data = getattr(order, "tradeData", None)
        symbol_id = _required_int(getattr(trade_data, "symbolId", None), field_name="symbolId")
        if symbol_id != expected_symbol_id:
            raise CTraderOpenApiTransportValidationError(
                "cTrader execution event symbol does not match submitted plan"
            )
        created_at = _timestamp(getattr(order, "utcLastUpdateTimestamp", None), received_at)
        return {
            "clientMsgId": client_msg_id,
            "createdAt": created_at.isoformat(),
            "orderId": str(order_id),
            "status": status,
            "symbolId": symbol_id,
        }

    def _retain_fill(
        self,
        event: object,
        received_at: datetime,
        *,
        cumulative_volume_override: int | None = None,
        complete_override: bool | None = None,
    ) -> None:
        execution_type = getattr(event, "executionType", None)
        if execution_type not in {3, 11}:
            return
        order = getattr(event, "order", None)
        deal = getattr(event, "deal", None)
        if order is None or deal is None:
            return
        order_id = _required_int(getattr(order, "orderId", None), field_name="orderId")
        deal_id = _required_int(getattr(deal, "dealId", None), field_name="dealId")
        symbol_id = _required_int(getattr(deal, "symbolId", None), field_name="deal symbolId")
        filled_volume = _required_int(
            getattr(deal, "filledVolume", None), field_name="filledVolume"
        )
        cumulative_volume = _required_int(
            cumulative_volume_override
            if cumulative_volume_override is not None
            else getattr(order, "executedVolume", None),
            field_name="executedVolume",
        )
        price = getattr(deal, "executionPrice", None)
        if not isinstance(price, float) or price <= 0.0:
            raise CTraderOpenApiTransportValidationError(
                "cTrader execution price must be a positive float"
            )
        provider_at = _timestamp(getattr(deal, "executionTimestamp", None), received_at)
        payload = json.dumps(
            {
                "cumulativeVolume": cumulative_volume,
                "fillId": str(deal_id),
                "filledVolume": filled_volume,
                "isComplete": execution_type == 3
                if complete_override is None
                else complete_override,
                "orderId": str(order_id),
                "price": format(Decimal(str(price)), "f"),
                "symbolId": symbol_id,
                "timestamp": provider_at.isoformat(),
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        with self._lock:
            self._fill_payloads.setdefault(str(order_id), []).append(payload)

    def submit_order(
        self,
        plan: CTraderOrderCreatePlan,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        del metadata
        ready = self._ready()
        if isinstance(ready, Failure):
            return ready
        fields: dict[str, object] = {
            "ctidTraderAccountId": self._client.account_id,
            "orderType": _ORDER_TYPES[plan.order_type.value],
            "symbolId": plan.symbol_id,
            "tradeSide": _TRADE_SIDES[plan.side.value],
            "volume": plan.volume_units,
        }
        if plan.limit_price is not None:
            fields["limitPrice"] = float(plan.limit_price)
        response = self._client.request(
            "ProtoOANewOrderReq",
            fields,
            client_msg_id=plan.client_msg_id,
            timeout_seconds=plan.timeout.milliseconds / 1000,
        )
        if isinstance(response, Failure):
            return Failure(CTraderOpenApiTransportError(str(response.error)))
        received_at = self._clock()
        try:
            payload = self._execution_payload(
                response.value,
                client_msg_id=plan.client_msg_id,
                expected_symbol_id=plan.symbol_id,
                received_at=received_at,
            )
            self._retain_fill(response.value, received_at)
            return Success(_json_response(payload, received_at))
        except (CTraderOpenApiTransportError, ValueError) as error:
            return Failure(CTraderOpenApiTransportError(str(error)))

    def cancel_order(
        self,
        plan: CTraderOrderCancelPlan,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        del metadata
        ready = self._ready()
        if isinstance(ready, Failure):
            return ready
        try:
            order_id = int(plan.provider_order_ref)
        except ValueError:
            return Failure(CTraderOpenApiTransportError("provider order ref must be numeric"))
        response = self._client.request(
            "ProtoOACancelOrderReq",
            {
                "ctidTraderAccountId": self._client.account_id,
                "orderId": order_id,
            },
            client_msg_id=f"cancel:{plan.provider_order_ref}",
            timeout_seconds=plan.timeout.milliseconds / 1000,
        )
        if isinstance(response, Failure):
            return Failure(CTraderOpenApiTransportError(str(response.error)))
        received_at = self._clock()
        if getattr(response.value, "executionType", None) != 5:
            return Failure(
                CTraderOpenApiTransportError("cTrader cancellation did not return ORDER_CANCELLED")
            )
        order = getattr(response.value, "order", None)
        native_order_id = getattr(order, "orderId", None)
        if native_order_id != order_id:
            return Failure(CTraderOpenApiTransportError("cancelled order id mismatch"))
        cancelled_at = _timestamp(getattr(order, "utcLastUpdateTimestamp", None), received_at)
        return Success(
            _json_response(
                {
                    "cancelledAt": cancelled_at.isoformat(),
                    "orderId": plan.provider_order_ref,
                    "status": "cancelled",
                },
                received_at,
            )
        )

    def query_order(
        self,
        provider_order_ref: str,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        del metadata
        ready = self._ready()
        if isinstance(ready, Failure):
            return ready
        try:
            order_id = int(provider_order_ref)
        except ValueError:
            return Failure(CTraderOpenApiTransportError("provider order ref must be numeric"))
        response = self._client.request(
            "ProtoOAOrderDetailsReq",
            {
                "ctidTraderAccountId": self._client.account_id,
                "orderId": order_id,
            },
            client_msg_id=f"query:{provider_order_ref}",
            timeout_seconds=self._configuration.rest_timeout.milliseconds / 1000,
        )
        if isinstance(response, Failure):
            return Failure(CTraderOpenApiTransportError(str(response.error)))
        received_at = self._clock()
        order = getattr(response.value, "order", None)
        native_id = getattr(order, "orderId", None)
        order_status = getattr(order, "orderStatus", None)
        if type(order_status) is not int:
            return Failure(CTraderOpenApiTransportError("invalid order query status"))
        status = _ORDER_STATUSES.get(order_status)
        if native_id != order_id or status is None:
            return Failure(CTraderOpenApiTransportError("invalid order query response"))
        created_at = _timestamp(getattr(order, "utcLastUpdateTimestamp", None), received_at)
        deals = getattr(response.value, "deal", ())
        try:
            ordered_deals = sorted(
                deals,
                key=lambda item: (
                    getattr(item, "executionTimestamp", 0),
                    getattr(item, "dealId", 0),
                ),
            )
            cumulative_volume = 0
            for index, deal in enumerate(ordered_deals):
                cumulative_volume += _required_int(
                    getattr(deal, "filledVolume", None), field_name="filledVolume"
                )
                event_proxy = _ExecutionEventProxy(order=order, deal=deal)
                self._retain_fill(
                    event_proxy,
                    received_at,
                    cumulative_volume_override=cumulative_volume,
                    complete_override=(status == "filled" and index == len(ordered_deals) - 1),
                )
        except (TypeError, CTraderOpenApiTransportValidationError):
            return Failure(CTraderOpenApiTransportError("invalid order deal collection"))
        return Success(
            _json_response(
                {
                    "createdAt": created_at.isoformat(),
                    "orderId": provider_order_ref,
                    "status": status,
                },
                received_at,
            )
        )

    def drain_fill_payloads(self, provider_order_ref: str) -> tuple[bytes, ...]:
        """Return each native deal once for canonical gateway ingestion."""
        with self._lock:
            return tuple(self._fill_payloads.pop(provider_order_ref, ()))


class _ExecutionEventProxy:
    __slots__ = ("deal", "executionType", "order")

    def __init__(self, *, order: object, deal: object) -> None:
        self.executionType = 3
        self.order = order
        self.deal = deal
