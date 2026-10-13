"""G5 VT31 read-only cTrader DEMO historical BID/ASK availability pilot.

NO V1 replay, no strategies, no fills, no prices persisted, no live orders.
Four tiny as-of historical windows do NOT certify continuous coverage.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Protocol

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

ONE_WEEK_MILLISECONDS = 604_800_000
SCALE = 100_000
QUOTE_TYPES = {"bid": 1, "ask": 2}
ALLOWED_READ_MESSAGES = frozenset((
    "ProtoOASymbolsListReq", "ProtoOASymbolByIdReq", "ProtoOAGetTickDataReq",
))
SAMPLES = (
    ("2023-10", datetime(2023, 10, 10, 14, 0, tzinfo=UTC)),
    ("2024-10", datetime(2024, 10, 8, 14, 0, tzinfo=UTC)),
    ("2025-10", datetime(2025, 10, 7, 14, 0, tzinfo=UTC)),
    ("2026-09", datetime(2026, 9, 15, 14, 0, tzinfo=UTC)),
)


class TickReadBoundary(Protocol):
    @property
    def is_ready(self) -> bool: ...

    @property
    def account_id(self) -> int: ...

    def connect_and_authenticate(self) -> Any: ...

    def request(
        self, message_name: str, fields: dict[str, object], *,
        client_msg_id: str, timeout_seconds: float,
    ) -> Any: ...


class PilotDataError(ValueError):
    """Invalid or inconsistent sample; fail-closed, never infer prices."""


@dataclass(frozen=True)
class ProbeWindow:
    label: str
    opened: datetime
    closed: datetime

    def __post_init__(self) -> None:
        if self.opened.tzinfo is None or self.closed.tzinfo is None:
            raise PilotDataError("UTC sample window required")
        millis = int((self.closed - self.opened).total_seconds() * 1000)
        if millis <= 0 or millis > ONE_WEEK_MILLISECONDS:
            raise PilotDataError("cTrader historical tick request is limited to one week")

    @property
    def start_ms(self) -> int:
        return int(self.opened.timestamp() * 1000)

    @property
    def end_ms(self) -> int:
        return int(self.closed.timestamp() * 1000)


def decode_response(
    response: object, *, window: ProbeWindow, account_id: int,
) -> dict[str, object]:
    """Check newest-first absolute timestamp + older relative deltas.

    Do NOT use these pilot quotes for entry, fills, tick PnL or replay.
    """
    if getattr(response, "ctidTraderAccountId", None) != account_id:
        raise PilotDataError("BROKER_ACCOUNT_MISMATCH")
    more = getattr(response, "hasMore", None)
    if type(more) is not bool:
        raise PilotDataError("MISSING_HAS_MORE_PAGINATION_WITNESS")
    data = getattr(response, "tickData", None)
    if data is None:
        raise PilotDataError("NO_TICK_DATA_FIELD")
    rows = tuple(data)
    if not rows:
        return {"count": 0, "has_more": more, "first_ms": None, "last_ms": None}
    latest: int | None = None
    earliest: int | None = None
    moment = 0
    for i, entry in enumerate(rows):
        time_field = getattr(entry, "timestamp", None)
        tick = getattr(entry, "tick", None)
        if type(time_field) is not int or type(tick) is not int or tick <= 0:
            raise PilotDataError("INVALID_TICK_PAYLOAD")
        if i == 0:
            moment = time_field
            latest = moment
        else:
            if time_field < 0:
                raise PilotDataError("NEGATIVE_TICK_DELTA")
            moment -= time_field
        if not window.start_ms <= moment <= window.end_ms:
            raise PilotDataError("TICK_OUTSIDE_REQUEST_WINDOW_OR_DELTA_INVALID")
        earliest = moment
    return {
        "count": len(rows),
        "has_more": more,
        "first_ms": earliest,
        "last_ms": latest,
    }


def read_pilot(
    client: TickReadBoundary, *, symbol_name: str, windows: tuple[ProbeWindow, ...],
) -> dict[str, object]:
    if not symbol_name or not symbol_name.isascii() or not symbol_name.isalnum():
        raise PilotDataError("EXACT_BROKER_SYMBOL_REQUIRED")
    if not windows:
        raise PilotDataError("PROBE_WINDOWS_REQUIRED")
    if not client.is_ready:
        logged_in = client.connect_and_authenticate()
        if isinstance(logged_in, Failure):
            raise PilotDataError("BROKER_DEMO_AUTH_UNAVAILABLE")
    if type(client.account_id) is not int or client.account_id <= 0:
        raise PilotDataError("BROKER_ACCOUNT_UNVERIFIED")

    def request(name: str, fields: dict[str, object], nonce: str) -> object:
        if name not in ALLOWED_READ_MESSAGES:
            raise PilotDataError("PROHIBITED_WRITE_MESSAGE")
        result = client.request(
            name, fields, client_msg_id=f"qore-vt31-g5:{nonce}",
            timeout_seconds=12.0,
        )
        if isinstance(result, Failure):
            raise PilotDataError("BROKER_READ_FAILED")
        return result.value

    listed = request(
        "ProtoOASymbolsListReq",
        {"ctidTraderAccountId": client.account_id, "includeArchivedSymbols": False},
        "symbols",
    )
    if getattr(listed, "ctidTraderAccountId", None) != client.account_id:
        raise PilotDataError("BROKER_ACCOUNT_MISMATCH")
    matches = [
        row for row in getattr(listed, "symbol", ())
        if getattr(row, "symbolName", None) == symbol_name
        and getattr(row, "enabled", None) is True
    ]
    if len(matches) != 1:
        return {
            "status": "BLOCKED_EXACT_SYMBOL_ABSENT_OR_AMBIGUOUS",
            "symbol": symbol_name,
            "read_only": True, "executions": 0,
            "g3_signature_state": "PENDING_DUAL_SIGNATURE",
            "edge_economic": "NOT_IDENTIFIED",
        }
    ident = getattr(matches[0], "symbolId", None)
    if type(ident) is not int or ident <= 0:
        raise PilotDataError("BAD_BROKER_SYMBOL_ID")
    detail_response = request(
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": client.account_id, "symbolId": [ident]},
        "exact-symbol-detail",
    )
    if getattr(detail_response, "ctidTraderAccountId", None) != client.account_id:
        raise PilotDataError("BROKER_ACCOUNT_MISMATCH")
    full = [
        row for row in getattr(detail_response, "symbol", ())
        if getattr(row, "symbolId", None) == ident
    ]
    if len(full) != 1:
        raise PilotDataError("SYMBOL_DETAILS_NOT_VERIFIABLE")
    digits = getattr(full[0], "digits", None)
    if type(digits) is not int or not 0 <= digits <= 10:
        raise PilotDataError("INVALID_BROKER_SYMBOL_DIGITS")

    samples = []
    for sample in windows:
        entry: dict[str, object] = {
            "label": sample.label,
            "from_utc": sample.opened.isoformat(),
            "to_utc": sample.closed.isoformat(),
        }
        for side, quote_type in QUOTE_TYPES.items():
            response = request(
                "ProtoOAGetTickDataReq",
                {
                    "ctidTraderAccountId": client.account_id,
                    "symbolId": ident,
                    "type": quote_type,
                    "fromTimestamp": sample.start_ms,
                    "toTimestamp": sample.end_ms,
                },
                f"{sample.label}-{side}",
            )
            entry[side] = decode_response(
                response, window=sample, account_id=client.account_id,
            )
        samples.append(entry)

    any_missing = any(
        item[side]["count"] == 0 for item in samples for side in QUOTE_TYPES
    )
    any_more = any(
        item[side]["has_more"] for item in samples for side in QUOTE_TYPES
    )
    # Even all four windows passing is NOT 3Y full-coverage proof.
    status = (
        "HISTORICAL_SAMPLE_GAPS" if any_missing else
        "SAMPLE_PAGINATION_REQUIRED" if any_more else
        "PILOT_BOTH_SIDES_PRESENT_NONCERTIFIED"
    )
    return {
        "schema": "qore.vt31.g5.ctrader.demo_tick_pilot.v1",
        "status": status, "read_only": True, "executions": 0,
        "symbol": symbol_name, "symbol_id": ident, "digits": digits,
        "demo_account_fingerprint": sha256(
            f"qore:ctrader-demo-account:v1:{client.account_id}".encode("ascii")
        ).hexdigest(),
        "pilot_15min_windows": samples,
        "three_year_coverage_verified": False,
        "broker_matches_original_m1_verified": False,
        "tick_size_contract_and_fees_verified": False,
        "ack_and_fill_history_verified": False,
        "g3_signature_state": "PENDING_DUAL_SIGNATURE",
        "edge_economic": "NOT_IDENTIFIED",
    }


def pilot_windows() -> tuple[ProbeWindow, ...]:
    return tuple(
        ProbeWindow(label, start, start + timedelta(minutes=15))
        for label, start in SAMPLES
    )


def main() -> None:
    env_names = (
        "QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_CLIENT_SECRET",
        "QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_REFRESH_TOKEN",
        "QORE_CTRADER_DEMO_ACCOUNT_ID",
    )
    missing = [name for name in env_names if not os.getenv(name)]
    symbol = os.getenv("QORE_VT31_CTRADER_SYMBOL", "NAS100")
    result: dict[str, object]
    if missing:
        result = {
            "status": "BLOCKED_DEMO_AUTH_NOT_CONFIGURED",
            "missing_environment_keys_only": missing,
            "symbol": symbol,
        }
    else:
        client: SpotwareCTraderOpenApiClient | None = None
        try:
            client = SpotwareCTraderOpenApiClient(
                credentials=CTraderOpenApiCredentials(
                    client_id=os.environ["QORE_CTRADER_CLIENT_ID"],
                    client_secret=os.environ["QORE_CTRADER_CLIENT_SECRET"],
                    access_token=os.environ["QORE_CTRADER_ACCESS_TOKEN"],
                    refresh_token=os.environ["QORE_CTRADER_REFRESH_TOKEN"],
                    ctid_trader_account_id=int(
                        os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"]
                    ),
                ),
                request_timeout_seconds=12.0,
                read_only=True,
            )
            result = read_pilot(
                client, symbol_name=symbol, windows=pilot_windows(),
            )
        except (PilotDataError, OSError, ValueError) as error:
            result = {
                "status": "BLOCKED_PROVIDER_OR_SAMPLE_INCONSISTENT",
                "error_type": type(error).__name__,
                # Never publish tokens, internal account IDs or exception messages.
            }
        finally:
            if client is not None:
                client.close()
    result.update({
        "read_only": True, "executions": 0,
        "historical_m1_ohlc_is_not_executable_quotes": True,
        "g3_signature_state": "PENDING_DUAL_SIGNATURE",
        "edge_economic": "NOT_IDENTIFIED",
        "no_v1_replay": True,
    })
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
