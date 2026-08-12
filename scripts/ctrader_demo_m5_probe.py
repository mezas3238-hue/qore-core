from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ctrader_open_api import Client, EndPoints, Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoHeartbeatEvent
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAAccountAuthReq,
    ProtoOAAccountAuthRes,
    ProtoOAApplicationAuthReq,
    ProtoOAApplicationAuthRes,
    ProtoOAErrorRes,
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
from twisted.internet import reactor

from qore.infrastructure.ctrader_demo_market_data import CTraderTrendbar
from qore.infrastructure.ctrader_demo_operational_probe import (
    CTraderClientPermissionScope,
    CTraderDemoOperationalObservation,
    CTraderDemoOperationalProbeInputs,
    CTraderFullSymbolObservation,
    CTraderGrantedAccount,
    CTraderLightSymbolObservation,
    CTraderTrendbarsResponseObservation,
    closed_m5_interval,
    normalize_ctrader_symbol_name,
    run_ctrader_demo_closed_m5_probe,
    unix_milliseconds,
)
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure

_RUNTIME_TIMEOUT_SECONDS = 30
_TRENDBAR_REQUIRED_FIELDS = (
    "low",
    "deltaOpen",
    "deltaClose",
    "deltaHigh",
    "utcTimestampInMinutes",
)


@dataclass(frozen=True, slots=True, repr=False)
class RuntimeCredentials:
    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)
    access_token: str = field(repr=False)

    def __post_init__(self) -> None:
        for value in (self.client_id, self.client_secret, self.access_token):
            if not isinstance(value, str) or not value:
                raise ValueError("cTrader runtime credentials must be non-empty strings")

    def __repr__(self) -> str:
        return (
            "RuntimeCredentials("
            "client_id=<redacted>, client_secret=<redacted>, access_token=<redacted>)"
        )


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value:
        raise ValueError(f"required cTrader operational environment binding is missing: {name}")
    return value


def _load_inputs() -> tuple[CTraderDemoOperationalProbeInputs, RuntimeCredentials]:
    client_id = _required_environment("QORE_CTRADER_CLIENT_ID")
    client_secret = _required_environment("QORE_CTRADER_CLIENT_SECRET")
    access_token = _required_environment("QORE_CTRADER_ACCESS_TOKEN")
    instrument = _required_environment("QORE_CTRADER_INSTRUMENT")
    run_key = _required_environment("QORE_PROBE_RUN_KEY")
    started_raw = _required_environment("QORE_PROBE_STARTED_AT")

    for secret_name in (
        "QORE_CTRADER_CLIENT_SECRET",
        "QORE_CTRADER_ACCESS_TOKEN",
    ):
        os.environ.pop(secret_name, None)

    try:
        started_at = datetime.fromisoformat(started_raw)
    except ValueError as error:
        raise ValueError("QORE_PROBE_STARTED_AT must be ISO-8601") from error

    inputs = CTraderDemoOperationalProbeInputs(
        run_key=run_key,
        instrument=instrument,
        started_at=started_at,
    )
    credentials = RuntimeCredentials(
        client_id=client_id,
        client_secret=client_secret,
        access_token=access_token,
    )
    return inputs, credentials


def _wire_failure(code: str) -> str:
    return json.dumps(
        {
            "environment": "demo",
            "provider_key": "ctrader-open-api",
            "status": "failure",
            "error_code": code,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class CTraderDemoSdkProbeRunner:
    """Own the outer SDK/Twisted lifecycle for one explicitly invoked Demo probe."""

    def __init__(
        self,
        *,
        inputs: CTraderDemoOperationalProbeInputs,
        credentials: RuntimeCredentials,
    ) -> None:
        self.inputs = inputs
        self.credentials = credentials
        self.client = Client(
            EndPoints.PROTOBUF_DEMO_HOST,
            EndPoints.PROTOBUF_PORT,
            TcpProtocol,
        )
        self.account_id: int | None = None
        self.granted_accounts: tuple[CTraderGrantedAccount, ...] = ()
        self.permission_scope: CTraderClientPermissionScope | None = None
        self.permission_scope_explicit = False
        self.light_symbols: tuple[CTraderLightSymbolObservation, ...] = ()
        self.symbol_id: int | None = None
        self.full_symbol: CTraderFullSymbolObservation | None = None
        self.finished = False
        self.exit_code = 0

    def _finish(self) -> None:
        if self.finished:
            return
        self.finished = True
        try:
            self.client.stopService()
        finally:
            if reactor.running:
                reactor.stop()

    def _fail(self, code: str) -> None:
        if self.finished:
            return
        self.exit_code = 1
        print(_wire_failure(code))
        self._finish()

    def _send(self, request: Any) -> None:
        try:
            deferred = self.client.send(request)
        except Exception:
            self._fail("provider-send-failure")
            return
        deferred.addErrback(lambda _: self._fail("provider-send-failure"))

    def connected(self, client: Client) -> None:
        if client is not self.client:
            self._fail("unexpected-client-instance")
            return
        request = ProtoOAApplicationAuthReq()
        request.clientId = self.credentials.client_id
        request.clientSecret = self.credentials.client_secret
        self._send(request)

    def disconnected(self, client: Client, reason: Any) -> None:
        del reason
        if client is not self.client:
            return
        if not self.finished:
            self._fail("provider-disconnected")

    def _handle_application_auth(self) -> None:
        request = ProtoOAGetAccountListByAccessTokenReq()
        request.accessToken = self.credentials.access_token
        self._send(request)

    def _handle_account_list(self, message: Any) -> None:
        response = Protobuf.extract(message)
        self.permission_scope_explicit = response.HasField("permissionScope")
        if not self.permission_scope_explicit:
            self._fail("permission-scope-missing")
            return
        try:
            self.permission_scope = CTraderClientPermissionScope(
                int(response.permissionScope)
            )
        except ValueError:
            self._fail("permission-scope-unknown")
            return
        if self.permission_scope is not CTraderClientPermissionScope.VIEW:
            self._fail("permission-scope-not-view")
            return

        accounts = tuple(
            CTraderGrantedAccount(
                account_id=int(item.ctidTraderAccountId),
                is_live=bool(item.isLive),
                is_live_explicit=item.HasField("isLive"),
            )
            for item in response.ctidTraderAccount
        )
        self.granted_accounts = accounts
        if len(accounts) != 1:
            self._fail("granted-account-count-invalid")
            return
        account = accounts[0]
        if not account.is_live_explicit:
            self._fail("account-environment-missing")
            return
        if account.is_live:
            self._fail("live-account-refused")
            return

        self.account_id = account.account_id
        request = ProtoOAAccountAuthReq()
        request.ctidTraderAccountId = account.account_id
        request.accessToken = self.credentials.access_token
        self._send(request)

    def _handle_account_auth(self, message: Any) -> None:
        response = Protobuf.extract(message)
        if self.account_id is None or int(response.ctidTraderAccountId) != self.account_id:
            self._fail("account-auth-binding-mismatch")
            return
        request = ProtoOASymbolsListReq()
        request.ctidTraderAccountId = self.account_id
        request.includeArchivedSymbols = False
        self._send(request)

    def _handle_symbol_list(self, message: Any) -> None:
        response = Protobuf.extract(message)
        if self.account_id is None or int(response.ctidTraderAccountId) != self.account_id:
            self._fail("symbol-list-account-mismatch")
            return

        symbols = tuple(
            CTraderLightSymbolObservation(
                symbol_id=int(item.symbolId),
                symbol_name=str(item.symbolName),
                enabled=bool(item.enabled),
                symbol_name_explicit=item.HasField("symbolName"),
                enabled_explicit=item.HasField("enabled"),
            )
            for item in response.symbol
        )
        self.light_symbols = symbols
        matching = tuple(
            item
            for item in symbols
            if item.symbol_name_explicit
            and normalize_ctrader_symbol_name(item.symbol_name) == self.inputs.instrument
        )
        if len(matching) != 1:
            self._fail("symbol-selection-ambiguous")
            return
        selected = matching[0]
        if not selected.enabled_explicit or not selected.enabled:
            self._fail("symbol-not-enabled")
            return

        self.symbol_id = selected.symbol_id
        request = ProtoOASymbolByIdReq()
        request.ctidTraderAccountId = self.account_id
        request.symbolId.append(self.symbol_id)
        self._send(request)

    def _handle_full_symbol(self, message: Any) -> None:
        response = Protobuf.extract(message)
        if self.account_id is None or int(response.ctidTraderAccountId) != self.account_id:
            self._fail("full-symbol-account-mismatch")
            return
        if self.symbol_id is None or len(response.symbol) != 1:
            self._fail("full-symbol-count-invalid")
            return
        symbol = response.symbol[0]
        if int(symbol.symbolId) != self.symbol_id:
            self._fail("full-symbol-id-mismatch")
            return

        self.full_symbol = CTraderFullSymbolObservation(
            symbol_id=int(symbol.symbolId),
            digits=int(symbol.digits),
        )
        opened_at, closed_at = closed_m5_interval(self.inputs.started_at)
        request = ProtoOAGetTrendbarsReq()
        request.ctidTraderAccountId = self.account_id
        request.symbolId = self.symbol_id
        request.period = ProtoOATrendbarPeriod.Value("M5")
        request.fromTimestamp = unix_milliseconds(opened_at)
        request.toTimestamp = unix_milliseconds(closed_at)
        request.count = 1
        self._send(request)

    def _handle_trendbars(self, message: Any) -> None:
        response = Protobuf.extract(message)
        if (
            self.account_id is None
            or self.symbol_id is None
            or self.permission_scope is None
            or self.full_symbol is None
        ):
            self._fail("runtime-state-incomplete")
            return
        if not response.HasField("symbolId"):
            self._fail("trendbar-symbol-id-missing")
            return
        fields_explicit = all(
            all(item.HasField(field_name) for field_name in _TRENDBAR_REQUIRED_FIELDS)
            for item in response.trendbar
        )
        if not fields_explicit and len(response.trendbar) > 0:
            self._fail("trendbar-required-field-missing")
            return
        try:
            trendbars = tuple(
                CTraderTrendbar(
                    low_relative=int(item.low),
                    delta_open=int(item.deltaOpen),
                    delta_high=int(item.deltaHigh),
                    delta_close=int(item.deltaClose),
                    utc_timestamp_in_minutes=int(item.utcTimestampInMinutes),
                )
                for item in response.trendbar
            )
        except (ExternalPortError, TypeError, ValueError):
            self._fail("trendbar-structure-invalid")
            return

        observation = CTraderDemoOperationalObservation(
            permission_scope=self.permission_scope,
            permission_scope_explicit=self.permission_scope_explicit,
            granted_accounts=self.granted_accounts,
            authorized_account_id=self.account_id,
            light_symbols=self.light_symbols,
            full_symbol=self.full_symbol,
            trendbars_response=CTraderTrendbarsResponseObservation(
                account_id=int(response.ctidTraderAccountId),
                symbol_id=int(response.symbolId),
                symbol_id_explicit=response.HasField("symbolId"),
                period_code=int(response.period),
                trendbars=trendbars,
                trendbar_fields_explicit=fields_explicit,
                has_more=bool(response.hasMore),
            ),
        )
        result = run_ctrader_demo_closed_m5_probe(self.inputs, observation)
        if isinstance(result, Failure):
            self._fail(type(result.error).__name__)
            return
        print(result.value.to_json())
        self._finish()

    def on_message_received(self, client: Client, message: Any) -> None:
        if client is not self.client or self.finished:
            return
        try:
            payload_type = message.payloadType
            if payload_type == ProtoHeartbeatEvent().payloadType:
                return
            if payload_type == ProtoOAErrorRes().payloadType:
                self._fail("provider-error-response")
                return
            if payload_type == ProtoOAApplicationAuthRes().payloadType:
                self._handle_application_auth()
                return
            if payload_type == ProtoOAGetAccountListByAccessTokenRes().payloadType:
                self._handle_account_list(message)
                return
            if payload_type == ProtoOAAccountAuthRes().payloadType:
                self._handle_account_auth(message)
                return
            if payload_type == ProtoOASymbolsListRes().payloadType:
                self._handle_symbol_list(message)
                return
            if payload_type == ProtoOASymbolByIdRes().payloadType:
                self._handle_full_symbol(message)
                return
            if payload_type == ProtoOAGetTrendbarsRes().payloadType:
                self._handle_trendbars(message)
        except Exception:
            self._fail("provider-message-processing-failure")

    def run(self) -> int:
        self.client.setConnectedCallback(self.connected)
        self.client.setDisconnectedCallback(self.disconnected)
        self.client.setMessageReceivedCallback(self.on_message_received)
        self.client.startService()
        reactor.callLater(
            _RUNTIME_TIMEOUT_SECONDS,
            lambda: self._fail("runtime-timeout"),
        )
        reactor.run()
        return self.exit_code


def main() -> int:
    try:
        inputs, credentials = _load_inputs()
        runner = CTraderDemoSdkProbeRunner(
            inputs=inputs,
            credentials=credentials,
        )
        return runner.run()
    except Exception:
        print(_wire_failure("runtime-initialization-failure"))
        return 1


if __name__ == "__main__":
    sys.exit(main())
