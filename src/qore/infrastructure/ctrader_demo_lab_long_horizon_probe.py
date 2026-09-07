"""Long-horizon read-only cTrader DEMO evidence collector for Trader Lab.

This collector is the credibility-grade counterpart to the short smoke probe.
It requires at least 730 requested days, obtains the history in bounded
30-day chunks, paces chunk requests below the cTrader historical-data rate
limit, verifies one exact DEMO account/symbol binding across every chunk, and
fails closed when the merged provider history does not cover the requested
horizon closely enough.

It never submits, amends, cancels, or otherwise mutates an order.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from time import sleep

from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabClosedTrendbar,
    CTraderDemoLabMarketEvidence,
    CTraderDemoLabProbeError,
    collect_ctrader_demo_lab_market_evidence,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

_MIN_LOOKBACK_DAYS = 730
_MAX_LOOKBACK_DAYS = 1095
_CHUNK_DAYS = 30
_CHUNK_PAUSE_SECONDS = 1.05
_COVERAGE_TOLERANCE_DAYS = 10
_REQUIRED_PERIODS = ("M1", "M5", "M15", "H4")


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise CTraderDemoLabProbeError(f"missing required environment input: {name}")


def _merge_chunk(
    retained: dict[tuple[str, datetime], CTraderDemoLabClosedTrendbar],
    evidence: CTraderDemoLabMarketEvidence,
) -> None:
    for bar in evidence.bars:
        key = (bar.period, bar.opened_at)
        existing = retained.get(key)
        if existing is not None and existing != bar:
            raise CTraderDemoLabProbeError(
                "cTrader long-horizon chunks contradict on the same trendbar"
            )
        retained[key] = bar


def _validate_coverage(
    bars: tuple[CTraderDemoLabClosedTrendbar, ...],
    *,
    requested_opened_at: datetime,
    checked_at: datetime,
) -> None:
    tolerance = timedelta(days=_COVERAGE_TOLERANCE_DAYS)
    for period in _REQUIRED_PERIODS:
        period_bars = tuple(item for item in bars if item.period == period)
        if not period_bars:
            raise CTraderDemoLabProbeError(
                f"cTrader long-horizon evidence is missing {period}"
            )
        first = period_bars[0].opened_at
        last = period_bars[-1].closed_at
        if first > requested_opened_at + tolerance:
            raise CTraderDemoLabProbeError(
                f"cTrader {period} history does not reach the two-year boundary"
            )
        if last < checked_at - tolerance:
            raise CTraderDemoLabProbeError(
                f"cTrader {period} history is stale at the recent boundary"
            )


def collect_long_horizon_market_evidence(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_name: str,
    requested_opened_at: datetime,
    checked_at: datetime,
) -> CTraderDemoLabMarketEvidence:
    """Collect and merge bounded cTrader DEMO chunks for one long horizon."""
    if requested_opened_at.tzinfo is None or requested_opened_at.utcoffset() is None:
        raise CTraderDemoLabProbeError("requested_opened_at must be timezone-aware")
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise CTraderDemoLabProbeError("checked_at must be timezone-aware")
    opened = requested_opened_at.astimezone(UTC)
    checked = checked_at.astimezone(UTC)
    if opened >= checked:
        raise CTraderDemoLabProbeError("requested_opened_at must predate checked_at")

    cursor = opened
    retained: dict[tuple[str, datetime], CTraderDemoLabClosedTrendbar] = {}
    account_fingerprint: str | None = None
    symbol = None
    chunk_index = 0
    while cursor < checked:
        chunk_end = min(cursor + timedelta(days=_CHUNK_DAYS), checked)
        if chunk_index:
            sleep(_CHUNK_PAUSE_SECONDS)
        evidence = collect_ctrader_demo_lab_market_evidence(
            client,
            symbol_name=symbol_name,
            opened_at=cursor,
            checked_at=chunk_end,
        )
        if account_fingerprint is None:
            account_fingerprint = evidence.account_fingerprint
            symbol = evidence.symbol
        elif evidence.account_fingerprint != account_fingerprint or evidence.symbol != symbol:
            raise CTraderDemoLabProbeError(
                "cTrader long-horizon chunks changed account or symbol binding"
            )
        _merge_chunk(retained, evidence)
        cursor = chunk_end
        chunk_index += 1

    if account_fingerprint is None or symbol is None or not retained:
        raise CTraderDemoLabProbeError("cTrader long-horizon collection returned no evidence")
    bars = tuple(sorted(retained.values(), key=lambda item: (item.period, item.opened_at)))
    _validate_coverage(
        bars,
        requested_opened_at=opened,
        checked_at=checked,
    )
    return CTraderDemoLabMarketEvidence(
        account_fingerprint=account_fingerprint,
        symbol=symbol,
        checked_at=checked,
        bars=bars,
    )


def main() -> None:
    """Collect credibility-grade two-year DEMO evidence without printing secrets."""
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
    symbol_name = _required_env("QORE_DEMO_LAB_SYMBOL")
    lookback_days = int(os.environ.get("QORE_DEMO_LAB_LOOKBACK_DAYS", "730"))
    if lookback_days < _MIN_LOOKBACK_DAYS or lookback_days > _MAX_LOOKBACK_DAYS:
        raise CTraderDemoLabProbeError(
            "long-horizon Lab lookback days must be between 730 and 1095"
        )
    checked_at = datetime.now(UTC)
    requested_opened_at = checked_at - timedelta(days=lookback_days)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        evidence = collect_long_horizon_market_evidence(
            client,
            symbol_name=symbol_name,
            requested_opened_at=requested_opened_at,
            checked_at=checked_at,
        )
        payload = evidence.sanitized_payload()
        payload["requested_lookback_days"] = lookback_days
        payload["requested_opened_at"] = requested_opened_at.isoformat(timespec="microseconds")
        payload["historical_chunk_days"] = _CHUNK_DAYS
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
