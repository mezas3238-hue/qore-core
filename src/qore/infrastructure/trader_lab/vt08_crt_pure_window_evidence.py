"""Window-parameterized evidence loader for VT08 CRT PURE research.

This module generalizes the already-used cTrader M5 loader and parent-CRT builder
without changing methodology. It exists so development candidates can be evaluated
on historical windows that were not used to define the candidate family.

BTCUSD keeps the same broker-schedule-aware completeness semantics used by the
current CRT PURE evidence lineage. Missing bars during declared closed slots are
not fabricated; missing bars while open remain fail-closed.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    CHUNK_DAYS,
    ReplayBar,
    _aggregate,
    _days,
    _partition_windows,
    _segment,
    _to_replay_bar,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_btcusd_schedule_aware_replay import (
    _session_segment,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_ctrader_market_calendar import (
    load_btcusd_ctrader_calendar,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_m5_consumer import (
    _credentials,
    _selected_symbol,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_m5_windowed_runtime import (
    read_windowed_chunk,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    ParentCrt,
    _parent_direction,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_timing_policy import (
    NY,
    utc_triplet_windows_for_local_date,
)
from qore.kernel.result import Failure


def load_m5_window(
    market: CrtPureMarket,
    *,
    start: datetime,
    end_exclusive: datetime,
) -> tuple[ReplayBar, ...]:
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("start must be timezone-aware")
    if end_exclusive.tzinfo is None or end_exclusive.utcoffset() is None:
        raise ValueError("end_exclusive must be timezone-aware")
    if end_exclusive <= start:
        raise ValueError("replay window must be positive")

    fetch_start = start - timedelta(days=1)
    fetch_end = end_exclusive + timedelta(days=1)
    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader authentication failed: {ready.error}")
        provider_symbol, symbol_id, digits, pip_position = _selected_symbol(
            client,
            canonical_symbol=market.value,
        )
        by_time: dict[datetime, ReplayBar] = {}
        windows = _partition_windows(fetch_start, fetch_end)
        # Preserve the existing 7-day evidence-chunk contract.
        if any((closed - opened) > timedelta(days=CHUNK_DAYS) for opened, closed in windows):
            raise RuntimeError("window partition exceeded frozen cTrader chunk size")
        for index, (opened, closed) in enumerate(windows):
            native_bars = read_windowed_chunk(
                client,
                account_id=client.account_id,
                symbol_id=symbol_id,
                opened_at=opened,
                closed_at=closed,
                client_msg_id=f"crt-pure-window:{market.value}:{index}",
            )
            for native in native_bars:
                bar = _to_replay_bar(
                    native,
                    market=market,
                    provider_symbol=provider_symbol,
                    provider_symbol_id=symbol_id,
                    digits=digits,
                    pip_position=pip_position,
                )
                if not fetch_start <= bar.opened_at < fetch_end:
                    raise RuntimeError("provider returned M5 outside requested evidence window")
                existing = by_time.get(bar.opened_at)
                if existing is None:
                    by_time[bar.opened_at] = bar
                elif existing.payload() != bar.payload():
                    raise RuntimeError("contradictory duplicate M5 payload in window evidence")
        return tuple(by_time[key] for key in sorted(by_time))
    finally:
        client.close()


def build_parent_crts_for_window(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
    *,
    start: datetime,
    end_exclusive: datetime,
) -> tuple[ParentCrt, ...]:
    if end_exclusive <= start:
        raise ValueError("parent CRT window must be positive")

    by_time = {bar.opened_at: bar for bar in bars}
    calendar = load_btcusd_ctrader_calendar() if market is CrtPureMarket.BTCUSD else None
    start_day = (start - timedelta(days=1)).astimezone(NY).date()
    end_day = end_exclusive.astimezone(NY).date()
    result: list[ParentCrt] = []

    for day in _days(start_day, end_day):
        local_noon = datetime(day.year, day.month, day.day, 12, tzinfo=NY)
        for timing_index, window in enumerate(
            utc_triplet_windows_for_local_date(market, local_noon)
        ):
            if not start <= window.candle_3_open < end_exclusive:
                continue
            if calendar is None:
                c1_m5 = _segment(by_time, window.candle_1_open, window.candle_2_open)
                c2_m5 = _segment(by_time, window.candle_2_open, window.candle_3_open)
                c3_m5 = _segment(by_time, window.candle_3_open, window.window_close)
            else:
                c1_m5, _, _, _ = _session_segment(
                    by_time,
                    window.candle_1_open,
                    window.candle_2_open,
                    calendar,
                )
                c2_m5, _, _, _ = _session_segment(
                    by_time,
                    window.candle_2_open,
                    window.candle_3_open,
                    calendar,
                )
                c3_m5, _, _, _ = _session_segment(
                    by_time,
                    window.candle_3_open,
                    window.window_close,
                    calendar,
                )
            if c1_m5 is None or c2_m5 is None or c3_m5 is None:
                continue

            c1 = _aggregate(c1_m5, window.candle_1_open, window.candle_2_open)
            c2 = _aggregate(c2_m5, window.candle_2_open, window.candle_3_open)
            direction = _parent_direction(c1, c2)
            if direction is None:
                continue

            result.append(
                ParentCrt(
                    market=market,
                    direction=direction,
                    triplet=str(timing_index + 1),
                    c3_opened_at=window.candle_3_open,
                    c3_closed_at=window.window_close,
                    c1=c1,
                    c2=c2,
                    c3_m5=c3_m5,
                )
            )
    return tuple(result)
