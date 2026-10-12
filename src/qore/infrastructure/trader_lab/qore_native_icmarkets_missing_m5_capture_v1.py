"""Missing-only IC Markets cTrader DEMO native M5 capture with broker proof.

After credential validity AND explicit brokerTitleShort IC Markets, checks
exact symbolId in DEMO catalog then invokes QORE's audited 7-day M5
windowed collector. A symbol with historical M5 already held 10Y is
rejected to prevent re-downloading or changing immutable corpora.
No token refresh and no trading functionality. Broker identity must be
proven anew on each independent worker.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiConnectionError,
    CTraderOpenApiProtocolError,
    SpotwareCTraderOpenApiClient,
    _ensure_reactor_running,
    _method,
)
from qore.infrastructure.trader_lab import cibo_market_atlas_10y_m5_consumer_v1 as base
from qore.infrastructure.trader_lab import cibo_market_atlas_10y_windowed_runtime_v1 as windowed
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import (
    probe_catalog,
)
from qore.infrastructure.trader_lab.qore_native_universe_33_source_registry_v1 import (
    M5_10Y, universe,
)
from qore.kernel.result import Failure, Success

IDENTITY = "QORE_NATIVE_ICMARKETS_DEMO_UNIVERSE33_M5_10Y_NEW_CAPTURE_V1"
PARENT_IDENTITY = "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1"
SCHEMA = "qore.native.icmarkets_demo_universe33_m5_10y.v1"
CAPTURE_START = "2016-09-17T00:00:00+00:00"
CAPTURE_END = "2026-09-17T00:00:00+00:00"


class _ReadOnlyIcMarketsHistoryClient(SpotwareCTraderOpenApiClient):
    """History-only DEMO adapter accepting SCOPE_VIEW=0 without SDK changes."""

    def _refresh_tokens(self):
        return Failure(CTraderOpenApiProtocolError(
            "REAUTH_REQUIRED_NO_TOKEN_REFRESH_PERMITTED"
        ))

    def connect_and_authenticate(self):
        if self.is_ready:
            return Success(None)
        self._disconnected.clear()
        try:
            _ensure_reactor_running(self._bindings.reactor)
            _method(self._bindings.reactor, "callFromThread")(
                _method(self._client, "startService")
            )
        except (CTraderOpenApiProtocolError, CTraderOpenApiConnectionError) as exc:
            return Failure(exc)
        if not self._connected.wait(self._request_timeout_seconds):
            return Failure(CTraderOpenApiConnectionError(
                "IC Markets DEMO historical TLS connection timeout"
            ))
        app = self._authenticate_request("ProtoOAApplicationAuthReq", {
            "clientId": self._credentials.client_id,
            "clientSecret": self._credentials.client_secret,
        }, "icmarkets-history-app")
        if isinstance(app, Failure):
            return app
        if not isinstance(
            app.value, self._bindings.messages["ProtoOAApplicationAuthRes"]
        ):
            return Failure(CTraderOpenApiProtocolError("unexpected app auth"))

        accounts = self._authenticate_request(
            "ProtoOAGetAccountListByAccessTokenReq",
            {"accessToken": self._access_token},
            "icmarkets-history-account-list",
        )
        if isinstance(accounts, Failure):
            return accounts  # Never refresh/rotate GitHub Actions secrets.
        if not isinstance(
            accounts.value,
            self._bindings.messages["ProtoOAGetAccountListByAccessTokenRes"],
        ):
            return Failure(CTraderOpenApiProtocolError(
                "unexpected account-list message"
            ))
        scope = getattr(accounts.value, "permissionScope", None)
        if type(scope) is not int or scope not in (0, 1):
            return Failure(CTraderOpenApiProtocolError(
                "historical source requires explicit VIEW or TRADE scope"
            ))
        entries = getattr(accounts.value, "ctidTraderAccount", None)
        if entries is None:
            return Failure(CTraderOpenApiProtocolError(
                "historical account evidence absent"
            ))
        matching = [
            a for a in entries
            if getattr(a, "ctidTraderAccountId", None)
            == self._credentials.ctid_trader_account_id
        ]
        if len(matching) != 1:
            return Failure(CTraderOpenApiProtocolError(
                "exact source broker account mismatch"
            ))
        account = matching[0]
        present = getattr(account, "HasField", None)
        try:
            live_explicit = (
                present("isLive") is True
                if callable(present) else hasattr(account, "isLive")
            )
        except (TypeError, ValueError):
            live_explicit = False
        if not live_explicit or getattr(account, "isLive", None) is not False:
            return Failure(CTraderOpenApiProtocolError(
                "source account is LIVE or unclassified"
            ))
        auth = self._authenticate_request("ProtoOAAccountAuthReq", {
            "ctidTraderAccountId": self._credentials.ctid_trader_account_id,
            "accessToken": self._access_token,
        }, "icmarkets-history-account-auth")
        if isinstance(auth, Failure):
            return auth
        if not isinstance(
            auth.value, self._bindings.messages["ProtoOAAccountAuthRes"]
        ) or getattr(auth.value, "ctidTraderAccountId", None) != (
            self._credentials.ctid_trader_account_id
        ):
            return Failure(CTraderOpenApiProtocolError(
                "exact account authorization response mismatch"
            ))
        self._ready = True
        return Success(None)


def require_capture_candidate(symbol: str, enabled_exact: set[str]) -> None:
    if symbol not in universe():
        raise ValueError("UNIVERSE33_OUT_OF_SCOPE")
    if symbol in M5_10Y:
        raise ValueError("EXISTING_10Y_M5_NO_REDUNDANT_DOWNLOAD")
    if symbol not in enabled_exact:
        raise ValueError("BROKER_SYMBOL_NOT_EXACT_ENABLED_MATCH")


def activate_capture(symbol: str, account_id: int) -> None:
    if type(account_id) is not int or account_id <= 0:
        raise ValueError("NO_VERIFIED_DEMO_ACCOUNT")
    if base.TARGET_START.isoformat() != CAPTURE_START:
        raise ValueError("HISTORIC_START_CHANGED")
    if base.TARGET_END_EXCLUSIVE.isoformat() != CAPTURE_END:
        raise ValueError("HISTORIC_END_CHANGED")
    if base.CHUNK_DAYS != 7 or base.PERIOD_M5 != 5:
        raise ValueError("TRANSPORT_CONTRACT_CHANGED")
    # The already authenticated exact DEMO broker account is forced into
    # the existing read-only collector for this process, never persisted.
    os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"] = str(account_id)
    os.environ.pop("QORE_CTRADER_ACCOUNT_ID", None)
    base.PROVIDER_SYMBOL_MAP = {symbol: symbol}
    base.TARGET_SYMBOLS = (symbol,)
    base.IDENTITY = IDENTITY
    base.PARENT_IDENTITY = PARENT_IDENTITY
    base.SCHEMA = SCHEMA
    base.RAW_SCHEMA = SCHEMA + ".raw"
    base.QUALITY_SCHEMA = SCHEMA + ".quality"
    windowed.install_windowed_transport()

    # Bind an isolated read-only adapter for THIS research Atlas reader only.
    # Shared production client remains unchanged.
    base.SpotwareCTraderOpenApiClient = _ReadOnlyIcMarketsHistoryClient


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: <symbol> <output>")
    symbol, target = sys.argv[1], Path(sys.argv[2])
    if symbol not in universe() or symbol in M5_10Y:
        raise SystemExit("OUT_OF_SCOPE_OR_ALREADY_ARCHIVED")
    report = probe_catalog()
    if report["status"] != "ICMARKETS_DEMO_CATALOG_VERIFIED":
        raise SystemExit("ICMARKETS_SOURCE_AUTH_UNVERIFIED")
    catalog = report["catalog"]
    require_capture_candidate(
        symbol, set(catalog["available_exact"])
    )
    # Strong check: exact symbol ID and positive enabled; no inferred aliases.
    row = catalog["catalog_exact_matches"][symbol]
    if row["broker_symbol"] != symbol or type(row["symbol_id"]) is not int:
        raise SystemExit("UNVERIFIED_PROVIDER_SYMBOL_ID")
    account_id = report["_ephemeral_account_id"]
    activate_capture(symbol, account_id)
    sys.argv = [sys.argv[0], symbol, str(target)]
    base.main()


if __name__ == "__main__":
    main()
