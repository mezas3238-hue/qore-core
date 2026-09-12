"""Long-horizon read-only cTrader DEMO M1 collector for VT-31 Silver Bullet V2.

The legacy first-cohort collector intentionally keeps M1 as a short auxiliary
series because V1 does not consume M1. VT-31 V2 is different: its source-bound
decision contract is M1, so two-year methodology research requires two-year M1
rather than an M5 proxy.

This module is additive and does not change V1 evidence semantics. It collects
only the source-authorized canonical ``NAS100`` market and never mutates broker
state. Provider symbol aliases are resolved through an explicit, narrow
NASDAQ-100 allowlist; fuzzy name inference is prohibited.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import cast

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _HISTORICAL_PAGE_COUNT,
    _collect_period_window,
    _native_int,
    _required_env,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabClosedTrendbar,
    CTraderDemoLabProbeError,
    CTraderDemoLabSymbolEvidence,
    compute_ctrader_demo_lab_account_fingerprint,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_SCHEMA = "qore.ctrader_demo.vt31_silver_bullet_v2_m1_evidence.v1"
_SYMBOL = "NAS100"
_NATIVE_M1_PERIOD = 1
_M1_SECONDS = 60
_MIN_LOOKBACK_DAYS = 730
_MAX_LOOKBACK_DAYS = 1095
_REQUIRED_COVERAGE_DAYS = 730
_RECENT_BOUNDARY_TOLERANCE_DAYS = 10
# M1 must use a smaller acquisition window than the shared M5 collector. Three
# calendar days contain at most 4,320 one-minute bars, which stays below the
# provider's 5,000-bar response ceiling even if every minute traded.
_M1_CHUNK_DAYS = 3

# Explicit provider aliases for the same canonical NASDAQ-100 market. A suffix
# is accepted only when separated from one of these exact roots (for example
# ``USTEC.cash``). This is intentionally not a fuzzy contains/substring map.
_NAS100_PROVIDER_ROOTS: tuple[str, ...] = (
    "NAS100",
    "US100",
    "USTEC",
    "USTECH",
    "NASDAQ100",
)
_PROVIDER_SUFFIX_SEPARATORS = frozenset({".", "_", "-", "/"})


def _provider_root(value: str) -> str | None:
    if type(value) is not str or not value:
        return None
    upper = value.upper()
    for root in _NAS100_PROVIDER_ROOTS:
        if upper == root:
            return root
        if upper.startswith(root) and len(upper) > len(root):
            separator = upper[len(root)]
            if separator in _PROVIDER_SUFFIX_SEPARATORS:
                suffix = upper[len(root) + 1 :]
                if suffix and re.fullmatch(r"[A-Z0-9]+", suffix) is not None:
                    return root
    return None


def _select_nas100_provider_symbol_name(
    symbols: tuple[tuple[str, bool], ...],
) -> str:
    """Select exactly one enabled provider alias for canonical NAS100."""

    if type(symbols) is not tuple or any(
        type(item) is not tuple
        or len(item) != 2
        or type(item[0]) is not str
        or type(item[1]) is not bool
        for item in symbols
    ):
        raise CTraderDemoLabProbeError(
            "provider symbol observations must be immutable (name, enabled) pairs"
        )
    matches = tuple(
        name
        for name, enabled in symbols
        if enabled and _provider_root(name) is not None
    )
    if not matches:
        raise CTraderDemoLabProbeError(
            "canonical NAS100 has no enabled explicit cTrader provider alias"
        )
    if len(matches) != 1:
        raise CTraderDemoLabProbeError(
            "canonical NAS100 provider alias is ambiguous; exact one-to-one binding required"
        )
    return matches[0]


def _connect_and_resolve_nas100(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    timeout_seconds: float,
) -> tuple[int, str, CTraderDemoLabSymbolEvidence, str]:
    """Resolve canonical NAS100 to one exact enabled broker symbol identity."""

    if not client.is_ready:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise CTraderDemoLabProbeError(
                f"cTrader DEMO authentication failed: {type(connected.error).__name__}"
            )
    account_id = client.account_id
    listed = client.request(
        "ProtoOASymbolsListReq",
        {"ctidTraderAccountId": account_id, "includeArchivedSymbols": False},
        client_msg_id="qore-vt31-v2-nas100-symbol-list",
        timeout_seconds=timeout_seconds,
    )
    if isinstance(listed, Failure):
        raise CTraderDemoLabProbeError("cTrader DEMO symbol-list read failed")
    native_symbols = getattr(listed.value, "symbol", None)
    if native_symbols is None:
        raise CTraderDemoLabProbeError("cTrader DEMO symbol list is missing")
    observed: list[tuple[str, bool]] = []
    by_name: dict[str, object] = {}
    for item in cast(tuple[object, ...], tuple(native_symbols)):
        name = getattr(item, "symbolName", None)
        enabled = getattr(item, "enabled", None)
        if type(name) is not str or type(enabled) is not bool:
            continue
        observed.append((name, enabled))
        if name in by_name:
            raise CTraderDemoLabProbeError(
                "cTrader DEMO symbol list duplicates provider symbol names"
            )
        by_name[name] = item
    provider_symbol_name = _select_nas100_provider_symbol_name(tuple(observed))
    selected = by_name[provider_symbol_name]
    symbol_id = _native_int(selected, "symbolId")
    details = client.request(
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
        client_msg_id=f"qore-vt31-v2-nas100-symbol-details:{symbol_id}",
        timeout_seconds=timeout_seconds,
    )
    if isinstance(details, Failure):
        raise CTraderDemoLabProbeError("cTrader DEMO symbol-details read failed")
    native_details = getattr(details.value, "symbol", None)
    if native_details is None:
        raise CTraderDemoLabProbeError("cTrader DEMO symbol details are missing")
    detail = next(
        (
            item
            for item in cast(tuple[object, ...], tuple(native_details))
            if getattr(item, "symbolId", None) == symbol_id
        ),
        None,
    )
    if detail is None:
        raise CTraderDemoLabProbeError("cTrader DEMO exact NAS100 symbol details are absent")

    # Keep the QORE-facing symbol canonical. Provider identity is retained
    # separately in the evidence payload and the native symbol_id is preserved.
    canonical_symbol = CTraderDemoLabSymbolEvidence(
        symbol_id=symbol_id,
        symbol_name=_SYMBOL,
        digits=_native_int(detail, "digits"),
        min_volume_units=_native_int(detail, "minVolume"),
        max_volume_units=_native_int(detail, "maxVolume"),
        step_volume_units=_native_int(detail, "stepVolume"),
    )
    return (
        account_id,
        compute_ctrader_demo_lab_account_fingerprint(account_id),
        canonical_symbol,
        provider_symbol_name,
    )


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


def _m1_collection_windows(
    opened_at: datetime,
    checked_at: datetime,
) -> tuple[tuple[datetime, datetime], ...]:
    """Return contiguous M1 request windows that cannot hit the 5,000-bar ceiling."""

    windows: list[tuple[datetime, datetime]] = []
    cursor = opened_at
    while cursor < checked_at:
        window_end = min(cursor + timedelta(days=_M1_CHUNK_DAYS), checked_at)
        windows.append((cursor, window_end))
        cursor = window_end
    return tuple(windows)


def collect_vt31_v2_m1_evidence(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    requested_opened_at: datetime,
    checked_at: datetime,
    timeout_seconds: float = 15.0,
) -> dict[str, object]:
    """Collect source-required two-year M1 evidence for canonical NAS100 only."""

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

    account_id, account_fingerprint, symbol, provider_symbol_name = (
        _connect_and_resolve_nas100(
            client,
            timeout_seconds=timeout_seconds,
        )
    )
    retained: dict[datetime, CTraderDemoLabClosedTrendbar] = {}
    for window_index, (cursor, window_end) in enumerate(
        _m1_collection_windows(opened, checked)
    ):
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
        "provider_symbol_name": provider_symbol_name,
        "checked_at": checked.isoformat(timespec="microseconds"),
        "requested_opened_at": opened.isoformat(timespec="microseconds"),
        "required_coverage_days": _REQUIRED_COVERAGE_DAYS,
        "historical_chunk_days": _M1_CHUNK_DAYS,
        "historical_page_count": _HISTORICAL_PAGE_COUNT,
        "decision_timeframe": "M1",
        "source_authorized_market": _SYMBOL,
        "coverage": _coverage_payload(ordered),
        "periods": {"M1": [item.payload() for item in ordered]},
    }


def main() -> None:
    """Collect two-year canonical NAS100 M1 DEMO evidence without printing secrets."""

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
