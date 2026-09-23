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
    SourceCandle,
    _h1_open_for,
    _h4_open_for,
    build_daily,
    build_h1,
    build_h4,
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
    new_bar_first_seen_at: datetime
    market_state_updated_at: datetime
    aggregate_finished_at: datetime
    complete_bars: tuple[Bar, ...]
    h1: tuple[SourceCandle, ...]
    h4: tuple[SourceCandle, ...]
    d1: tuple[SourceCandle, ...]


@dataclass(frozen=True, slots=True)
class M5RefreshTelemetry:
    new_bar_first_seen_at: datetime
    market_state_updated_at: datetime
    aggregate_finished_at: datetime


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
        self._h1_groups: dict[datetime, dict[datetime, Bar]] = {}
        self._h4_groups: dict[datetime, dict[datetime, Bar]] = {}
        self._h1: dict[datetime, SourceCandle] = {}
        self._h4: dict[datetime, SourceCandle] = {}
        self._d1: tuple[SourceCandle, ...] = ()
        self._digits: int | None = None
        self._preloaded = False
        self._preload_calls = 0
        self._incremental_calls = 0
        self._last_refresh_at: datetime | None = None

    @staticmethod
    def _replace_aggregate(
        *,
        opened: datetime,
        group: dict[datetime, Bar],
        aggregates: dict[datetime, SourceCandle],
        builder: Callable[[tuple[Bar, ...]], tuple[SourceCandle, ...]],
    ) -> None:
        rebuilt = builder(tuple(group[key] for key in sorted(group)))
        if rebuilt:
            if len(rebuilt) != 1 or rebuilt[0].opened_at != opened:
                raise RuntimeError("incremental aggregate identity drift")
            aggregates[opened] = rebuilt[0]
        else:
            aggregates.pop(opened, None)

    def _update_resident_aggregates(
        self,
        changed: tuple[Bar, ...],
        *,
        evicted: tuple[Bar, ...] = (),
    ) -> None:
        affected_h1: set[datetime] = set()
        affected_h4: set[datetime] = set()
        for bar in changed:
            h1_open = _h1_open_for(bar.opened_at)
            h4_open = _h4_open_for(bar.opened_at)
            self._h1_groups.setdefault(h1_open, {})[bar.opened_at] = bar
            self._h4_groups.setdefault(h4_open, {})[bar.opened_at] = bar
            affected_h1.add(h1_open)
            affected_h4.add(h4_open)
        for bar in evicted:
            h1_open = _h1_open_for(bar.opened_at)
            h4_open = _h4_open_for(bar.opened_at)
            h1_group = self._h1_groups.get(h1_open)
            h4_group = self._h4_groups.get(h4_open)
            if h1_group is not None:
                h1_group.pop(bar.opened_at, None)
            if h4_group is not None:
                h4_group.pop(bar.opened_at, None)
            affected_h1.add(h1_open)
            affected_h4.add(h4_open)
        for opened in affected_h1:
            group = self._h1_groups.get(opened, {})
            self._replace_aggregate(
                opened=opened,
                group=group,
                aggregates=self._h1,
                builder=build_h1,
            )
            if not group:
                self._h1_groups.pop(opened, None)
        h4_changed = False
        for opened in affected_h4:
            group = self._h4_groups.get(opened, {})
            before = self._h4.get(opened)
            self._replace_aggregate(
                opened=opened,
                group=group,
                aggregates=self._h4,
                builder=build_h4,
            )
            h4_changed = h4_changed or self._h4.get(opened) != before
            if not group:
                self._h4_groups.pop(opened, None)
        if h4_changed:
            self._d1 = build_daily(tuple(self._h4[key] for key in sorted(self._h4)))

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

    def _ingest(
        self,
        rows: Any,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> tuple[datetime, datetime]:
        now = clock or (lambda: datetime.now(UTC))
        changed: list[Bar] = []
        for row in rows:
            opened = normalise_fundednext_server_epoch(int(row["time"]))
            bar = Bar(
                opened_at=opened,
                closed_at=opened + timedelta(minutes=5),
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
            )
            if self._bars.get(opened) != bar:
                self._bars[opened] = bar
                changed.append(bar)
        evicted: list[Bar] = []
        if len(self._bars) > self._max_bars:
            keys = sorted(self._bars)
            for key in keys[: len(keys) - self._max_bars]:
                evicted.append(self._bars.pop(key))
        market_state_updated_at = now().astimezone(UTC)
        if changed or evicted:
            self._update_resident_aggregates(
                tuple(changed),
                evicted=tuple(evicted),
            )
        return market_state_updated_at, now().astimezone(UTC)

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
        clock: Callable[[], datetime] | None = None,
    ) -> M5RefreshTelemetry:
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
        stage_clock = clock or (lambda: datetime.now(UTC))
        new_bar_first_seen_at = stage_clock().astimezone(UTC)
        market_state_updated_at, aggregate_finished_at = self._ingest(
            rows,
            clock=stage_clock,
        )
        self._incremental_calls += 1
        self._last_refresh_at = now.astimezone(UTC)
        return M5RefreshTelemetry(
            new_bar_first_seen_at=new_bar_first_seen_at,
            market_state_updated_at=market_state_updated_at,
            aggregate_finished_at=aggregate_finished_at,
        )

    def evidence(self) -> Evidence:
        if not self._preloaded or self._digits is None:
            raise RuntimeError(f"{self.error_prefix} M5 cache not ready")
        bars = tuple(self._bars[key] for key in sorted(self._bars))
        if len(bars) < MIN_HISTORY_M5_BARS:
            raise RuntimeError(f"{self.error_prefix} M5 cache underfilled")
        return Evidence(symbol=self.symbol, digits=self._digits, bars=bars)

    def prepared_context(
        self,
        *,
        anchor: datetime,
    ) -> tuple[
        tuple[Bar, ...],
        tuple[SourceCandle, ...],
        tuple[SourceCandle, ...],
        tuple[SourceCandle, ...],
    ]:
        """Return resident aggregates restricted to evidence known at anchor."""

        anchor = anchor.astimezone(UTC)
        complete = tuple(
            self._bars[key] for key in sorted(self._bars) if self._bars[key].closed_at <= anchor
        )
        h1 = tuple(self._h1[key] for key in sorted(self._h1) if self._h1[key].closed_at <= anchor)
        h4 = tuple(self._h4[key] for key in sorted(self._h4) if self._h4[key].closed_at <= anchor)
        d1 = tuple(item for item in self._d1 if item.closed_at <= anchor)
        return complete, h1, h4, d1

    def boundary_snapshot(
        self,
        api: Any,
        *,
        anchor: datetime,
        observed_at: datetime,
        refresh_telemetry: M5RefreshTelemetry | None = None,
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
            raise RuntimeError(f"{self.error_prefix} exact newly-closed M5 unavailable")
        if current is None or current.opened_at != anchor:
            raise RuntimeError(f"{self.error_prefix} exact new M5 unavailable")
        tick = api.symbol_info_tick(self.symbol)
        if tick is None:
            raise RuntimeError(f"{self.error_prefix} broker tick unavailable")
        raw_msc = int(getattr(tick, "time_msc", 0) or 0)
        if raw_msc > 0:
            raw_seconds, millis = divmod(raw_msc, 1000)
            broker_tick_at = normalise_fundednext_server_epoch(raw_seconds) + timedelta(
                milliseconds=millis
            )
        else:
            raw_seconds = int(getattr(tick, "time", 0) or 0)
            if raw_seconds <= 0:
                raise RuntimeError(f"{self.error_prefix} broker tick timestamp unavailable")
            broker_tick_at = normalise_fundednext_server_epoch(raw_seconds)
        tick_age = observed - broker_tick_at
        if tick_age < timedelta(seconds=-0.5):
            raise RuntimeError(f"{self.error_prefix} broker tick from future")
        if tick_age > M5_PROFILE.tick_max_age:
            raise RuntimeError(f"{self.error_prefix} broker tick older than 2s")
        complete, h1, h4, d1 = self.prepared_context(anchor=anchor)
        telemetry = refresh_telemetry or M5RefreshTelemetry(
            new_bar_first_seen_at=observed,
            market_state_updated_at=observed,
            aggregate_finished_at=observed,
        )
        return M5BoundarySnapshot(
            symbol=self.symbol,
            anchor=anchor,
            evidence=self.evidence(),
            current_open=current.open,
            broker_tick_at=broker_tick_at,
            observed_at=observed,
            new_bar_first_seen_at=telemetry.new_bar_first_seen_at,
            market_state_updated_at=telemetry.market_state_updated_at,
            aggregate_finished_at=telemetry.aggregate_finished_at,
            complete_bars=complete,
            h1=h1,
            h4=h4,
            d1=d1,
        )


def next_hour_boundary(now: datetime) -> datetime:
    current = now.astimezone(UTC)
    return current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def boundary_to_arm(now: datetime) -> datetime | None:
    current = now.astimezone(UTC)
    current_hour = current.replace(minute=0, second=0, microsecond=0)
    elapsed = current - current_hour
    if timedelta(0) <= elapsed <= M5_PROFILE.order_send_deadline:
        return current_hour
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
    on_snapshot: Callable[[str, M5BoundarySnapshot], None] | None = None,
) -> dict[str, M5BoundarySnapshot]:
    """Deliver each market snapshot once, inside its original 2-second SLA."""

    clock = now_fn or (lambda: datetime.now(UTC))
    anchor = anchor.astimezone(UTC)
    deadline = anchor + M5_PROFILE.order_send_deadline
    last_reasons: dict[str, str] = {}
    last_pre_refresh: datetime | None = None
    snapshots: dict[str, M5BoundarySnapshot] = {}

    while True:
        observed = clock().astimezone(UTC)
        if observed > deadline:
            if snapshots:
                return snapshots
            detail = ";".join(f"{name}:{reason}" for name, reason in sorted(last_reasons.items()))
            raise TimeoutError(f"M5 portfolio hard 2s SLA expired:{detail}")

        if observed < anchor:
            if (
                last_pre_refresh is None
                or (observed - last_pre_refresh).total_seconds() >= NORMAL_FEED_REFRESH_SECONDS
            ):
                for cache in caches.values():
                    cache.refresh_incremental(api, now=observed)
                last_pre_refresh = observed
            remaining = (anchor - observed).total_seconds()
            sleep_fn(min(BOUNDARY_RETRY_SECONDS, max(0.001, remaining)))
            continue
        for name, cache in caches.items():
            if name in snapshots:
                continue
            try:
                refresh_telemetry = cache.refresh_incremental(
                    api,
                    now=observed,
                    count=BOUNDARY_RECENT_M5_BARS,
                    clock=clock,
                )
                checked = clock().astimezone(UTC)
                snapshot = cache.boundary_snapshot(
                    api,
                    anchor=anchor,
                    observed_at=checked,
                    refresh_telemetry=refresh_telemetry,
                )
                snapshots[name] = snapshot
                if on_snapshot is not None:
                    on_snapshot(name, snapshot)
            except (RuntimeError, TimeoutError) as error:
                last_reasons[name] = str(error)

        if snapshots:
            # Release every market that is ready now. Slow siblings retry on the
            # next resident cycle inside the same hard boundary SLA.
            return snapshots
        checked = clock().astimezone(UTC)
        remaining = (deadline - checked).total_seconds()
        if remaining <= 0:
            if snapshots:
                return snapshots
            detail = ";".join(f"{name}:{reason}" for name, reason in sorted(last_reasons.items()))
            raise TimeoutError(f"M5 portfolio hard 2s SLA expired:{detail}")
        sleep_fn(min(BOUNDARY_RETRY_SECONDS, remaining))
