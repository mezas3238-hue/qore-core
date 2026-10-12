"""One-shot IC Markets DEMO catalog-only probe; never refreshes OAuth tokens.

Open API read-only requests:
ProtoOAApplicationAuthReq, ProtoOAGetAccountListByAccessTokenReq,
ProtoOAAccountAuthReq, ProtoOASymbolsListReq.
No order messages, no trendbars yet, no refresh-token request.
BROKER ID must be explicitly reported by the account; cTrader DEMO
alone does NOT attest IC Markets. Only exact provider symbol names pass.
"""
from __future__ import annotations

import json
import os
from collections.abc import Iterable
from importlib import import_module
from pathlib import Path
from threading import Event

from qore.infrastructure.ctrader_open_api_client import _SdkBindings
from qore.infrastructure.ctrader_demo_account_discovery import (
    _ensure_reactor_running, _method, _set_sdk_field, _verify_tls_server_identity,
)
from qore.infrastructure.trader_lab.qore_native_universe_33_source_registry_v1 import (
    inventory,
)

IDENTITY = "QORE_NATIVE_ICMARKETS_DEMO_SOURCE_CATALOG_NO_REFRESH_V1"
HOST = "demo.ctraderapi.com"
PORT = 5035


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise ValueError("MISSING_REQUIRED_CTRADER_SECRET_INPUT")
    return value


def select_complete_credential_bundle() -> str:
    """Never mix tokens/client IDs between app grants or rotate secrets."""
    key_names = ("CLIENT_ID", "CLIENT_SECRET", "ACCESS_TOKEN", "REFRESH_TOKEN")
    for prefix in ("QORE_CTRADER_DEMO_", "QORE_CTRADER_"):
        values = {suffix: os.environ.get(prefix + suffix, "") for suffix in key_names}
        if all(values.values()):
            for suffix, value in values.items():
                os.environ["QORE_CTRADER_" + suffix] = value
            return "DEMO_ALIAS_BUNDLE" if prefix.endswith("DEMO_") else "GENERIC_BUNDLE"
    raise ValueError("NO_COMPLETE_CTRADER_OAUTH_BUNDLE")


def _ic_markets_label(value: object) -> bool:
    """Match IC Markets broker identity, not e.g. 'Not IC Markets'."""
    if not isinstance(value, str):
        return False
    normalized = "".join(ch for ch in value.casefold() if ch.isalnum())
    return normalized.startswith("icmarkets")


def classify_accounts(
    items: Iterable[object], permission: object
) -> tuple[int, str | None]:
    """Select one labelled DEMO or a single unlabelled DEMO pending broker proof.

    brokerTitleShort is OPTIONAL in cTrader Open API. A missing title is not
    proof of IC Markets. Only the later authenticated Trader brokerName check
    may promote an unlabelled account; otherwise downloads remain blocked.
    """
    if type(permission) is not int or permission not in (0, 1):
        raise ValueError("READ_ONLY_PERMISSION_UNRECOGNIZED")
    matching: list[tuple[int, str]] = []
    unknown: list[tuple[int, None]] = []
    for a in items:
        has_field = getattr(a, "HasField", None)
        try:
            explicit = (
                has_field("isLive") is True
                if callable(has_field) else hasattr(a, "isLive")
            )
        except (TypeError, ValueError):
            explicit = False
        if not explicit or getattr(a, "isLive", None) is not False:
            continue
        id_value = getattr(a, "ctidTraderAccountId", None)
        broker_title = getattr(a, "brokerTitleShort", None)
        if type(id_value) is not int or id_value <= 0:
            raise ValueError("INVALID_DEMO_ACCOUNT_ID")
        if not isinstance(broker_title, str) or not broker_title.strip():
            unknown.append((id_value, None))
        elif _ic_markets_label(broker_title):
            matching.append((id_value, broker_title.strip()))
    if len(matching) == 1:
        return matching[0]
    if not matching and len(unknown) == 1:
        return unknown[0]
    raise ValueError("REQUIRE_EXACT_ONE_ICMARKETS_DEMO_ACCOUNT")


def match_catalog(entries: Iterable[object]) -> dict[str, object]:
    owned = inventory()
    seen: dict[str, dict[str, object]] = {}
    duplicates: set[str] = set()
    requested = {str(row["symbol"]) for row in owned["rows"]}
    # SP500 is historically mapped to provider US500 in the original CIBO
    # M5 atlas. Confirm this EXACT broker symbol by provider ID, never infer it.
    requested.add("US500")
    for item in entries:
        name = getattr(item, "symbolName", None)
        if not isinstance(name, str) or name not in requested:
            continue
        symid = getattr(item, "symbolId", None)
        enabled = getattr(item, "enabled", None)
        if type(symid) is not int or symid <= 0:
            raise ValueError("BAD_PROVIDER_SYMBOL_ID")
        if name in seen:
            duplicates.add(name)
        seen[name] = {
            "broker_symbol": name,
            "symbol_id": symid,
            "enabled": enabled is True,
        }
    if duplicates:
        raise ValueError("AMBIGUOUS_BROKER_SYMBOL_ALIAS")
    return {
        "available_exact": sorted(
            name for name, item in seen.items() if item["enabled"]
        ),
        "not_listed_or_inactive": sorted(requested - {
            name for name, item in seen.items() if item["enabled"]
        }),
        "catalog_exact_matches": seen,
        "no_aliases_inferred": True,
    }


def probe_catalog() -> dict[str, object]:
    selected_bundle = select_complete_credential_bundle()
    bindings = _SdkBindings()
    required = (
        "ProtoOAApplicationAuthReq", "ProtoOAApplicationAuthRes",
        "ProtoOAGetAccountListByAccessTokenReq",
        "ProtoOAGetAccountListByAccessTokenRes",
        "ProtoOAAccountAuthReq", "ProtoOAAccountAuthRes",
        "ProtoOASymbolsListReq", "ProtoOASymbolsListRes",
    )
    # The base SDK binding is restricted. Import only documented read-only
    # TraderReq/Res into this isolated catalog probe's message dictionary.
    if "ProtoOATraderReq" not in bindings.messages:
        proto = import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        for name in ("ProtoOATraderReq", "ProtoOATraderRes"):
            message_type = getattr(proto, name, None)
            if not isinstance(message_type, type):
                raise ValueError("SDK_TRADER_BROKER_PROOF_UNAVAILABLE")
            bindings.messages[name] = message_type
    if any(k not in bindings.messages for k in required):
        raise ValueError("SDK_REQUIRED_PROTO_MISSING")
    client = bindings.client_type(
        HOST, PORT, bindings.tcp_protocol, numberOfMessagesToSendPerSecond=5,
    )
    connected = Event()
    _method(client, "setConnectedCallback")(
        lambda c: connected.set() if c is client else None
    )
    reactor = bindings.reactor

    def req(name: str, fields: dict[str, object], cid: str) -> object:
        typ = bindings.messages[name]()
        for key, value in fields.items():
            _set_sdk_field(typ, key, value)
        done = Event()
        responses: list[object] = []
        def send() -> None:
            deferred = _method(client, "send")(
                typ, clientMsgId="qore-universe33-" + cid,
                responseTimeoutInSeconds=15.0,
            )
            def ok(x: object) -> object:
                responses.append(x)
                done.set()
                return x
            def bad(x: object) -> object:
                done.set()
                return x
            _method(deferred, "addCallbacks")(ok, bad)
        _method(reactor, "callFromThread")(send)
        if not done.wait(16.0) or not responses:
            raise ValueError("READ_ONLY_REQUEST_FAILED_AT_" + cid.upper().replace("-", "_"))
        try:
            return bindings.extract(responses[0])
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("BROKER_RESPONSE_NOT_DECODABLE") from exc

    # Probe is strictly no-refresh, to protect shared token lifecycle.
    try:
        _verify_tls_server_identity(HOST, PORT, 10.0)
        _ensure_reactor_running(reactor)
        _method(reactor, "callFromThread")(_method(client, "startService"))
        if not connected.wait(12):
            raise ValueError("CTRADER_DEMO_TLS_CONNECT_FAILED")
        app = req("ProtoOAApplicationAuthReq", {
            "clientId": _env("QORE_CTRADER_CLIENT_ID"),
            "clientSecret": _env("QORE_CTRADER_CLIENT_SECRET"),
        }, "app")
        if not isinstance(app, bindings.messages["ProtoOAApplicationAuthRes"]):
            raise ValueError("CTRADER_APP_AUTH_FAILED")
        list_response = req("ProtoOAGetAccountListByAccessTokenReq", {
            "accessToken": _env("QORE_CTRADER_ACCESS_TOKEN"),
        }, "accounts")
        if not isinstance(list_response, bindings.messages["ProtoOAGetAccountListByAccessTokenRes"]):
            raise ValueError("CTRADER_ACCESS_TOKEN_INVALID_NO_REFRESH_ATTEMPTED")
        account_id, broker = classify_accounts(
            getattr(list_response, "ctidTraderAccount", ()),
            getattr(list_response, "permissionScope", None),
        )
        auth = req("ProtoOAAccountAuthReq", {
            "ctidTraderAccountId": account_id,
            "accessToken": _env("QORE_CTRADER_ACCESS_TOKEN"),
        }, "account-auth")
        if not isinstance(auth, bindings.messages["ProtoOAAccountAuthRes"]):
            raise ValueError("DEMO_ACCOUNT_AUTH_FAILED")
        if broker is None:
            trader_response = req("ProtoOATraderReq", {
                "ctidTraderAccountId": account_id,
            }, "trader-broker-proof")
            if not isinstance(trader_response, bindings.messages["ProtoOATraderRes"]):
                raise ValueError("TRADER_BROKER_PROOF_FAILED")
            trader = getattr(trader_response, "trader", None)
            name = getattr(trader, "brokerName", None)
            if not _ic_markets_label(name):
                raise ValueError("BROKER_IDENTITY_NOT_PROVEN_ICMARKETS")
            broker = name.strip()
        symbols = req("ProtoOASymbolsListReq", {
            "ctidTraderAccountId": account_id,
            "includeArchivedSymbols": False,
        }, "symbols")
        if not isinstance(symbols, bindings.messages["ProtoOASymbolsListRes"]):
            raise ValueError("DEMO_SYMBOLS_LIST_FAILED")
        catalog = match_catalog(getattr(symbols, "symbol", ()))
        return {
            "identity": IDENTITY, "status": "ICMARKETS_DEMO_CATALOG_VERIFIED",
            "_ephemeral_account_id": account_id,
            "broker_label": broker,
            "broker_identity_verified_from_account": True,
            "token_refreshed": False,
            "credential_bundle_type": selected_bundle,
            "account_is_live": False,
            "source_only": True, "live_authorized": False,
            "economic_replay_authorized": False,
            "catalog": catalog,
            # account ID is NOT written to reports: caller can obtain an
            # ephemeral context only via already-authenticated env/session.
        }
    finally:
        stop = getattr(client, "stopService", None)
        if callable(stop) and getattr(reactor, "running", None) is True:
            _method(reactor, "callFromThread")(stop)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = probe_catalog()
        report.pop("_ephemeral_account_id", None)
    except (ValueError, OSError, RuntimeError) as exc:
        # Only whitelisted static diagnostic codes are published, never raw
        # connection error text, URLs, tokens or arbitrary exception payloads.
        static_codes = {
            "NO_COMPLETE_CTRADER_OAUTH_BUNDLE",
            "READ_ONLY_PERMISSION_UNRECOGNIZED",
            "INVALID_DEMO_ACCOUNT_ID",
            "BROKER_NAME_MISSING",
            "SDK_TRADER_BROKER_PROOF_UNAVAILABLE",
            "TRADER_BROKER_PROOF_FAILED",
            "BROKER_IDENTITY_NOT_PROVEN_ICMARKETS",
            "READ_ONLY_REQUEST_FAILED_AT_TRADER_BROKER_PROOF",
            "REQUIRE_EXACT_ONE_ICMARKETS_DEMO_ACCOUNT",
            "SDK_REQUIRED_PROTO_MISSING",
            "CTRADER_DEMO_TLS_CONNECT_FAILED",
            "CTRADER_APP_AUTH_FAILED",
            "CTRADER_ACCESS_TOKEN_INVALID_NO_REFRESH_ATTEMPTED",
            "DEMO_ACCOUNT_AUTH_FAILED",
            "DEMO_SYMBOLS_LIST_FAILED",
            "AMBIGUOUS_BROKER_SYMBOL_ALIAS",
            "BAD_PROVIDER_SYMBOL_ID",
            "READ_ONLY_REQUEST_FAILED_AT_APP",
            "READ_ONLY_REQUEST_FAILED_AT_ACCOUNTS",
            "READ_ONLY_REQUEST_FAILED_AT_ACCOUNT_AUTH",
            "READ_ONLY_REQUEST_FAILED_AT_SYMBOLS",
        }
        code = str(exc) if type(exc) is ValueError else ""
        report = {
            "identity": IDENTITY, "status": "ICMARKETS_DEMO_AUTH_OR_CATALOG_BLOCKED",
            "safe_blocker": code if code in static_codes else "UNCLASSIFIED_SAFE_FAIL_CLOSED",
            "error_class": type(exc).__name__,
            "broker_identity_verified_from_account": False,
            "token_refreshed": False, "source_only": True,
            "live_authorized": False, "economic_replay_authorized": False,
            "catalog": None,
        }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("QORE_33_ICMARKETS_CATALOG_GATE", report["status"], report.get("safe_blocker", "NO_BLOCKER"))
    if report["status"] != "ICMARKETS_DEMO_CATALOG_VERIFIED":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
