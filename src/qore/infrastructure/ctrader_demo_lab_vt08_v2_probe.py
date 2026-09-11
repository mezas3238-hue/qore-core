"""Read-only two-year M15 cTrader DEMO evidence for VT-08 CRT H4 AMD V2.

The collector keeps QORE canonical market identity separate from provider symbol
aliases and never performs a broker mutation.  Alias resolution is explicit and
fail-closed; fuzzy substring matching is prohibited.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import cast

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _CHUNK_DAYS,
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

_SCHEMA = "qore.ctrader_demo.vt08_crt_h4_amd_v2_m15_evidence.v1"
_NATIVE_M15_PERIOD = 7
_M15_SECONDS = 900
_MIN_LOOKBACK_DAYS = 730
_MAX_LOOKBACK_DAYS = 1095
_REQUIRED_COVERAGE_DAYS = 730
_RECENT_BOUNDARY_TOLERANCE_DAYS = 10
_PROVIDER_SUFFIX_SEPARATORS = frozenset({".", "_", "-", "/"})

_PROVIDER_ROOTS: dict[str, tuple[str, ...]] = {
    "EURUSD": ("EURUSD",),
    "GBPUSD": ("GBPUSD",),
    "USDJPY": ("USDJPY",),
    "AUDUSD": ("AUDUSD",),
    "USDCAD": ("USDCAD",),
    "XAUUSD": ("XAUUSD", "GOLD"),
    "GBPJPY": ("GBPJPY",),
    "AUDJPY": ("AUDJPY",),
    "NAS100": ("NAS100", "USTEC", "US100", "USTECH", "NASDAQ100"),
    "SP500": ("SP500", "US500", "SPX500", "USSPX500"),
    "US30": ("US30", "DJ30", "DJI30", "WALLSTREET30"),
}


def _root_match(name: str, root: str) -> bool:
    upper = name.upper()
    root_upper = root.upper()
    if upper == root_upper:
        return True
    if not upper.startswith(root_upper) or len(upper) <= len(root_upper):
        return False
    if upper[len(root_upper)] not in _PROVIDER_SUFFIX_SEPARATORS:
        return False
    suffix = upper[len(root_upper) + 1 :]
    return bool(suffix) and re.fullmatch(r"[A-Z0-9]+", suffix) is not None


def select_vt08_provider_symbol_name(
    canonical_symbol: str,
    symbols: tuple[tuple[str, bool], ...],
) -> str:
    """Resolve one canonical market to exactly one explicit provider identity."""

    roots = _PROVIDER_ROOTS.get(canonical_symbol)
    if roots is None:
        raise CTraderDemoLabProbeError("unsupported VT-08 V2 canonical market")
    if type(symbols) is not tuple or any(
        type(item) is not tuple
        or len(item) != 2
        or type(item[0]) is not str
        or type(item[1]) is not bool
        for item in symbols
    ):
        raise CTraderDemoLabProbeError("provider symbols must be immutable name/enabled pairs")
    enabled = tuple(name for name, is_enabled in symbols if is_enabled)
    for root in roots:
        exact = tuple(name for name in enabled if name.upper() == root.upper())
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            raise CTraderDemoLabProbeError("duplicate exact cTrader provider symbol identity")
        suffixed = tuple(name for name in enabled if _root_match(name, root))
        if len(suffixed) == 1:
            return suffixed[0]
        if len(suffixed) > 1:
            raise CTraderDemoLabProbeError(
                "canonical VT-08 V2 provider alias is ambiguous at one explicit root"
            )
    raise CTraderDemoLabProbeError(
        f"canonical {canonical_symbol} has no enabled explicit cTrader provider alias"
    )


def _connect_and_resolve(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    canonical_symbol: str,
    timeout_seconds: float,
) -> tuple[int, str, CTraderDemoLabSymbolEvidence, str]:
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
        client_msg_id=f"qore-vt08-v2-symbol-list:{canonical_symbol}",
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
        if name in by_name:
            raise CTraderDemoLabProbeError("cTrader DEMO symbol list duplicates names")
        observed.append((name, enabled))
        by_name[name] = item
    provider_symbol_name = select_vt08_provider_symbol_name(
        canonical_symbol, tuple(observed)
    )
    selected = by_name[provider_symbol_name]
    symbol_id = _native_int(selected, "symbolId")
    details = client.request(
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
        client_msg_id=f"qore-vt08-v2-symbol-details:{canonical_symbol}:{symbol_id}",
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
        raise CTraderDemoLabProbeError("exact cTrader provider symbol details are absent")
    canonical = CTraderDemoLabSymbolEvidence(
        symbol_id=symbol_id,
        symbol_name=canonical_symbol,
        digits=_native_int(detail, "digits"),
        min_volume_units=_native_int(detail, "minVolume"),
        max_volume_units=_native_int(detail, "maxVolume"),
        step_volume_units=_native_int(detail, "stepVolume"),
    )
    return (
        account_id,
        compute_ctrader_demo_lab_account_fingerprint(account_id),
        canonical,
        provider_symbol_name,
    )


def _validate_coverage(
    bars: tuple[CTraderDemoLabClosedTrendbar, ...],
    *,
    requested_opened_at: datetime,
    checked_at: datetime,
) -> None:
    if not bars or any(item.period != "M15" for item in bars):
        raise CTraderDemoLabProbeError("VT-08 V2 requires non-empty M15 evidence only")
    if bars != tuple(sorted(bars, key=lambda item: item.opened_at)):
        raise CTraderDemoLabProbeError("VT-08 V2 M15 evidence must be chronological")
    identities = tuple(item.opened_at for item in bars)
    if len(set(identities)) != len(identities):
        raise CTraderDemoLabProbeError("VT-08 V2 M15 evidence contains duplicate bars")
    first = bars[0].opened_at.astimezone(UTC)
    last = bars[-1].closed_at.astimezone(UTC)
    if last - first < timedelta(days=_REQUIRED_COVERAGE_DAYS):
        raise CTraderDemoLabProbeError("VT-08 V2 M15 history spans less than 730 days")
    if first < requested_opened_at.astimezone(UTC):
        raise CTraderDemoLabProbeError("VT-08 V2 evidence predates acquisition boundary")
    if last < checked_at.astimezone(UTC) - timedelta(days=_RECENT_BOUNDARY_TOLERANCE_DAYS):
        raise CTraderDemoLabProbeError("VT-08 V2 M15 evidence is stale")
    if any(item.closed_at > checked_at for item in bars):
        raise CTraderDemoLabProbeError("VT-08 V2 evidence contains a future/open bar")


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
        "span_seconds": int((bars[-1].closed_at - bars[0].opened_at).total_seconds()),
        "observed_gap_count": len(gaps),
        "observed_gap_seconds": sum(gaps),
        "maximum_observed_gap_seconds": max(gaps, default=0),
        "gap_policy": (
            "raw provider discontinuities retained; source-H4 construction requires exact "
            "contiguous M15 windows and never manufactures missing candles"
        ),
    }


def collect_vt08_v2_m15_evidence(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    canonical_symbol: str,
    requested_opened_at: datetime,
    checked_at: datetime,
    timeout_seconds: float = 15.0,
) -> dict[str, object]:
    """Collect two-year M15 evidence for one of Core's eleven canonical markets."""

    if canonical_symbol not in _PROVIDER_ROOTS:
        raise CTraderDemoLabProbeError("VT-08 V2 market is outside the 11-market Core set")
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

    account_id, account_fingerprint, symbol, provider_symbol_name = _connect_and_resolve(
        client,
        canonical_symbol=canonical_symbol,
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
            period_name="M15",
            native_period=_NATIVE_M15_PERIOD,
            seconds=_M15_SECONDS,
            opened_at=cursor,
            checked_at=window_end,
            window_index=window_index,
            timeout_seconds=timeout_seconds,
        )
        for bar in bars:
            existing = retained.get(bar.opened_at)
            if existing is not None and existing != bar:
                raise CTraderDemoLabProbeError(
                    "VT-08 V2 collection windows contradict on the same M15 bar"
                )
            retained[bar.opened_at] = bar
        cursor = window_end
        window_index += 1
    ordered = tuple(retained[key] for key in sorted(retained))
    _validate_coverage(ordered, requested_opened_at=opened, checked_at=checked)
    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "trading_permission_verified": True,
        "account_fingerprint": account_fingerprint,
        "symbol": symbol.payload(),
        "canonical_symbol": canonical_symbol,
        "provider_symbol_name": provider_symbol_name,
        "checked_at": checked.isoformat(timespec="microseconds"),
        "requested_opened_at": opened.isoformat(timespec="microseconds"),
        "required_coverage_days": _REQUIRED_COVERAGE_DAYS,
        "historical_chunk_days": _CHUNK_DAYS,
        "historical_page_count": _HISTORICAL_PAGE_COUNT,
        "decision_timeframe": "M15",
        "higher_timeframe": "source-aligned-H4-derived-from-M15",
        "source_timing": {
            "timezone": "America/New_York",
            "forex_h4_open_hours": [17, 21, 1, 5, 9, 13],
            "futures_h4_open_hours": [18, 22, 2, 6, 10, 14],
            "index_markets_using_futures_timing": ["NAS100", "SP500", "US30"],
        },
        "coverage": _coverage_payload(ordered),
        "periods": {"M15": [item.payload() for item in ordered]},
    }


def main() -> None:
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
        raise CTraderDemoLabProbeError("QORE_SOFTWARE_SHA must be exact lowercase Git SHA")
    canonical_symbol = _required_env("QORE_DEMO_LAB_SYMBOL")
    lookback_days = int(os.environ.get("QORE_DEMO_LAB_LOOKBACK_DAYS", "760"))
    if not _MIN_LOOKBACK_DAYS <= lookback_days <= _MAX_LOOKBACK_DAYS:
        raise CTraderDemoLabProbeError("VT-08 V2 lookback must be 730..1095 days")
    checked_at = datetime.now(UTC)
    requested_opened_at = checked_at - timedelta(days=lookback_days)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt08_v2_m15_evidence(
            client,
            canonical_symbol=canonical_symbol,
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
                allow_nan=False,
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
