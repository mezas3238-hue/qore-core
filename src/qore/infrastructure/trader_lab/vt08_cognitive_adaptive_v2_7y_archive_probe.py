"""Strict seven-year raw archives for CADJPY/NZDUSD Adaptive V2 validation.

Collection only. No strategy replay or economics are inspected in this module.
"""
from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Final, cast

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _coverage_payload,
    _required_env,
    collect_long_horizon_market_evidence,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

ARCHIVE_MARKETS: Final = ("CADJPY", "NZDUSD")
ARCHIVE_LOOKBACK_DAYS: Final = 2555
MIN_ARCHIVE_SPAN_DAYS: Final = 2545
START_TOLERANCE_DAYS: Final = 5
RECENT_TOLERANCE_DAYS: Final = 5
REQUIRED_PERIODS: Final = ("M5", "M15", "H4")


def _timestamp(value: object, *, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be timestamp text")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def validate_seven_year_coverage(
    payload: dict[str, object],
    *,
    symbol_name: str,
    requested_opened_at: datetime,
    checked_at: datetime,
) -> None:
    if symbol_name not in ARCHIVE_MARKETS:
        raise ValueError("adaptive V2 archive market outside frozen scope")
    if payload.get("environment") != "demo":
        raise ValueError("adaptive V2 archive must be DEMO")
    if payload.get("read_only") is not True:
        raise ValueError("adaptive V2 archive must be read-only")
    if payload.get("account_is_live") is not False:
        raise ValueError("adaptive V2 archive cannot use LIVE account")
    symbol = cast(dict[str, object], payload["symbol"])
    if symbol.get("symbol_name") != symbol_name:
        raise ValueError("adaptive V2 archive symbol mismatch")

    coverage = cast(dict[str, dict[str, object]], payload["coverage"])
    for period in REQUIRED_PERIODS:
        item = coverage.get(period)
        if item is None:
            raise ValueError(f"adaptive V2 archive missing {period}")
        first = _timestamp(item["first_opened_at"], name=f"{period}.first")
        last = _timestamp(item["last_closed_at"], name=f"{period}.last")
        if first > requested_opened_at + timedelta(days=START_TOLERANCE_DAYS):
            raise ValueError(f"{period} does not reach seven-year start")
        if last < checked_at - timedelta(days=RECENT_TOLERANCE_DAYS):
            raise ValueError(f"{period} is stale")
        if last - first < timedelta(days=MIN_ARCHIVE_SPAN_DAYS):
            raise ValueError(f"{period} span is shorter than seven-year contract")


def collect_seven_year_payload() -> dict[str, object]:
    symbol_name = _required_env("QORE_DEMO_LAB_SYMBOL")
    if symbol_name not in ARCHIVE_MARKETS:
        raise ValueError("adaptive V2 seven-year collector market outside scope")
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise ValueError("QORE_SOFTWARE_SHA must be exact lowercase Git SHA")

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
    checked_at = datetime.now(UTC)
    requested_opened_at = checked_at - timedelta(days=ARCHIVE_LOOKBACK_DAYS)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        evidence = collect_long_horizon_market_evidence(
            client,
            symbol_name=symbol_name,
            requested_opened_at=requested_opened_at,
            checked_at=checked_at,
        )
    finally:
        client.close()

    payload = evidence.sanitized_payload()
    payload["requested_lookback_days"] = ARCHIVE_LOOKBACK_DAYS
    payload["requested_opened_at"] = requested_opened_at.isoformat(
        timespec="microseconds"
    )
    payload["software_sha"] = software_sha
    payload["coverage"] = _coverage_payload(evidence.bars)
    payload["sealed_raw_archive"] = True
    payload["strategy_replay_performed"] = False
    payload["intended_future_use"] = "ADAPTIVE_PROTECTION_V2_FRESH_SCREEN"
    validate_seven_year_coverage(
        payload,
        symbol_name=symbol_name,
        requested_opened_at=requested_opened_at,
        checked_at=checked_at,
    )
    return payload


def main() -> None:
    print(
        json.dumps(
            collect_seven_year_payload(),
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
