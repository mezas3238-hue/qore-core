"""Realtime boundary probe for the certified VT08 FundedNext runtime."""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from qore.infrastructure.fundednext_mt5_clock import (
    normalise_fundednext_server_epoch,
)
from qore.infrastructure.fundednext_realtime_market_data import (
    MARKET_DATA_SLA_SECONDS,
)


def vt08_boundary_ready(
    api: Any,
    *,
    symbol: str,
    anchor: datetime,
    now_fn: Callable[[], datetime] | None = None,
) -> tuple[bool, str | None]:
    """Require the exact current/closed M15 bars plus a <=2s broker tick."""
    anchor_utc = anchor.astimezone(UTC)
    if (
        anchor_utc.minute % 15
        or anchor_utc.second
        or anchor_utc.microsecond
    ):
        raise ValueError("VT08 anchor must be an exact M15 boundary")

    rows = api.copy_rates_from_pos(symbol, api.TIMEFRAME_M15, 0, 2)
    if rows is None or len(rows) < 2:
        return False, f"{symbol} recent M15 unavailable"

    opened = {
        normalise_fundednext_server_epoch(int(row["time"]))
        for row in rows
    }
    expected_current = anchor_utc
    expected_closed = expected_current - timedelta(minutes=15)
    if expected_current not in opened or expected_closed not in opened:
        latest = max(opened, default=None)
        return (
            False,
            f"{symbol} exact M15 boundary unavailable; latest="
            f"{None if latest is None else latest.isoformat()}",
        )

    tick = api.symbol_info_tick(symbol)
    if tick is None:
        return False, f"{symbol} tick unavailable"
    raw_tick = int(getattr(tick, "time", 0))
    if raw_tick <= 0:
        return False, f"{symbol} tick timestamp unavailable"
    tick_at = normalise_fundednext_server_epoch(raw_tick)
    observed = (now_fn or (lambda: datetime.now(UTC)))().astimezone(UTC)
    age = abs((observed - tick_at).total_seconds())
    if age > MARKET_DATA_SLA_SECONDS:
        return (
            False,
            f"{symbol} tick stale: {age:.3f}s > "
            f"{MARKET_DATA_SLA_SECONDS:.1f}s",
        )
    return True, None
