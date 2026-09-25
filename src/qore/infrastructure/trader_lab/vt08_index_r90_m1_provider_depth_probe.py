"""VT08 Index R90 — cTrader DEMO native-M1 historical depth probe.

R89 closed the standard/retest/positional execution-path density question.
R88 showed H1->M5 is source-valid but still insufficient. The next plausible
source-fractal layer is M15->M1, but the authoritative CIBO 10Y corpus stores
M5, not M1.

R90 does not backtest or create trades. It probes provider-native M1 availability
at four fixed historical points for NAS100/SP500/US30 using strict
[fromTimestamp, toTimestamp) requests with no count parameter.

Governance:
- DEMO only; Spotware client rejects LIVE accounts;
- read-only trendbar requests only;
- no synthetic/interpolated M1;
- no PnL;
- no fresh-holdout claim;
- no runtime/live authority.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

SCHEMA = "qore.trader_lab.vt08_index_r90_m1_provider_depth_probe.v1"
IDENTITY = "VT08_INDEX_R90_CTRADER_DEMO_NATIVE_M1_DEPTH_PROBE_001"

PERIOD_M1 = 1
PROBE_DURATION = timedelta(hours=24)
PROBE_OPENINGS = (
    datetime(2016, 9, 19, 0, 0, tzinfo=UTC),
    datetime(2018, 9, 17, 0, 0, tzinfo=UTC),
    datetime(2024, 9, 16, 0, 0, tzinfo=UTC),
    datetime(2026, 9, 14, 0, 0, tzinfo=UTC),
)
PROVIDER_SYMBOLS = {
    "NAS100": "USTEC",
    "SP500": "US500",
    "US30": "US30",
}


@dataclass(frozen=True, slots=True)
class ProbeResult:
    canonical_symbol: str
    provider_symbol: str
    opened_at: str
    closed_at: str
    retained_m1_bars: int
    earliest_observed_m1: str | None
    latest_observed_m1: str | None
    timestamp_alignment_errors: int
    out_of_window_bars: int
    contradictory_timestamps: int
    provider_payload_valid: bool
    m1_available: bool


def _required_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    raise RuntimeError(
        "missing required environment variable: " + " or ".join(names)
    )


def _credentials() -> CTraderOpenApiCredentials:
    return CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID",
            "QORE_CTRADER_DEMO_CLIENT_ID",
        ),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET",
            "QORE_CTRADER_DEMO_CLIENT_SECRET",
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN",
            "QORE_CTRADER_DEMO_ACCESS_TOKEN",
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN",
            "QORE_CTRADER_DEMO_REFRESH_TOKEN",
        ),
        ctid_trader_account_id=int(
            _required_env(
                "QORE_CTRADER_DEMO_ACCOUNT_ID",
                "QORE_CTRADER_ACCOUNT_ID",
            )
        ),
    )


def _native_int(value: object, name: str) -> int:
    raw = getattr(value, name)
    if type(raw) is not int:
        raise TypeError(f"{name} must be int")
    return raw


def _discover_symbol(
    client: SpotwareCTraderOpenApiClient,
    *,
    canonical_symbol: str,
) -> tuple[str, int]:
    provider_symbol = PROVIDER_SYMBOLS[canonical_symbol]
    listed = client.request(
        "ProtoOASymbolsListReq",
        {
            "ctidTraderAccountId": client.account_id,
            "includeArchivedSymbols": False,
        },
        client_msg_id=f"r90-symbols:{canonical_symbol}",
        timeout_seconds=30.0,
    )
    if isinstance(listed, Failure):
        raise RuntimeError(
            f"R90 symbol discovery failed for {canonical_symbol}: "
            f"{listed.error}"
        )
    symbols = cast(
        Iterable[object],
        getattr(listed.value, "symbol", ()),
    )
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
            f"R90 provider symbol unavailable: "
            f"{canonical_symbol}->{provider_symbol}"
        )
    return provider_symbol, _native_int(selected, "symbolId")


def _probe_window(
    client: SpotwareCTraderOpenApiClient,
    *,
    canonical_symbol: str,
    provider_symbol: str,
    symbol_id: int,
    opened_at: datetime,
) -> ProbeResult:
    closed_at = opened_at + PROBE_DURATION
    response = client.request(
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "period": PERIOD_M1,
            "symbolId": symbol_id,
            "toTimestamp": int(closed_at.timestamp() * 1000) - 1,
        },
        client_msg_id=(
            f"r90-m1:{canonical_symbol}:{opened_at.date().isoformat()}"
        ),
        timeout_seconds=60.0,
    )
    if isinstance(response, Failure):
        raise RuntimeError(
            f"R90 M1 request failed for {canonical_symbol} "
            f"{opened_at.date()}: {response.error}"
        )

    rows = tuple(
        cast(
            Iterable[object],
            getattr(response.value, "trendbar", ()),
        )
    )
    timestamps: list[datetime] = []
    alignment_errors = 0
    out_of_window = 0
    seen: set[int] = set()
    contradictions = 0

    payload_by_timestamp: dict[int, tuple[int, int, int, int]] = {}
    for native in rows:
        minute = _native_int(native, "utcTimestampInMinutes")
        low = _native_int(native, "low")
        delta_open = _native_int(native, "deltaOpen")
        delta_high = _native_int(native, "deltaHigh")
        delta_close = _native_int(native, "deltaClose")
        if (
            low <= 0
            or min(delta_open, delta_high, delta_close, minute) < 0
            or delta_open > delta_high
            or delta_close > delta_high
        ):
            raise ValueError("R90 invalid native M1 provider payload")

        observed = datetime.fromtimestamp(minute * 60, tz=UTC)
        timestamps.append(observed)
        alignment_errors += int(
            observed.second != 0
            or observed.microsecond != 0
        )
        out_of_window += int(
            not (opened_at <= observed < closed_at)
        )
        payload = (low, delta_open, delta_high, delta_close)
        prior = payload_by_timestamp.get(minute)
        if prior is not None and prior != payload:
            contradictions += 1
        payload_by_timestamp.setdefault(minute, payload)
        seen.add(minute)

    ordered = sorted(set(timestamps))
    payload_valid = (
        alignment_errors == 0
        and out_of_window == 0
        and contradictions == 0
    )
    return ProbeResult(
        canonical_symbol=canonical_symbol,
        provider_symbol=provider_symbol,
        opened_at=opened_at.isoformat(),
        closed_at=closed_at.isoformat(),
        retained_m1_bars=len(seen),
        earliest_observed_m1=(
            ordered[0].isoformat() if ordered else None
        ),
        latest_observed_m1=(
            ordered[-1].isoformat() if ordered else None
        ),
        timestamp_alignment_errors=alignment_errors,
        out_of_window_bars=out_of_window,
        contradictory_timestamps=contradictions,
        provider_payload_valid=payload_valid,
        m1_available=bool(ordered) and payload_valid,
    )


def _symbol_report(
    client: SpotwareCTraderOpenApiClient,
    *,
    canonical_symbol: str,
) -> dict[str, Any]:
    provider_symbol, symbol_id = _discover_symbol(
        client,
        canonical_symbol=canonical_symbol,
    )
    probes = tuple(
        _probe_window(
            client,
            canonical_symbol=canonical_symbol,
            provider_symbol=provider_symbol,
            symbol_id=symbol_id,
            opened_at=opened_at,
        )
        for opened_at in PROBE_OPENINGS
    )
    return {
        "canonical_symbol": canonical_symbol,
        "provider_symbol": provider_symbol,
        "provider_symbol_id": symbol_id,
        "probes": [asdict(row) for row in probes],
        "all_probe_dates_have_native_m1": all(
            row.m1_available
            for row in probes
        ),
        "earliest_probe_has_native_m1": probes[0].m1_available,
        "2018_probe_has_native_m1": probes[1].m1_available,
    }


def build_report() -> dict[str, Any]:
    client = SpotwareCTraderOpenApiClient(
        credentials=_credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(
                f"R90 cTrader DEMO authentication failed: {ready.error}"
            )
        symbols = {
            symbol: _symbol_report(
                client,
                canonical_symbol=symbol,
            )
            for symbol in PROVIDER_SYMBOLS
        }
    finally:
        client.close()

    all_2016 = all(
        bool(row["earliest_probe_has_native_m1"])
        for row in symbols.values()
    )
    all_2018 = all(
        bool(row["2018_probe_has_native_m1"])
        for row in symbols.values()
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "period": "M1_NATIVE",
        "period_proto_value": PERIOD_M1,
        "probe_openings_utc": [
            item.isoformat()
            for item in PROBE_OPENINGS
        ],
        "symbols": symbols,
        "depth_conclusion": {
            "all_three_indices_have_m1_at_2016_probe": all_2016,
            "all_three_indices_have_m1_at_2018_probe": all_2018,
            "historical_m1_supports_r66_and_5y_research": (
                all_2016 and all_2018
            ),
        },
        "decision": "R90_NATIVE_M1_DEPTH_PROBE_COMPLETE_NO_TRADES",
        "governance": {
            "provider_demo_only": True,
            "read_only": True,
            "fresh_holdout_claim": False,
            "strict_from_to_without_count": True,
            "synthetic_m1_created": False,
            "interpolated_m1_created": False,
            "pnl_evaluated": False,
            "candidate_created": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "depth_conclusion": report["depth_conclusion"],
                "symbols": {
                    key: {
                        "all_probe_dates_have_native_m1": value[
                            "all_probe_dates_have_native_m1"
                        ],
                        "probes": [
                            {
                                "opened_at": probe["opened_at"],
                                "retained_m1_bars": probe[
                                    "retained_m1_bars"
                                ],
                                "m1_available": probe["m1_available"],
                            }
                            for probe in value["probes"]
                        ],
                    }
                    for key, value in report["symbols"].items()
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
