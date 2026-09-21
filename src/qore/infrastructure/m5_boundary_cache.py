"""Shared resident M5 cache for live Turtle Soup adapters.

This module changes transport timing only. Certified trader methodology,
signal construction, stops, targets, memory and risk remain owned by each
specialist adapter.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from qore.infrastructure.fundednext_mt5_clock import (
    normalise_fundednext_server_epoch,
)
from qore.infrastructure.trader_execution_profile import M5_PROFILE
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)

RECENT_M5_BARS = 8
BOUNDARY_RECENT_M5_BARS = 4
MIN_HISTORY_M5_BARS = 2_000
BOUNDARY_RETRY_SECONDS = M5_PROFILE.boundary_retry_ms / 1000.0
NORMAL_FEED_REFRESH_SECONDS = float(M5_PROFILE.normal_feed_refresh_seconds)
@dataclass(frozen=True, slots=True)
class M5BoundarySnapshot:
    symbol: str
    anchor: datetime
    evidence: Evidence
    current_open: Decimal
    broker_tick_at: datetime
    observed_at: datetime


class M5BoundaryCache:
    """One historical preload followed by small incremental M5 reads."""

    def __init__(
        self,
        *,
        symbol: str,
        error_prefix: str,
        max_bars: int = 15_000,
    ) -> None:
        if max_bars < MIN_HISTORY_M5_BARS:
            raise ValueError(f"{error_prefix} cache requires >=2000 M5 bars")
        self.symbol = symbol
        self.error_prefix = error_prefix
        self._max_bars = max_bars
        self._bars: dict[datetime, Bar] = {}
        self._digits: int | None = None
        self._preloaded = False
        self._preload_calls = 0
        self._incremental_calls = 0
        self._last_refresh_at: datetime | None = None
    @property
    def preloaded(self) -> bool:
        return self._preloaded

    @property
    def preload_calls(self) -> int:
        return self._preload_calls

    @property
    def incremental_calls(self) -> int:
        return self._incremental_calls

    @property
    def last_refresh_at(self) -> datetime | None:
        return self._last_refresh_at

    def _ingest(self, rows: Any) -> None:
        for row in rows:
            opened = normalise_fundednext_server_epoch(int(row["time"]))
            self._bars[opened] = Bar(
                opened_at=opened,
                closed_at=opened + timedelta(minutes=5),
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
            )
        if len(self._bars) > self._max_bars:
            keys = sorted(self._bars)
            for key in keys[: len(keys) - self._max_bars]:
                del self._bars[key]
    def preload(self, api: Any, *, now: datetime) -> None:
        if self._preloaded:
            raise RuntimeError(f"{self.error_prefix} M5 preload may run only once")
        rows = api.copy_rates_from_pos(
            self.symbol,
            api.TIMEFRAME_M5,
            0,
            self._max_bars,
        )
        if rows is None or len(rows) < MIN_HISTORY_M5_BARS:
            raise RuntimeError(f"{self.error_prefix} M5 preload unavailable")
        info = api.symbol_info(self.symbol)
        if info is None:
            raise RuntimeError(f"{self.error_prefix} symbol info unavailable")
        self._digits = int(info.digits)
        self._ingest(rows)
        self._preloaded = True
        self._preload_calls += 1
        self._last_refresh_at = now.astimezone(UTC)

    def refresh_incremental(
        self,
        api: Any,
        *,
        now: datetime,
        count: int = RECENT_M5_BARS,
    ) -> None:
        if not self._preloaded:
            raise RuntimeError(f"{self.error_prefix} M5 cache not preloaded")
        if count <= 0 or count > 64:
            raise ValueError(f"{self.error_prefix} incremental count invalid")
        rows = api.copy_rates_from_pos(
            self.symbol,
            api.TIMEFRAME_M5,
            0,
            count,
        )
        if rows is None or len(rows) < 2:
            raise RuntimeError(f"{self.error_prefix} M5 refresh unavailable")
        self._ingest(rows)
        self._incremental_calls += 1
        self._last_refresh_at = now.astimezone(UTC)

    def evidence(self) -> Evidence:
        if not self._preloaded or self._digits is None:
            raise RuntimeError(f"{self.error_prefix} M5 cache not ready")
        bars = tuple(self._bars[key] for key in sorted(self._bars))
        if len(bars) < MIN_HISTORY_M5_BARS:
            raise RuntimeError(f"{self.error_prefix} M5 cache underfilled")
        return Evidence(symbol=self.symbol, digits=self._digits, bars=bars)

    def boundary_snapshot(
        self,
        api: Any,
        *,
        anchor: datetime,
        observed_at: datetime,
    ) -> M5BoundarySnapshot:
        anchor = anchor.astimezone(UTC)
        observed = observed_at.astimezone(UTC)
        deadline = anchor + M5_PROFILE.order_send_deadline
        if observed < anchor:
            raise RuntimeError(f"{self.error_prefix} boundary not reached")
        if observed > deadline:
            raise TimeoutError(f"{self.error_prefix} hard 2s SLA expired")
        prior = self._bars.get(anchor - timedelta(minutes=5))
        current = self._bars.get(anchor)
        if prior is None or prior.closed_at != anchor:
            raise RuntimeError(
                f"{self.error_prefix} exact newly-closed M5 unavailable"
            )
        if current is None or current.opened_at != anchor:
            raise RuntimeError(f"{self.error_prefix} exact new M5 unavailable")
        tick = api.symbol_info_tick(self.symbol)
        if tick is None:
            raise RuntimeError(f"{self.error_prefix} broker tick unavailable")
        raw_msc = int(getattr(tick, "time_msc", 0) or 0)
        if raw_msc > 0:
            raw_seconds, millis = divmod(raw_msc, 1000)
            broker_tick_at = normalise_fundednext_server_epoch(
                raw_seconds
            ) + timedelta(milliseconds=millis)
        else:
            raw_seconds = int(getattr(tick, "time", 0) or 0)
            if raw_seconds <= 0:
                raise RuntimeError(
                    f"{self.error_prefix} broker tick timestamp unavailable"
                )
            broker_tick_at = normalise_fundednext_server_epoch(raw_seconds)
        tick_age = observed - broker_tick_at
        if tick_age < timedelta(seconds=-0.5):
            raise RuntimeError(f"{self.error_prefix} broker tick from future")
        if tick_age > M5_PROFILE.tick_max_age:
            raise RuntimeError(f"{self.error_prefix} broker tick older than 2s")
        return M5BoundarySnapshot(
            symbol=self.symbol,
            anchor=anchor,
            evidence=self.evidence(),
            current_open=current.open,
            broker_tick_at=broker_tick_at,
            observed_at=observed,
        )


def next_hour_boundary(now: datetime) -> datetime:
    current = now.astimezone(UTC)
    return current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def boundary_to_arm(now: datetime) -> datetime | None:
    current = now.astimezone(UTC)
    anchor = next_hour_boundary(current)
    remaining = anchor - current
    lead = timedelta(seconds=float(M5_PROFILE.boundary_arm_lead_seconds))
    if timedelta(0) < remaining <= lead:
        return anchor
    return None
def await_boundary_snapshots(
    api: Any,
    *,
    caches: Mapping[str, M5BoundaryCache],
    anchor: datetime,
    now_fn: Callable[[], datetime] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, M5BoundarySnapshot]:
    """Acquire every M5 specialist snapshot inside one shared 2-second SLA."""

    clock = now_fn or (lambda: datetime.now(UTC))
    anchor = anchor.astimezone(UTC)
    deadline = anchor + M5_PROFILE.order_send_deadline
    last_reasons: dict[str, str] = {}
    last_pre_refresh: datetime | None = None

    while True:
        observed = clock().astimezone(UTC)
        if observed > deadline:
            detail = ";".join(
                f"{name}:{reason}" for name, reason in sorted(last_reasons.items())
            )
            raise TimeoutError(f"M5 portfolio hard 2s SLA expired:{detail}")

        if observed < anchor:
            if (
                last_pre_refresh is None
                or (observed - last_pre_refresh).total_seconds()
                >= NORMAL_FEED_REFRESH_SECONDS
            ):
                for cache in caches.values():
                    cache.refresh_incremental(api, now=observed)
                last_pre_refresh = observed
            remaining = (anchor - observed).total_seconds()
            sleep_fn(min(BOUNDARY_RETRY_SECONDS, max(0.001, remaining)))
            continue
        snapshots: dict[str, M5BoundarySnapshot] = {}
        for name, cache in caches.items():
            try:
                cache.refresh_incremental(
                    api,
                    now=observed,
                    count=BOUNDARY_RECENT_M5_BARS,
                )
                checked = clock().astimezone(UTC)
                snapshots[name] = cache.boundary_snapshot(
                    api,
                    anchor=anchor,
                    observed_at=checked,
                )
            except (RuntimeError, TimeoutError) as error:
                last_reasons[name] = str(error)

        if len(snapshots) == len(caches):
            return snapshots
        checked = clock().astimezone(UTC)
        remaining = (deadline - checked).total_seconds()
        if remaining <= 0:
            detail = ";".join(
                f"{name}:{reason}" for name, reason in sorted(last_reasons.items())
            )
            raise TimeoutError(f"M5 portfolio hard 2s SLA expired:{detail}")
        sleep_fn(min(BOUNDARY_RETRY_SECONDS, remaining))
