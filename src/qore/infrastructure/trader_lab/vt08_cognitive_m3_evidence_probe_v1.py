"""Collect M3-only DEMO evidence over the exact immutable 1095D window.

The existing 1095D artifact remains the source of M15/H4 context. This collector
adds only the source-authorized M3_FRACTAL observation profile and does not run
strategy economics.
"""
from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Final

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _CHUNK_DAYS,
    _collect_period_window,
    _connect_and_resolve_symbol,
    _merge_bars,
    _required_env,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

PERIOD_NAME: Final = "M3"
NATIVE_PERIOD: Final = 3
PERIOD_SECONDS: Final = 180
MIN_SPAN_DAYS: Final = 1080


def _aware_env(name: str) -> datetime:
    raw = _required_env(name)
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def collect_m3_payload() -> dict[str, object]:
    symbol_name = _required_env("QORE_DEMO_LAB_SYMBOL")
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise ValueError("QORE_SOFTWARE_SHA must be exact lowercase Git SHA")
    opened = _aware_env("QORE_M3_REQUESTED_OPENED_AT")
    checked = _aware_env("QORE_M3_CHECKED_AT")
    if opened >= checked:
        raise ValueError("M3 requested boundary must predate checked boundary")

    credentials = CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID",
            "QORE_CTRADER_DEMO_CLIENT_ID",
        ),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET",
            "QORE_CTRADER_DEMO_CLIENT_SECRET",
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN",
            "QORE_CTRADER_DEMO_ACCESS_TOKEN",
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN",
            "QORE_CTRADER_DEMO_REFRESH_TOKEN",
        ),
        ctid_trader_account_id=int(
            _required_env(
                "QORE_CTRADER_DEMO_ACCOUNT_ID",
                "QORE_CTRADER_ACCOUNT_ID",
            )
        ),
    )

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        account_id, fingerprint, symbol = _connect_and_resolve_symbol(
            client,
            symbol_name=symbol_name,
            timeout_seconds=15.0,
        )
        retained = {}
        cursor = opened
        window_index = 0
        while cursor < checked:
            window_end = min(cursor + timedelta(days=_CHUNK_DAYS), checked)
            bars = _collect_period_window(
                client,
                account_id=account_id,
                symbol=symbol,
                period_name=PERIOD_NAME,
                native_period=NATIVE_PERIOD,
                seconds=PERIOD_SECONDS,
                opened_at=cursor,
                checked_at=window_end,
                window_index=window_index,
                timeout_seconds=15.0,
            )
            _merge_bars(retained, bars)
            cursor = window_end
            window_index += 1
    finally:
        client.close()

    ordered = tuple(sorted(retained.values(), key=lambda item: item.opened_at))
    if not ordered:
        raise ValueError("M3 collection returned no bars")
    if ordered[-1].closed_at - ordered[0].opened_at < timedelta(days=MIN_SPAN_DAYS):
        raise ValueError("M3 actual span is shorter than frozen 1095D profile contract")
    if ordered[0].opened_at < opened:
        raise ValueError("M3 evidence predates requested immutable boundary")
    if ordered[-1].closed_at < checked - timedelta(days=10):
        raise ValueError("M3 evidence is stale at recent boundary")

    return {
        "schema": "qore.trader_lab.vt08.m3_evidence.v1",
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "account_fingerprint": fingerprint,
        "symbol": {
            "symbol_name": symbol.symbol_name,
            "digits": symbol.digits,
        },
        "software_sha": software_sha,
        "requested_opened_at": opened.isoformat(),
        "checked_at": checked.isoformat(),
        "period": PERIOD_NAME,
        "native_period": NATIVE_PERIOD,
        "period_seconds": PERIOD_SECONDS,
        "bar_count": len(ordered),
        "first_opened_at": ordered[0].opened_at.isoformat(),
        "last_closed_at": ordered[-1].closed_at.isoformat(),
        "bars": [
            {
                "opened_at": item.opened_at.isoformat(),
                "closed_at": item.closed_at.isoformat(),
                "open": item.open,
                "high": item.high,
                "low": item.low,
                "close": item.close,
            }
            for item in ordered
        ],
        "strategy_replay_performed": False,
    }


def main() -> None:
    print(json.dumps(collect_m3_payload(), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
