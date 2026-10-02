from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

from qore.infrastructure import ctrader_historical_tick_data as tick_data
from qore.infrastructure.ctrader_historical_tick_collector import (
    CTraderHistoricalReadOnlyMessageClient,
    CTraderHistoricalSensorIdentity,
    CTraderHistoricalTickCollector,
    resolve_ctrader_historical_sensor_identity,
    split_historical_request_windows,
)
from qore.infrastructure.ctrader_open_api_client import CTraderOpenApiProtocolError
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.kernel.result import Failure, Success

_BASE = datetime(2017, 1, 1, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("79000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("79000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo-historical"),
)


@dataclass(frozen=True)
class NativeTick:
    timestamp: int
    tick: int


class FakeReader:
    def __init__(self) -> None:
        self.requests: list[tick_data.CTraderHistoricalTickRequest] = []

    def read_page(
        self,
        *,
        request: tick_data.CTraderHistoricalTickRequest,
        digits: int,
        client_msg_id: str,
    ):
        del client_msg_id
        self.requests.append(request)
        newest = request.to_at - timedelta(milliseconds=10)
        page = tick_data.decode_historical_tick_page(
            request=request,
            native_ticks=(
                NativeTick(int(newest.timestamp() * 1_000), 2_012_410_000),
            ),
            has_more=False,
            digits=digits,
        )
        return Success(page)


class FakeClient:
    def __init__(self) -> None:
        self.is_ready = True
        self.account_id = 123
        self.requests: list[str] = []

    def connect_and_authenticate(self):
        return Success(None)

    def request(
        self,
        message_name: str,
        fields,
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ):
        del fields, client_msg_id, timeout_seconds
        self.requests.append(message_name)
        if message_name == "ProtoOASymbolsListReq":
            return Success(
                SimpleNamespace(
                    ctidTraderAccountId=123,
                    symbol=[
                        SimpleNamespace(
                            symbolId=456,
                            symbolName="USTEC",
                            enabled=True,
                        )
                    ],
                )
            )
        if message_name == "ProtoOASymbolByIdReq":
            return Success(
                SimpleNamespace(
                    ctidTraderAccountId=123,
                    symbol=[SimpleNamespace(symbolId=456, digits=2)],
                )
            )
        raise AssertionError(message_name)

    def wait_for_event(self, *args, **kwargs):
        raise AssertionError("historical identity resolution must not subscribe")

    def close(self) -> None:
        return None


def test_windows_are_bounded_and_do_not_overlap() -> None:
    windows = split_historical_request_windows(
        from_at=_BASE,
        to_at=_BASE + timedelta(days=15),
    )

    assert len(windows) == 3
    assert all(
        window.to_at - window.from_at <= timedelta(days=7)
        for window in windows
    )
    assert windows[1].from_at == windows[0].to_at + timedelta(milliseconds=1)
    assert windows[2].from_at == windows[1].to_at + timedelta(milliseconds=1)


def test_symbol_identity_is_resolved_from_authenticated_provider() -> None:
    client = FakeClient()
    result = resolve_ctrader_historical_sensor_identity(
        client=client,
        provider_symbol="USTEC",
        timeout_seconds=10.0,
    )

    assert isinstance(result, Success)
    assert result.value == CTraderHistoricalSensorIdentity(
        account_id=123,
        symbol_id=456,
        provider_symbol="USTEC",
        digits=2,
    )
    assert client.requests == [
        "ProtoOASymbolsListReq",
        "ProtoOASymbolByIdReq",
    ]


def test_collector_reads_bid_and_ask_as_independent_streams() -> None:
    reader = FakeReader()
    sleeps: list[float] = []
    clock_values = iter(
        _BASE + timedelta(days=100, seconds=index)
        for index in range(20)
    )
    collector = CTraderHistoricalTickCollector(
        reader=reader,
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        provider_symbol="USTEC",
        clock=lambda: next(clock_values),
        sleeper=sleeps.append,
        request_interval_seconds=0.2,
    )
    identity = CTraderHistoricalSensorIdentity(
        account_id=123,
        symbol_id=456,
        provider_symbol="USTEC",
        digits=2,
    )

    result = collector.collect(
        identity=identity,
        from_at=_BASE,
        to_at=_BASE + timedelta(days=8),
    )

    assert isinstance(result, Success)
    assert result.value.coverage.bid_count == 2
    assert result.value.coverage.ask_count == 2
    assert result.value.coverage.bid_page_count == 2
    assert result.value.coverage.ask_page_count == 2
    assert len(result.value.coverage.digest_sha256) == 64
    assert {item.quote_side.value for item in result.value.bid} == {"bid"}
    assert {item.quote_side.value for item in result.value.ask} == {"ask"}
    assert [request.quote_type for request in reader.requests] == [
        tick_data.CTraderQuoteType.BID,
        tick_data.CTraderQuoteType.BID,
        tick_data.CTraderQuoteType.ASK,
        tick_data.CTraderQuoteType.ASK,
    ]
    assert sleeps == [0.2, 0.2]


def test_collection_digest_is_deterministic_for_same_evidence() -> None:
    identity = CTraderHistoricalSensorIdentity(
        account_id=123,
        symbol_id=456,
        provider_symbol="USTEC",
        digits=2,
    )

    def collect_once():
        reader = FakeReader()
        collector = CTraderHistoricalTickCollector(
            reader=reader,
            instrument=Instrument("NAS100"),
            source=_SOURCE,
            provider_symbol="USTEC",
            clock=lambda: _BASE + timedelta(days=100),
            sleeper=lambda _: None,
            request_interval_seconds=0.2,
        )
        return collector.collect(
            identity=identity,
            from_at=_BASE,
            to_at=_BASE + timedelta(days=1),
        )

    first = collect_once()
    second = collect_once()

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.coverage.digest_sha256 == second.value.coverage.digest_sha256



class FirewallClient(FakeClient):
    def request(
        self,
        message_name: str,
        fields,
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ):
        if message_name in {"ProtoOASymbolsListReq", "ProtoOASymbolByIdReq"}:
            return super().request(
                message_name,
                fields,
                client_msg_id=client_msg_id,
                timeout_seconds=timeout_seconds,
            )
        return Success(SimpleNamespace())


def test_read_only_message_firewall_rejects_order_requests() -> None:
    firewall = CTraderHistoricalReadOnlyMessageClient(FirewallClient())

    result = firewall.request(
        "ProtoOANewOrderReq",
        {"ctidTraderAccountId": 123},
        client_msg_id="must-fail",
        timeout_seconds=10.0,
    )

    from qore.kernel.result import Failure

    assert isinstance(result, Failure)
    assert "non-read-only" in str(result.error)


def test_read_only_message_firewall_allows_historical_tick_request() -> None:
    firewall = CTraderHistoricalReadOnlyMessageClient(FirewallClient())

    result = firewall.request(
        "ProtoOAGetTickDataReq",
        {
            "ctidTraderAccountId": 123,
            "symbolId": 456,
            "type": 1,
            "fromTimestamp": 1,
            "toTimestamp": 2,
        },
        client_msg_id="read-only",
        timeout_seconds=10.0,
    )

    assert isinstance(result, Success)


class FailingFirewallClient(FirewallClient):
    def request(
        self,
        message_name: str,
        fields,
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ):
        if message_name == "ProtoOAGetTickDataReq":
            return Failure(
                CTraderOpenApiProtocolError(
                    "cTrader request rejected: HISTORICAL_DATA_NOT_AVAILABLE"
                )
            )
        return super().request(
            message_name,
            fields,
            client_msg_id=client_msg_id,
            timeout_seconds=timeout_seconds,
        )


def test_read_only_firewall_preserves_sanitized_provider_rejection() -> None:
    firewall = CTraderHistoricalReadOnlyMessageClient(FailingFirewallClient())

    result = firewall.request(
        "ProtoOAGetTickDataReq",
        {
            "ctidTraderAccountId": 123,
            "symbolId": 456,
            "type": 1,
            "fromTimestamp": 1,
            "toTimestamp": 2,
        },
        client_msg_id="diagnostic",
        timeout_seconds=10.0,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderOpenApiProtocolError)
    assert "HISTORICAL_DATA_NOT_AVAILABLE" in str(result.error)
