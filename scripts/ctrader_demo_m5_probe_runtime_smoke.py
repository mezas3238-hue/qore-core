from __future__ import annotations

import json
import runpy
from contextlib import redirect_stdout
from datetime import UTC, datetime
from io import StringIO
from typing import Any

from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAAccountAuthReq,
    ProtoOAAccountAuthRes,
    ProtoOAApplicationAuthReq,
    ProtoOAGetAccountListByAccessTokenReq,
    ProtoOAGetAccountListByAccessTokenRes,
    ProtoOAGetTrendbarsReq,
    ProtoOAGetTrendbarsRes,
    ProtoOASymbolByIdReq,
    ProtoOASymbolByIdRes,
    ProtoOASymbolsListReq,
    ProtoOASymbolsListRes,
)
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATrendbarPeriod

_ACCOUNT_ID = 7_654_321
_SYMBOL_ID = 1_234


class _FakeDeferred:
    def addErrback(self, callback: Any) -> _FakeDeferred:
        del callback
        return self


class _FakeClient:
    def __init__(self, host: str, port: int, protocol: object) -> None:
        self.host = host
        self.port = port
        self.protocol = protocol
        self.sent: list[object] = []
        self.stopped = False

    def send(self, request: object) -> _FakeDeferred:
        self.sent.append(request)
        return _FakeDeferred()

    def stopService(self) -> None:
        self.stopped = True


def _envelope(payload: Any) -> ProtoMessage:
    return ProtoMessage(
        payloadType=payload.payloadType,
        payload=payload.SerializeToString(),
        clientMsgId="runtime-smoke",
    )


def _last_sent(client: _FakeClient, expected_type: type[Any]) -> Any:
    assert client.sent
    request = client.sent[-1]
    assert isinstance(request, expected_type), (type(request), expected_type)
    return request


def main() -> None:
    module = runpy.run_path(
        "scripts/ctrader_demo_m5_probe.py",
        run_name="ctrader_probe_runtime_smoke",
    )

    inputs_type = module["CTraderDemoOperationalProbeInputs"]
    credentials_type = module["RuntimeCredentials"]
    runner_type = module["CTraderDemoSdkProbeRunner"]
    runner_type.__init__.__globals__["Client"] = _FakeClient

    inputs = inputs_type(
        run_key="290-99",
        instrument="EURUSD",
        started_at=datetime(2026, 8, 12, 13, 7, tzinfo=UTC),
    )
    credentials = credentials_type(
        client_id="fake-client-id",
        client_secret="fake-client-secret",
        access_token="fake-access-token",
    )
    runner = runner_type(inputs=inputs, credentials=credentials)
    client = runner.client
    assert isinstance(client, _FakeClient)
    assert client.host == "demo.ctraderapi.com"
    assert client.port == 5035

    runner.connected(client)
    app_auth = _last_sent(client, ProtoOAApplicationAuthReq)
    assert app_auth.clientId == "fake-client-id"
    assert app_auth.clientSecret == "fake-client-secret"

    runner._handle_application_auth()
    account_list_request = _last_sent(client, ProtoOAGetAccountListByAccessTokenReq)
    assert account_list_request.accessToken == "fake-access-token"

    account_list_response = ProtoOAGetAccountListByAccessTokenRes()
    account_list_response.accessToken = "fake-access-token"
    account_list_response.permissionScope = 0
    account = account_list_response.ctidTraderAccount.add()
    account.ctidTraderAccountId = _ACCOUNT_ID
    account.isLive = False
    runner._handle_account_list(_envelope(account_list_response))

    account_auth = _last_sent(client, ProtoOAAccountAuthReq)
    assert account_auth.ctidTraderAccountId == _ACCOUNT_ID
    assert account_auth.accessToken == "fake-access-token"

    account_auth_response = ProtoOAAccountAuthRes()
    account_auth_response.ctidTraderAccountId = _ACCOUNT_ID
    runner._handle_account_auth(_envelope(account_auth_response))

    symbols_request = _last_sent(client, ProtoOASymbolsListReq)
    assert symbols_request.ctidTraderAccountId == _ACCOUNT_ID
    assert symbols_request.includeArchivedSymbols is False

    symbols_response = ProtoOASymbolsListRes()
    symbols_response.ctidTraderAccountId = _ACCOUNT_ID
    light_symbol = symbols_response.symbol.add()
    light_symbol.symbolId = _SYMBOL_ID
    light_symbol.symbolName = "EUR/USD"
    light_symbol.enabled = True
    runner._handle_symbol_list(_envelope(symbols_response))

    symbol_request = _last_sent(client, ProtoOASymbolByIdReq)
    assert symbol_request.ctidTraderAccountId == _ACCOUNT_ID
    assert tuple(symbol_request.symbolId) == (_SYMBOL_ID,)

    symbol_response = ProtoOASymbolByIdRes()
    symbol_response.ctidTraderAccountId = _ACCOUNT_ID
    full_symbol = symbol_response.symbol.add()
    full_symbol.symbolId = _SYMBOL_ID
    full_symbol.digits = 5
    full_symbol.pipPosition = 4
    runner._handle_full_symbol(_envelope(symbol_response))

    trendbar_request = _last_sent(client, ProtoOAGetTrendbarsReq)
    assert trendbar_request.ctidTraderAccountId == _ACCOUNT_ID
    assert trendbar_request.symbolId == _SYMBOL_ID
    assert trendbar_request.period == ProtoOATrendbarPeriod.Value("M5")
    assert trendbar_request.count == 1
    assert trendbar_request.fromTimestamp == 1_786_539_600_000
    assert trendbar_request.toTimestamp == 1_786_539_899_999

    trendbars_response = ProtoOAGetTrendbarsRes()
    trendbars_response.ctidTraderAccountId = _ACCOUNT_ID
    trendbars_response.period = ProtoOATrendbarPeriod.Value("M5")
    trendbars_response.symbolId = _SYMBOL_ID
    trendbar = trendbars_response.trendbar.add()
    trendbar.volume = 1
    trendbar.low = 110_000
    trendbar.deltaOpen = 10
    trendbar.deltaHigh = 50
    trendbar.deltaClose = 25
    trendbar.utcTimestampInMinutes = 29_775_660

    output = StringIO()
    with redirect_stdout(output):
        runner._handle_trendbars(_envelope(trendbars_response))

    assert runner.finished is True
    assert runner.exit_code == 0
    assert client.stopped is True
    evidence_text = output.getvalue().strip()
    evidence = json.loads(evidence_text)
    assert evidence["provider_key"] == "ctrader-open-api"
    assert evidence["environment"] == "demo"
    assert evidence["instrument"] == "EURUSD"
    assert evidence["symbol_id"] == _SYMBOL_ID
    assert evidence["digits"] == 5
    assert evidence["timeframe_seconds"] == 300
    assert evidence["opened_at"] == "2026-08-12T13:00:00+00:00"
    assert evidence["closed_at"] == "2026-08-12T13:05:00+00:00"
    assert evidence["open"] == 1.1001
    assert evidence["high"] == 1.1005
    assert evidence["low"] == 1.1
    assert evidence["close"] == 1.10025
    assert evidence["provider_has_more_supported"] is False
    assert evidence["provider_has_more_explicit"] is False
    assert evidence["provider_has_more"] is None
    assert str(_ACCOUNT_ID) not in evidence_text
    assert "fake-client-secret" not in evidence_text
    assert "fake-access-token" not in evidence_text


if __name__ == "__main__":
    main()
