"""Read-only source-availability probe for the next CIBO Phase22 holdout.

This probe never executes Trader logic or inspects outcomes. It only proves
whether cTrader DEMO still exposes market data near both boundaries of the
preregistered V2 holdout candidate. M5 is required for the shared holdout
universe and M1 NAS100 is additionally required for VT31.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
    candidate_is_burn_clean_for_all_lineages,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab.cibo_market_atlas_10y_m5_consumer_v1 import (
    PROVIDER_SYMBOL_MAP,
)
from qore.kernel.result import Failure

IDENTITY = "CIBO_PHASE22_HOLDOUT_V2_SOURCE_AVAILABILITY_V1"
PERIOD_M1 = 1
PERIOD_M5 = 5
M1_WINDOW = timedelta(days=2)
M5_WINDOW = timedelta(days=7)
REQUIRED_M5_SYMBOLS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "USDCAD",
    "USDJPY",
    "XAUUSD",
)


@dataclass(frozen=True, slots=True)
class SourceBoundaryProbe:
    symbol: str
    provider_symbol: str
    timeframe: str
    period_minutes: int
    first_window_start: datetime
    first_window_end: datetime
    last_window_start: datetime
    last_window_end: datetime
    first_window_bars: int
    last_window_bars: int
    first_observed_at: datetime | None
    last_observed_at: datetime | None
    available: bool

    def __post_init__(self) -> None:
        if self.symbol not in REQUIRED_M5_SYMBOLS:
            raise CiboCapitalManagementError("unexpected V2 source symbol")
        if not self.provider_symbol:
            raise CiboCapitalManagementError("provider symbol is required")
        if self.timeframe not in {"M1", "M5"}:
            raise CiboCapitalManagementError("unsupported V2 source timeframe")
        expected_period = PERIOD_M1 if self.timeframe == "M1" else PERIOD_M5
        if self.period_minutes != expected_period:
            raise CiboCapitalManagementError("V2 source period/timeframe drift")
        if self.timeframe == "M1" and self.symbol != "NAS100":
            raise CiboCapitalManagementError("only NAS100 M1 is required for V2")
        if (
            self.first_window_end <= self.first_window_start
            or self.last_window_end <= self.last_window_start
        ):
            raise CiboCapitalManagementError("invalid V2 source probe window")
        expected_available = (
            self.first_window_bars > 0
            and self.last_window_bars > 0
            and self.first_observed_at is not None
            and self.last_observed_at is not None
            and self.first_window_start
            <= self.first_observed_at
            < self.first_window_end
            and self.last_window_start
            <= self.last_observed_at
            < self.last_window_end
        )
        if self.available != expected_available:
            raise CiboCapitalManagementError("V2 source availability drift")


def probe_windows(
    *,
    start_at: datetime,
    end_exclusive_at: datetime,
    timeframe: str,
) -> tuple[tuple[datetime, datetime], tuple[datetime, datetime]]:
    if start_at.tzinfo is None or start_at.utcoffset() is None:
        raise CiboCapitalManagementError("V2 probe start must be timezone-aware")
    if end_exclusive_at.tzinfo is None or end_exclusive_at.utcoffset() is None:
        raise CiboCapitalManagementError("V2 probe end must be timezone-aware")
    if end_exclusive_at <= start_at:
        raise CiboCapitalManagementError("V2 probe interval invalid")
    if timeframe == "M1":
        width = M1_WINDOW
    elif timeframe == "M5":
        width = M5_WINDOW
    else:
        raise CiboCapitalManagementError("V2 probe timeframe must be M1 or M5")
    first = (start_at, min(start_at + width, end_exclusive_at))
    last = (max(start_at, end_exclusive_at - width), end_exclusive_at)
    return first, last


def assess_boundary_probe(
    *,
    symbol: str,
    provider_symbol: str,
    timeframe: str,
    first_window: tuple[datetime, datetime],
    last_window: tuple[datetime, datetime],
    first_timestamps: tuple[datetime, ...],
    last_timestamps: tuple[datetime, ...],
) -> SourceBoundaryProbe:
    period = PERIOD_M1 if timeframe == "M1" else PERIOD_M5
    for collection in (first_timestamps, last_timestamps):
        if collection != tuple(sorted(collection)):
            raise CiboCapitalManagementError("V2 source timestamps not chronological")
        if len(collection) != len(set(collection)):
            raise CiboCapitalManagementError("V2 source timestamps duplicated")
        for value in collection:
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    "V2 source timestamp must be timezone-aware"
                )
            if int(value.timestamp() // 60) % period != 0:
                raise CiboCapitalManagementError(
                    "V2 source timestamp alignment error"
                )
    return SourceBoundaryProbe(
        symbol=symbol,
        provider_symbol=provider_symbol,
        timeframe=timeframe,
        period_minutes=period,
        first_window_start=first_window[0],
        first_window_end=first_window[1],
        last_window_start=last_window[0],
        last_window_end=last_window[1],
        first_window_bars=len(first_timestamps),
        last_window_bars=len(last_timestamps),
        first_observed_at=(None if not first_timestamps else first_timestamps[0]),
        last_observed_at=(None if not last_timestamps else last_timestamps[-1]),
        available=bool(first_timestamps and last_timestamps),
    )


def _required_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    raise RuntimeError(f"missing required environment variable: {' or '.join(names)}")


def _credentials() -> CTraderOpenApiCredentials:
    return CTraderOpenApiCredentials(
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


def _native_int(value: object, name: str) -> int:
    raw = getattr(value, name)
    if type(raw) is not int:
        raise TypeError(f"{name} must be int")
    return raw


def _provider_symbol_id(
    client: SpotwareCTraderOpenApiClient,
    *,
    canonical_symbol: str,
) -> tuple[str, int]:
    provider_symbol = PROVIDER_SYMBOL_MAP[canonical_symbol]
    listed = client.request(
        "ProtoOASymbolsListReq",
        {
            "ctidTraderAccountId": client.account_id,
            "includeArchivedSymbols": False,
        },
        client_msg_id=f"cibo-phase22-v2-symbol-list:{canonical_symbol}",
        timeout_seconds=30.0,
    )
    if isinstance(listed, Failure):
        raise RuntimeError(f"cTrader symbol discovery failed: {listed.error}")
    symbols = tuple(cast(Iterable[object], getattr(listed.value, "symbol", ())))
    selected = next(
        (
            item
            for item in symbols
            if getattr(item, "symbolName", None) == provider_symbol
            and getattr(item, "enabled", None) is True
        ),
        None,
    )
    if selected is None:
        raise RuntimeError(
            f"V2 required provider symbol unavailable: "
            f"{canonical_symbol}->{provider_symbol}"
        )
    return provider_symbol, _native_int(selected, "symbolId")


def _read_timestamps(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    period_minutes: int,
    opened_at: datetime,
    closed_at: datetime,
    label: str,
) -> tuple[datetime, ...]:
    result = client.request(
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "period": period_minutes,
            "symbolId": symbol_id,
            "toTimestamp": int(closed_at.timestamp() * 1000) - 1,
        },
        client_msg_id=f"cibo-phase22-v2-source:{label}",
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(f"cTrader V2 source probe failed: {result.error}")
    raw = tuple(cast(Iterable[object], getattr(result.value, "trendbar", ())))
    maximum = int((closed_at - opened_at).total_seconds() // 60 // period_minutes) + 1
    if len(raw) > maximum:
        raise RuntimeError("provider returned more bars than calendar window permits")
    timestamps = tuple(
        sorted(
            datetime.fromtimestamp(
                _native_int(item, "utcTimestampInMinutes") * 60,
                tz=UTC,
            )
            for item in raw
        )
    )
    if any(not (opened_at <= value < closed_at) for value in timestamps):
        raise RuntimeError("provider returned bars outside strict V2 probe window")
    return timestamps


def run_probe() -> dict[str, object]:
    candidate = ACTIVE_USD60_HOLDOUT_CANDIDATE
    if not candidate_is_burn_clean_for_all_lineages(candidate):
        raise CiboCapitalManagementError("V2 candidate overlaps confirmed burn")
    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    probes: list[SourceBoundaryProbe] = []
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader DEMO authentication failed: {ready.error}")
        for symbol in REQUIRED_M5_SYMBOLS:
            provider_symbol, symbol_id = _provider_symbol_id(
                client,
                canonical_symbol=symbol,
            )
            for timeframe in (("M5",) if symbol != "NAS100" else ("M5", "M1")):
                first, last = probe_windows(
                    start_at=candidate.start_at,
                    end_exclusive_at=candidate.end_exclusive_at,
                    timeframe=timeframe,
                )
                period = PERIOD_M1 if timeframe == "M1" else PERIOD_M5
                first_rows = _read_timestamps(
                    client,
                    symbol_id=symbol_id,
                    period_minutes=period,
                    opened_at=first[0],
                    closed_at=first[1],
                    label=f"{symbol}:{timeframe}:first",
                )
                last_rows = _read_timestamps(
                    client,
                    symbol_id=symbol_id,
                    period_minutes=period,
                    opened_at=last[0],
                    closed_at=last[1],
                    label=f"{symbol}:{timeframe}:last",
                )
                probes.append(
                    assess_boundary_probe(
                        symbol=symbol,
                        provider_symbol=provider_symbol,
                        timeframe=timeframe,
                        first_window=first,
                        last_window=last,
                        first_timestamps=first_rows,
                        last_timestamps=last_rows,
                    )
                )
    finally:
        client.close()

    expected = {(symbol, "M5") for symbol in REQUIRED_M5_SYMBOLS}
    expected.add(("NAS100", "M1"))
    observed = {(item.symbol, item.timeframe) for item in probes}
    if observed != expected:
        raise CiboCapitalManagementError("V2 source probe surface incomplete")
    source_available = all(item.available for item in probes)
    return {
        "schema": "qore.cibo.phase22.holdout-v2-source-availability.v1",
        "identity": IDENTITY,
        "candidate_id": candidate.candidate_id,
        "window": {
            "start": candidate.start_at.isoformat(),
            "end_exclusive": candidate.end_exclusive_at.isoformat(),
        },
        "candidate_burn_clean": True,
        "probe_count": len(probes),
        "required_surface_count": len(expected),
        "source_available": source_available,
        "status": "SOURCE_AVAILABLE" if source_available else "SOURCE_UNAVAILABLE",
        "probes": [
            {
                **asdict(item),
                "first_window_start": item.first_window_start.isoformat(),
                "first_window_end": item.first_window_end.isoformat(),
                "last_window_start": item.last_window_start.isoformat(),
                "last_window_end": item.last_window_end.isoformat(),
                "first_observed_at": (
                    None
                    if item.first_observed_at is None
                    else item.first_observed_at.isoformat()
                ),
                "last_observed_at": (
                    None
                    if item.last_observed_at is None
                    else item.last_observed_at.isoformat()
                ),
            }
            for item in probes
        ],
        "trader_logic_executed": False,
        "outcomes_inspected": False,
        "productive_authority": False,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = run_probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    if payload["source_available"] is not True:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
