"""Native cTrader DEMO EURUSD historical BID/ASK tick acquisition — G0 source audit.

Official Spotware ProtoOAGetTickDataReq only. Not Dukascopy, bar interpolation,
order flow or trading. No refresh token consumed: unsafe rotation fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from importlib import import_module
from pathlib import Path
from time import sleep
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.ctrader_demo_account_discovery import select_single_demo_account_id
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_NATIVE_RESET_CTRADER_DEMO_TICK_G0_V1"
SOURCE_RUN = 35166210458
SOURCE_ARTIFACT = 10475354631
QUOTE_TYPES = {"BID": 1, "ASK": 2}
LONDON = ZoneInfo("Europe/London")
START_YEAR = 2016
END_YEAR = 2026
MAX_WINDOW_MS = 604_800_000
MIN_SECONDS_BETWEEN_REQUESTS = 0.30
MAX_REQUESTS_PER_SIDE_DATE = 128


class TickSourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class NativeTick:
    timestamp_ms: int
    integer_price: int


def probe_dates() -> tuple[date, ...]:
    """First Tuesday on or after September 15, each year; fixed before results."""
    result = []
    for year in range(START_YEAR, END_YEAR + 1):
        base = date(year, 9, 15)
        result.append(base + timedelta(days=(1 - base.weekday()) % 7))
    return tuple(result)


def fixing_range_utc(day: date) -> tuple[int, int]:
    """[15:45,16:15) London as actual UTC Unix milliseconds (DST-aware)."""
    left = datetime(day.year, day.month, day.day, 15, 45, tzinfo=LONDON)
    right = datetime(day.year, day.month, day.day, 16, 15, tzinfo=LONDON)
    return int(left.timestamp() * 1000), int(right.timestamp() * 1000)


def decode_native_newest_first(
    tick_data: Any, *, from_ms: int, to_ms_inclusive: int
) -> list[NativeTick]:
    """Official cTrader response: FIRST is absolute, FOLLOWING are backward deltas."""
    decoded = []
    previous: int | None = None
    for raw in tick_data:
        timestamp = getattr(raw, "timestamp", None)
        price = getattr(raw, "tick", None)
        if type(timestamp) is not int or type(price) is not int or price <= 0:
            raise TickSourceError("invalid cTrader native historical tick")
        if previous is None:
            absolute = timestamp
        else:
            if timestamp < 0:
                raise TickSourceError("negative cTrader historical delta")
            absolute = previous - timestamp
        if not from_ms <= absolute <= to_ms_inclusive:
            raise TickSourceError("cTrader historical tick outside requested interval")
        if previous is not None and absolute > previous:
            raise TickSourceError("cTrader historical tick chronology invalid")
        decoded.append(NativeTick(absolute, price))
        previous = absolute
    return decoded


def complete_side_range(
    request: Any, *,
    from_ms: int, to_ms_inclusive: int,
    max_requests: int = MAX_REQUESTS_PER_SIDE_DATE,
) -> tuple[list[NativeTick], int]:
    """Split on hasMore so timestamps never silently disappear at a page boundary.

    Inclusive disjoint [a,m] + [m+1,b] ranges. At one-millisecond resolution,
    hasMore cannot be paginated losslessly: fail closed (not 'complete').
    """
    if from_ms < 0 or to_ms_inclusive < from_ms or (
        to_ms_inclusive - from_ms + 1 > MAX_WINDOW_MS
    ):
        raise TickSourceError("cTrader tick request outside documented maximum week")
    pending = [(from_ms, to_ms_inclusive)]
    merged: list[NativeTick] = []
    total_requests = 0
    while pending:
        begin, finish = pending.pop()
        total_requests += 1
        if total_requests > max_requests:
            raise TickSourceError("cTrader tick hasMore pagination budget exceeded")
        result = request(begin, finish)
        if type(result.get("has_more")) is not bool:
            raise TickSourceError("missing cTrader hasMore guarantee")
        native = decode_native_newest_first(
            result.get("tick_data", ()), from_ms=begin, to_ms_inclusive=finish
        )
        if result["has_more"]:
            if begin == finish:
                raise TickSourceError("nonpaginated multiple ticks at same millisecond")
            middle = begin + (finish - begin) // 2
            pending.extend([(middle + 1, finish), (begin, middle)])
            continue
        merged.extend(native)
    merged.sort(key=lambda t: (t.timestamp_ms, t.integer_price))
    return merged, total_requests


def validate_symbol_manifest(root: Path) -> int:
    path = root / "symbol-consumption-manifest.json"
    witness = root / "MANIFEST_SHA256SUMS.txt"
    if not path.is_file() or not witness.is_file():
        raise TickSourceError("source EURUSD M5 identity manifest missing")
    expected = {}
    for line in witness.read_text().splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) == 2:
            expected[fields[1].strip()] = fields[0]
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected.get(path.name) != actual_sha:
        raise TickSourceError("source manifest SHA256 not verified")
    source = json.loads(path.read_text())
    if (source.get("canonical_symbol") != "EURUSD"
            or source.get("provider_symbol") != "EURUSD"
            or source.get("retained_bars") != 745458
            or source.get("research_evidence_consumed") is not True
            or source.get("live_authorized") is not False):
        raise TickSourceError("EURUSD original cTrader DEMO identity mismatch")
    symbol_id = source.get("provider_symbol_id")
    if type(symbol_id) is not int or symbol_id <= 0:
        raise TickSourceError("original EURUSD symbol id missing")
    return symbol_id


class ReadOnlyNativeTickSession:
    """DEMО-pinned authenticated connection, no OAuth refresh and no trade requests."""

    def __init__(self, *, client_id: str, client_secret: str,
                 access_token: str, expected_account_id: str = "") -> None:
        if not all((client_id, client_secret, access_token)):
            raise TickSourceError("missing configured cTrader DEMO OAuth inputs")
        # Sentinel identity is *never* sent to cTrader. Actual explicit DEMO
        # account is bound before ProtoOAAccountAuthReq and any symbol request.
        credentials = CTraderOpenApiCredentials(
            client_id=client_id, client_secret=client_secret,
            access_token=access_token, refresh_token="DISABLED_NO_REFRESH",
            ctid_trader_account_id=1,
        )
        self.client = SpotwareCTraderOpenApiClient(
            credentials=credentials, request_timeout_seconds=18.0
        )
        sdk = import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        for name in ("ProtoOAGetTickDataReq", "ProtoOAGetTickDataRes"):
            cls = getattr(sdk, name, None)
            if not isinstance(cls, type):
                raise TickSourceError("official SDK lacks cTrader native tick proto")
            self.client._bindings.messages[name] = cls
        self.access_token = access_token
        self.expected_account_id = expected_account_id
        self.account_id = 0
        self.requests_sent = 0

    def _request(self, name: str, fields: dict[str, object], label: str) -> object:
        approved = {
            "ProtoOAApplicationAuthReq",
            "ProtoOAGetAccountListByAccessTokenReq",
            "ProtoOAAccountAuthReq",
            "ProtoOASymbolsListReq",
            "ProtoOAGetTickDataReq",
        }
        if name not in approved:
            raise TickSourceError("unapproved request type (orders forbidden)")
        result = self.client.request(
            name, fields, client_msg_id="qore-reset-tick-" + label,
            timeout_seconds=18.0,
        )
        if isinstance(result, Failure):
            raise TickSourceError("official cTrader DEMO request refused: " + name)
        return result.value

    def authenticate(self, frozen_symbol_id: int) -> None:
        from qore.infrastructure.ctrader_open_api_client import _ensure_reactor_running, _method
        sdk = self.client._bindings
        _ensure_reactor_running(sdk.reactor)
        _method(sdk.reactor, "callFromThread")(_method(self.client._client, "startService"))
        if not self.client._connected.wait(18.0) or self.client._disconnected.is_set():
            raise TickSourceError("cTrader DEMO TLS not connected")
        app = self._request("ProtoOAApplicationAuthReq", {
            "clientId": self.client._credentials.client_id,
            "clientSecret": self.client._credentials.client_secret,
        }, "app")
        if not isinstance(app, sdk.messages["ProtoOAApplicationAuthRes"]):
            raise TickSourceError("cTrader DEMO application authentication failed")
        accounts = self._request("ProtoOAGetAccountListByAccessTokenReq", {
            "accessToken": self.access_token
        }, "accounts")
        if not isinstance(accounts, sdk.messages["ProtoOAGetAccountListByAccessTokenRes"]):
            raise TickSourceError("cTrader access token invalid; refresh deliberately disabled")
        if getattr(accounts, "permissionScope", None) not in (0, 1):
            raise TickSourceError("cTrader account missing authorized view scope")
        account_id = select_single_demo_account_id(
            getattr(accounts, "ctidTraderAccount", ())
        )
        if self.expected_account_id:
            if str(account_id) != self.expected_account_id:
                raise TickSourceError("DEMO account does not match pinned configured identity")
        self.account_id = account_id
        # Bind the exact DEMO identity before account-auth/tick request.
        self.client._credentials = CTraderOpenApiCredentials(
            client_id=self.client._credentials.client_id,
            client_secret=self.client._credentials.client_secret,
            access_token=self.access_token, refresh_token="DISABLED_NO_REFRESH",
            ctid_trader_account_id=account_id,
        )
        auth = self._request("ProtoOAAccountAuthReq", {
            "ctidTraderAccountId": account_id, "accessToken": self.access_token,
        }, "account-auth")
        if not isinstance(auth, sdk.messages["ProtoOAAccountAuthRes"]):
            raise TickSourceError("official DEMO account auth failed")
        self.client._ready = True
        listed = self._request("ProtoOASymbolsListReq", {
            "ctidTraderAccountId": account_id,
        }, "symbols")
        if not isinstance(listed, sdk.messages["ProtoOASymbolsListRes"]):
            raise TickSourceError("account symbol list response invalid")
        found = [
            s for s in getattr(listed, "symbol", ())
            if getattr(s, "symbolId", None) == frozen_symbol_id
            and getattr(s, "symbolName", None) == "EURUSD"
        ]
        if len(found) != 1:
            raise TickSourceError("archived EURUSD symbol ID does not resolve on authenticated DEMO")

    def fetch(self, symbol_id: int, quote_type: int, begin: int, finish: int) -> dict[str, Any]:
        sleep(MIN_SECONDS_BETWEEN_REQUESTS)  # <= 3.34 historical req/s
        self.requests_sent += 1
        obj = self._request("ProtoOAGetTickDataReq", {
            "ctidTraderAccountId": self.account_id,
            "symbolId": symbol_id,
            "type": quote_type,
            "fromTimestamp": begin,
            "toTimestamp": finish,
        }, f"historical-{self.requests_sent}")
        if not isinstance(obj, self.client._bindings.messages["ProtoOAGetTickDataRes"]):
            raise TickSourceError("official DEMO historical tick response invalid")
        if getattr(obj, "ctidTraderAccountId", None) != self.account_id:
            raise TickSourceError("historical tick response account mismatch")
        return {"has_more": getattr(obj, "hasMore", None),
                "tick_data": getattr(obj, "tickData", ())}

    def close(self) -> None:
        self.client.close()


def collect(root: Path, out_dir: Path) -> dict[str, Any]:
    frozen_symbol_id = validate_symbol_manifest(root)
    session = ReadOnlyNativeTickSession(
        client_id=os.getenv("QORE_CTRADER_CLIENT_ID", ""),
        client_secret=os.getenv("QORE_CTRADER_CLIENT_SECRET", ""),
        access_token=os.getenv("QORE_CTRADER_ACCESS_TOKEN", ""),
        expected_account_id=os.getenv("QORE_CTRADER_DEMO_ACCOUNT_ID", ""),
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    try:
        session.authenticate(frozen_symbol_id)
        for day in probe_dates():
            from_ms, stop_ms = fixing_range_utc(day)
            by_side = {}
            for side, quote_type in QUOTE_TYPES.items():
                try:
                    ticks, req_count = complete_side_range(
                        lambda first, last: session.fetch(
                            frozen_symbol_id, quote_type, first, last),
                        from_ms=from_ms, to_ms_inclusive=stop_ms - 1,
                    )
                    target = out_dir / f"EURUSD-{day.isoformat()}-{side}-ctrader-ticks.jsonl"
                    with target.open("w", encoding="utf-8") as stream:
                        for tick in ticks:
                            stream.write(json.dumps({
                                "timestamp_ms_utc": tick.timestamp_ms,
                                "price_int_1e5": tick.integer_price,
                                "quote_side": side,
                                "source": "CTRADER_OPEN_API_DEMO",
                            }, separators=(",", ":"), sort_keys=True) + "\n")
                    by_side[side] = {
                        "status": "COMPLETE" if ticks else "ZERO_TICKS_UNVERIFIED",
                        "ticks": len(ticks), "requests": req_count,
                        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        "file": target.name,
                        "first_ms": ticks[0].timestamp_ms if ticks else None,
                        "last_ms": ticks[-1].timestamp_ms if ticks else None,
                    }
                except TickSourceError as error:
                    by_side[side] = {"status": "INCOMPLETE", "reason": str(error)}
            results.append({
                "day_london": day.isoformat(),
                "window_utc_ms": [from_ms, stop_ms],
                "by_side": by_side,
            })
    finally:
        session.close()
    complete = sum(
        all(d["by_side"].get(side, {}).get("status") == "COMPLETE"
            for side in QUOTE_TYPES) for d in results
    )
    report = {
        "identity": IDENTITY, "source": "CTRADER_OPEN_API_DEMO",
        "primary_symbol": "EURUSD", "original_cibo_source_run": SOURCE_RUN,
        "original_cibo_symbol_artifact": SOURCE_ARTIFACT,
        "frozen_symbol_id_verified": True, "demo_account_verified": True,
        "access_scope_view_or_trade": True, "oauth_refresh_performed": False,
        "g2_economic_test_performed": False, "broker_fills_claimed": False,
        "post2015_years_sampled": len(probe_dates()),
        "complete_bid_ask_dates": complete,
        "status": ("SOURCE_G0_CANDIDATE" if complete == len(probe_dates())
                   else "SOURCE_G0_PARTIAL"),
        "results": results,
    }
    (out_dir / "source-coverage-manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("original_cibo_manifest_root", type=Path)
    p.add_argument("out_dir", type=Path)
    args = p.parse_args()
    report = collect(args.original_cibo_manifest_root, args.out_dir)
    print(json.dumps({
        "status": report["status"],
        "source": report["source"], "complete_bid_ask_dates": report["complete_bid_ask_dates"],
        "post2015_years_sampled": report["post2015_years_sampled"],
        "no_oauth_refresh": True, "no_live": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
