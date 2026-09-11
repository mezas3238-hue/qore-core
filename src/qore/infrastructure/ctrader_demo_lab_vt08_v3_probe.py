"""Two-year read-only cTrader DEMO evidence for VT-08 CRT 1-5-9 V3.

V3 needs retained M15 for H4/H1/M15 nesting plus provider D1 context. Broker
symbol resolution is inherited from the explicit 11-market VT-08 V2 resolver;
no fuzzy alias inference is introduced here.
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
    _required_env,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabClosedTrendbar,
    CTraderDemoLabProbeError,
)
from qore.infrastructure.ctrader_demo_lab_vt08_v2_probe import (
    _PROVIDER_ROOTS,
    _connect_and_resolve,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)

_SCHEMA = "qore.ctrader_demo.vt08_crt_159_v3_evidence.v1"
_REQUIRED_COVERAGE_DAYS = 730
_MIN_LOOKBACK_DAYS = 730
_MAX_LOOKBACK_DAYS = 1095
_RECENT_TOLERANCE_DAYS = 10
_PRIMARY_SOURCE_SHA256 = (
    "9968f10cee6b5c94d7406c3cdc31bef2623221a5a6e6529f7b4293c1bbe97664",
    "fceacd2b59039bc94aea3b7390804c1c68f1ac10b1e7bc3e318a7645d867a5ee",
    "57206b5c3e48a2281b4648da7c69b1c20c39ea5c1edd34c689a1a9080341c225",
)
_PERIODS = (
    ("M15", 7, 900),
    ("D1", 12, 86_400),
)


def _validate_period(
    name: str,
    bars: tuple[CTraderDemoLabClosedTrendbar, ...],
    *,
    opened_at: datetime,
    checked_at: datetime,
) -> None:
    if not bars:
        raise CTraderDemoLabProbeError(
            f"VT-08 V3 {name} evidence is empty"
        )
    first = bars[0].opened_at
    last = bars[-1].closed_at
    if last - first < timedelta(days=_REQUIRED_COVERAGE_DAYS):
        raise CTraderDemoLabProbeError(
            f"VT-08 V3 {name} spans less than 730 days"
        )
    if first < opened_at:
        raise CTraderDemoLabProbeError(
            f"VT-08 V3 {name} predates requested boundary"
        )
    if last < checked_at - timedelta(days=_RECENT_TOLERANCE_DAYS):
        raise CTraderDemoLabProbeError(
            f"VT-08 V3 {name} evidence is stale"
        )


def collect_vt08_v3_evidence(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    canonical_symbol: str,
    requested_opened_at: datetime,
    checked_at: datetime,
    timeout_seconds: float = 15.0,
) -> dict[str, object]:
    if canonical_symbol not in _PROVIDER_ROOTS:
        raise CTraderDemoLabProbeError(
            "VT-08 V3 market is outside Core 11-market set"
        )
    if requested_opened_at.tzinfo is None or checked_at.tzinfo is None:
        raise CTraderDemoLabProbeError(
            "VT-08 V3 acquisition timestamps must be aware"
        )
    opened = requested_opened_at.astimezone(UTC)
    checked = checked_at.astimezone(UTC)
    if opened >= checked:
        raise CTraderDemoLabProbeError(
            "VT-08 V3 acquisition start must predate end"
        )
    (
        account_id,
        account_fingerprint,
        symbol,
        provider_symbol,
    ) = _connect_and_resolve(
        client,
        canonical_symbol=canonical_symbol,
        timeout_seconds=timeout_seconds,
    )
    period_payload: dict[str, object] = {}
    coverage: dict[str, dict[str, object]] = {}
    for period_name, native_period, seconds in _PERIODS:
        retained: dict[datetime, CTraderDemoLabClosedTrendbar] = {}
        cursor = opened
        window_index = 0
        while cursor < checked:
            window_end = min(cursor + timedelta(days=_CHUNK_DAYS), checked)
            bars = _collect_period_window(
                client,
                account_id=account_id,
                symbol=symbol,
                period_name=period_name,
                native_period=native_period,
                seconds=seconds,
                opened_at=cursor,
                checked_at=window_end,
                window_index=window_index,
                timeout_seconds=timeout_seconds,
            )
            for bar in bars:
                prior = retained.get(bar.opened_at)
                if prior is not None and prior != bar:
                    raise CTraderDemoLabProbeError(
                        "VT-08 V3 acquisition windows contradict on one bar"
                    )
                retained[bar.opened_at] = bar
            cursor = window_end
            window_index += 1
        ordered = tuple(retained[key] for key in sorted(retained))
        _validate_period(
            period_name,
            ordered,
            opened_at=opened,
            checked_at=checked,
        )
        period_payload[period_name] = [
            bar.payload() for bar in ordered
        ]
        coverage[period_name] = {
            "bar_count": len(ordered),
            "first_opened_at": ordered[0].opened_at.isoformat(
                timespec="microseconds"
            ),
            "last_closed_at": ordered[-1].closed_at.isoformat(
                timespec="microseconds"
            ),
            "span_seconds": int(
                (
                    ordered[-1].closed_at - ordered[0].opened_at
                ).total_seconds()
            ),
        }
    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "trading_permission_verified": True,
        "account_fingerprint": account_fingerprint,
        "symbol": symbol.payload(),
        "canonical_symbol": canonical_symbol,
        "provider_symbol_name": provider_symbol,
        "checked_at": checked.isoformat(timespec="microseconds"),
        "requested_opened_at": opened.isoformat(timespec="microseconds"),
        "required_coverage_days": _REQUIRED_COVERAGE_DAYS,
        "historical_chunk_days": _CHUNK_DAYS,
        "historical_page_count": _HISTORICAL_PAGE_COUNT,
        "primary_source_sha256": list(_PRIMARY_SOURCE_SHA256),
        "decision_timeframe": "M15",
        "context_timeframes": [
            "D1",
            "H4-derived-M15",
            "H1-derived-M15",
            "M15",
        ],
        "source_clock": {
            "timezone": "America/New_York",
            "h4_reference_open": "01:00",
            "h4_manipulation_open": "05:00",
            "h4_distribution_open": "09:00",
            "h1_reference_open": "09:00",
            "h1_manipulation_open": "10:00",
            "m15_reference_open": "11:00",
            "m15_manipulation_open": "11:15",
            "entry_open": "11:30",
            "distribution_expiry": "13:00",
        },
        "coverage": coverage,
        "periods": period_payload,
    }


def main() -> None:
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
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise CTraderDemoLabProbeError(
            "QORE_SOFTWARE_SHA must be exact Git SHA"
        )
    canonical_symbol = _required_env("QORE_DEMO_LAB_SYMBOL")
    lookback_days = int(
        os.environ.get("QORE_DEMO_LAB_LOOKBACK_DAYS", "760")
    )
    if not _MIN_LOOKBACK_DAYS <= lookback_days <= _MAX_LOOKBACK_DAYS:
        raise CTraderDemoLabProbeError(
            "VT-08 V3 lookback must be 730..1095 days"
        )
    checked_at = datetime.now(UTC)
    opened_at = checked_at - timedelta(days=lookback_days)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt08_v3_evidence(
            client,
            canonical_symbol=canonical_symbol,
            requested_opened_at=opened_at,
            checked_at=checked_at,
        )
        payload["requested_lookback_days"] = lookback_days
        payload["software_sha"] = software_sha
        print(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
