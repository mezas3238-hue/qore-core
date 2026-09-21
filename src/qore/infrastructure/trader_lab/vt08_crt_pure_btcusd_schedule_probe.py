"""Read-only cTrader BTCUSD trading-schedule probe for CRT PURE research."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import cast

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab.vt08_crt_pure_m5_consumer import _credentials
from qore.kernel.result import Failure


def _native_int(value: object, name: str) -> int:
    raw = getattr(value, name)
    if type(raw) is not int:
        raise TypeError(f"{name} must be int")
    return raw


def probe_btcusd_schedule() -> dict[str, object]:
    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader authentication failed: {ready.error}")
        account_id = client.account_id
        listed = client.request(
            "ProtoOASymbolsListReq",
            {"ctidTraderAccountId": account_id, "includeArchivedSymbols": False},
            client_msg_id="crt-btcusd-schedule-list",
            timeout_seconds=30.0,
        )
        if isinstance(listed, Failure):
            raise RuntimeError(f"cTrader symbol discovery failed: {listed.error}")
        light = next(
            (
                item
                for item in cast(Iterable[object], getattr(listed.value, "symbol", ()))
                if getattr(item, "symbolName", None) == "BTCUSD"
                and getattr(item, "enabled", None) is True
            ),
            None,
        )
        if light is None:
            raise RuntimeError("BTCUSD is unavailable on configured cTrader DEMO account")
        symbol_id = _native_int(light, "symbolId")
        details = client.request(
            "ProtoOASymbolByIdReq",
            {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
            client_msg_id="crt-btcusd-schedule-detail",
            timeout_seconds=30.0,
        )
        if isinstance(details, Failure):
            raise RuntimeError(f"cTrader symbol details failed: {details.error}")
        detail = next(
            (
                item
                for item in cast(Iterable[object], getattr(details.value, "symbol", ()))
                if getattr(item, "symbolId", None) == symbol_id
            ),
            None,
        )
        if detail is None:
            raise RuntimeError("BTCUSD symbol detail missing")
        schedule = tuple(cast(Iterable[object], getattr(detail, "schedule", ())))
        holidays = tuple(cast(Iterable[object], getattr(detail, "holiday", ())))
        return {
            "schema": "qore.vt08.crt_pure.btcusd_ctrader_schedule_probe.v1",
            "provider_symbol": "BTCUSD",
            "symbol_id": symbol_id,
            "schedule_time_zone": getattr(detail, "scheduleTimeZone", None),
            "schedule": [
                {
                    "start_second": _native_int(item, "startSecond"),
                    "end_second": _native_int(item, "endSecond"),
                }
                for item in schedule
            ],
            "holidays": [
                {
                    "holiday_id": _native_int(item, "holidayId"),
                    "name": getattr(item, "name", None),
                    "description": getattr(item, "description", None),
                    "schedule_time_zone": getattr(item, "scheduleTimeZone", None),
                    "holiday_date": _native_int(item, "holidayDate"),
                    "is_recurring": getattr(item, "isRecurring", None),
                    "start_second": getattr(item, "startSecond", None),
                    "end_second": getattr(item, "endSecond", None),
                }
                for item in holidays
            ],
            "research_only": True,
            "mutated_runtime": False,
        }
    finally:
        client.close()


def main() -> None:
    print("CRT_BTCUSD_SCHEDULE_JSON=" + json.dumps(probe_btcusd_schedule(), sort_keys=True))


if __name__ == "__main__":
    main()
