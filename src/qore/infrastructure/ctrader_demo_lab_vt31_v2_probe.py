"""Long-horizon read-only cTrader DEMO M1 collector for VT-31 Silver Bullet V2.

The legacy first-cohort collector intentionally keeps M1 as a short auxiliary
series because V1 does not consume M1.  VT-31 V2 is different: its source-bound
decision contract is M1, so two-year methodology research requires two-year M1
rather than an M5 proxy.

This module is additive and does not change V1 evidence semantics.  It collects
only the source-authorized ``NAS100`` market and never mutates broker state.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _CHUNK_DAYS,
    _HISTORICAL_PAGE_COUNT,
    _collect_period_window,
    _connect_and_resolve_symbol,
    _required_env,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabClosedTrendbar,
    CTraderDemoLabProbeError,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)

_SCHEMA = "qore.ctrader_demo.vt31_silver_bullet_v2_m1_evidence.v1"
_SYMBOL = "NAS100"
_NATIVE_M1_PERIOD = 1
_M1_SECONDS = 60
_MIN_LOOKBACK_DAYS = 730
_MAX_LOOKBACK_DAYS = 1095
_REQUIRED_COVERAGE_DAYS = 730
_RECENT_BOUNDARY_TOLERANCE_DAYS = 10


def _validate_m1_coverage(
    bars: tuple[CTraderDemoLabClosedTrendbar, ...],
    *,
    requested_opened_at: datetime,
    checked_at: datetime,
) -> None:
    if not bars:
        raise CTraderDemoLabProbeError("VT-31 V2 M1 evidence is empty")
    if any(item.period != "M1" for item in bars):
        raise CTraderDemoLabProbeError("VT-31 V2 evidence must contain only M1 bars")
    if bars != tuple(sorted(bars, key=lambda item: item.opened_at)):
        raise CTraderDemoLabProbeError("VT-31 V2 M1 evidence must be chronological")
    identities = tuple(item.opened_at for item in bars)
    if len(set(identities)) != len(identities):
        raise CTraderDemoLabProbeError("VT-31 V2 M1 evidence contains duplicate bars")
    first = bars[0].opened_at.astimezone(UTC)
    last = bars[-1].closed_at.astimezone(UTC)
    opened = requested_opened_at.astimezone(UTC)
    checked = checked_at.astimezone(UTC)
    if last - first < timedelta(days=_REQUIRED_COVERAGE_DAYS):
        raise CTraderDemoLabProbeError(
            "VT-31 V2 M1 evidence has less than 730 days between actual bars"
        )
    if first < opened:
        raise CTraderDemoLabProbeError(
            "VT-31 V2 M1 evidence predates the requested acquisition boundary"
        )
    if last < checked - timedelta(days=_RECENT_BOUNDARY_TOLERANCE_DAYS):
        raise CTraderDemoLabProbeError("VT-31 V2 M1 evidence is stale")
    if any(item.closed_at > checked for item in bars):
        raise CTraderDemoLabProbeError("VT-31 V2 evidence must contain only closed bars")


def _coverage_payload(
    bars: tuple[CTraderDemoLabClosedTrendbar, ...],
) -> dict[str, object]:
    gaps = [
        int((current.opened_at - previous.closed_at).total_seconds())
        for previous, current in zip(bars, bars[1:], strict=False)
        if current.opened_at > previous.closed_at
    ]
    return {
        "bar_count": len(bars),
        "first_opened_at": bars[0].opened_at.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
        "last_closed_at": bars[-1].closed_at.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
        "span_seconds": int(
            (bars[-1].closed_at - bars[0].opened_at).total_seconds()
        ),
        "observed_gap_count": len(gaps),
        "observed_gap_seconds": sum(gaps),
        "maximum_observed_gap_seconds": max(gaps, default=0),
        "gap_policy": (
            "raw provider discontinuities retained; legitimate market closures are not "
            "invented as candles"
        ),
    }


def collect_vt31_v2_m1_evidence(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    requested_opened_at: datetime,
    checked_at: datetime,
    timeout_seconds: float = 15.0,
) -> dict[str, object]:
    """Collect source-required two-year M1 evidence for NAS100 only."""

    if requested_opened_at.tzinfo is None or requested_opened_at.utcoffset() is None:
        raise CTraderDemoLabProbeError("requested_opened_at must be timezone-aware")
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise CTraderDemoLabProbeError("checked_at must be timezone-aware")
    if type(timeout_seconds) is not float or timeout_seconds <= 0:
        raise CTraderDemoLabProbeError("timeout_seconds must be a positive float")
    opened = requested_opened_at.astimezone(UTC)
    checked = checked_at.astimezone(UTC)
    if opened >= checked:
        raise CTraderDemoLabProbeError("requested_opened_at must predate checked_at")

    account_id, account_fingerprint, symbol = _connect_and_resolve_symbol(
        client,
        symbol_name=_SYMBOL,
        timeout_seconds=timeout_seconds,
    )
    retained: dict[datetime, CTraderDemoLabClosedTrendbar] = {}
    cursor = opened
    window_index = 0
    while cursor < checked:
        window_end = min(cursor + timedelta(days=_CHUNK_DAYS), checked)
        bars = _collect_period_window(
            client,
            account_id=account_id,
            symbol=symbol,
            period_name="M1",
            native_period=_NATIVE_M1_PERIOD,
            seconds=_M1_SECONDS,
            opened_at=cursor,
            checked_at=window_end,
            window_index=window_index,
            timeout_seconds=timeout_seconds,
        )
        for bar in bars:
            existing = retained.get(bar.opened_at)
            if existing is not None and existing != bar:
                raise CTraderDemoLabProbeError(
                    "VT-31 V2 M1 windows contradict on the same trendbar"
                )
            retained[bar.opened_at] = bar
        cursor = window_end
        window_index += 1

    ordered = tuple(retained[key] for key in sorted(retained))
    _validate_m1_coverage(
        ordered,
        requested_opened_at=opened,
        checked_at=checked,
    )
    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "trading_permission_verified": True,
        "account_fingerprint": account_fingerprint,
        "symbol": symbol.payload(),
        "checked_at": checked.isoformat(timespec="microseconds"),
        "requested_opened_at": opened.isoformat(timespec="microseconds"),
        "required_coverage_days": _REQUIRED_COVERAGE_DAYS,
        "historical_chunk_days": _CHUNK_DAYS,
        "historical_page_count": _HISTORICAL_PAGE_COUNT,
        "decision_timeframe": "M1",
        "source_authorized_market": _SYMBOL,
        "coverage": _coverage_payload(ordered),
        "periods": {"M1": [item.payload() for item in ordered]},
    }


def main() -> None:
    """Collect two-year NAS100 M1 DEMO evidence without printing secrets."""

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
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise CTraderDemoLabProbeError(
            "QORE_SOFTWARE_SHA must be the exact lowercase 40-character Git SHA"
        )
    configured_symbol = os.environ.get("QORE_DEMO_LAB_SYMBOL", _SYMBOL)
    if configured_symbol != _SYMBOL:
        raise CTraderDemoLabProbeError(
            "VT-31 V2 source contract authorizes only NAS100 for this research candidate"
        )
    lookback_days = int(os.environ.get("QORE_DEMO_LAB_LOOKBACK_DAYS", "760"))
    if not _MIN_LOOKBACK_DAYS <= lookback_days <= _MAX_LOOKBACK_DAYS:
        raise CTraderDemoLabProbeError(
            "VT-31 V2 lookback days must be between 730 and 1095"
        )
    checked_at = datetime.now(UTC)
    requested_opened_at = checked_at - timedelta(days=lookback_days)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt31_v2_m1_evidence(
            client,
            requested_opened_at=requested_opened_at,
            checked_at=checked_at,
        )
        payload["requested_lookback_days"] = lookback_days
        payload["software_sha"] = software_sha
        print(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
