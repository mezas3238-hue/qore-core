"""VT08 Index R91 — R66 native-M1 M15->M1 source density census.

R90 proved that provider-native M1 exists for NAS100/SP500/US30 at both the
2016 and 2018 historical probes. R91 consumes that native M1 read-only over the
already-consumed R66 window and evaluates the next source fractal only:

    frozen V7 daily bias -> M15 source structure -> M1 source-exact
    Protected Swing -> M1 continuation -> M15 wick/body transition.

The higher-timeframe bias and authorized H4 windows remain the existing CIBO
M15/V7 evidence. M1 is never synthesized or interpolated. A current M15 is
eligible only when all fifteen provider M1 bars exist. The prior three M15
source bars used for FVG/relevant-swing/CISD POIs are likewise built only from
complete fifteen-of-fifteen native M1 components.

This is an R66 consumed-evidence density census only. No PnL, target, risk or
candidate is attached.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_tuning_round1 as r1,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r84_source_exact_ps_event_census as r84,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r90_m1_provider_depth_probe as r90,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)
from qore.kernel.result import Failure

SCHEMA = "qore.trader_lab.vt08_index_r91_r66_m15_m1_density.v1"
IDENTITY = "VT08_INDEX_R91_R66_NATIVE_M1_M15_M1_DENSITY_CENSUS_001"

SOURCE_R90_RUN_ID = 35527759264
SOURCE_R90_ARTIFACT_ID = 10609363779
SOURCE_R90_ARTIFACT_DIGEST = (
    "sha256:a75a8c06b4aa8a62f48b5144d8de536747e0ec22ce915f01404dbfb85ca0db5c"
)

PERIOD_M1 = 1
CHUNK_DAYS = 2
MAX_CALENDAR_M1_PER_CHUNK = CHUNK_DAYS * 24 * 60
_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class NativeM1Payload:
    opened_at: datetime
    low_relative: int
    delta_open: int
    delta_high: int
    delta_close: int

    def identity(self) -> tuple[int, int, int, int]:
        return (
            self.low_relative,
            self.delta_open,
            self.delta_high,
            self.delta_close,
        )


@dataclass(frozen=True, slots=True)
class M15M1Executable:
    symbol: str
    h4_opened_at: datetime
    m15_opened_at: datetime
    side: DemoTradingSetupSide
    source_poi_kind: str
    family: str
    protected_swing: Decimal
    ps_confirmed_at: datetime
    continuation_at: datetime
    entry: Decimal

    def identity(self) -> tuple[object, ...]:
        return (
            self.symbol,
            self.continuation_at.astimezone(UTC),
            self.side.value,
            self.entry,
            self.protected_swing,
        )


def _native_payload(native: object) -> NativeM1Payload:
    minute = r90._native_int(native, "utcTimestampInMinutes")
    low = r90._native_int(native, "low")
    delta_open = r90._native_int(native, "deltaOpen")
    delta_high = r90._native_int(native, "deltaHigh")
    delta_close = r90._native_int(native, "deltaClose")
    if (
        low <= 0
        or min(delta_open, delta_high, delta_close, minute) < 0
        or delta_open > delta_high
        or delta_close > delta_high
    ):
        raise ValueError("R91 invalid provider-native M1 payload")
    return NativeM1Payload(
        opened_at=datetime.fromtimestamp(minute * 60, tz=UTC),
        low_relative=low,
        delta_open=delta_open,
        delta_high=delta_high,
        delta_close=delta_close,
    )


def _read_chunk(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol: str,
    symbol_id: int,
    opened_at: datetime,
    closed_at: datetime,
    chunk_index: int,
) -> tuple[NativeM1Payload, ...]:
    response = client.request(
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "period": PERIOD_M1,
            "symbolId": symbol_id,
            "toTimestamp": int(closed_at.timestamp() * 1000) - 1,
        },
        client_msg_id=f"r91-m1:{symbol}:{chunk_index}",
        timeout_seconds=60.0,
    )
    if isinstance(response, Failure):
        raise RuntimeError(
            f"R91 native M1 request failed for {symbol}: {response.error}"
        )
    native = tuple(
        cast(Iterable[object], getattr(response.value, "trendbar", ()))
    )
    if len(native) > MAX_CALENDAR_M1_PER_CHUNK:
        raise RuntimeError(
            "R91 provider returned more M1 bars than calendar grid allows"
        )
    rows = tuple(_native_payload(item) for item in native)
    if any(
        not (opened_at <= row.opened_at < closed_at)
        for row in rows
    ):
        raise RuntimeError("R91 provider returned out-of-window M1")
    return rows


def _load_native_m1(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol: str,
    symbol_id: int,
) -> tuple[dict[datetime, NativeM1Payload], dict[str, Any]]:
    start_local = datetime.combine(
        r66.START_DATE,
        time.min,
        tzinfo=_NY,
    ) - timedelta(hours=1)
    end_local = datetime.combine(
        r66.END_DATE_EXCLUSIVE,
        time.min,
        tzinfo=_NY,
    )
    start = start_local.astimezone(UTC)
    end = end_local.astimezone(UTC)

    rows: dict[datetime, NativeM1Payload] = {}
    identical_duplicates = 0
    cursor = start
    chunk_index = 0
    nonempty_chunks = 0
    while cursor < end:
        closed_at = min(
            cursor + timedelta(days=CHUNK_DAYS),
            end,
        )
        chunk = _read_chunk(
            client,
            symbol=symbol,
            symbol_id=symbol_id,
            opened_at=cursor,
            closed_at=closed_at,
            chunk_index=chunk_index,
        )
        nonempty_chunks += int(bool(chunk))
        for row in chunk:
            prior = rows.get(row.opened_at)
            if prior is None:
                rows[row.opened_at] = row
            elif prior.identity() == row.identity():
                identical_duplicates += 1
            else:
                raise RuntimeError(
                    f"R91 contradictory M1 payload at {row.opened_at}"
                )
        cursor = closed_at
        chunk_index += 1

    return rows, {
        "requested_start_utc": start.isoformat(),
        "requested_end_exclusive_utc": end.isoformat(),
        "chunk_days": CHUNK_DAYS,
        "chunks_requested": chunk_index,
        "nonempty_chunks": nonempty_chunks,
        "retained_unique_m1": len(rows),
        "identical_duplicates": identical_duplicates,
        "contradictory_m1": 0,
        "out_of_window_m1": 0,
        "synthetic_m1": 0,
        "interpolated_m1": 0,
    }


def _minute_bar(row: NativeM1Payload) -> Vt08IndexC2R1Bar:
    low = row.low_relative
    return Vt08IndexC2R1Bar(
        opened_at=row.opened_at,
        closed_at=row.opened_at + timedelta(minutes=1),
        open=r1._price(low + row.delta_open),
        high=r1._price(low + row.delta_high),
        low=r1._price(low),
        close=r1._price(low + row.delta_close),
    )


def _complete_m15(
    raw: dict[datetime, NativeM1Payload],
) -> tuple[
    dict[datetime, Vt08IndexC2R1Bar],
    dict[datetime, tuple[Vt08IndexC2R1Bar, ...]],
]:
    buckets: dict[datetime, list[NativeM1Payload]] = defaultdict(list)
    for opened, row in raw.items():
        bucket = opened.replace(
            minute=(opened.minute // 15) * 15,
            second=0,
            microsecond=0,
        )
        buckets[bucket].append(row)

    aggregated: dict[datetime, Vt08IndexC2R1Bar] = {}
    components: dict[datetime, tuple[Vt08IndexC2R1Bar, ...]] = {}
    for bucket, rows in sorted(buckets.items()):
        by_open = {row.opened_at: row for row in rows}
        expected = tuple(
            bucket + timedelta(minutes=index)
            for index in range(15)
        )
        if any(moment not in by_open for moment in expected):
            continue
        bars = tuple(
            _minute_bar(by_open[moment])
            for moment in expected
        )
        aggregated[bucket] = Vt08IndexC2R1Bar(
            opened_at=bucket,
            closed_at=bucket + timedelta(minutes=15),
            open=bars[0].open,
            high=max(bar.high for bar in bars),
            low=min(bar.low for bar in bars),
            close=bars[-1].close,
        )
        components[bucket] = bars
    return aggregated, components


def _m15_source_pois(
    *,
    m15: dict[datetime, Vt08IndexC2R1Bar],
    m15_keys: tuple[datetime, ...],
    components: dict[datetime, tuple[Vt08IndexC2R1Bar, ...]],
    before: datetime,
    side: DemoTradingSetupSide,
) -> tuple[v6.SourcePoi, ...]:
    stop = bisect_left(m15_keys, before.astimezone(UTC))
    keys = m15_keys[max(0, stop - 3) : stop]
    if len(keys) < 3:
        return ()
    a, b, c = (m15[key] for key in keys)
    result: list[v6.SourcePoi] = []

    if side is DemoTradingSetupSide.LONG and a.high < c.low:
        result.append(
            v6.SourcePoi(v6.PoiKind.FVG, a.high, c.low, c.closed_at)
        )
    if side is DemoTradingSetupSide.SHORT and a.low > c.high:
        result.append(
            v6.SourcePoi(v6.PoiKind.FVG, c.high, a.low, c.closed_at)
        )

    if side is DemoTradingSetupSide.LONG and b.low < a.low and b.low < c.low:
        result.append(
            v6.SourcePoi(
                v6.PoiKind.RELEVANT_SWING,
                b.low,
                b.low,
                c.closed_at,
            )
        )
    if side is DemoTradingSetupSide.SHORT and b.high > a.high and b.high > c.high:
        result.append(
            v6.SourcePoi(
                v6.PoiKind.RELEVANT_SWING,
                b.high,
                b.high,
                c.closed_at,
            )
        )

    cisd = v6._last_cisd_poi(
        components[keys[-1]],
        side=side,
    )
    if cisd is not None:
        result.append(cisd)

    priority = {
        v6.PoiKind.FVG: 0,
        v6.PoiKind.RELEVANT_SWING: 1,
        v6.PoiKind.CISD: 2,
    }
    unique: dict[tuple[object, ...], v6.SourcePoi] = {}
    for poi in sorted(
        result,
        key=lambda item: (
            priority[item.kind],
            item.observed_at.astimezone(UTC),
            item.low,
            item.high,
        ),
    ):
        unique.setdefault(
            (
                poi.kind.value,
                poi.low,
                poi.high,
                poi.observed_at.astimezone(UTC),
            ),
            poi,
        )
    return tuple(unique.values())


def _m1_executables(
    *,
    symbol: str,
    h4_opened_at: datetime,
    m15_opened_at: datetime,
    side: DemoTradingSetupSide,
    pois: Sequence[v6.SourcePoi],
    m1: Sequence[Vt08IndexC2R1Bar],
    m15_bar: Vt08IndexC2R1Bar,
) -> tuple[M15M1Executable, ...]:
    swings = r84._short_term_swings(m1, side=side)
    series_rows = r84._confirmed_opposing_series(m1, side=side)
    result: dict[tuple[object, ...], M15M1Executable] = {}

    for poi in pois:
        touches = r4._touch_indices(m1, poi, start_index=0)
        for touch_index in touches:
            for series in series_rows:
                if series.confirm_index <= touch_index:
                    continue
                liquidity = r84._swept_known_short_term_liquidity(
                    swings,
                    series=series,
                    side=side,
                    touch_index=touch_index,
                )
                fvg = r84._original_fvg_reaction(
                    m1,
                    poi=poi,
                    series=series,
                    touch_index=touch_index,
                )
                family = r84._event_family(
                    liquidity=liquidity,
                    fvg=fvg,
                )
                if family is None:
                    continue

                continuation_index = v6._first_continuation(
                    m1,
                    side=side,
                    start_index=series.confirm_index + 1,
                    protected_swing=series.extreme,
                )
                if continuation_index is None:
                    continue
                continuation = m1[continuation_index]
                entry = continuation.close
                in_body = (
                    entry > m15_bar.open
                    if side is DemoTradingSetupSide.LONG
                    else entry < m15_bar.open
                )
                if not in_body:
                    continue
                risk = (
                    entry - series.extreme
                    if side is DemoTradingSetupSide.LONG
                    else series.extreme - entry
                )
                if risk <= 0:
                    continue

                row = M15M1Executable(
                    symbol=symbol,
                    h4_opened_at=h4_opened_at,
                    m15_opened_at=m15_opened_at,
                    side=side,
                    source_poi_kind=poi.kind.value,
                    family=family,
                    protected_swing=series.extreme,
                    ps_confirmed_at=m1[
                        series.confirm_index
                    ].closed_at.astimezone(UTC),
                    continuation_at=continuation.closed_at.astimezone(UTC),
                    entry=entry,
                )
                result.setdefault(row.identity(), row)

    return tuple(
        sorted(
            result.values(),
            key=lambda row: (
                row.continuation_at,
                row.protected_swing,
            ),
        )
    )


def build_symbol_report(
    *,
    symbol: str,
    m15_root: Path,
) -> dict[str, Any]:
    if symbol not in r90.PROVIDER_SYMBOLS:
        raise ValueError(f"R91 unsupported index: {symbol}")
    if 14 in r4.V7_ANCHORS or 18 in r4.V7_ANCHORS:
        raise ValueError("R91 executable anchor contract drift")

    cibo_m15, cibo_provenance = r66._load_cibo_m15_holdout(
        m15_root,
        symbol=symbol,
    )
    cibo_indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in cibo_m15
    }
    h4 = v6._build_h4(cibo_indexed)
    h4_keys = tuple(sorted(h4))

    client = SpotwareCTraderOpenApiClient(
        credentials=r90._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(
                f"R91 cTrader DEMO authentication failed: {ready.error}"
            )
        provider_symbol, symbol_id = r90._discover_symbol(
            client,
            canonical_symbol=symbol,
        )
        raw_m1, m1_provenance = _load_native_m1(
            client,
            symbol=symbol,
            symbol_id=symbol_id,
        )
    finally:
        client.close()

    m15, components = _complete_m15(raw_m1)
    m15_keys = tuple(sorted(m15))
    rows: dict[tuple[object, ...], M15M1Executable] = {}
    by_family: Counter[str] = Counter()
    by_poi: Counter[str] = Counter()
    by_anchor: Counter[str] = Counter()
    side_cache: dict[Any, DemoTradingSetupSide | None] = {}

    authorized_h4 = 0
    m15_slots_examined = 0
    complete_current_m15 = 0
    m15_with_source_poi = 0
    m15_with_executable = 0

    for h4_opened in h4_keys:
        local = h4_opened.astimezone(_NY)
        local_date = local.date()
        if not (
            r66.START_DATE
            <= local_date
            < r66.END_DATE_EXCLUSIVE
        ):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(
                cibo_indexed,
                before=h4_opened,
            )
        side = side_cache[local_date]
        if side is None:
            continue

        authorized_h4 += 1
        for offset in range(16):
            m15_opened = (
                h4_opened.astimezone(UTC)
                + timedelta(minutes=15 * offset)
            )
            m15_slots_examined += 1
            current = m15.get(m15_opened)
            current_components = components.get(m15_opened)
            if current is None or current_components is None:
                continue
            complete_current_m15 += 1

            pois = _m15_source_pois(
                m15=m15,
                m15_keys=m15_keys,
                components=components,
                before=m15_opened,
                side=side,
            )
            if not pois:
                continue
            m15_with_source_poi += 1

            executable = _m1_executables(
                symbol=symbol,
                h4_opened_at=h4_opened,
                m15_opened_at=m15_opened,
                side=side,
                pois=pois,
                m1=current_components,
                m15_bar=current,
            )
            if not executable:
                continue
            m15_with_executable += 1
            for row in executable:
                rows.setdefault(row.identity(), row)

    ordered = tuple(
        sorted(
            rows.values(),
            key=lambda row: (
                row.continuation_at,
                row.symbol,
                row.protected_swing,
            ),
        )
    )
    grouped: dict[datetime, list[M15M1Executable]] = defaultdict(list)
    for row in ordered:
        grouped[row.h4_opened_at.astimezone(UTC)].append(row)
        by_family[row.family] += 1
        by_poi[row.source_poi_kind] += 1
        by_anchor[
            str(row.h4_opened_at.astimezone(_NY).hour)
        ] += 1

    first = sum(bool(group) for group in grouped.values())
    additional = sum(
        max(0, len(group) - 1)
        for group in grouped.values()
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "symbol": symbol,
        "provider_symbol": provider_symbol,
        "source_r90": {
            "run_id": SOURCE_R90_RUN_ID,
            "artifact_id": SOURCE_R90_ARTIFACT_ID,
            "artifact_digest": SOURCE_R90_ARTIFACT_DIGEST,
        },
        "window": {
            "id": "R66_CONSUMED",
            "start_date": r66.START_DATE.isoformat(),
            "end_date_exclusive": r66.END_DATE_EXCLUSIVE.isoformat(),
            "fresh_holdout_claim": False,
        },
        "source_contract": {
            "higher_bias": "V7_DAILY_BIAS_FROM_CIBO_M15",
            "authorized_h4_windows_ny": list(r4.V7_ANCHORS),
            "owner_disabled_14_preserved": True,
            "context_only_18_preserved": True,
            "nested_structure_timeframe": "M15",
            "nested_entry_timeframe": "M1_NATIVE",
            "m15_requires_15_of_15_native_m1": True,
            "m15_poi_hierarchy": [
                "fvg",
                "relevant-swing",
                "cisd",
            ],
            "m15_relevant_swing_window": 3,
            "m1_ps_families": [
                r84.FAMILY_LIQUIDITY,
                r84.FAMILY_FVG,
                r84.FAMILY_BOTH,
            ],
            "m1_continuation": "EXACT_V6_FIRST_CONTINUATION",
            "m15_wick_body_transition_required": True,
        },
        "counts": {
            "authorized_h4_with_bias": authorized_h4,
            "m15_slots_examined": m15_slots_examined,
            "complete_current_m15": complete_current_m15,
            "m15_with_source_poi": m15_with_source_poi,
            "m15_with_m1_executable": m15_with_executable,
            "deduplicated_m15_m1_executables": len(ordered),
            "first_executables_per_h4": first,
            "additional_executables_same_h4": additional,
        },
        "by_family": dict(sorted(by_family.items())),
        "by_source_poi": dict(sorted(by_poi.items())),
        "by_anchor": dict(sorted(by_anchor.items())),
        "native_m1_provenance": m1_provenance,
        "cibo_m15_provenance": cibo_provenance,
        "governance": {
            "forensics_only": True,
            "consumed_r66_only": True,
            "provider_demo_only": True,
            "read_only": True,
            "native_m1_only": True,
            "synthetic_m1_created": False,
            "interpolated_m1_created": False,
            "future_information_used": False,
            "pnl_evaluated": False,
            "target_attached": False,
            "risk_changed": False,
            "candidate_created": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--symbol",
        choices=tuple(r90.PROVIDER_SYMBOLS),
        required=True,
    )
    parser.add_argument("--m15-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_symbol_report(
        symbol=args.symbol,
        m15_root=args.m15_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "symbol": report["symbol"],
                "counts": report["counts"],
                "decision": "R91_SYMBOL_NATIVE_M1_DENSITY_CENSUS_COMPLETE",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
