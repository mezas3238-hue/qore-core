from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import cast

from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoExecutionError,
    CTraderDemoExecutionNotAcceptedError,
    CTraderDemoExecutionOutcome,
    CTraderDemoExecutionValidationError,
    CTraderDemoFillObservation,
    CTraderDemoOrderDisposition,
)
from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryError,
    ExecutionStatus,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import (
    ExecutionInstrument,
    OrderSide,
    OrderType,
)
from qore.infrastructure.test_execution_adapter import TestExecutionGatewayReceipt
from qore.infrastructure.transport import (
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Failure, Result, Success

_CTRADER_DEMO_ORIGIN = "https://demo.ctraderapi.com:5035"
_WIRE_SIDES = {OrderSide.BUY: "BUY", OrderSide.SELL: "SELL"}
_WIRE_ORDER_TYPES = {OrderType.MARKET: "MARKET", OrderType.LIMIT: "LIMIT"}
_WIRE_DISPOSITIONS: dict[str, CTraderDemoOrderDisposition] = {
    "accepted": CTraderDemoOrderDisposition.ACCEPTED,
    "rejected": CTraderDemoOrderDisposition.REJECTED,
    "partially_filled": CTraderDemoOrderDisposition.PARTIALLY_FILLED,
    "filled": CTraderDemoOrderDisposition.FILLED,
    "cancelled": CTraderDemoOrderDisposition.CANCELLED,
    "expired": CTraderDemoOrderDisposition.EXPIRED,
}


def _aware_timestamp(
    value: object,
    *,
    field_name: str,
) -> Result[datetime, CTraderDemoExecutionError]:
    if not isinstance(value, str) or not value:
        return Failure(
            CTraderDemoExecutionValidationError(
                f"cTrader {field_name} must be a non-empty RFC3339 string"
            )
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return Failure(
            CTraderDemoExecutionValidationError(f"cTrader {field_name} must be parseable RFC3339")
        )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return Failure(
            CTraderDemoExecutionValidationError(f"cTrader {field_name} must be timezone-aware")
        )
    return Success(parsed)


def _json_object(
    payload: bytes,
) -> Result[dict[str, object], CTraderDemoExecutionError]:
    try:
        decoded: object = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader execution response must be a UTF-8 JSON object"
            )
        )
    if not isinstance(decoded, dict):
        return Failure(
            CTraderDemoExecutionValidationError("cTrader execution response root must be an object")
        )
    if any(not isinstance(key, str) for key in decoded):
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader execution response root must use string keys"
            )
        )
    return Success(cast(dict[str, object], decoded))


def _decimal_string(
    value: object,
    *,
    field_name: str,
) -> Result[Decimal, CTraderDemoExecutionError]:
    if not isinstance(value, str) or not value:
        return Failure(
            CTraderDemoExecutionValidationError(
                f"cTrader {field_name} must be a non-empty decimal string"
            )
        )
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return Failure(
            CTraderDemoExecutionValidationError(f"cTrader {field_name} must be a decimal string")
        )
    if not parsed.is_finite():
        return Failure(CTraderDemoExecutionValidationError(f"cTrader {field_name} must be finite"))
    return Success(parsed)


def _quantity_to_units(
    quantity: Decimal,
    step: Decimal,
) -> Result[int, CTraderDemoExecutionError]:
    if not isinstance(quantity, Decimal) or not quantity.is_finite() or quantity <= 0:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader volume mapping requires a finite positive quantity"
            )
        )
    if not isinstance(step, Decimal) or not step.is_finite() or step <= 0:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader volume mapping requires a finite positive volume_step"
            )
        )
    try:
        quotient, remainder = divmod(quantity, step)
    except InvalidOperation:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader volume mapping could not divide quantity by step"
            )
        )
    if remainder != 0:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader quantity must be an integer multiple of symbol volume_step"
            )
        )
    units = int(quotient)
    if units <= 0:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader volume mapping must produce a positive unit count"
            )
        )
    return Success(units)


def _units_to_quantity(
    units: object,
    step: Decimal,
    *,
    field_name: str,
) -> Result[Decimal, CTraderDemoExecutionError]:
    if type(units) is not int or units <= 0:
        return Failure(
            CTraderDemoExecutionValidationError(
                f"cTrader {field_name} must be a positive integer volume"
            )
        )
    quantity = Decimal(units) * step
    if not quantity.is_finite() or quantity <= 0:
        return Failure(
            CTraderDemoExecutionValidationError(
                f"cTrader {field_name} must map to a finite positive quantity"
            )
        )
    return Success(quantity)


def _exact_price(
    price: Decimal,
    digits: int,
) -> Result[str, CTraderDemoExecutionError]:
    if not isinstance(price, Decimal) or not price.is_finite() or price <= 0:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader price mapping requires a finite positive price"
            )
        )
    if type(digits) is not int or digits < 0:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader price mapping requires non-negative digits"
            )
        )
    try:
        quantum = Decimal(1).scaleb(-digits)
        rounded = price.quantize(quantum, rounding=ROUND_HALF_EVEN)
    except (InvalidOperation, ValueError):
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader price cannot be normalized with symbol digits"
            )
        )
    if rounded != price:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader price must be exactly representable at symbol digits"
            )
        )
    return Success(format(price, f".{digits}f"))


def _mapping_for_instrument(
    configuration: CTraderDemoRuntimeConfiguration,
    instrument: ExecutionInstrument,
) -> Result[CTraderSymbolMapping, CTraderDemoExecutionError]:
    if not isinstance(instrument, ExecutionInstrument):
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader symbol mapping requires a canonical ExecutionInstrument"
            )
        )
    mapping = configuration.symbol_mapping(instrument)
    if mapping is None:
        return Failure(
            CTraderDemoExecutionValidationError(
                "execution instrument is not mapped by cTrader DEMO configuration"
            )
        )
    return Success(mapping)


@dataclass(frozen=True, slots=True)
class CTraderOrderCreatePlan:
    """Secret-free deterministic plan for one future cTrader order-create request."""

    account: MarketTestAccountIdentity
    endpoint_origin: str
    client_msg_id: str
    symbol_id: int
    symbol_name: str
    side: OrderSide
    order_type: OrderType
    volume_units: int
    limit_price: str | None
    timeout: ExternalTransportTimeout
    body_json: str

    def __post_init__(self) -> None:
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise CTraderDemoExecutionValidationError(
                "order-create plan requires MarketTestAccountIdentity"
            )
        if self.account.provider_key != "ctrader-demo":
            raise CTraderDemoExecutionValidationError(
                "order-create plan provider must be ctrader-demo"
            )
        if self.account.environment is not MarketRuntimeEnvironment.DEMO:
            raise CTraderDemoExecutionValidationError("order-create plan environment must be demo")
        if self.endpoint_origin != _CTRADER_DEMO_ORIGIN:
            raise CTraderDemoExecutionValidationError(
                "order-create plan endpoint must be the cTrader DEMO host"
            )
        if not isinstance(self.client_msg_id, str) or not self.client_msg_id:
            raise CTraderDemoExecutionValidationError(
                "order-create plan client_msg_id must be non-empty"
            )
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CTraderDemoExecutionValidationError(
                "order-create plan symbol_id must be a positive int"
            )
        if not isinstance(self.symbol_name, str) or not self.symbol_name:
            raise CTraderDemoExecutionValidationError(
                "order-create plan symbol_name must be non-empty"
            )
        if not isinstance(self.side, OrderSide):
            raise CTraderDemoExecutionValidationError("order-create plan side must be OrderSide")
        if not isinstance(self.order_type, OrderType):
            raise CTraderDemoExecutionValidationError(
                "order-create plan order_type must be OrderType"
            )
        if type(self.volume_units) is not int or self.volume_units <= 0:
            raise CTraderDemoExecutionValidationError(
                "order-create plan volume_units must be a positive int"
            )
        if self.order_type is OrderType.MARKET and self.limit_price is not None:
            raise CTraderDemoExecutionValidationError(
                "market order-create plan must not carry limit price"
            )
        if self.order_type is OrderType.LIMIT:
            if self.limit_price is None:
                raise CTraderDemoExecutionValidationError(
                    "limit order-create plan requires limit price"
                )
            price = _decimal_string(self.limit_price, field_name="planned limit price")
            if isinstance(price, Failure) or price.value <= 0:
                raise CTraderDemoExecutionValidationError(
                    "limit order-create plan price must be positive"
                )
        if not isinstance(self.timeout, ExternalTransportTimeout):
            raise CTraderDemoExecutionValidationError(
                "order-create plan requires ExternalTransportTimeout"
            )
        expected_body: dict[str, object] = {
            "clientMsgId": self.client_msg_id,
            "symbolId": self.symbol_id,
            "tradeSide": _WIRE_SIDES[self.side],
            "orderType": _WIRE_ORDER_TYPES[self.order_type],
            "volume": self.volume_units,
        }
        if self.order_type is OrderType.LIMIT:
            expected_body["limitPrice"] = self.limit_price
        try:
            decoded_body: object = json.loads(self.body_json)
        except (TypeError, json.JSONDecodeError) as error:
            raise CTraderDemoExecutionValidationError(
                "order-create plan body must be valid deterministic JSON"
            ) from error
        if decoded_body != expected_body:
            raise CTraderDemoExecutionValidationError(
                "order-create plan body must contain only the canonical cTrader order"
            )

    @property
    def account_fingerprint(self) -> str:
        from qore.infrastructure.ctrader_demo_execution_contracts import (
            ctrader_demo_account_fingerprint,
        )

        return ctrader_demo_account_fingerprint(self.account.account_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account.logical_values(),
            self.endpoint_origin,
            self.client_msg_id,
            self.symbol_id,
            self.symbol_name,
            self.side.value,
            self.order_type.value,
            self.volume_units,
            self.limit_price,
            self.timeout.logical_values(),
            self.body_json,
        )

    def sanitized_values(self) -> tuple[object, ...]:
        return (
            self.account.provider_key,
            self.account.environment.value,
            self.account_fingerprint,
            self.endpoint_origin,
            self.client_msg_id,
            self.symbol_id,
            self.symbol_name,
            self.side.value,
            self.order_type.value,
            self.volume_units,
            self.limit_price,
            self.timeout.logical_values(),
            self.body_json,
        )


def build_ctrader_demo_order_create_plan(
    configuration: CTraderDemoRuntimeConfiguration,
    submission: ExecutionSubmission,
) -> Result[CTraderOrderCreatePlan, CTraderDemoExecutionError]:
    """Map an already-authorized canonical submission to a secret-free cTrader order."""
    if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
        return Failure(
            CTraderDemoExecutionValidationError(
                "order-create mapping requires CTraderDemoRuntimeConfiguration"
            )
        )
    if not isinstance(submission, ExecutionSubmission):
        return Failure(
            CTraderDemoExecutionValidationError("order-create mapping requires ExecutionSubmission")
        )
    if CTraderDemoCapability.ORDERS not in configuration.capabilities:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader DEMO configuration must authorize orders capability"
            )
        )
    intent = submission.authorized_intent.intent
    mapping_result = _mapping_for_instrument(configuration, intent.instrument)
    if isinstance(mapping_result, Failure):
        return mapping_result
    mapping = mapping_result.value
    units_result = _quantity_to_units(intent.quantity.value, mapping.volume_step)
    if isinstance(units_result, Failure):
        return units_result
    units = units_result.value
    if not (mapping.min_volume_units <= units <= mapping.max_volume_units):
        return Failure(
            CTraderDemoExecutionValidationError("cTrader volume is outside provider symbol bounds")
        )
    if units % mapping.step_volume_units != 0:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader volume does not align to provider stepVolume"
            )
        )
    limit_price: str | None = None
    if intent.order_type is OrderType.LIMIT:
        if intent.limit_price is None:
            return Failure(
                CTraderDemoExecutionValidationError("canonical limit intent must carry limit price")
            )
        price_result = _exact_price(intent.limit_price.value, mapping.digits)
        if isinstance(price_result, Failure):
            return price_result
        limit_price = price_result.value
    body: dict[str, object] = {
        "clientMsgId": str(intent.idempotency_key.value),
        "symbolId": mapping.symbol_id,
        "tradeSide": _WIRE_SIDES[intent.side],
        "orderType": _WIRE_ORDER_TYPES[intent.order_type],
        "volume": units,
    }
    if limit_price is not None:
        body["limitPrice"] = limit_price
    body_json = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
    try:
        plan = CTraderOrderCreatePlan(
            account=configuration.account,
            endpoint_origin=configuration.endpoint.origin,
            client_msg_id=str(intent.idempotency_key.value),
            symbol_id=mapping.symbol_id,
            symbol_name=mapping.symbol_name,
            side=intent.side,
            order_type=intent.order_type,
            volume_units=units,
            limit_price=limit_price,
            timeout=configuration.rest_timeout,
            body_json=body_json,
        )
    except CTraderDemoExecutionError as error:
        return Failure(error)
    return Success(plan)


@dataclass(frozen=True, slots=True)
class CTraderOrderCancelPlan:
    """Secret-free deterministic plan for one future cTrader order cancellation."""

    account: MarketTestAccountIdentity
    endpoint_origin: str
    provider_order_ref: str
    requested_at: datetime
    timeout: ExternalTransportTimeout

    def __post_init__(self) -> None:
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise CTraderDemoExecutionValidationError(
                "order-cancel plan requires MarketTestAccountIdentity"
            )
        if self.account.provider_key != "ctrader-demo":
            raise CTraderDemoExecutionValidationError(
                "order-cancel plan provider must be ctrader-demo"
            )
        if self.account.environment is not MarketRuntimeEnvironment.DEMO:
            raise CTraderDemoExecutionValidationError("order-cancel plan environment must be demo")
        if self.endpoint_origin != _CTRADER_DEMO_ORIGIN:
            raise CTraderDemoExecutionValidationError(
                "order-cancel plan endpoint must be the cTrader DEMO host"
            )
        if not isinstance(self.provider_order_ref, str) or not self.provider_order_ref:
            raise CTraderDemoExecutionValidationError(
                "order-cancel plan provider_order_ref must be non-empty"
            )
        if not isinstance(self.requested_at, datetime):
            raise CTraderDemoExecutionValidationError(
                "order-cancel plan requested_at must be a datetime"
            )
        if self.requested_at.tzinfo is None or self.requested_at.utcoffset() is None:
            raise CTraderDemoExecutionValidationError(
                "order-cancel plan requested_at must be timezone-aware"
            )
        if not isinstance(self.timeout, ExternalTransportTimeout):
            raise CTraderDemoExecutionValidationError(
                "order-cancel plan requires ExternalTransportTimeout"
            )

    @property
    def account_fingerprint(self) -> str:
        from qore.infrastructure.ctrader_demo_execution_contracts import (
            ctrader_demo_account_fingerprint,
        )

        return ctrader_demo_account_fingerprint(self.account.account_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account.logical_values(),
            self.endpoint_origin,
            self.provider_order_ref,
            self.requested_at.isoformat(),
            self.timeout.logical_values(),
        )

    def sanitized_values(self) -> tuple[object, ...]:
        return (
            self.account.provider_key,
            self.account.environment.value,
            self.account_fingerprint,
            self.endpoint_origin,
            self.provider_order_ref,
            self.requested_at.isoformat(),
            self.timeout.logical_values(),
        )


def build_ctrader_demo_order_cancel_plan(
    configuration: CTraderDemoRuntimeConfiguration,
    *,
    provider_order_ref: str,
    requested_at: datetime,
) -> Result[CTraderOrderCancelPlan, CTraderDemoExecutionError]:
    """Build one exact secret-free cTrader cancellation plan."""
    if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
        return Failure(
            CTraderDemoExecutionValidationError(
                "order-cancel planning requires CTraderDemoRuntimeConfiguration"
            )
        )
    if CTraderDemoCapability.ORDERS not in configuration.capabilities:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader DEMO configuration must authorize orders capability"
            )
        )
    if not isinstance(provider_order_ref, str) or not provider_order_ref:
        return Failure(
            CTraderDemoExecutionValidationError("provider_order_ref must be a non-empty string")
        )
    if not isinstance(requested_at, datetime):
        return Failure(CTraderDemoExecutionValidationError("requested_at must be a datetime"))
    if requested_at.tzinfo is None or requested_at.utcoffset() is None:
        return Failure(CTraderDemoExecutionValidationError("requested_at must be timezone-aware"))
    try:
        plan = CTraderOrderCancelPlan(
            account=configuration.account,
            endpoint_origin=configuration.endpoint.origin,
            provider_order_ref=provider_order_ref,
            requested_at=requested_at,
            timeout=configuration.rest_timeout,
        )
    except CTraderDemoExecutionError as error:
        return Failure(error)
    return Success(plan)


def decode_ctrader_demo_order_create_response(
    configuration: CTraderDemoRuntimeConfiguration,
    submission: ExecutionSubmission,
    plan: CTraderOrderCreatePlan,
    response: ExternalTransportResponse,
) -> Result[CTraderDemoExecutionOutcome, CTraderDemoExecutionError]:
    """Decode one cTrader order-create response without performing provider IO."""
    if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
        return Failure(
            CTraderDemoExecutionValidationError(
                "create response decoding requires cTrader configuration"
            )
        )
    if not isinstance(submission, ExecutionSubmission):
        return Failure(
            CTraderDemoExecutionValidationError(
                "create response decoding requires ExecutionSubmission"
            )
        )
    if not isinstance(plan, CTraderOrderCreatePlan):
        return Failure(
            CTraderDemoExecutionValidationError(
                "create response decoding requires CTraderOrderCreatePlan"
            )
        )
    expected_plan = build_ctrader_demo_order_create_plan(configuration, submission)
    if isinstance(expected_plan, Failure):
        return expected_plan
    if expected_plan.value != plan:
        return Failure(
            CTraderDemoExecutionValidationError(
                "create response plan must match the canonical submission exactly"
            )
        )
    if not isinstance(response, ExternalTransportResponse):
        return Failure(
            CTraderDemoExecutionValidationError(
                "create response decoding requires ExternalTransportResponse"
            )
        )
    if not response.is_success:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader order-create response must be an HTTP 2xx success"
            )
        )
    root_result = _json_object(response.payload)
    if isinstance(root_result, Failure):
        return root_result
    root = root_result.value
    order_ref = root.get("orderId")
    if not isinstance(order_ref, str) or not order_ref:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader create response orderId must be a non-empty string"
            )
        )
    client_msg_id = root.get("clientMsgId")
    if client_msg_id != plan.client_msg_id:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader create response clientMsgId must match the plan"
            )
        )
    symbol_id = root.get("symbolId")
    if type(symbol_id) is not int or symbol_id != plan.symbol_id:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader create response symbolId must match the plan"
            )
        )
    raw_disposition = root.get("status")
    if not isinstance(raw_disposition, str):
        return Failure(
            CTraderDemoExecutionValidationError("cTrader create response requires a status string")
        )
    disposition = _WIRE_DISPOSITIONS.get(raw_disposition)
    if disposition is None:
        return Failure(
            CTraderDemoExecutionValidationError("cTrader create response status is unsupported")
        )
    created_at_result = _aware_timestamp(
        root.get("createdAt"), field_name="create response createdAt"
    )
    if isinstance(created_at_result, Failure):
        return created_at_result
    created_at = created_at_result.value
    if response.received_at < created_at:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader create response must not predate provider creation time"
            )
        )
    if response.received_at < submission.submitted_at:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader create response must not predate canonical submission"
            )
        )
    try:
        outcome = CTraderDemoExecutionOutcome(
            account=configuration.account,
            provider_order_ref=order_ref,
            disposition=disposition,
            created_at=created_at,
            recorded_at=response.received_at,
        )
    except CTraderDemoExecutionError as error:
        return Failure(error)
    return Success(outcome)


def build_ctrader_demo_submit_gateway_receipt(
    outcome: CTraderDemoExecutionOutcome,
) -> Result[TestExecutionGatewayReceipt, CTraderDemoExecutionError]:
    """Project definitive provider evidence into the canonical submit acknowledgement."""
    if not isinstance(outcome, CTraderDemoExecutionOutcome):
        return Failure(
            CTraderDemoExecutionValidationError(
                "gateway receipt projection requires CTraderDemoExecutionOutcome"
            )
        )
    if outcome.disposition in {
        CTraderDemoOrderDisposition.REJECTED,
        CTraderDemoOrderDisposition.CANCELLED,
        CTraderDemoOrderDisposition.EXPIRED,
    }:
        return Failure(
            CTraderDemoExecutionNotAcceptedError(
                f"cTrader order was not accepted: {outcome.disposition.value}"
            )
        )
    try:
        receipt = TestExecutionGatewayReceipt(
            provider_execution_ref=outcome.provider_order_ref,
            status=ExecutionStatus.ACCEPTED,
            recorded_at=outcome.recorded_at,
        )
    except ExecutionBoundaryError as error:
        return Failure(
            CTraderDemoExecutionValidationError(
                f"cTrader gateway receipt construction failed: {error}"
            )
        )
    return Success(receipt)


def decode_ctrader_demo_order_cancel_response(
    configuration: CTraderDemoRuntimeConfiguration,
    *,
    provider_order_ref: str,
    response: ExternalTransportResponse,
) -> Result[TestExecutionGatewayReceipt, CTraderDemoExecutionError]:
    """Decode one explicit cTrader cancellation response without provider IO."""
    if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
        return Failure(
            CTraderDemoExecutionValidationError("cancel decoding requires cTrader configuration")
        )
    if not isinstance(provider_order_ref, str) or not provider_order_ref:
        return Failure(
            CTraderDemoExecutionValidationError("provider_order_ref must be a non-empty string")
        )
    if not isinstance(response, ExternalTransportResponse):
        return Failure(
            CTraderDemoExecutionValidationError(
                "cancel decoding requires ExternalTransportResponse"
            )
        )
    if not response.is_success:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader order-cancel response must be an HTTP 2xx success"
            )
        )
    root_result = _json_object(response.payload)
    if isinstance(root_result, Failure):
        return root_result
    root = root_result.value
    order_ref = root.get("orderId")
    if order_ref != provider_order_ref:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader cancel response orderId must match provider order ref"
            )
        )
    raw_status = root.get("status")
    if raw_status != "cancelled":
        return Failure(
            CTraderDemoExecutionValidationError("cTrader cancel response status must be cancelled")
        )
    cancelled_at_result = _aware_timestamp(
        root.get("cancelledAt"), field_name="cancel response cancelledAt"
    )
    if isinstance(cancelled_at_result, Failure):
        return cancelled_at_result
    cancelled_at = cancelled_at_result.value
    if response.received_at < cancelled_at:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader cancel response must not predate cancellation"
            )
        )
    try:
        receipt = TestExecutionGatewayReceipt(
            provider_execution_ref=provider_order_ref,
            status=ExecutionStatus.CANCELLED,
            recorded_at=cancelled_at,
        )
    except ExecutionBoundaryError as error:
        return Failure(
            CTraderDemoExecutionValidationError(
                f"cTrader cancel receipt construction failed: {error}"
            )
        )
    return Success(receipt)


def decode_ctrader_demo_fill_observation(
    configuration: CTraderDemoRuntimeConfiguration,
    submission: ExecutionSubmission,
    payload: bytes,
    *,
    received_at: datetime,
) -> Result[CTraderDemoFillObservation, CTraderDemoExecutionError]:
    """Decode one cTrader fill event into trustworthy provider fill evidence."""
    if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
        return Failure(
            CTraderDemoExecutionValidationError("fill decoding requires cTrader configuration")
        )
    if not isinstance(submission, ExecutionSubmission):
        return Failure(
            CTraderDemoExecutionValidationError("fill decoding requires ExecutionSubmission")
        )
    if not isinstance(received_at, datetime):
        return Failure(CTraderDemoExecutionValidationError("fill received_at must be a datetime"))
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        return Failure(
            CTraderDemoExecutionValidationError("fill received_at must be timezone-aware")
        )
    root_result = _json_object(payload)
    if isinstance(root_result, Failure):
        return root_result
    root = root_result.value
    order_ref = root.get("orderId")
    if not isinstance(order_ref, str) or not order_ref:
        return Failure(
            CTraderDemoExecutionValidationError("cTrader fill orderId must be a non-empty string")
        )
    fill_ref = root.get("fillId")
    if not isinstance(fill_ref, str) or not fill_ref:
        return Failure(
            CTraderDemoExecutionValidationError("cTrader fill fillId must be a non-empty string")
        )
    if fill_ref == order_ref:
        return Failure(
            CTraderDemoExecutionValidationError("cTrader fill fillId must not equal orderId")
        )
    symbol_id = root.get("symbolId")
    if type(symbol_id) is not int or symbol_id <= 0:
        return Failure(
            CTraderDemoExecutionValidationError("cTrader fill symbolId must be a positive int")
        )
    intent = submission.authorized_intent.intent
    mapping_result = _mapping_for_instrument(configuration, intent.instrument)
    if isinstance(mapping_result, Failure):
        return mapping_result
    mapping = mapping_result.value
    if symbol_id != mapping.symbol_id:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader fill symbolId must match the submission mapping"
            )
        )
    fill_units = root.get("filledVolume")
    if type(fill_units) is not int or fill_units <= 0:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader fill filledVolume must be a positive integer"
            )
        )
    cumulative_units = root.get("cumulativeVolume")
    if type(cumulative_units) is not int or cumulative_units <= 0:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader fill cumulativeVolume must be a positive integer"
            )
        )
    fill_quantity_result = _units_to_quantity(
        fill_units, mapping.volume_step, field_name="fill filledVolume"
    )
    if isinstance(fill_quantity_result, Failure):
        return fill_quantity_result
    cumulative_result = _units_to_quantity(
        cumulative_units, mapping.volume_step, field_name="fill cumulativeVolume"
    )
    if isinstance(cumulative_result, Failure):
        return cumulative_result
    raw_price = root.get("price")
    price_result = _decimal_string(raw_price, field_name="fill price")
    if isinstance(price_result, Failure):
        return price_result
    if price_result.value <= 0:
        return Failure(CTraderDemoExecutionValidationError("cTrader fill price must be positive"))
    provider_timestamp_result = _aware_timestamp(root.get("timestamp"), field_name="fill timestamp")
    if isinstance(provider_timestamp_result, Failure):
        return provider_timestamp_result
    is_complete = root.get("isComplete", False)
    if type(is_complete) is not bool:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader fill isComplete must be a strict bool when present"
            )
        )
    try:
        observation = CTraderDemoFillObservation(
            receipt_id=submission.receipt_id,
            idempotency_key=submission.idempotency_key,
            account=configuration.account,
            instrument=intent.instrument,
            side=intent.side,
            provider_order_ref=order_ref,
            fill_ref=fill_ref,
            fill_quantity=fill_quantity_result.value,
            cumulative_quantity=cumulative_result.value,
            fill_price=price_result.value,
            provider_timestamp=provider_timestamp_result.value,
            received_at=received_at,
            is_complete=is_complete,
        )
    except CTraderDemoExecutionError as error:
        return Failure(error)
    return Success(observation)


def decode_ctrader_demo_order_query_response(
    configuration: CTraderDemoRuntimeConfiguration,
    *,
    provider_order_ref: str,
    response: ExternalTransportResponse,
) -> Result[CTraderDemoExecutionOutcome, CTraderDemoExecutionError]:
    """Decode one cTrader order-state query used for reconciliation search."""
    if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
        return Failure(
            CTraderDemoExecutionValidationError(
                "order query decoding requires cTrader configuration"
            )
        )
    if not isinstance(provider_order_ref, str) or not provider_order_ref:
        return Failure(
            CTraderDemoExecutionValidationError("provider_order_ref must be a non-empty string")
        )
    if not isinstance(response, ExternalTransportResponse):
        return Failure(
            CTraderDemoExecutionValidationError(
                "order query decoding requires ExternalTransportResponse"
            )
        )
    if response.status_code == 404:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader order query must not decode a not-found response"
            )
        )
    if not response.is_success:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader order-query response must be an HTTP 2xx success"
            )
        )
    root_result = _json_object(response.payload)
    if isinstance(root_result, Failure):
        return root_result
    root = root_result.value
    order_ref = root.get("orderId")
    if order_ref != provider_order_ref:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader order query orderId must match provider order ref"
            )
        )
    raw_status = root.get("status")
    if not isinstance(raw_status, str):
        return Failure(
            CTraderDemoExecutionValidationError("cTrader order query requires a status string")
        )
    disposition = _WIRE_DISPOSITIONS.get(raw_status)
    if disposition is None:
        return Failure(
            CTraderDemoExecutionValidationError("cTrader order query status is unsupported")
        )
    created_at_result = _aware_timestamp(root.get("createdAt"), field_name="order query createdAt")
    if isinstance(created_at_result, Failure):
        return created_at_result
    if response.received_at < created_at_result.value:
        return Failure(
            CTraderDemoExecutionValidationError(
                "cTrader order query must not predate provider creation time"
            )
        )
    try:
        outcome = CTraderDemoExecutionOutcome(
            account=configuration.account,
            provider_order_ref=order_ref,
            disposition=disposition,
            created_at=created_at_result.value,
            recorded_at=response.received_at,
        )
    except CTraderDemoExecutionError as error:
        return Failure(error)
    return Success(outcome)
