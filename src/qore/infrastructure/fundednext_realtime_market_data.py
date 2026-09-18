"""Low-latency FundedNext MT5 market-data cache for certified live traders.

The engine warms historical M5 context once, then refreshes only a tiny recent
window at strategy boundaries. A boundary snapshot is valid only when:
- the broker tick is fresh within MARKET_DATA_SLA_SECONDS;
- the exact just-closed M5 bar exists;
- the exact new M5 bar for the boundary exists;
- all of the above are observed no later than two seconds after the boundary.

No strategy logic lives here. This module only supplies temporally exact market
evidence to certified adapters.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from qore.infrastructure.fundednext_mt5_clock import (
    normalise_fundednext_server_epoch,
)

MARKET_DATA_SLA_SECONDS = 2.0
MARKET_DATA_POLL_SECONDS = 0.05
RECENT_M5_REFRESH_BARS = 8
MIN_HISTORY_BARS = 2_000


class MarketDataSlaError(RuntimeError):
    """Raised when exact boundary evidence is not available inside the SLA."""


@dataclass(frozen=True, slots=True)
class FundedNextM5Rate:
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class FundedNextM5Snapshot:
    symbol: str
    anchor: datetime
    closed_rates: tuple[FundedNextM5Rate, ...]
    current_rate: FundedNextM5Rate
    tick_observed_at: datetime
    captured_at: datetime

    @property
    def tick_age_seconds(self) -> float:
        return abs((self.captured_at - self.tick_observed_at).total_seconds())


class FundedNextRealtimeMarketData:
    """Single-process M5 cache shared by all live Turtle Soup adapters."""

    def __init__(
        self,
        *,
        sla_seconds: float = MARKET_DATA_SLA_SECONDS,
        poll_seconds: float = MARKET_DATA_POLL_SECONDS,
        now_fn: Callable[[], datetime] | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        if sla_seconds <= 0 or sla_seconds > MARKET_DATA_SLA_SECONDS:
            raise ValueError("market-data SLA must be within (0, 2] seconds")
        if poll_seconds <= 0 or poll_seconds > sla_seconds:
            raise ValueError("market-data poll interval invalid")
        self._sla_seconds = float(sla_seconds)
        self._poll_seconds = float(poll_seconds)
        self._now_fn = now_fn or (lambda: datetime.now(UTC))
        self._sleep_fn = sleep_fn
        self._history: dict[str, dict[datetime, FundedNextM5Rate]] = {}
        self._history_limits: dict[str, int] = {}
        self._snapshots: dict[tuple[str, datetime], FundedNextM5Snapshot] = {}
        self._failures: dict[tuple[str, datetime], str] = {}

    @staticmethod
    def _anchor_utc(anchor: datetime) -> datetime:
        value = anchor.astimezone(UTC)
        if value.second or value.microsecond or value.minute % 5:
            raise ValueError("market-data anchor must be an exact M5 boundary")
        return value

    @staticmethod
    def _rate(row: Any) -> FundedNextM5Rate:
        opened = normalise_fundednext_server_epoch(int(row["time"]))
        return FundedNextM5Rate(
            opened_at=opened,
            open=Decimal(str(row["open"])),
            high=Decimal(str(row["high"])),
            low=Decimal(str(row["low"])),
            close=Decimal(str(row["close"])),
        )

    def _read_rates(
        self,
        api: Any,
        *,
        symbol: str,
        count: int,
    ) -> tuple[FundedNextM5Rate, ...]:
        rows = api.copy_rates_from_pos(symbol, api.TIMEFRAME_M5, 0, count)
        if rows is None:
            raise MarketDataSlaError(f"{symbol} M5 history unavailable")
        retained: dict[datetime, FundedNextM5Rate] = {}
        for row in rows:
            rate = self._rate(row)
            prior = retained.get(rate.opened_at)
            if prior is not None and prior != rate:
                raise MarketDataSlaError(f"{symbol} contradictory M5 bar")
            retained[rate.opened_at] = rate
        return tuple(retained[key] for key in sorted(retained))

    def _merge(
        self,
        symbol: str,
        rates: tuple[FundedNextM5Rate, ...],
    ) -> None:
        retained = self._history.setdefault(symbol, {})
        for rate in rates:
            retained[rate.opened_at] = rate
        limit = self._history_limits.get(symbol)
        if limit is not None and len(retained) > limit + RECENT_M5_REFRESH_BARS:
            keep = sorted(retained)[-(limit + RECENT_M5_REFRESH_BARS):]
            self._history[symbol] = {key: retained[key] for key in keep}

    def warm(
        self,
        api: Any,
        *,
        symbol: str,
        history_bars: int,
    ) -> None:
        if history_bars < MIN_HISTORY_BARS:
            raise ValueError("market-data history requirement below safe minimum")
        rates = self._read_rates(api, symbol=symbol, count=history_bars)
        if len(rates) < MIN_HISTORY_BARS:
            raise MarketDataSlaError(f"{symbol} M5 history unavailable")
        self._history_limits[symbol] = history_bars
        self._merge(symbol, rates)

    def warm_many(
        self,
        api: Any,
        *,
        symbols: dict[str, int],
    ) -> None:
        for symbol, history_bars in symbols.items():
            self.warm(api, symbol=symbol, history_bars=history_bars)

    def _tick_observed_at(self, api: Any, *, symbol: str) -> datetime:
        tick = api.symbol_info_tick(symbol)
        if tick is None:
            raise MarketDataSlaError(f"{symbol} tick unavailable")
        raw = int(getattr(tick, "time", 0))
        if raw <= 0:
            raise MarketDataSlaError(f"{symbol} tick timestamp unavailable")
        return normalise_fundednext_server_epoch(raw)

    def _try_snapshot(
        self,
        api: Any,
        *,
        symbol: str,
        anchor: datetime,
        history_bars: int,
    ) -> FundedNextM5Snapshot | None:
        if symbol not in self._history:
            raise MarketDataSlaError(
                f"{symbol} market-data cache not warmed before boundary"
            )
        recent = self._read_rates(
            api,
            symbol=symbol,
            count=RECENT_M5_REFRESH_BARS,
        )
        self._merge(symbol, recent)
        now = self._now_fn().astimezone(UTC)
        tick_at = self._tick_observed_at(api, symbol=symbol)
        if abs((now - tick_at).total_seconds()) > self._sla_seconds:
            return None

        expected_closed = anchor - timedelta(minutes=5)
        retained = self._history[symbol]
        current = retained.get(anchor)
        closed = retained.get(expected_closed)
        if current is None or closed is None:
            return None

        closed_rates = tuple(
            retained[key]
            for key in sorted(retained)
            if key <= expected_closed
        )
        if len(closed_rates) < MIN_HISTORY_BARS:
            raise MarketDataSlaError(f"{symbol} cached M5 history unavailable")
        return FundedNextM5Snapshot(
            symbol=symbol,
            anchor=anchor,
            closed_rates=closed_rates[-history_bars:],
            current_rate=current,
            tick_observed_at=tick_at,
            captured_at=now,
        )

    def refresh_many(
        self,
        api: Any,
        *,
        symbols: tuple[str, ...],
        now: datetime | None = None,
    ) -> dict[str, str | None]:
        """Continuously refresh recent M5 bars and verify live tick freshness."""
        observed = (now or self._now_fn()).astimezone(UTC)
        result: dict[str, str | None] = {}
        for symbol in symbols:
            if symbol not in self._history:
                result[symbol] = f"{symbol} market-data cache not warmed"
                continue
            try:
                recent = self._read_rates(
                    api,
                    symbol=symbol,
                    count=RECENT_M5_REFRESH_BARS,
                )
                self._merge(symbol, recent)
                tick_at = self._tick_observed_at(api, symbol=symbol)
                age = abs((observed - tick_at).total_seconds())
                if age > self._sla_seconds:
                    result[symbol] = (
                        f"{symbol} tick stale: {age:.3f}s > "
                        f"{self._sla_seconds:.1f}s"
                    )
                else:
                    result[symbol] = None
            except MarketDataSlaError as error:
                result[symbol] = str(error)
        return result


    def latest_closed_rates(
        self,
        api: Any,
        *,
        symbol: str,
        history_bars: int,
        now: datetime | None = None,
    ) -> tuple[FundedNextM5Rate, ...]:
        """Refresh incremental data and return only fully closed M5 bars."""
        if symbol not in self._history:
            raise MarketDataSlaError(
                f"{symbol} market-data cache not warmed before management"
            )
        recent = self._read_rates(
            api,
            symbol=symbol,
            count=RECENT_M5_REFRESH_BARS,
        )
        self._merge(symbol, recent)
        observed = (now or self._now_fn()).astimezone(UTC)
        tick_at = self._tick_observed_at(api, symbol=symbol)
        if abs((observed - tick_at).total_seconds()) > self._sla_seconds:
            raise MarketDataSlaError(f"{symbol} tick stale beyond 2.0s")
        boundary = observed.replace(
            minute=(observed.minute // 5) * 5,
            second=0,
            microsecond=0,
        )
        expected_latest_closed = boundary - timedelta(minutes=5)
        retained = self._history[symbol]
        if expected_latest_closed not in retained:
            raise MarketDataSlaError(
                f"{symbol} latest closed M5 unavailable; "
                f"expected={expected_latest_closed.isoformat()}"
            )
        closed = tuple(
            retained[key]
            for key in sorted(retained)
            if key <= expected_latest_closed
        )
        if len(closed) < MIN_HISTORY_BARS:
            raise MarketDataSlaError(f"{symbol} cached M5 history unavailable")
        return closed[-history_bars:]


    def prime_anchor_group(
        self,
        api: Any,
        *,
        anchor: datetime,
        symbols: dict[str, int],
    ) -> dict[str, str | None]:
        anchor_utc = self._anchor_utc(anchor)
        pending = {
            symbol
            for symbol in symbols
            if (symbol, anchor_utc) not in self._snapshots
            and (symbol, anchor_utc) not in self._failures
        }
        deadline = anchor_utc + timedelta(seconds=self._sla_seconds)

        while pending:
            now = self._now_fn().astimezone(UTC)
            if now > deadline:
                break
            for symbol in tuple(pending):
                try:
                    snapshot = self._try_snapshot(
                        api,
                        symbol=symbol,
                        anchor=anchor_utc,
                        history_bars=symbols[symbol],
                    )
                except MarketDataSlaError as error:
                    self._failures[(symbol, anchor_utc)] = str(error)
                    pending.remove(symbol)
                    continue
                if snapshot is not None:
                    self._snapshots[(symbol, anchor_utc)] = snapshot
                    pending.remove(symbol)
            if pending:
                remaining = (deadline - self._now_fn().astimezone(UTC)).total_seconds()
                if remaining <= 0:
                    break
                self._sleep_fn(min(self._poll_seconds, remaining))

        for symbol in pending:
            retained = self._history.get(symbol, {})
            latest = max(retained, default=None)
            reason = (
                f"{symbol} exact M5 boundary unavailable within "
                f"{self._sla_seconds:.1f}s"
            )
            if latest is not None:
                reason += f"; latest={latest.isoformat()}"
            self._failures[(symbol, anchor_utc)] = reason

        return {
            symbol: self._failures.get((symbol, anchor_utc))
            for symbol in symbols
        }

    def snapshot(
        self,
        api: Any,
        *,
        symbol: str,
        anchor: datetime,
        history_bars: int,
    ) -> FundedNextM5Snapshot:
        anchor_utc = self._anchor_utc(anchor)
        key = (symbol, anchor_utc)
        failure = self._failures.get(key)
        if failure is not None:
            raise MarketDataSlaError(failure)
        snapshot = self._snapshots.get(key)
        if snapshot is None:
            self.prime_anchor_group(
                api,
                anchor=anchor_utc,
                symbols={symbol: history_bars},
            )
            failure = self._failures.get(key)
            if failure is not None:
                raise MarketDataSlaError(failure)
            snapshot = self._snapshots.get(key)
        if snapshot is None:
            raise MarketDataSlaError(f"{symbol} boundary snapshot unavailable")
        return snapshot


DEFAULT_FUNDEDNEXT_REALTIME_MARKET_DATA = FundedNextRealtimeMarketData()
