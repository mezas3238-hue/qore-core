from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.oanda_practice_account_activation import (
    OandaPracticeAccountActivationValidationError,
    OandaPracticeAccountSummaryDecoder,
    OandaPracticeAccountSummaryRequestFactory,
)
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeCapability,
    OandaPracticeOperationalLimits,
    OandaPracticeRuntimeConfiguration,
    oanda_practice_secret_requirements,
)
from qore.infrastructure.transport import (
    ExternalTransportMethod,
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Failure, Success

_RECEIVED_AT = datetime(2026, 8, 8, 22, 0, tzinfo=UTC)


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


def _payload(**account_overrides: object) -> bytes:
    account: dict[str, object] = {
        "id": "practice-001",
        "currency": "USD",
        "createdTime": "2026-01-02T03:04:05+00:00",
        "hedgingEnabled": False,
        "pendingOrderCount": 0,
        "openTradeCount": 0,
        "openPositionCount": 0,
        "marginRate": "0.02",
        "lastTransactionID": "6356",
    }
    account.update(account_overrides)
    return json.dumps(
        {
            "account": account,
            "lastTransactionID": "6356",
        }
    ).encode("utf-8")


def _response(
    *,
    payload: bytes | None = None,
    status_code: int = 200,
) -> ExternalTransportResponse:
    return ExternalTransportResponse(
        status_code=status_code,
        received_at=_RECEIVED_AT,
        payload=payload if payload is not None else _payload(),
    )


def test_account_summary_request_is_read_only_and_practice_bound() -> None:
    request = OandaPracticeAccountSummaryRequestFactory(_configuration()).build()

    assert request.endpoint.host == "api-fxpractice.oanda.com"
    assert request.method is ExternalTransportMethod.GET
    assert request.path == "/v3/accounts/practice-001/summary"
    assert request.query == ()
    assert request.headers == {
        "accept": "application/json",
        "accept-datetime-format": "RFC3339",
    }
    assert "authorization" not in request.headers


def test_decoder_binds_exact_account_identity_and_sanitizes_evidence_values() -> None:
    configuration = _configuration()
    result = OandaPracticeAccountSummaryDecoder().decode(
        _response(),
        configuration=configuration,
    )

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.account == configuration.account
    assert snapshot.currency == "USD"
    assert snapshot.created_at == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert snapshot.observed_at == _RECEIVED_AT
    assert snapshot.hedging_enabled is False
    assert snapshot.pending_order_count == 0
    assert snapshot.open_trade_count == 0
    assert snapshot.open_position_count == 0
    assert snapshot.margin_rate == "0.02"
    assert snapshot.last_transaction_ref == "6356"
    assert snapshot.logical_values() == snapshot.logical_values()
    sanitized = snapshot.sanitized_values()
    assert "practice-001" not in repr(sanitized)
    assert "sha256:" in repr(sanitized)
    assert "token" not in repr(sanitized).lower()


def test_decoder_rejects_account_identity_mismatch() -> None:
    result = OandaPracticeAccountSummaryDecoder().decode(
        _response(payload=_payload(id="other-account")),
        configuration=_configuration(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeAccountActivationValidationError)
    assert "identity" in str(result.error)


def test_decoder_rejects_non_success_without_echoing_payload() -> None:
    secret_like_payload = b'{"token":"must-not-appear"}'
    result = OandaPracticeAccountSummaryDecoder().decode(
        _response(payload=secret_like_payload, status_code=401),
        configuration=_configuration(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeAccountActivationValidationError)
    assert "must-not-appear" not in str(result.error)
    assert "token" not in str(result.error).lower()


def test_decoder_requires_matching_transaction_references() -> None:
    payload = json.dumps(
        {
            "account": json.loads(_payload())["account"],
            "lastTransactionID": "7000",
        }
    ).encode("utf-8")
    result = OandaPracticeAccountSummaryDecoder().decode(
        _response(payload=payload),
        configuration=_configuration(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeAccountActivationValidationError)
    assert "transaction references" in str(result.error)


def test_decoder_uses_strict_bool_and_int_account_fields() -> None:
    bool_result = OandaPracticeAccountSummaryDecoder().decode(
        _response(payload=_payload(hedgingEnabled=1)),
        configuration=_configuration(),
    )
    int_result = OandaPracticeAccountSummaryDecoder().decode(
        _response(payload=_payload(openTradeCount=True)),
        configuration=_configuration(),
    )

    assert isinstance(bool_result, Failure)
    assert isinstance(int_result, Failure)
    assert "hedgingEnabled" in str(bool_result.error)
    assert "openTradeCount" in str(int_result.error)


def test_decoder_rejects_invalid_timestamp_currency_and_margin_rate() -> None:
    for payload in (
        _payload(createdTime="2026-01-02T03:04:05"),
        _payload(currency="usd"),
        _payload(marginRate="NaN"),
    ):
        result = OandaPracticeAccountSummaryDecoder().decode(
            _response(payload=payload),
            configuration=_configuration(),
        )
        assert isinstance(result, Failure)
        assert isinstance(result.error, OandaPracticeAccountActivationValidationError)


def test_snapshot_rejects_observation_that_predates_account_creation() -> None:
    response = ExternalTransportResponse(
        status_code=200,
        received_at=datetime(2025, 1, 1, tzinfo=UTC),
        payload=_payload(),
    )
    result = OandaPracticeAccountSummaryDecoder().decode(
        response,
        configuration=_configuration(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeAccountActivationValidationError)
    assert "must not predate" in str(result.error)


def test_request_factory_rejects_invalid_configuration_type() -> None:
    with pytest.raises(OandaPracticeAccountActivationValidationError):
        OandaPracticeAccountSummaryRequestFactory(configuration=object())  # type: ignore[arg-type]
