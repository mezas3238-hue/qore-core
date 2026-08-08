from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.activation_policy import (
    ProviderActivationDecisionSnapshot,
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
    HttpsResponseBoundary,
)
from qore.infrastructure.live_market_data import ControlledLiveMarketDataFlow
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcRequest,
    OhlcSnapshot,
    QuoteRequest,
    QuoteSnapshot,
    Timeframe,
)
from qore.infrastructure.market_data_certification_preparation import (
    MarketDataCertificationFindingCode,
    MarketDataCertificationPreparationPolicy,
    evaluate_market_data_certification_preparation,
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
from qore.infrastructure.secret_resolution import MappingSecretMaterialResolver
from qore.infrastructure.secrets import SecretExternalReference, SecretRef, SecretRefId
from qore.infrastructure.transport import ExternalTransportTimeout
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)
_PROVIDER_ID = ProviderId(UUID("e1000000-0000-0000-0000-000000000001"))
_ADAPTER_ID = AdapterId(UUID("e1000000-0000-0000-0000-000000000002"))
_SOURCE_ID = SourceId(UUID("e1000000-0000-0000-0000-000000000003"))
_CORRELATION_ID = CorrelationId(UUID("e1000000-0000-0000-0000-000000000004"))
_CAUSATION_ID = CausationId(UUID("e1000000-0000-0000-0000-000000000005"))
_SECRET_REF_ID = SecretRefId(UUID("e1000000-0000-0000-0000-000000000006"))
_SECRET_REFERENCE = SecretExternalReference("oanda/practice/personal-access-token")
_SECRET_BYTES = b"practice-dryrun-token-material"


def _snapshot_id(seed: int) -> MarketDataSnapshotId:
    return MarketDataSnapshotId(UUID(int=9000 + seed))


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=_CAUSATION_ID,
        attributes={"workflow": "mission-03-market-data-certification-dryrun"},
    )


def _configuration() -> OandaPracticeRuntimeConfiguration:
    return OandaPracticeRuntimeConfiguration(
        provider_key="oanda-v20",
        environment=MarketRuntimeEnvironment.DEMO,
        rest_endpoint=ProviderEndpoint(host="api-fxpractice.oanda.com"),
        streaming_endpoint=ProviderEndpoint(host="stream-fxpractice.oanda.com"),
        account=MarketTestAccountIdentity(
            provider_key="oanda-v20",
            account_ref="practice-dryrun-001",
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


def _activation() -> ProviderActivationDecisionSnapshot:
    provider = _provider()
    source = _source()
    adapter_configuration = ExternalAdapterConfiguration(
        provider=provider,
        source=source,
        mode=AdapterConfigurationMode.READ_ONLY,
        secret_requirements=oanda_practice_secret_requirements(),
    )
    declared = declare_adapter_lifecycle(
        descriptor=source,
        provider=provider,
        declared_at=_BASE - timedelta(seconds=10),
        actor=AdapterLifecycleActor("mission03.dryrun"),
        metadata=_metadata(),
    )
    assert isinstance(declared, Success)
    lifecycle = declared.value
    for offset, state, reason in (
        (
            9,
            AdapterLifecycleState.CONFIGURED,
            AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED,
        ),
        (
            8,
            AdapterLifecycleState.INITIALIZED,
            AdapterLifecycleTransitionReason.INITIALIZE_REQUESTED,
        ),
    ):
        transition = apply_adapter_lifecycle_transition(
            lifecycle,
            AdapterLifecycleTransitionRequest(
                to_state=state,
                reason=reason,
                transitioned_at=_BASE - timedelta(seconds=offset),
                actor=AdapterLifecycleActor("mission03.dryrun"),
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
            configuration=adapter_configuration,
            lifecycle=lifecycle,
            secrets=ProviderActivationSecretReferences((_secret_ref(),)),
            evaluated_at=_BASE - timedelta(seconds=7),
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
        activated_at=_BASE - timedelta(seconds=6),
    )
    assert isinstance(result, Success)
    return result.value


class FakeClock:
    def now(self) -> datetime:
        return _BASE - timedelta(seconds=1)


class ScriptedResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.status = 200

    def read(self) -> bytes:
        return self._payload

    def getheaders(self) -> list[tuple[str, str]]:
        return [("Content-Type", "application/json"), ("RequestID", "dryrun")]


class ScriptedConnection:
    def __init__(
        self,
        payload: bytes,
        calls: list[tuple[str, str, tuple[tuple[str, str], ...]]],
    ) -> None:
        self._payload = payload
        self._calls = calls
        self.closed = False

    def request(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str],
    ) -> None:
        self._calls.append((method, path, tuple(sorted(headers.items()))))

    def getresponse(self) -> HttpsResponseBoundary:
        return ScriptedResponse(self._payload)

    def close(self) -> None:
        self.closed = True


class ScriptedFactory:
    def __init__(self, payloads: tuple[bytes, ...]) -> None:
        self._payloads = list(payloads)
        self.calls: list[tuple[str, str, tuple[tuple[str, str], ...]]] = []
        self.created: list[tuple[str, int, float]] = []

    def create(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
    ) -> HttpsConnectionBoundary:
        if not self._payloads:
            raise AssertionError("unexpected extra HTTPS connection")
        self.created.append((host, port, timeout_seconds))
        return ScriptedConnection(self._payloads.pop(0), self.calls)

    @property
    def remaining_payloads(self) -> int:
        return len(self._payloads)


def _quote_payload(symbol: str, observed_at: datetime, bid: str, ask: str) -> bytes:
    timestamp = observed_at.isoformat().replace("+00:00", "Z")
    return (
        "{"
        '"prices":[{'
        f'"instrument":"{symbol}",'
        f'"time":"{timestamp}",'
        '"tradeable":true,'
        f'"bids":[{{"price":"{bid}","liquidity":1000}}],'
        f'"asks":[{{"price":"{ask}","liquidity":1000}}]'
        "}],"
        f'time":"{timestamp}"'
        "}"
    ).encode()


def _ohlc_payload(
    symbol: str,
    opened_at: datetime,
    *,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> bytes:
    timestamp = opened_at.isoformat()
    return (
        "{"
        f'"instrument":"{symbol}",'
        '"granularity":"M15",'
        '"candles":[{'
        '"complete":true,'
        f'"time":"{timestamp}",'
        '"volume":12,'
        '"mid":{'
        f'"o":"{open_price}",'
        f'"h":"{high}",'
        f'"l":"{low}",'
        f'"c":"{close}"'
        "}}]}"
    ).encode()


def _build_flow(
    payloads: tuple[bytes, ...],
) -> tuple[ControlledLiveMarketDataFlow, ScriptedFactory]:
    factory = ScriptedFactory(payloads)
    transport = ConcreteBearerHttpsExternalTransport(
        connection_factory=factory,
        clock=FakeClock(),
    )
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
        resolved_at=_BASE - timedelta(seconds=5),
    )
    assert isinstance(flow, Success)
    return flow.value, factory


def _read_clean_window() -> tuple[
    tuple[QuoteSnapshot, ...],
    tuple[OhlcSnapshot, ...],
    ExternalSourceDescriptor,
    ScriptedFactory,
]:
    eur_quote_time = _BASE - timedelta(seconds=2)
    gbp_quote_time = _BASE - timedelta(seconds=1)
    first_bar = _BASE - timedelta(minutes=30)
    second_bar = _BASE - timedelta(minutes=15)
    payloads = (
        _quote_payload("EUR_USD", eur_quote_time, "1.1000", "1.1002"),
        _quote_payload("GBP_USD", gbp_quote_time, "1.2700", "1.2703"),
        _ohlc_payload(
            "EUR_USD",
            first_bar,
            open_price="1.0990",
            high="1.1010",
            low="1.0980",
            close="1.1000",
        ),
        _ohlc_payload(
            "EUR_USD",
            second_bar,
            open_price="1.1000",
            high="1.1020",
            low="1.0995",
            close="1.1010",
        ),
        _ohlc_payload(
            "GBP_USD",
            first_bar,
            open_price="1.2680",
            high="1.2710",
            low="1.2670",
            close="1.2700",
        ),
        _ohlc_payload(
            "GBP_USD",
            second_bar,
            open_price="1.2700",
            high="1.2720",
            low="1.2690",
            close="1.2710",
        ),
    )
    flow, factory = _build_flow(payloads)
    quotes: list[QuoteSnapshot] = []
    for seed, symbol in ((1, "EUR_USD"), (2, "GBP_USD")):
        result = flow.read_quote(
            QuoteRequest(Instrument(symbol)),
            snapshot_id=_snapshot_id(seed),
            metadata=_metadata(),
        )
        assert isinstance(result, Success)
        quotes.append(result.value)

    ohlc: list[OhlcSnapshot] = []
    seed = 10
    for symbol in ("EUR_USD", "GBP_USD"):
        for opened_at in (first_bar, second_bar):
            result = flow.read_ohlc(
                OhlcRequest(
                    instrument=Instrument(symbol),
                    timeframe=Timeframe(900),
                    opened_at=opened_at,
                    closed_at=opened_at + timedelta(minutes=15),
                ),
                snapshot_id=_snapshot_id(seed),
                metadata=_metadata(),
            )
            assert isinstance(result, Success)
            ohlc.append(result.value)
            seed += 1
    return tuple(quotes), tuple(ohlc), flow.descriptor, factory


def test_oanda_practice_full_dryrun_reaches_prepared_canonical_window() -> None:
    quotes, ohlc, source, factory = _read_clean_window()
    policy = MarketDataCertificationPreparationPolicy(
        expected_source=source,
        required_symbols=("EUR_USD", "GBP_USD"),
        required_timeframes=(Timeframe(900),),
        max_quote_age=timedelta(seconds=5),
        maximum_ohlc_gap_intervals=0,
    )

    result = evaluate_market_data_certification_preparation(
        quotes,
        ohlc,
        policy=policy,
        evaluated_at=_BASE,
    )

    assert isinstance(result, Success)
    assert result.value.is_prepared is True
    assert result.value.findings == ()
    assert result.value.quote_count == 2
    assert result.value.ohlc_count == 4
    assert factory.remaining_payloads == 0
    assert len(factory.created) == 6
    assert all(host == "api-fxpractice.oanda.com" for host, _, _ in factory.created)
    assert all(
        dict(headers)["authorization"].startswith("Bearer ")
        for _, _, headers in factory.calls
    )
    assert _SECRET_BYTES.decode() not in repr(result.value)


def test_dryrun_surfaces_provider_origin_stale_quote_after_canonical_ingestion() -> None:
    stale_time = _BASE - timedelta(seconds=30)
    first_bar = _BASE - timedelta(minutes=30)
    second_bar = _BASE - timedelta(minutes=15)
    payloads = (
        _quote_payload("EUR_USD", stale_time, "1.1000", "1.1002"),
        _quote_payload("GBP_USD", _BASE - timedelta(seconds=1), "1.2700", "1.2703"),
        _ohlc_payload(
            "EUR_USD",
            first_bar,
            open_price="1.0990",
            high="1.1010",
            low="1.0980",
            close="1.1000",
        ),
        _ohlc_payload(
            "EUR_USD",
            second_bar,
            open_price="1.1000",
            high="1.1020",
            low="1.0995",
            close="1.1010",
        ),
        _ohlc_payload(
            "GBP_USD",
            first_bar,
            open_price="1.2680",
            high="1.2710",
            low="1.2670",
            close="1.2700",
        ),
        _ohlc_payload(
            "GBP_USD",
            second_bar,
            open_price="1.2700",
            high="1.2720",
            low="1.2690",
            close="1.2710",
        ),
    )
    flow, factory = _build_flow(payloads)
    eur_quote = flow.read_quote(
        QuoteRequest(Instrument("EUR_USD")),
        snapshot_id=_snapshot_id(30),
        metadata=_metadata(),
    )
    gbp_quote = flow.read_quote(
        QuoteRequest(Instrument("GBP_USD")),
        snapshot_id=_snapshot_id(31),
        metadata=_metadata(),
    )
    assert isinstance(eur_quote, Success)
    assert isinstance(gbp_quote, Success)
    quotes = (eur_quote.value, gbp_quote.value)

    ohlc: list[OhlcSnapshot] = []
    seed = 40
    for symbol in ("EUR_USD", "GBP_USD"):
        for opened_at in (first_bar, second_bar):
            result = flow.read_ohlc(
                OhlcRequest(
                    instrument=Instrument(symbol),
                    timeframe=Timeframe(900),
                    opened_at=opened_at,
                    closed_at=opened_at + timedelta(minutes=15),
                ),
                snapshot_id=_snapshot_id(seed),
                metadata=_metadata(),
            )
            assert isinstance(result, Success)
            ohlc.append(result.value)
            seed += 1
    policy = MarketDataCertificationPreparationPolicy(
        expected_source=flow.descriptor,
        required_symbols=("EUR_USD", "GBP_USD"),
        required_timeframes=(Timeframe(900),),
        max_quote_age=timedelta(seconds=5),
    )

    result = evaluate_market_data_certification_preparation(
        quotes,
        tuple(ohlc),
        policy=policy,
        evaluated_at=_BASE,
    )

    assert isinstance(result, Success)
    assert result.value.is_prepared is False
    assert tuple(item.code for item in result.value.findings) == (
        MarketDataCertificationFindingCode.QUOTE_STALE,
    )
    assert result.value.findings[0].instrument == "EUR_USD"
    assert factory.remaining_payloads == 0


def test_malformed_oanda_wire_fails_before_certification_window_exists() -> None:
    flow, factory = _build_flow((b'{"prices":"not-an-array"}',))

    result = flow.read_quote(
        QuoteRequest(Instrument("EUR_USD")),
        snapshot_id=_snapshot_id(70),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert factory.remaining_payloads == 0
    assert "prices must be an array" in str(result.error)
    assert _SECRET_BYTES.decode() not in str(result.error)
