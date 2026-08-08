from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.activation_policy import (
    ProviderActivationEvaluation,
    ProviderActivationMode,
    ProviderActivationPolicy,
    ProviderActivationSecretReferences,
    evaluate_provider_activation_policy,
)
from qore.infrastructure.adapter_configuration import (
    AdapterConfigurationMode,
    ExternalAdapterConfiguration,
)
from qore.infrastructure.adapter_lifecycle import (
    AdapterLifecycleActor,
    AdapterLifecycleState,
    AdapterLifecycleTransitionReason,
    AdapterLifecycleTransitionRequest,
    apply_adapter_lifecycle_transition,
    declare_adapter_lifecycle,
)
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.https_transport import (
    ConcreteBearerHttpsExternalTransport,
    HttpsConnectionBoundary,
    HttpsConnectionFactoryBoundary,
    HttpsResponseBoundary,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcRequest,
    QuoteRequest,
    Timeframe,
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
from qore.infrastructure.oanda_practice_credentials import (
    OandaPracticeCredentialActivation,
    activate_oanda_practice_credentials,
)
from qore.infrastructure.oanda_practice_market_feed import (
    OandaPracticeMarketDataDecoder,
    OandaPracticeMarketDataRequestFactory,
    OandaPracticeMarketFeedValidationError,
    build_oanda_practice_market_data_flow,
    compose_oanda_practice_read_only_provider,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderCapabilitySet,
    ProviderDescriptor,
    ProviderEnablement,
    ProviderId,
    ProviderName,
)
from qore.infrastructure.secret_resolution import MappingSecretMaterialResolver, SecretMaterial
from qore.infrastructure.secrets import (
    SecretExternalReference,
    SecretRef,
    SecretRefId,
)
from qore.infrastructure.transport import (
    ExternalTransportMethod,
    ExternalTransportRequest,
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 8, 11, 30, tzinfo=UTC)
_PRICE_TIME = datetime(2026, 8, 8, 11, 31, 0, 123456, tzinfo=UTC)
_PROVIDER_ID = ProviderId(UUID("d1000000-0000-0000-0000-000000000001"))
_ADAPTER_ID = AdapterId(UUID("d1000000-0000-0000-0000-000000000002"))
_SOURCE_ID = SourceId(UUID("d1000000-0000-0000-0000-000000000003"))
_CORRELATION_ID = CorrelationId(UUID("d1000000-0000-0000-0000-000000000004"))
_CAUSATION_ID = CausationId(UUID("d1000000-0000-0000-0000-000000000005"))
_SECRET_REF_ID = SecretRefId(UUID("d1000000-0000-0000-0000-000000000006"))
_SNAPSHOT_ID = MarketDataSnapshotId(UUID("d1000000-0000-0000-0000-000000000007"))
_SECRET_REFERENCE = SecretExternalReference("oanda/practice/personal-access-token")
_SECRET_BYTES = b"practice-test-token-material"


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=_CAUSATION_ID,
        attributes={"workflow": "mission-03-market-feed"},
    )


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
            rest_requests_per_second=60,
            active_streams=2,
            new_connections_per_second=1,
        ),
        secret_requirements=oanda_practice_secret_requirements(),
    )


def _provider() -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("oanda-v20"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(
            (ProviderCapability.HEALTH, ProviderCapability.MARKET_DATA_READ)
        ),
    )


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_ADAPTER_ID,
        source_id=_SOURCE_ID,
        port_name=PortName("market-data.oanda-practice"),
    )


def _secret_ref() -> SecretRef:
    configuration = _configuration()
    return SecretRef(
        ref_id=_SECRET_REF_ID,
        name=configuration.secret_requirements.requirements[0].name,
        external_reference=_SECRET_REFERENCE,
        metadata={
            "account-ref": configuration.account.account_ref,
            "environment": configuration.environment.value,
            "provider": configuration.provider_key,
        },
    )


def _activation():
    provider = _provider()
    source = _source()
    configuration = ExternalAdapterConfiguration(
        provider=provider,
        source=source,
        mode=AdapterConfigurationMode.READ_ONLY,
        secret_requirements=oanda_practice_secret_requirements(),
    )
    declared = declare_adapter_lifecycle(
        descriptor=source,
        provider=provider,
        declared_at=_BASE,
        actor=AdapterLifecycleActor("mission03.supervisor"),
        metadata=_metadata(),
    )
    assert isinstance(declared, Success)
    lifecycle = declared.value
    for offset, state, reason in (
        (
            1,
            AdapterLifecycleState.CONFIGURED,
            AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED,
        ),
        (
            2,
            AdapterLifecycleState.INITIALIZED,
            AdapterLifecycleTransitionReason.INITIALIZE_REQUESTED,
        ),
    ):
        transition = apply_adapter_lifecycle_transition(
            lifecycle,
            AdapterLifecycleTransitionRequest(
                to_state=state,
                reason=reason,
                transitioned_at=_BASE + timedelta(seconds=offset),
                actor=AdapterLifecycleActor("mission03.supervisor"),
                metadata=_metadata(),
            ),
        )
        assert isinstance(transition, Success)
        lifecycle = transition.value
    result = evaluate_provider_activation_policy(
        ProviderActivationEvaluation(
            policy=ProviderActivationPolicy(
                provider=provider,
                source=source,
                mode=ProviderActivationMode.READ_ONLY,
                required_capabilities=(ProviderCapability.MARKET_DATA_READ,),
            ),
            configuration=configuration,
            lifecycle=lifecycle,
            secrets=ProviderActivationSecretReferences((_secret_ref(),)),
            evaluated_at=_BASE + timedelta(seconds=3),
            metadata=_metadata(),
        )
    )
    assert isinstance(result, Success)
    assert result.value.can_activate is True
    return result.value


def _credential() -> OandaPracticeCredentialActivation:
    result = activate_oanda_practice_credentials(
        _configuration(),
        _secret_ref(),
        resolver=MappingSecretMaterialResolver({_SECRET_REFERENCE: _SECRET_BYTES}),
        metadata=_metadata(),
        activated_at=_BASE + timedelta(seconds=4),
    )
    assert isinstance(result, Success)
    return result.value


class FakeClock:
    def now(self) -> datetime:
        return _BASE + timedelta(seconds=10)


class FakeResponse:
    def __init__(self, payload: bytes, *, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def getheaders(self) -> list[tuple[str, str]]:
        return [
            ("Content-Type", "application/json"),
            ("RequestID", "request-001"),
            ("Set-Cookie", "must-not-surface=secret"),
        ]


class FakeConnection:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.calls: list[tuple[str, str, tuple[tuple[str, str], ...]]] = []
        self.closed = False

    def request(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str],
    ) -> None:
        self.calls.append((method, path, tuple(sorted(headers.items()))))

    def getresponse(self) -> HttpsResponseBoundary:
        return FakeResponse(self._payload)

    def close(self) -> None:
        self.closed = True


class FakeFactory:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.created: list[tuple[str, int, float]] = []

    def create(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
    ) -> HttpsConnectionBoundary:
        self.created.append((host, port, timeout_seconds))
        return self.connection


def _transport(payload: bytes) -> tuple[ConcreteBearerHttpsExternalTransport, FakeConnection]:
    connection = FakeConnection(payload)
    factory: HttpsConnectionFactoryBoundary = FakeFactory(connection)
    return (
        ConcreteBearerHttpsExternalTransport(
            connection_factory=factory,
            clock=FakeClock(),
        ),
        connection,
    )


def test_bearer_transport_injects_secret_out_of_band_only() -> None:
    transport, connection = _transport(b'{"ok":true}')
    request = ExternalTransportRequest(
        endpoint=ProviderEndpoint(host="api-fxpractice.oanda.com"),
        method=ExternalTransportMethod.GET,
        path="/v3/accounts",
        timeout=ExternalTransportTimeout(milliseconds=1000),
        headers={"accept": "application/json"},
    )

    result = transport.execute_authenticated(
        request,
        secret=SecretMaterial(_SECRET_BYTES),
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    assert connection.closed is True
    sent_headers = dict(connection.calls[0][2])
    assert sent_headers["authorization"] == f"Bearer {_SECRET_BYTES.decode()}"
    assert "authorization" not in request.headers
    assert _SECRET_BYTES.decode() not in repr(request)
    assert result.value.headers["requestid"] == "request-001"
    assert "set-cookie" not in result.value.headers


def test_bearer_transport_rejects_header_unsafe_secret_without_network() -> None:
    transport, connection = _transport(b'{"ok":true}')
    request = ExternalTransportRequest(
        endpoint=ProviderEndpoint(host="api-fxpractice.oanda.com"),
        method=ExternalTransportMethod.GET,
        path="/v3/accounts",
        timeout=ExternalTransportTimeout(milliseconds=1000),
    )

    result = transport.execute_authenticated(
        request,
        secret=SecretMaterial(b"unsafe\nvalue"),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert connection.calls == []


def test_oanda_practice_quote_flows_through_canonical_ingestion() -> None:
    payload = (
        b'{"prices":[{"instrument":"EUR_USD","time":"2026-08-08T11:31:00.123456Z",'
        b'"tradeable":true,"bids":[{"price":"1.10010","liquidity":1000},'
        b'{"price":"1.10020","liquidity":100}],"asks":['
        b'{"price":"1.10040","liquidity":1000},{"price":"1.10030","liquidity":100}]}],'
        b'"time":"2026-08-08T11:31:00.123456Z"}'
    )
    transport, connection = _transport(payload)
    provider = compose_oanda_practice_read_only_provider(
        configuration=_configuration(),
        credential=_credential(),
        activation=_activation(),
        authenticated_transport=transport,
    )
    assert isinstance(provider, Success)
    flow = build_oanda_practice_market_data_flow(
        provider=provider.value,
        configuration=_configuration(),
        resolved_at=_BASE + timedelta(seconds=5),
    )
    assert isinstance(flow, Success)

    result = flow.value.read_quote(
        QuoteRequest(Instrument("EUR_USD")),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    assert result.value.instrument.symbol == "EUR_USD"
    assert result.value.observed_at == _PRICE_TIME
    assert result.value.bid == pytest.approx(1.10020)
    assert result.value.ask == pytest.approx(1.10030)
    assert connection.calls[0][1] == "/v3/accounts/practice-001/pricing?instruments=EUR_USD"
    assert dict(connection.calls[0][2])["authorization"].startswith("Bearer ")


def test_oanda_practice_ohlc_flows_through_canonical_ingestion() -> None:
    opened_at = datetime(2026, 8, 8, 11, 15, tzinfo=UTC)
    closed_at = opened_at + timedelta(minutes=15)
    payload = (
        b'{"instrument":"EUR_USD","granularity":"M15","candles":[{'
        b'"complete":true,"time":"2026-08-08T11:15:00+00:00","volume":12,'
        b'"mid":{"o":"1.1000","h":"1.1020","l":"1.0990","c":"1.1010"}}]}'
    )
    transport, connection = _transport(payload)
    provider = compose_oanda_practice_read_only_provider(
        configuration=_configuration(),
        credential=_credential(),
        activation=_activation(),
        authenticated_transport=transport,
    )
    assert isinstance(provider, Success)
    flow = build_oanda_practice_market_data_flow(
        provider=provider.value,
        configuration=_configuration(),
        resolved_at=_BASE + timedelta(seconds=5),
    )
    assert isinstance(flow, Success)

    result = flow.value.read_ohlc(
        OhlcRequest(
            instrument=Instrument("EUR_USD"),
            timeframe=Timeframe(900),
            opened_at=opened_at,
            closed_at=closed_at,
        ),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    assert result.value.timeframe.seconds == 900
    assert result.value.open == pytest.approx(1.1000)
    assert result.value.high == pytest.approx(1.1020)
    assert result.value.low == pytest.approx(1.0990)
    assert result.value.close == pytest.approx(1.1010)
    assert connection.calls[0][1].startswith(
        "/v3/accounts/practice-001/instruments/EUR_USD/candles?"
    )
    assert "granularity=M15" in connection.calls[0][1]
    assert "price=M" in connection.calls[0][1]


def test_request_factory_rejects_instrument_not_in_configuration() -> None:
    factory = OandaPracticeMarketDataRequestFactory(_configuration())

    with pytest.raises(
        OandaPracticeMarketFeedValidationError,
        match="not allowlisted",
    ):
        factory.quote_request(QuoteRequest(Instrument("USD_JPY")))


def test_quote_decoder_fails_closed_for_non_tradeable_price() -> None:
    decoder = OandaPracticeMarketDataDecoder()
    response = ExternalTransportResponse(
        status_code=200,
        received_at=_BASE,
        payload=(
            b'{"prices":[{"instrument":"EUR_USD","time":"2026-08-08T11:31:00Z",'
            b'"tradeable":false,"bids":[{"price":"1.1"}],"asks":[{"price":"1.2"}]}]}'
        ),
    )

    result = decoder.decode_quote(
        response,
        source=_source(),
        request=QuoteRequest(Instrument("EUR_USD")),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeMarketFeedValidationError)


def test_provider_composition_requires_allowed_activation_before_io() -> None:
    allowed = _activation()
    blocked = allowed.__class__(
        policy=allowed.policy,
        configuration=allowed.configuration,
        decision=allowed.decision.BLOCKED,
        reasons=(allowed.reasons.__class__.__args__[0].POLICY_DISABLED,)
        if False
        else (),
        evaluated_at=allowed.evaluated_at,
        lifecycle=allowed.lifecycle,
        secret_references=allowed.secret_references,
        metadata=allowed.metadata,
    )
    assert blocked is not None
