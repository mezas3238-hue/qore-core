"""Read-only historical BID-tick evidence for Turtle Soup R5 Classic ambiguities."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from time import sleep
from typing import cast

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _connect_and_resolve_symbol,
    _native_int,
    _normalized_price,
    _required_env,
)
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab.turtle_soup_candidate_r5_classic_tick_targets import (
    frozen_tick_target_manifest,
)
from qore.kernel.result import Failure

_SCHEMA = "qore.trader_lab.turtle_soup_candidate_r5.classic_tick_evidence.v1"
_BID_QUOTE_TYPE = 1
_MINUTE = timedelta(minutes=1)
_HISTORICAL_REQUEST_PAUSE_SECONDS = 0.22
_SHA40 = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True, slots=True)
class TurtleSoupR5HistoricalTick:
    timestamp_ms: int
    price: str
    response_order: int

    def __post_init__(self) -> None:
        if type(self.timestamp_ms) is not int or self.timestamp_ms < 0:
            raise CTraderDemoLabProbeError("historical tick timestamp must be non-negative int")
        if type(self.response_order) is not int or self.response_order < 0:
            raise CTraderDemoLabProbeError("historical tick response_order must be non-negative int")
        try:
            value = float(self.price)
        except ValueError as exc:
            raise CTraderDemoLabProbeError("historical tick price must be numeric") from exc
        if value <= 0:
            raise CTraderDemoLabProbeError("historical tick price must be positive")

    def payload(self) -> dict[str, object]:
        return {
            "timestamp_ms": self.timestamp_ms,
            "timestamp": datetime.fromtimestamp(
                self.timestamp_ms / 1000, tz=UTC
            ).isoformat(timespec="milliseconds"),
            "price": self.price,
            "response_order": self.response_order,
        }


def _parse_time(raw: object) -> datetime:
    if not isinstance(raw, str):
        raise CTraderDemoLabProbeError("R5 target minute must be a string")
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CTraderDemoLabProbeError("R5 target minute is invalid") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise CTraderDemoLabProbeError("R5 target minute must be timezone-aware")
    value = value.astimezone(UTC)
    if value.second != 0 or value.microsecond != 0:
        raise CTraderDemoLabProbeError("R5 target must begin on an exact minute")
    return value


def _decode_tick_page(
    native_ticks: tuple[object, ...], *, digits: int
) -> tuple[TurtleSoupR5HistoricalTick, ...]:
    """Decode cTrader newest-first absolute/delta millisecond timestamps."""

    decoded: list[TurtleSoupR5HistoricalTick] = []
    previous_ms: int | None = None
    for response_order, native in enumerate(native_ticks):
        raw_timestamp = _native_int(native, "timestamp")
        raw_tick = _native_int(native, "tick")
        if response_order == 0:
            if raw_timestamp < 0:
                raise CTraderDemoLabProbeError("first historical tick timestamp is negative")
            timestamp_ms = raw_timestamp
        else:
            if previous_ms is None:  # pragma: no cover - guarded by loop state
                raise CTraderDemoLabProbeError("lost historical tick timestamp state")
            if raw_timestamp < 0:
                raise CTraderDemoLabProbeError("historical tick delta must be non-negative")
            timestamp_ms = previous_ms - raw_timestamp
            if timestamp_ms > previous_ms:
                raise CTraderDemoLabProbeError("historical tick chronology moved forward")
        decoded.append(
            TurtleSoupR5HistoricalTick(
                timestamp_ms=timestamp_ms,
                price=_normalized_price(raw_tick, digits=digits),
                response_order=response_order,
            )
        )
        previous_ms = timestamp_ms
    return tuple(decoded)


def _collect_minute_ticks(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    account_id: int,
    symbol_id: int,
    digits: int,
    opened_at: datetime,
    target_index: int,
    timeout_seconds: float,
) -> tuple[TurtleSoupR5HistoricalTick, ...]:
    start_ms = int(opened_at.timestamp() * 1000)
    end_ms = int((opened_at + _MINUTE).timestamp() * 1000) - 1
    cursor_end_ms = end_ms
    pages: list[tuple[TurtleSoupR5HistoricalTick, ...]] = []
    page_index = 0
    while cursor_end_ms >= start_ms:
        sleep(_HISTORICAL_REQUEST_PAUSE_SECONDS)
        response = client.request(
            "ProtoOAGetTickDataReq",
            {
                "ctidTraderAccountId": account_id,
                "symbolId": symbol_id,
                "type": _BID_QUOTE_TYPE,
                "fromTimestamp": start_ms,
                "toTimestamp": cursor_end_ms,
            },
            client_msg_id=(
                f"qore-turtle-soup-r5-ticks:{symbol_id}:{target_index}:{page_index}"
            ),
            timeout_seconds=timeout_seconds,
        )
        if isinstance(response, Failure):
            raise CTraderDemoLabProbeError("cTrader R5 historical tick read failed")
        native = getattr(response.value, "tickData", None)
        if native is None:
            raise CTraderDemoLabProbeError("cTrader R5 tick response missing tickData")
        page = _decode_tick_page(cast(tuple[object, ...], tuple(native)), digits=digits)
        if any(item.timestamp_ms < start_ms or item.timestamp_ms > cursor_end_ms for item in page):
            raise CTraderDemoLabProbeError("cTrader R5 tick response escaped requested minute")
        has_more = getattr(response.value, "hasMore", False)
        if type(has_more) is not bool:
            raise CTraderDemoLabProbeError("cTrader R5 tick hasMore must be bool")
        if not page:
            if has_more:
                raise CTraderDemoLabProbeError("cTrader R5 tick pagination made no progress")
            break
        pages.append(page)
        oldest_ms = min(item.timestamp_ms for item in page)
        if not has_more:
            break
        if oldest_ms <= start_ms:
            raise CTraderDemoLabProbeError(
                "cTrader R5 tick pagination cannot disambiguate boundary timestamp"
            )
        next_end = oldest_ms - 1
        if next_end >= cursor_end_ms:
            raise CTraderDemoLabProbeError("cTrader R5 tick pagination stalled")
        cursor_end_ms = next_end
        page_index += 1
        if page_index > 100:
            raise CTraderDemoLabProbeError("cTrader R5 tick pagination exceeded safe bound")

    combined: list[TurtleSoupR5HistoricalTick] = []
    global_order = 0
    for page in reversed(pages):
        # Each response page is newest-first. Reverse each page for chronological
        # storage, while retaining an explicit order marker. Equal timestamps are
        # later treated as one unresolved timestamp group by the resolver.
        for item in reversed(page):
            combined.append(
                TurtleSoupR5HistoricalTick(
                    timestamp_ms=item.timestamp_ms,
                    price=item.price,
                    response_order=global_order,
                )
            )
            global_order += 1
    if any(
        right.timestamp_ms < left.timestamp_ms
        for left, right in zip(combined, combined[1:], strict=False)
    ):
        raise CTraderDemoLabProbeError("cTrader R5 ticks are not chronological")
    return tuple(combined)


def collect_r5_classic_tick_evidence(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    symbol_name: str,
    software_sha: str,
    timeout_seconds: float = 15.0,
) -> dict[str, object]:
    if _SHA40.fullmatch(software_sha) is None:
        raise CTraderDemoLabProbeError("software_sha must be exact Git SHA")
    manifest = frozen_tick_target_manifest()
    targets = manifest["targets"]
    if not isinstance(targets, dict) or symbol_name not in targets:
        raise CTraderDemoLabProbeError("symbol is outside frozen R5 target universe")
    rows = targets[symbol_name]
    if not isinstance(rows, list) or not rows:
        raise CTraderDemoLabProbeError("R5 symbol has no frozen tick targets")

    account_id, account_fingerprint, symbol = _connect_and_resolve_symbol(
        client,
        symbol_name=symbol_name,
        timeout_seconds=timeout_seconds,
    )
    minute_payloads: list[dict[str, object]] = []
    unavailable = 0
    for target_index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CTraderDemoLabProbeError("R5 target row must be object")
        opened_at = _parse_time(row.get("minute_opened_at"))
        side = row.get("side")
        if side not in {"long", "short"}:
            raise CTraderDemoLabProbeError("R5 target side is invalid")
        ticks = _collect_minute_ticks(
            client,
            account_id=account_id,
            symbol_id=symbol.symbol_id,
            digits=symbol.digits,
            opened_at=opened_at,
            target_index=target_index,
            timeout_seconds=timeout_seconds,
        )
        if not ticks:
            unavailable += 1
        minute_payloads.append(
            {
                "minute_opened_at": opened_at.isoformat(timespec="microseconds"),
                "minute_closed_at": (opened_at + _MINUTE).isoformat(timespec="microseconds"),
                "side": side,
                "tick_count": len(ticks),
                "status": "TICK_DATA_AVAILABLE" if ticks else "TICK_DATA_UNAVAILABLE",
                "ticks": [item.payload() for item in ticks],
            }
        )

    evidence_material = json.dumps(
        minute_payloads,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return {
        "schema": _SCHEMA,
        "environment": "development-market-data",
        "read_only": True,
        "research_only": True,
        "fresh_oos_consumed": False,
        "research_identity": "turtle-soup-candidate-r5",
        "selection_reason": "resolve-only-R1-CLASSIC-M1-INTRABAR_PATH_AMBIGUOUS",
        "quote_type": "BID",
        "native_quote_type_value": _BID_QUOTE_TYPE,
        "target_manifest_digest_sha256": manifest["manifest_digest_sha256"],
        "symbol": symbol.symbol_name,
        "symbol_digits": symbol.digits,
        "account_fingerprint": account_fingerprint,
        "target_count": len(rows),
        "available_target_count": len(rows) - unavailable,
        "unavailable_target_count": unavailable,
        "software_sha": software_sha,
        "evidence_digest_sha256": sha256(evidence_material).hexdigest(),
        "minutes": minute_payloads,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--software-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env("QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET", "QORE_CTRADER_DEMO_CLIENT_SECRET"
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_DEMO_ACCESS_TOKEN"
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN", "QORE_CTRADER_DEMO_REFRESH_TOKEN"
        ),
        ctid_trader_account_id=int(
            _required_env("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID")
        ),
    )
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_r5_classic_tick_evidence(
            client,
            symbol_name=args.symbol,
            software_sha=args.software_sha,
        )
    finally:
        client.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
