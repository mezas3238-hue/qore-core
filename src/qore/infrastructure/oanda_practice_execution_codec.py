from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from re import fullmatch
from typing import cast

from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryError,
    ExecutionStatus,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeCapability,
    OandaPracticeRuntimeConfiguration,
)
from qore.infrastructure.order_intent import OrderSide, OrderType
from qore.infrastructure.test_execution_adapter import TestExecutionGatewayReceipt
from qore.infrastructure.transport import (
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Failure, Result, Success


class OandaPracticeExecutionCodecError(ExecutionBoundaryError):
    """Base error for deterministic OANDA Practice execution wire mapping."""

    __slots__ = ()


class OandaPracticeExecutionCodecValidationError(OandaPracticeExecutionCodecError):
    """A Practice execution request or response violates codec invariants."""

    __slots__ = ()


class OandaPracticeExecutionNotAcceptedError(OandaPracticeExecutionCodecError):
    """Provider acknowledged a request but did not leave an accepted execution."""

    __slots__ = ()


def _account_fingerprint(account_ref: str) -> str:
    digest = hashlib.sha256(account_ref.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:24]}"


def _aware_timestamp(value: object, *, field_name: str) -> Result[datetime, ExecutionBoundaryError]:
    if not isinstance(value, str) or not value:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                f"OANDA {field_name} must be a non-empty RFC3339 string"
            )
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                f"OANDA {field_name} must be parseable RFC3339"
            )
        )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                f"OANDA {field_name} must be timezone-aware"
            )
        )
    return Success(parsed)


def _numeric_ref(value: object, *, field_name: str) -> Result[str, ExecutionBoundaryError]:
    if not isinstance(value, str) or fullmatch(r"[0-9]+", value) is None:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                f"OANDA {field_name} must be a numeric reference"
            )
        )
    return Success(value)


def _decimal_number(
    value: object,
    *,
    field_name: str,
    allow_zero: bool = False,
) -> Result[Decimal, ExecutionBoundaryError]:
    if not isinstance(value, str) or not value:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                f"OANDA {field_name} must be a decimal string"
            )
        )
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                f"OANDA {field_name} must be a decimal string"
            )
        )
    if not parsed.is_finite() or (parsed == 0 and not allow_zero):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                f"OANDA {field_name} must be finite and non-zero"
            )
        )
    return Success(parsed)


def _json_object(payload: bytes) -> Result[dict[str, object], ExecutionBoundaryError]:
    try:
        decoded: object = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA execution response must be a UTF-8 JSON object"
            )
        )
    if not isinstance(decoded, dict) or any(not isinstance(key, str) for key in decoded):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA execution response root must be a string-keyed object"
            )
        )
    return Success(cast(dict[str, object], decoded))


def _transaction_object(
    root: dict[str, object],
    field_name: str,
) -> Result[dict[str, object] | None, ExecutionBoundaryError]:
    value = root.get(field_name)
    if value is None:
        return Success(None)
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                f"OANDA {field_name} must be an object when present"
            )
        )
    return Success(cast(dict[str, object], value))


def _related_transaction_refs(
    value: object,
) -> Result[tuple[str, ...], ExecutionBoundaryError]:
    if not isinstance(value, list) or not value:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA relatedTransactionIDs must be a non-empty array"
            )
        )
    refs: list[str] = []
    for item in value:
        parsed = _numeric_ref(item, field_name="relatedTransactionIDs entry")
        if isinstance(parsed, Failure):
            return parsed
        refs.append(parsed.value)
    if len(set(refs)) != len(refs):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA relatedTransactionIDs must not contain duplicates"
            )
        )
    return Success(tuple(refs))


def _signed_units(submission: ExecutionSubmission) -> Decimal:
    quantity = submission.authorized_intent.intent.quantity.value
    if submission.authorized_intent.intent.side is OrderSide.BUY:
        return quantity
    return -quantity


def _canonical_decimal(value: Decimal) -> str:
    return format(value, "f")


@dataclass(frozen=True, slots=True)
class OandaPracticeOrderCreatePlan:
    """Secret-free deterministic plan for one future Practice order-create request."""

    account: MarketTestAccountIdentity
    endpoint_origin: str
    path: str
    timeout: ExternalTransportTimeout
    body_json: str
    instrument: str
    signed_units: str
    order_type: OrderType
    limit_price: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise OandaPracticeExecutionCodecValidationError(
                "execution plan requires MarketTestAccountIdentity"
            )
        if self.account.provider_key != "oanda-v20":
            raise OandaPracticeExecutionCodecValidationError(
                "execution plan provider must be oanda-v20"
            )
        if self.account.environment is not MarketRuntimeEnvironment.DEMO:
            raise OandaPracticeExecutionCodecValidationError(
                "execution plan environment must be demo"
            )
        if self.endpoint_origin != "https://api-fxpractice.oanda.com":
            raise OandaPracticeExecutionCodecValidationError(
                "execution plan endpoint must be OANDA Practice"
            )
        expected_path = f"/v3/accounts/{self.account.account_ref}/orders"
        if self.path != expected_path:
            raise OandaPracticeExecutionCodecValidationError(
                "execution plan path must match configured Practice account"
            )
        if not isinstance(self.timeout, ExternalTransportTimeout):
            raise OandaPracticeExecutionCodecValidationError(
                "execution plan requires ExternalTransportTimeout"
            )
        if not isinstance(self.body_json, str) or not self.body_json:
            raise OandaPracticeExecutionCodecValidationError(
                "execution plan requires deterministic JSON body"
            )
        if not isinstance(self.instrument, str) or not self.instrument:
            raise OandaPracticeExecutionCodecValidationError(
                "execution plan requires instrument"
            )
        units = _decimal_number(self.signed_units, field_name="planned units")
        if isinstance(units, Failure):
            raise OandaPracticeExecutionCodecValidationError(
                "execution plan units must be finite and non-zero"
            ) from units.error
        if not isinstance(self.order_type, OrderType):
            raise OandaPracticeExecutionCodecValidationError(
                "execution plan requires canonical OrderType"
            )
        if self.order_type is OrderType.MARKET and self.limit_price is not None:
            raise OandaPracticeExecutionCodecValidationError(
                "market execution plan must not carry limit price"
            )
        if self.order_type is OrderType.LIMIT:
            if self.limit_price is None:
                raise OandaPracticeExecutionCodecValidationError(
                    "limit execution plan requires limit price"
                )
            price = _decimal_number(self.limit_price, field_name="planned limit price")
            if isinstance(price, Failure) or price.value <= 0:
                raise OandaPracticeExecutionCodecValidationError(
                    "limit execution plan price must be positive and finite"
                )

    @property
    def account_fingerprint(self) -> str:
        return _account_fingerprint(self.account.account_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account.logical_values(),
            self.endpoint_origin,
            self.path,
            self.timeout.logical_values(),
            self.body_json,
            self.instrument,
            self.signed_units,
            self.order_type.value,
            self.limit_price,
        )

    def sanitized_values(self) -> tuple[object, ...]:
        return (
            self.account.provider_key,
            self.account.environment.value,
            self.account_fingerprint,
            self.endpoint_origin,
            self.timeout.logical_values(),
            self.body_json,
            self.instrument,
            self.signed_units,
            self.order_type.value,
            self.limit_price,
        )


def build_oanda_practice_order_create_plan(
    configuration: OandaPracticeRuntimeConfiguration,
    submission: ExecutionSubmission,
) -> Result[OandaPracticeOrderCreatePlan, ExecutionBoundaryError]:
    """Map one already-authorized canonical submission to secret-free Practice JSON."""

    if not isinstance(configuration, OandaPracticeRuntimeConfiguration):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "execution mapping requires OandaPracticeRuntimeConfiguration"
            )
        )
    if not isinstance(submission, ExecutionSubmission):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "execution mapping requires ExecutionSubmission"
            )
        )
    if OandaPracticeCapability.ORDERS not in configuration.capabilities:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA Practice configuration must authorize orders capability"
            )
        )
    intent = submission.authorized_intent.intent
    if intent.instrument.value not in configuration.symbols:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "execution instrument is not allowlisted by Practice configuration"
            )
        )
    signed_units = _signed_units(submission)
    order: dict[str, object] = {
        "instrument": intent.instrument.value,
        "positionFill": "DEFAULT",
        "type": "MARKET" if intent.order_type is OrderType.MARKET else "LIMIT",
        "units": _canonical_decimal(signed_units),
    }
    limit_price: str | None = None
    if intent.order_type is OrderType.MARKET:
        order["timeInForce"] = "FOK"
    else:
        if intent.limit_price is None:
            return Failure(
                OandaPracticeExecutionCodecValidationError(
                    "canonical limit intent must carry limit price"
                )
            )
        limit_price = _canonical_decimal(intent.limit_price.value)
        order["price"] = limit_price
        order["timeInForce"] = "GTC"
    body_json = json.dumps(
        {"order": order},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    try:
        plan = OandaPracticeOrderCreatePlan(
            account=configuration.account,
            endpoint_origin=configuration.rest_endpoint.origin,
            path=f"/v3/accounts/{configuration.account.account_ref}/orders",
            timeout=configuration.rest_timeout,
            body_json=body_json,
            instrument=intent.instrument.value,
            signed_units=_canonical_decimal(signed_units),
            order_type=intent.order_type,
            limit_price=limit_price,
        )
    except OandaPracticeExecutionCodecError as error:
        return Failure(error)
    return Success(plan)


class OandaPracticeExecutionDisposition(StrEnum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class OandaPracticeExecutionOutcome:
    """Sanitized provider lifecycle evidence for one accepted order-create response."""

    account: MarketTestAccountIdentity
    provider_execution_ref: str
    disposition: OandaPracticeExecutionDisposition
    created_at: datetime
    recorded_at: datetime
    related_transaction_refs: tuple[str, ...]
    last_transaction_ref: str
    terminal_transaction_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise OandaPracticeExecutionCodecValidationError(
                "execution outcome requires MarketTestAccountIdentity"
            )
        if self.account.provider_key != "oanda-v20":
            raise OandaPracticeExecutionCodecValidationError(
                "execution outcome provider must be oanda-v20"
            )
        if self.account.environment is not MarketRuntimeEnvironment.DEMO:
            raise OandaPracticeExecutionCodecValidationError(
                "execution outcome environment must be demo"
            )
        for value, field_name in (
            (self.provider_execution_ref, "provider_execution_ref"),
            (self.last_transaction_ref, "last_transaction_ref"),
            (self.terminal_transaction_ref, "terminal_transaction_ref"),
        ):
            parsed = _numeric_ref(value, field_name=field_name)
            if isinstance(parsed, Failure):
                raise OandaPracticeExecutionCodecValidationError(
                    f"execution outcome {field_name} must be numeric"
                ) from parsed.error
        if not isinstance(self.disposition, OandaPracticeExecutionDisposition):
            raise OandaPracticeExecutionCodecValidationError(
                "execution outcome requires explicit disposition"
            )
        for timestamp_value, field_name in (
            (self.created_at, "created_at"),
            (self.recorded_at, "recorded_at"),
        ):
            if not isinstance(timestamp_value, datetime):
                raise OandaPracticeExecutionCodecValidationError(
                    f"execution outcome {field_name} must be datetime"
                )
            if timestamp_value.tzinfo is None or timestamp_value.utcoffset() is None:
                raise OandaPracticeExecutionCodecValidationError(
                    f"execution outcome {field_name} must be timezone-aware"
                )
        if self.recorded_at < self.created_at:
            raise OandaPracticeExecutionCodecValidationError(
                "execution outcome recorded_at must not predate creation"
            )
        if not isinstance(self.related_transaction_refs, tuple) or not self.related_transaction_refs:
            raise OandaPracticeExecutionCodecValidationError(
                "execution outcome requires related transaction refs"
            )
        for ref in self.related_transaction_refs:
            parsed = _numeric_ref(ref, field_name="related transaction ref")
            if isinstance(parsed, Failure):
                raise OandaPracticeExecutionCodecValidationError(
                    "execution outcome related transaction refs must be numeric"
                ) from parsed.error
        if len(set(self.related_transaction_refs)) != len(self.related_transaction_refs):
            raise OandaPracticeExecutionCodecValidationError(
                "execution outcome related transaction refs must not duplicate"
            )
        if self.provider_execution_ref not in self.related_transaction_refs:
            raise OandaPracticeExecutionCodecValidationError(
                "provider execution ref must be present in related transactions"
            )
        if self.terminal_transaction_ref not in self.related_transaction_refs:
            raise OandaPracticeExecutionCodecValidationError(
                "terminal transaction ref must be present in related transactions"
            )
        if self.last_transaction_ref != self.terminal_transaction_ref:
            raise OandaPracticeExecutionCodecValidationError(
                "last transaction ref must match terminal execution transaction"
            )

    @property
    def account_fingerprint(self) -> str:
        return _account_fingerprint(self.account.account_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account.logical_values(),
            self.provider_execution_ref,
            self.disposition.value,
            self.created_at.isoformat(),
            self.recorded_at.isoformat(),
            self.related_transaction_refs,
            self.last_transaction_ref,
            self.terminal_transaction_ref,
        )

    def sanitized_values(self) -> tuple[object, ...]:
        return (
            self.account.provider_key,
            self.account.environment.value,
            self.account_fingerprint,
            self.provider_execution_ref,
            self.disposition.value,
            self.created_at.isoformat(),
            self.recorded_at.isoformat(),
            self.related_transaction_refs,
            self.last_transaction_ref,
            self.terminal_transaction_ref,
        )


def _validate_create_transaction(
    transaction: dict[str, object],
    *,
    configuration: OandaPracticeRuntimeConfiguration,
    plan: OandaPracticeOrderCreatePlan,
) -> Result[tuple[str, datetime], ExecutionBoundaryError]:
    transaction_ref = _numeric_ref(transaction.get("id"), field_name="orderCreateTransaction.id")
    if isinstance(transaction_ref, Failure):
        return transaction_ref
    if transaction.get("accountID") != configuration.account.account_ref:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA create transaction account must match configured Practice account"
            )
        )
    if transaction.get("instrument") != plan.instrument:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA create transaction instrument must match execution plan"
            )
        )
    units = _decimal_number(transaction.get("units"), field_name="orderCreateTransaction.units")
    if isinstance(units, Failure):
        return units
    expected_units = Decimal(plan.signed_units)
    if units.value != expected_units:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA create transaction units must match execution plan"
            )
        )
    expected_type = "MARKET_ORDER" if plan.order_type is OrderType.MARKET else "LIMIT_ORDER"
    if transaction.get("type") != expected_type:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA create transaction type must match execution plan"
            )
        )
    expected_tif = "FOK" if plan.order_type is OrderType.MARKET else "GTC"
    if transaction.get("timeInForce") != expected_tif:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA create transaction timeInForce must match execution plan"
            )
        )
    if transaction.get("positionFill") != "DEFAULT":
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA create transaction positionFill must remain DEFAULT"
            )
        )
    if plan.order_type is OrderType.LIMIT:
        price = _decimal_number(transaction.get("price"), field_name="orderCreateTransaction.price")
        if isinstance(price, Failure):
            return price
        if plan.limit_price is None or price.value != Decimal(plan.limit_price):
            return Failure(
                OandaPracticeExecutionCodecValidationError(
                    "OANDA create transaction price must match limit plan"
                )
            )
    created_at = _aware_timestamp(transaction.get("time"), field_name="orderCreateTransaction.time")
    if isinstance(created_at, Failure):
        return created_at
    return Success((transaction_ref.value, created_at.value))


def decode_oanda_practice_order_create_response(
    configuration: OandaPracticeRuntimeConfiguration,
    submission: ExecutionSubmission,
    plan: OandaPracticeOrderCreatePlan,
    response: ExternalTransportResponse,
) -> Result[OandaPracticeExecutionOutcome, ExecutionBoundaryError]:
    """Decode one deterministic OANDA order-create response without performing IO."""

    if not isinstance(configuration, OandaPracticeRuntimeConfiguration):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "execution response decoding requires OandaPracticeRuntimeConfiguration"
            )
        )
    if not isinstance(submission, ExecutionSubmission):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "execution response decoding requires ExecutionSubmission"
            )
        )
    if not isinstance(plan, OandaPracticeOrderCreatePlan):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "execution response decoding requires OandaPracticeOrderCreatePlan"
            )
        )
    if plan.account != configuration.account:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "execution response plan account must match configuration"
            )
        )
    if not isinstance(response, ExternalTransportResponse):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "execution response decoding requires ExternalTransportResponse"
            )
        )
    if response.status_code != 201:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA order-create response must be HTTP 201"
            )
        )
    root_result = _json_object(response.payload)
    if isinstance(root_result, Failure):
        return root_result
    root = root_result.value
    related_result = _related_transaction_refs(root.get("relatedTransactionIDs"))
    if isinstance(related_result, Failure):
        return related_result
    related = related_result.value
    last_result = _numeric_ref(root.get("lastTransactionID"), field_name="lastTransactionID")
    if isinstance(last_result, Failure):
        return last_result
    create_result = _transaction_object(root, "orderCreateTransaction")
    if isinstance(create_result, Failure):
        return create_result
    if create_result.value is None:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA accepted order response requires orderCreateTransaction"
            )
        )
    validated_create = _validate_create_transaction(
        create_result.value,
        configuration=configuration,
        plan=plan,
    )
    if isinstance(validated_create, Failure):
        return validated_create
    provider_ref, created_at = validated_create.value
    if provider_ref not in related:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA create transaction must be listed in related transactions"
            )
        )
    fill_result = _transaction_object(root, "orderFillTransaction")
    if isinstance(fill_result, Failure):
        return fill_result
    cancel_result = _transaction_object(root, "orderCancelTransaction")
    if isinstance(cancel_result, Failure):
        return cancel_result
    if fill_result.value is not None and cancel_result.value is not None:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA order response cannot be both filled and immediately cancelled"
            )
        )

    disposition = OandaPracticeExecutionDisposition.PENDING
    terminal_ref = provider_ref
    recorded_at = created_at
    terminal = fill_result.value or cancel_result.value
    if terminal is not None:
        terminal_ref_result = _numeric_ref(terminal.get("id"), field_name="terminal transaction id")
        if isinstance(terminal_ref_result, Failure):
            return terminal_ref_result
        if terminal.get("accountID") != configuration.account.account_ref:
            return Failure(
                OandaPracticeExecutionCodecValidationError(
                    "OANDA terminal transaction account must match configuration"
                )
            )
        if terminal.get("orderID") != provider_ref:
            return Failure(
                OandaPracticeExecutionCodecValidationError(
                    "OANDA terminal transaction orderID must match created execution"
                )
            )
        terminal_time = _aware_timestamp(terminal.get("time"), field_name="terminal transaction time")
        if isinstance(terminal_time, Failure):
            return terminal_time
        if terminal_time.value < created_at:
            return Failure(
                OandaPracticeExecutionCodecValidationError(
                    "OANDA terminal transaction must not predate order creation"
                )
            )
        terminal_ref = terminal_ref_result.value
        recorded_at = terminal_time.value
        if terminal_ref not in related:
            return Failure(
                OandaPracticeExecutionCodecValidationError(
                    "OANDA terminal transaction must be listed in related transactions"
                )
            )
        if fill_result.value is not None:
            if terminal.get("type") != "ORDER_FILL":
                return Failure(
                    OandaPracticeExecutionCodecValidationError(
                        "OANDA fill transaction type must be ORDER_FILL"
                    )
                )
            if terminal.get("instrument") != plan.instrument:
                return Failure(
                    OandaPracticeExecutionCodecValidationError(
                        "OANDA fill transaction instrument must match execution plan"
                    )
                )
            fill_units = _decimal_number(terminal.get("units"), field_name="orderFillTransaction.units")
            if isinstance(fill_units, Failure):
                return fill_units
            if fill_units.value != Decimal(plan.signed_units):
                return Failure(
                    OandaPracticeExecutionCodecValidationError(
                        "OANDA fill transaction units must match execution plan"
                    )
                )
            disposition = OandaPracticeExecutionDisposition.FILLED
        else:
            if terminal.get("type") != "ORDER_CANCEL":
                return Failure(
                    OandaPracticeExecutionCodecValidationError(
                        "OANDA cancel transaction type must be ORDER_CANCEL"
                    )
                )
            disposition = OandaPracticeExecutionDisposition.CANCELLED

    if last_result.value != terminal_ref:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA lastTransactionID must match terminal execution transaction"
            )
        )
    if recorded_at < submission.submitted_at:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA execution outcome must not predate canonical submission"
            )
        )
    try:
        outcome = OandaPracticeExecutionOutcome(
            account=configuration.account,
            provider_execution_ref=provider_ref,
            disposition=disposition,
            created_at=created_at,
            recorded_at=recorded_at,
            related_transaction_refs=related,
            last_transaction_ref=last_result.value,
            terminal_transaction_ref=terminal_ref,
        )
    except OandaPracticeExecutionCodecError as error:
        return Failure(error)
    return Success(outcome)


def build_oanda_practice_submit_gateway_receipt(
    outcome: OandaPracticeExecutionOutcome,
) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
    """Project a provider outcome into the existing submit acknowledgement boundary."""

    if not isinstance(outcome, OandaPracticeExecutionOutcome):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "gateway receipt projection requires OandaPracticeExecutionOutcome"
            )
        )
    if outcome.disposition is OandaPracticeExecutionDisposition.CANCELLED:
        return Failure(
            OandaPracticeExecutionNotAcceptedError(
                "OANDA order was immediately cancelled and is not an accepted execution"
            )
        )
    try:
        receipt = TestExecutionGatewayReceipt(
            provider_execution_ref=outcome.provider_execution_ref,
            status=ExecutionStatus.ACCEPTED,
            recorded_at=outcome.recorded_at,
        )
    except ExecutionBoundaryError as error:
        return Failure(error)
    return Success(receipt)


def decode_oanda_practice_order_cancel_response(
    configuration: OandaPracticeRuntimeConfiguration,
    *,
    provider_execution_ref: str,
    response: ExternalTransportResponse,
) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
    """Decode one explicit provider cancellation response without performing IO."""

    if not isinstance(configuration, OandaPracticeRuntimeConfiguration):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "cancel decoding requires OandaPracticeRuntimeConfiguration"
            )
        )
    provider_ref_result = _numeric_ref(
        provider_execution_ref,
        field_name="provider_execution_ref",
    )
    if isinstance(provider_ref_result, Failure):
        return provider_ref_result
    if not isinstance(response, ExternalTransportResponse):
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "cancel decoding requires ExternalTransportResponse"
            )
        )
    if response.status_code != 200:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA order-cancel response must be HTTP 200"
            )
        )
    root_result = _json_object(response.payload)
    if isinstance(root_result, Failure):
        return root_result
    root = root_result.value
    related_result = _related_transaction_refs(root.get("relatedTransactionIDs"))
    if isinstance(related_result, Failure):
        return related_result
    last_result = _numeric_ref(root.get("lastTransactionID"), field_name="lastTransactionID")
    if isinstance(last_result, Failure):
        return last_result
    transaction_result = _transaction_object(root, "orderCancelTransaction")
    if isinstance(transaction_result, Failure):
        return transaction_result
    transaction = transaction_result.value
    if transaction is None:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA cancel response requires orderCancelTransaction"
            )
        )
    cancel_ref_result = _numeric_ref(transaction.get("id"), field_name="orderCancelTransaction.id")
    if isinstance(cancel_ref_result, Failure):
        return cancel_ref_result
    if transaction.get("accountID") != configuration.account.account_ref:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA cancel transaction account must match configuration"
            )
        )
    if transaction.get("orderID") != provider_execution_ref:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA cancel transaction orderID must match provider execution ref"
            )
        )
    if transaction.get("type") != "ORDER_CANCEL":
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA cancel transaction type must be ORDER_CANCEL"
            )
        )
    if transaction.get("reason") != "CLIENT_REQUEST":
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA cancel transaction reason must be CLIENT_REQUEST"
            )
        )
    cancel_time = _aware_timestamp(transaction.get("time"), field_name="orderCancelTransaction.time")
    if isinstance(cancel_time, Failure):
        return cancel_time
    if cancel_ref_result.value not in related_result.value:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA cancel transaction must be listed in related transactions"
            )
        )
    if last_result.value != cancel_ref_result.value:
        return Failure(
            OandaPracticeExecutionCodecValidationError(
                "OANDA cancel lastTransactionID must match cancellation transaction"
            )
        )
    try:
        receipt = TestExecutionGatewayReceipt(
            provider_execution_ref=provider_execution_ref,
            status=ExecutionStatus.CANCELLED,
            recorded_at=cancel_time.value,
        )
    except ExecutionBoundaryError as error:
        return Failure(error)
    return Success(receipt)
