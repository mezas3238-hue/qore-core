from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_codec import (
    build_ctrader_demo_order_cancel_plan,
    build_ctrader_demo_order_create_plan,
    build_ctrader_demo_submit_gateway_receipt,
    decode_ctrader_demo_fill_observation,
    decode_ctrader_demo_order_cancel_response,
    decode_ctrader_demo_order_create_response,
    decode_ctrader_demo_order_query_response,
)
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoExecutionNotAcceptedError,
    CTraderDemoExecutionValidationError,
    CTraderDemoOrderDisposition,
)
from qore.infrastructure.execution_boundary import (
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionStatus,
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
from qore.infrastructure.transport import (
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 23, 30, tzinfo=UTC)
_ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="demo-001",
    environment=MarketRuntimeEnvironment.DEMO,
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("32000000-0000-0000-0000-000000000001"))
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


def _submission(
    *,
    suffix: int = 2,
    order_type: OrderType = OrderType.MARKET,
    quantity: str = "10",
    limit_price: str | None = None,
) -> ExecutionSubmission:
    intent = OrderIntent(
        intent_id=OrderIntentId(UUID(f"32000000-0000-0000-0000-{suffix:012d}")),
        idempotency_key=ExecutionIdempotencyKey(UUID(f"32000000-0000-0000-1000-{suffix:012d}")),
        instrument=ExecutionInstrument("EURUSD"),
        side=OrderSide.BUY,
        order_type=order_type,
        quantity=OrderQuantity(Decimal(quantity)),
        created_at=_NOW,
        metadata=_METADATA,
        limit_price=OrderPrice(Decimal(limit_price)) if limit_price else None,
    )
    authorization = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(UUID(f"32000000-0000-0000-2000-{suffix:012d}")),
        policy_id=PreTradePolicyId("mission03.demo.pretrade"),
        intent_id=intent.intent_id,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(minutes=1),
        reason="bounded demo execution approved",
    )
    authorized = AuthorizedOrderIntent(
        intent=intent,
        authorization=authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=_NOW + timedelta(seconds=2),
            reason="demo execution switch enabled",
        ),
        authorized_at=_NOW + timedelta(seconds=3),
    )
    return ExecutionSubmission(
        request_id=ExecutionRequestId(UUID(f"32000000-0000-0000-3000-{suffix:012d}")),
        receipt_id=ExecutionReceiptId(UUID(f"32000000-0000-0000-4000-{suffix:012d}")),
        authorized_intent=authorized,
        submitted_at=_NOW + timedelta(seconds=4),
    )


def _create_response(
    *,
    submission: ExecutionSubmission,
    provider_ref: str = "70001",
    status: str = "accepted",
    symbol_id: int = 1234,
) -> ExternalTransportResponse:
    payload = {
        "orderId": provider_ref,
        "clientMsgId": str(submission.idempotency_key.value),
        "symbolId": symbol_id,
        "status": status,
        "createdAt": "2026-08-08T23:30:05+00:00",
    }
    return ExternalTransportResponse(
        status_code=200,
        received_at=_NOW + timedelta(seconds=6),
        payload=json.dumps(payload).encode("utf-8"),
    )


def test_build_order_create_plan_is_deterministic_and_secret_free() -> None:
    submission = _submission()
    first = build_ctrader_demo_order_create_plan(_configuration(), submission)
    second = build_ctrader_demo_order_create_plan(_configuration(), submission)
    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value == second.value
    plan = first.value
    assert plan.symbol_id == 1234
    assert plan.volume_units == 10
    assert plan.client_msg_id == str(submission.idempotency_key.value)
    assert "demo-001" not in repr(plan.sanitized_values())
    assert plan.account_fingerprint.startswith("sha256:")


def test_quantity_must_be_integer_multiple_of_volume_step() -> None:
    submission = _submission(quantity="10.5")
    result = build_ctrader_demo_order_create_plan(_configuration(), submission)
    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoExecutionValidationError)


def test_quantity_must_respect_native_provider_volume_constraints() -> None:
    configuration = _configuration()
    mapping = replace(
        configuration.symbol_mappings[0],
        min_volume_units=5,
        max_volume_units=100,
        step_volume_units=5,
    )
    constrained = replace(configuration, symbol_mappings=(mapping,))

    below_minimum = build_ctrader_demo_order_create_plan(
        constrained,
        _submission(quantity="4"),
    )
    wrong_step = build_ctrader_demo_order_create_plan(
        constrained,
        _submission(quantity="6"),
    )
    above_maximum = build_ctrader_demo_order_create_plan(
        constrained,
        _submission(quantity="101"),
    )

    assert isinstance(below_minimum, Failure)
    assert isinstance(wrong_step, Failure)
    assert isinstance(above_maximum, Failure)


def test_limit_order_requires_exact_price() -> None:
    submission = _submission(
        order_type=OrderType.LIMIT,
        limit_price="1.234567",  # 6 decimals vs 5 digits
    )
    result = build_ctrader_demo_order_create_plan(_configuration(), submission)
    assert isinstance(result, Failure)


def test_decode_create_response_accepted() -> None:
    submission = _submission()
    plan_result = build_ctrader_demo_order_create_plan(_configuration(), submission)
    assert isinstance(plan_result, Success)
    response = _create_response(submission=submission)
    decoded = decode_ctrader_demo_order_create_response(
        _configuration(), submission, plan_result.value, response
    )
    assert isinstance(decoded, Success)
    assert decoded.value.disposition is CTraderDemoOrderDisposition.ACCEPTED
    assert decoded.value.provider_order_ref == "70001"


def test_decode_create_response_rejected_is_not_accepted() -> None:
    submission = _submission()
    plan_result = build_ctrader_demo_order_create_plan(_configuration(), submission)
    assert isinstance(plan_result, Success)
    response = _create_response(submission=submission, status="rejected")
    decoded = decode_ctrader_demo_order_create_response(
        _configuration(), submission, plan_result.value, response
    )
    assert isinstance(decoded, Success)
    receipt = build_ctrader_demo_submit_gateway_receipt(decoded.value)
    assert isinstance(receipt, Failure)
    assert isinstance(receipt.error, CTraderDemoExecutionNotAcceptedError)


def test_decode_create_response_symbol_mismatch_fails() -> None:
    submission = _submission()
    plan_result = build_ctrader_demo_order_create_plan(_configuration(), submission)
    assert isinstance(plan_result, Success)
    response = _create_response(submission=submission, symbol_id=9999)
    decoded = decode_ctrader_demo_order_create_response(
        _configuration(), submission, plan_result.value, response
    )
    assert isinstance(decoded, Failure)


def test_decode_fill_observation_and_cancel() -> None:
    submission = _submission()
    fill_payload = json.dumps(
        {
            "orderId": "70001",
            "fillId": "90001",
            "symbolId": 1234,
            "filledVolume": 4,
            "cumulativeVolume": 4,
            "price": "1.23456",
            "timestamp": "2026-08-08T23:30:06+00:00",
            "isComplete": False,
        }
    ).encode("utf-8")
    fill = decode_ctrader_demo_fill_observation(
        _configuration(),
        submission,
        fill_payload,
        received_at=_NOW + timedelta(seconds=7),
    )
    assert isinstance(fill, Success)
    assert fill.value.fill_quantity == Decimal("4")
    assert fill.value.cumulative_quantity == Decimal("4")

    cancel_payload = json.dumps(
        {
            "orderId": "70001",
            "status": "cancelled",
            "cancelledAt": "2026-08-08T23:30:08+00:00",
        }
    ).encode("utf-8")
    cancel = decode_ctrader_demo_order_cancel_response(
        _configuration(),
        provider_order_ref="70001",
        response=ExternalTransportResponse(
            status_code=200,
            received_at=_NOW + timedelta(seconds=9),
            payload=cancel_payload,
        ),
    )
    assert isinstance(cancel, Success)
    assert cancel.value.status is ExecutionStatus.CANCELLED


def test_cancel_plan_is_deterministic() -> None:
    requested = _NOW + timedelta(seconds=6)
    first = build_ctrader_demo_order_cancel_plan(
        _configuration(),
        provider_order_ref="70001",
        requested_at=requested,
    )
    second = build_ctrader_demo_order_cancel_plan(
        _configuration(),
        provider_order_ref="70001",
        requested_at=requested,
    )
    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value == second.value
    assert "demo-001" not in repr(first.value.sanitized_values())


def test_query_response_decode_rejects_mismatched_order_ref() -> None:
    payload = json.dumps(
        {
            "orderId": "70002",
            "status": "filled",
            "createdAt": "2026-08-08T23:30:05+00:00",
        }
    ).encode("utf-8")
    result = decode_ctrader_demo_order_query_response(
        _configuration(),
        provider_order_ref="70001",
        response=ExternalTransportResponse(
            status_code=200,
            received_at=_NOW + timedelta(seconds=6),
            payload=payload,
        ),
    )
    assert isinstance(result, Failure)
