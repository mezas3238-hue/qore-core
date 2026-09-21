"""Corrected cTrader windowed runtime for VT08 CRT PURE common M5 consumption.

cTrader's trendbar `count` parameter can cause a response to be anchored to the
request end rather than constrained to the requested start. This runtime replaces
only the transport read helper used by the frozen V1 consumer: seven-day windows
are defined exclusively by fromTimestamp/toTimestamp and are rejected if the
provider returns more M5 bars than can exist on the calendar grid.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from time import sleep
from typing import cast

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab import vt08_crt_pure_m5_consumer as base
from qore.kernel.result import Failure

IDENTITY = base.IDENTITY
TRANSPORT = "STRICT_FROM_TO_WINDOWED_V1"
PERIOD_M5 = base.PERIOD_M5
MAX_CALENDAR_M5_BARS_PER_CHUNK = base.CHUNK_DAYS * 24 * 60 // PERIOD_M5


def read_windowed_chunk(
    client: SpotwareCTraderOpenApiClient,
    *,
    account_id: int,
    symbol_id: int,
    opened_at: datetime,
    closed_at: datetime,
    client_msg_id: str,
) -> tuple[object, ...]:
    """Read one strict [opened_at, closed_at) M5 provider window without `count`."""
    sleep(base.REQUEST_PAUSE_SECONDS)
    result = client.request(
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": account_id,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "period": PERIOD_M5,
            "symbolId": symbol_id,
            "toTimestamp": int(closed_at.timestamp() * 1000) - 1,
        },
        client_msg_id=client_msg_id,
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(f"cTrader M5 consumption failed: {result.error}")
    bars = tuple(cast(Iterable[object], getattr(result.value, "trendbar", ())))
    if len(bars) > MAX_CALENDAR_M5_BARS_PER_CHUNK:
        raise RuntimeError(
            "provider returned more M5 bars than the seven-day calendar grid allows"
        )
    return bars


def install_windowed_transport() -> None:
    """Install the corrected transport helper without changing research semantics."""
    base.__dict__["_read_chunk"] = read_windowed_chunk


def main() -> None:
    install_windowed_transport()
    base.main()


if __name__ == "__main__":
    main()
