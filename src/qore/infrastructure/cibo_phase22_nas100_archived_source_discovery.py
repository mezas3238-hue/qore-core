"""Read-only discovery of archived cTrader NAS100-equivalent source history.

This probe inspects symbol metadata and trendbar timestamps only. It never runs
Trader logic, reads trade outcomes, or performs broker mutation.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_ALLOWED = frozenset({"ProtoOASymbolsListReq", "ProtoOAGetTrendbarsReq"})
_NAME_TOKENS = ("USTEC", "NAS", "US100", "NDX", "TECH100", "NASDAQ")
_WINDOWS = (
    ("V5_START", datetime(2014, 4, 19, tzinfo=UTC)),
    ("V5_END", datetime(2014, 10, 19, tzinfo=UTC)),
    ("V6_START", datetime(2013, 10, 19, tzinfo=UTC)),
    ("V6_END", datetime(2014, 4, 19, tzinfo=UTC)),
)


def _env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    raise RuntimeError(f"missing environment variable: {' or '.join(names)}")


def _credentials() -> CTraderOpenApiCredentials:
    return CTraderOpenApiCredentials(
        client_id=_env("QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"),
        client_secret=_env(
            "QORE_CTRADER_CLIENT_SECRET",
            "QORE_CTRADER_DEMO_CLIENT_SECRET",
        ),
        access_token=_env(
            "QORE_CTRADER_ACCESS_TOKEN",
            "QORE_CTRADER_DEMO_ACCESS_TOKEN",
        ),
        refresh_token=_env(
            "QORE_CTRADER_REFRESH_TOKEN",
            "QORE_CTRADER_DEMO_REFRESH_TOKEN",
        ),
        ctid_trader_account_id=int(
            _env("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID")
        ),
    )


def _request(
    client: SpotwareCTraderOpenApiClient,
    kind: str,
    payload: dict[str, object],
    *,
    msg_id: str,
) -> object:
    if kind not in _ALLOWED:
        raise CiboCapitalManagementError("archived source discovery mutation blocked")
    result = client.request(
        kind,
        payload,
        client_msg_id=msg_id,
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(f"read-only provider request failed: {result.error}")
    return result.value


def _int(obj: object, name: str) -> int:
    value = getattr(obj, name)
    if type(value) is not int:
        raise TypeError(f"{name} must be int")
    return value


def _bars(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    period: int,
    center: datetime,
    label: str,
) -> tuple[datetime, ...]:
    half = timedelta(days=4 if period == 5 else 2)
    opened = center - half
    closed = center + half
    response = _request(
        client,
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "fromTimestamp": int(opened.timestamp() * 1000),
            "period": period,
            "symbolId": symbol_id,
            "toTimestamp": int(closed.timestamp() * 1000) - 1,
        },
        msg_id=f"cibo-archived-nas100:{label}",
    )
    rows = tuple(cast(Iterable[object], getattr(response, "trendbar", ())))
    return tuple(
        sorted(
            datetime.fromtimestamp(
                _int(item, "utcTimestampInMinutes") * 60,
                tz=UTC,
            )
            for item in rows
        )
    )


def run_discovery() -> dict[str, object]:
    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader DEMO authentication failed: {ready.error}")
        response = _request(
            client,
            "ProtoOASymbolsListReq",
            {
                "ctidTraderAccountId": client.account_id,
                "includeArchivedSymbols": True,
            },
            msg_id="cibo-archived-nas100:list",
        )
        symbols = tuple(cast(Iterable[object], getattr(response, "symbol", ())))
        matches = []
        for item in symbols:
            name = str(getattr(item, "symbolName", ""))
            upper = name.upper()
            if not name or not any(token in upper for token in _NAME_TOKENS):
                continue
            symbol_id = _int(item, "symbolId")
            probes = []
            for window_name, center in _WINDOWS:
                for timeframe, period in (("M5", 5), ("M1", 1)):
                    rows = _bars(
                        client,
                        symbol_id=symbol_id,
                        period=period,
                        center=center,
                        label=f"{symbol_id}:{window_name}:{timeframe}",
                    )
                    probes.append(
                        {
                            "window": window_name,
                            "timeframe": timeframe,
                            "bar_count": len(rows),
                            "first_observed_at": (
                                None if not rows else rows[0].isoformat()
                            ),
                            "last_observed_at": (
                                None if not rows else rows[-1].isoformat()
                            ),
                        }
                    )
            matches.append(
                {
                    "symbol_id": symbol_id,
                    "symbol_name": name,
                    "enabled": getattr(item, "enabled", None),
                    "probes": probes,
                }
            )
        return {
            "schema": "qore.cibo.phase22.nas100-archived-source-discovery.v1",
            "symbol_match_count": len(matches),
            "matches": matches,
            "include_archived_symbols": True,
            "allowed_request_types": sorted(_ALLOWED),
            "trader_logic_executed": False,
            "outcomes_inspected": False,
            "broker_mutation": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "productive_authority": False,
        }
    finally:
        client.close()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = run_discovery()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
