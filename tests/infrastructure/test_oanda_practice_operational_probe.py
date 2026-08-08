from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.infrastructure.oanda_practice_operational_probe import (
    FixedOperationalProbeClock,
    OandaPracticeOperationalEvidence,
    OandaPracticeOperationalProbeInputs,
    OandaPracticeOperationalProbeValidationError,
    run_oanda_practice_quote_probe,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.secret_resolution import SecretMaterial
from qore.infrastructure.transport import (
    ExternalTransportError,
    ExternalTransportRequest,
    ExternalTransportResponse,
)
from qore.kernel.result import Result, Success

_STARTED_AT = datetime(2026, 8, 8, 11, 45, tzinfo=UTC)
_PRICE_AT = datetime(2026, 8, 8, 11, 45, 1, 123456, tzinfo=UTC)
_ACCOUNT_REF = "101-001-1234567-001"
_TOKEN = b"practice-operational-test-token"
_PRICE_PAYLOAD = b"""{
  "prices": [
    {
      "instrument": "EUR_USD",
      "time": "2026-08-08T11:45:01.123456+00:00",
      "tradeable": true,
      "bids": [{"price": "1.16321", "liquidity": 1000000}],
      "asks": [{"price": "1.16329", "liquidity": 1000000}]
    }
  ]
}"""


def _inputs(
    *,
    run_key: str = "31255470322-1",
    account_ref: str = _ACCOUNT_REF,
    instrument: str = "EUR_USD",
    token: bytes = _TOKEN,
    started_at: datetime = _STARTED_AT,
) -> OandaPracticeOperationalProbeInputs:
    return OandaPracticeOperationalProbeInputs(
        run_key=run_key,
        account_ref=account_ref,
        instrument=instrument,
        token_material=token,
        started_at=started_at,
    )


class FakeAuthenticatedTransport:
    def __init__(self) -> None:
        self.requests: list[ExternalTransportRequest] = []
        self.secret_reprs: list[str] = []

    def execute_authenticated(
        self,
        request: ExternalTransportRequest,
        *,
        secret: SecretMaterial,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExternalTransportError]:
        self.requests.append(request)
        self.secret_reprs.append(repr(secret))
        assert isinstance(metadata, ExternalRequestMetadata)
        return Success(
            ExternalTransportResponse(
                status_code=200,
                received_at=_STARTED_AT,
                payload=_PRICE_PAYLOAD,
                headers={
                    "content-type": "application/json",
                    "requestid": "practice-request-001",
                },
            )
        )


def test_operational_probe_traverses_practice_path_and_returns_sanitized_evidence() -> None:
    transport = FakeAuthenticatedTransport()

    result = run_oanda_practice_quote_probe(
        _inputs(),
        authenticated_transport=transport,
    )

    assert isinstance(result, Success)
    evidence = result.value
    assert evidence.provider_key == "oanda-v20"
    assert evidence.environment == "demo"
    assert evidence.endpoint_host == "api-fxpractice.oanda.com"
    assert evidence.instrument == "EUR_USD"
    assert evidence.observed_at == _PRICE_AT
    assert evidence.bid == 1.16321
    assert evidence.ask == 1.16329
    assert evidence.account_fingerprint.startswith("sha256:")
    assert _ACCOUNT_REF not in evidence.to_json()
    assert _TOKEN.decode() not in evidence.to_json()

    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.endpoint.host == "api-fxpractice.oanda.com"
    assert request.path == f"/v3/accounts/{_ACCOUNT_REF}/pricing"
    assert request.query == (("instruments", "EUR_USD"),)
    assert "authorization" not in request.headers
    assert transport.secret_reprs == ["SecretMaterial(<redacted>)"]


def test_operational_probe_inputs_redact_token_and_account_from_repr() -> None:
    inputs = _inputs()

    rendered = repr(inputs)

    assert _TOKEN.decode() not in rendered
    assert _ACCOUNT_REF not in rendered
    assert "token_material=<redacted>" in rendered
    assert "account_ref_fingerprint='sha256:" in rendered


def test_operational_probe_rejects_non_allowlisted_instrument() -> None:
    with pytest.raises(
        OandaPracticeOperationalProbeValidationError,
        match="approved OANDA Practice symbol",
    ):
        _inputs(instrument="USD_JPY")


def test_operational_probe_rejects_noncanonical_run_key_and_naive_time() -> None:
    with pytest.raises(
        OandaPracticeOperationalProbeValidationError,
        match="run_key",
    ):
        _inputs(run_key="manual")

    with pytest.raises(
        OandaPracticeOperationalProbeValidationError,
        match="timezone-aware",
    ):
        _inputs(started_at=datetime(2026, 8, 8, 11, 45))


def test_operational_evidence_rejects_production_endpoint() -> None:
    with pytest.raises(
        OandaPracticeOperationalProbeValidationError,
        match="endpoint must be OANDA Practice",
    ):
        OandaPracticeOperationalEvidence(
            run_key="31255470322-1",
            provider_key="oanda-v20",
            environment="demo",
            endpoint_host="api-fxtrade.oanda.com",
            account_fingerprint="sha256:deadbeefdeadbeefdeadbeef",
            instrument="EUR_USD",
            snapshot_id=UUID("d2000000-0000-0000-0000-000000000001"),
            observed_at=_PRICE_AT,
            bid=1.1,
            ask=1.2,
        )


def test_fixed_operational_probe_clock_is_explicit() -> None:
    clock = FixedOperationalProbeClock(_STARTED_AT)

    assert clock.now() == _STARTED_AT
