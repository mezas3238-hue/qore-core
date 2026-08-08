from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.infrastructure.connectivity import ProviderEndpoint
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
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeCapability,
    OandaPracticeOperationalLimits,
    OandaPracticeRuntimeConfiguration,
    oanda_practice_secret_requirements,
)
from qore.infrastructure.oanda_practice_execution_codec import (
    OandaPracticeExecutionCodecValidationError,
    OandaPracticeExecutionDisposition,
    OandaPracticeExecutionNotAcceptedError,
    build_oanda_practice_order_create_plan,
    build_oanda_practice_submit_gateway_receipt,
    decode_oanda_practice_order_cancel_response,
    decode_oanda_practice_order_create_response,
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

_NOW = datetime(2026, 8, 8, 22, 30, tzinfo=UTC)


def _configuration() -> OandaPracticeRuntimeConfiguration:
    return OandaPracticeRuntimeConfiguration(
        provider_key="oanda-v20",
        environment=MarketRuntimeEnvironment.DEMO,
        rest_endpoint=ProviderEndpoint(host="api-fxpractice.oanda.com"),
        streaming_endpoint=ProviderEndpoint(host="stream-fxpractice.oanda.com"),
        account=MarketTestAccountIdentity(
            provider_key="oanda-v20",
            account_ref="practice-001",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        symbols=("EUR_USD", "GBP_USD"),
        capabilities=(
            OandaPracticeCapability.ACCOUNT,
            OandaPracticeCapability.ORDERS,
            OandaPracticeCapability.PRICING,
            OandaPracticeCapability.TRANSACTIONS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        stream_connect_timeout=ExternalTransportTimeout(milliseconds=5000),
        limits=OandaPracticeOperationalLimits(
            rest_requests_per_second=1,
            active_streams=0,
            new_connections_per_second=1,
        ),
        secret_requirements=oanda_practice_secret_requirements(),
    )


def _submission(
    *,
    side: OrderSide = OrderSide.BUY,
    order_type: OrderType = OrderType.MARKET,
    quantity: str = "100",
    limit_price: str = "1.1000",
) -> ExecutionSubmission:
    intent = OrderIntent(
        intent_id=OrderIntentId(UUID("31000000-0000-0000-0000-000000000001")),
        idempotency_key=ExecutionIdempotencyKey(
            UUID("31000000-0000-0000-0000-000000000002")
        ),
        instrument=ExecutionInstrument("EUR_USD"),
        side=side,
        order_type=order_type,
        quantity=OrderQuantity(Decimal(quantity)),
        created_at=_NOW,
        metadata=ExternalRequestMetadata(
            correlation_id=CorrelationId(
                UUID("31000000-0000-0000-0000-000000000003")
            )
        ),
        limit_price=(
            OrderPrice(Decimal(limit_price))
            if order_type is OrderType.LIMIT
            else None
        ),
    )
    authorization = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(
            UUID("31000000-0000-0000-0000-000000000004")
        ),
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
        request_id=ExecutionRequestId(
            UUID("31000000-0000-0000-0000-000000000005")
        ),
        receipt_id=ExecutionReceiptId(
            UUID("31000000-0000-0000-0000-000000000006")
        ),
        authorized_intent=authorized,
        submitted_at=_NOW + timedelta(seconds=4),
    )


def _response(payload: dict[str, object], *, status_code: int) -> ExternalTransportResponse:
    return ExternalTransportResponse(
        status_code=status_code,
        received_at=_NOW + timedelta(seconds=6),
        payload=json.dumps(payload).encode("utf-8"),
    )


def _market_fill_payload(*, units: str = "100") -> dict[str, object]:
    return {
        "lastTransactionID": "6368",
        "orderCreateTransaction": {
            "accountID": "practice-001",
            "batchID": "6367",
            "id": "6367",
            "instrument": "EUR_USD",
            "positionFill": "DEFAULT",
            "reason": "CLIENT_ORDER",
            "time": "2026-08-08T22:30:05+00:00",
            "timeInForce": "FOK",
            "type": "MARKET_ORDER",
            "units": units,
        },
        "orderFillTransaction": {
            "accountID": "practice-001",
            "batchID": "6367",
            "id": "6368",
            "instrument": "EUR_USD",
            "orderID": "6367",
            "price": "1.13027",
            "reason": "MARKET_ORDER",
            "time": "2026-08-08T22:30:05.100000+00:00",
            "type": "ORDER_FILL",
            "units": units,
        },
        "relatedTransactionIDs": ["6367", "6368"],
    }


def _limit_pending_payload(*, units: str = "-25") -> dict[str, object]:
    return {
        "lastTransactionID": "648",
        "orderCreateTransaction": {
            "accountID": "practice-001",
            "batchID": "648",
            "id": "648",
            "instrument": "EUR_USD",
            "positionFill": "DEFAULT",
            "price": "1.10000",
            "reason": "CLIENT_ORDER",
            "time": "2026-08-08T22:30:05+00:00",
            "timeInForce": "GTC",
            "type": "LIMIT_ORDER",
            "units": units,
        },
        "relatedTransactionIDs": ["648"],
    }


def test_market_buy_plan_is_deterministic_and_secret_free() -> None:
    result = build_oanda_practice_order_create_plan(_configuration(), _submission())

    assert isinstance(result, Success)
    plan = result.value
    assert plan.endpoint_origin == "https://api-fxpractice.oanda.com"
    assert plan.path == "/v3/accounts/practice-001/orders"
    assert json.loads(plan.body_json) == {
        "order": {
            "instrument": "EUR_USD",
            "positionFill": "DEFAULT",
            "timeInForce": "FOK",
            "type": "MARKET",
            "units": "100",
        }
    }
    assert plan.signed_units == "100"
    assert plan.limit_price is None
    assert plan.logical_values() == plan.logical_values()
    assert "token" not in repr(plan.sanitized_values()).lower()
    assert "practice-001" not in repr(plan.sanitized_values())


def test_limit_sell_plan_uses_negative_units_and_explicit_price() -> None:
    result = build_oanda_practice_order_create_plan(
        _configuration(),
        _submission(
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity="25",
        ),
    )

    assert isinstance(result, Success)
    plan = result.value
    assert json.loads(plan.body_json) == {
        "order": {
            "instrument": "EUR_USD",
            "positionFill": "DEFAULT",
            "price": "1.1000",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "units": "-25",
        }
    }
    assert plan.signed_units == "-25"
    assert plan.limit_price == "1.1000"


def test_market_fill_decodes_provider_lifecycle_then_projects_accepted_receipt() -> None:
    configuration = _configuration()
    submission = _submission()
    plan_result = build_oanda_practice_order_create_plan(configuration, submission)
    assert isinstance(plan_result, Success)

    outcome_result = decode_oanda_practice_order_create_response(
        configuration,
        submission,
        plan_result.value,
        _response(_market_fill_payload(), status_code=201),
    )

    assert isinstance(outcome_result, Success)
    outcome = outcome_result.value
    assert outcome.provider_execution_ref == "6367"
    assert outcome.disposition is OandaPracticeExecutionDisposition.FILLED
    assert outcome.related_transaction_refs == ("6367", "6368")
    assert outcome.last_transaction_ref == "6368"
    assert "practice-001" not in repr(outcome.sanitized_values())

    receipt_result = build_oanda_practice_submit_gateway_receipt(outcome)
    assert isinstance(receipt_result, Success)
    assert receipt_result.value.provider_execution_ref == "6367"
    assert receipt_result.value.status is ExecutionStatus.ACCEPTED
    assert receipt_result.value.recorded_at == outcome.recorded_at


def test_limit_pending_decodes_as_accepted_pending_provider_outcome() -> None:
    configuration = _configuration()
    submission = _submission(
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        quantity="25",
    )
    plan_result = build_oanda_practice_order_create_plan(configuration, submission)
    assert isinstance(plan_result, Success)

    outcome_result = decode_oanda_practice_order_create_response(
        configuration,
        submission,
        plan_result.value,
        _response(_limit_pending_payload(), status_code=201),
    )

    assert isinstance(outcome_result, Success)
    assert outcome_result.value.disposition is OandaPracticeExecutionDisposition.PENDING
    receipt_result = build_oanda_practice_submit_gateway_receipt(outcome_result.value)
    assert isinstance(receipt_result, Success)
    assert receipt_result.value.status is ExecutionStatus.ACCEPTED


def test_immediate_cancel_is_evidence_but_not_an_accepted_gateway_submit() -> None:
    configuration = _configuration()
    submission = _submission()
    plan_result = build_oanda_practice_order_create_plan(configuration, submission)
    assert isinstance(plan_result, Success)
    payload = _market_fill_payload()
    payload.pop("orderFillTransaction")
    payload["orderCancelTransaction"] = {
        "accountID": "practice-001",
        "id": "6368",
        "orderID": "6367",
        "reason": "FILL_OR_KILL",
        "time": "2026-08-08T22:30:05.100000+00:00",
        "type": "ORDER_CANCEL",
    }

    outcome_result = decode_oanda_practice_order_create_response(
        configuration,
        submission,
        plan_result.value,
        _response(payload, status_code=201),
    )

    assert isinstance(outcome_result, Success)
    assert outcome_result.value.disposition is OandaPracticeExecutionDisposition.CANCELLED
    receipt_result = build_oanda_practice_submit_gateway_receipt(outcome_result.value)
    assert isinstance(receipt_result, Failure)
    assert isinstance(receipt_result.error, OandaPracticeExecutionNotAcceptedError)


def test_create_decoder_rejects_provider_identity_units_and_http_mismatches() -> None:
    configuration = _configuration()
    submission = _submission()
    plan_result = build_oanda_practice_order_create_plan(configuration, submission)
    assert isinstance(plan_result, Success)

    account_payload = _market_fill_payload()
    create_tx = account_payload["orderCreateTransaction"]
    assert isinstance(create_tx, dict)
    create_tx["accountID"] = "other-account"
    account_result = decode_oanda_practice_order_create_response(
        configuration,
        submission,
        plan_result.value,
        _response(account_payload, status_code=201),
    )
    units_result = decode_oanda_practice_order_create_response(
        configuration,
        submission,
        plan_result.value,
        _response(_market_fill_payload(units="200"), status_code=201),
    )
    http_result = decode_oanda_practice_order_create_response(
        configuration,
        submission,
        plan_result.value,
        _response({"errorMessage": "token=must-not-echo"}, status_code=400),
    )

    for result in (account_result, units_result, http_result):
        assert isinstance(result, Failure)
        assert isinstance(result.error, OandaPracticeExecutionCodecValidationError)
        assert "must-not-echo" not in str(result.error)
        assert "token=" not in str(result.error).lower()


def test_fill_must_match_created_order_and_last_transaction() -> None:
    configuration = _configuration()
    submission = _submission()
    plan_result = build_oanda_practice_order_create_plan(configuration, submission)
    assert isinstance(plan_result, Success)

    bad_order = _market_fill_payload()
    fill_tx = bad_order["orderFillTransaction"]
    assert isinstance(fill_tx, dict)
    fill_tx["orderID"] = "9999"
    order_result = decode_oanda_practice_order_create_response(
        configuration,
        submission,
        plan_result.value,
        _response(bad_order, status_code=201),
    )

    bad_last = _market_fill_payload()
    bad_last["lastTransactionID"] = "6367"
    last_result = decode_oanda_practice_order_create_response(
        configuration,
        submission,
        plan_result.value,
        _response(bad_last, status_code=201),
    )

    assert isinstance(order_result, Failure)
    assert isinstance(last_result, Failure)


def test_explicit_cancel_response_projects_cancelled_gateway_receipt() -> None:
    payload = {
        "lastTransactionID": "6377",
        "orderCancelTransaction": {
            "accountID": "practice-001",
            "batchID": "6377",
            "id": "6377",
            "orderID": "648",
            "reason": "CLIENT_REQUEST",
            "time": "2026-08-08T22:30:07+00:00",
            "type": "ORDER_CANCEL",
        },
        "relatedTransactionIDs": ["6377"],
    }

    result = decode_oanda_practice_order_cancel_response(
        _configuration(),
        provider_execution_ref="648",
        response=_response(payload, status_code=200),
    )

    assert isinstance(result, Success)
    assert result.value.provider_execution_ref == "648"
    assert result.value.status is ExecutionStatus.CANCELLED


def test_cancel_response_rejects_wrong_order_identity_and_reason() -> None:
    base = {
        "lastTransactionID": "6377",
        "orderCancelTransaction": {
            "accountID": "practice-001",
            "id": "6377",
            "orderID": "648",
            "reason": "CLIENT_REQUEST",
            "time": "2026-08-08T22:30:07+00:00",
            "type": "ORDER_CANCEL",
        },
        "relatedTransactionIDs": ["6377"],
    }
    wrong_order = json.loads(json.dumps(base))
    wrong_order["orderCancelTransaction"]["orderID"] = "9999"
    wrong_reason = json.loads(json.dumps(base))
    wrong_reason["orderCancelTransaction"]["reason"] = "OTHER"

    for payload in (wrong_order, wrong_reason):
        result = decode_oanda_practice_order_cancel_response(
            _configuration(),
            provider_execution_ref="648",
            response=_response(payload, status_code=200),
        )
        assert isinstance(result, Failure)
        assert isinstance(result.error, OandaPracticeExecutionCodecValidationError)
