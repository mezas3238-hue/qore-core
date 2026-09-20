"""VT08 Index R93 — 5Y + Recent2Y exact fractal cascade density validation.

R92 established that the exact H4->M15 + H1->M5 + M15->M1 union reaches
1,844 mechanically distinct executions in the already-consumed R66 window.

R93 validates the exact same architecture, identity and source rules on the two
other consumed development windows:
- 5Y: density must remain within the frozen 2,300-2,500 band.
- Recent2Y: density must remain >=1,000.

No PnL, target, risk, suppression, ranking or post-result tuning is allowed.
Native M1 is obtained read-only from cTrader DEMO; M15/H1 are built only from
complete provider components. Exact execution identity remains:
(symbol, continuation_at, side, entry, protected_swing).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_five_year_validation as r6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r88_nested_h1_m5_density as r88,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r90_m1_provider_depth_probe as r90,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r91_r66_m15_m1_density as r91,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r92_fractal_cascade_union as r92,
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

SCHEMA = "qore.trader_lab.vt08_index_r93_fractal_cascade_density_validation.v1"
IDENTITY = "VT08_INDEX_R93_EXACT_FRACTAL_CASCADE_DENSITY_VALIDATION_001"
SOURCE_R92_RUN_ID = 35530286516

ExecutionIdentity = tuple[str, datetime, str, object, object]


def _complete_m15_from_m5(
    raw_m5: Sequence[Vt08IndexC2R1Bar],
) -> tuple[Vt08IndexC2R1Bar, ...]:
    buckets: dict[datetime, list[Vt08IndexC2R1Bar]] = defaultdict(list)
    for bar in raw_m5:
        opened = bar.opened_at.astimezone(UTC)
        bucket = opened.replace(
            minute=(opened.minute // 15) * 15,
            second=0,
            microsecond=0,
        )
        buckets[bucket].append(bar)

    result: list[Vt08IndexC2R1Bar] = []
    for bucket, rows in sorted(buckets.items()):
        ordered = tuple(sorted(rows, key=lambda item: item.opened_at))
        expected = tuple(
            bucket + timedelta(minutes=5 * index)
            for index in range(3)
        )
        observed = tuple(
            item.opened_at.astimezone(UTC)
            for item in ordered
        )
        if observed != expected:
            continue
        result.append(
            Vt08IndexC2R1Bar(
                opened_at=bucket,
                closed_at=bucket + timedelta(minutes=15),
                open=ordered[0].open,
                high=max(item.high for item in ordered),
                low=min(item.low for item in ordered),
                close=ordered[-1].close,
            )
        )
    return tuple(result)


def _canonical_rows(
    *,
    symbol: str,
    m15: Sequence[Vt08IndexC2R1Bar],
    start_date: date,
    end_date: date,
) -> tuple[Any, ...]:
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in m15
    }
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[date, DemoTradingSetupSide | None] = {}
    rows: dict[ExecutionIdentity, Any] = {}

    for opened in h4_keys:
        local = opened.astimezone(v7._NY)
        if not (start_date <= local.date() < end_date):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local.date() not in side_cache:
            side_cache[local.date()] = v7._daily_bias(
                indexed,
                before=opened,
            )
        side = side_cache[local.date()]
        if side is None:
            continue
        for item in r6._opportunities_for_h4_fast(
            symbol=symbol,
            indexed=indexed,
            h4=h4,
            h4_keys=h4_keys,
            h4_opened_at=opened,
            side=side,
        ):
            rows.setdefault(r92._canonical_identity(item), item)

    return tuple(
        sorted(
            rows.values(),
            key=lambda item: (
                item.signal.signal_at,
                item.signal.symbol,
                item.signal.entry,
                item.signal.stop,
            ),
        )
    )


def _h1_m5_rows(
    *,
    symbol: str,
    m15: Sequence[Vt08IndexC2R1Bar],
    raw_m5: Sequence[Vt08IndexC2R1Bar],
    start_date: date,
    end_date: date,
) -> tuple[r88.NestedExecutable, ...]:
    h1, components = r88._complete_h1(raw_m5)
    h1_keys = tuple(sorted(h1))
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in m15
    }
    h4 = v6._build_h4(indexed)
    side_cache: dict[date, DemoTradingSetupSide | None] = {}
    rows: dict[ExecutionIdentity, r88.NestedExecutable] = {}

    for h4_opened in sorted(h4):
        local = h4_opened.astimezone(v7._NY)
        if not (start_date <= local.date() < end_date):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local.date() not in side_cache:
            side_cache[local.date()] = v7._daily_bias(
                indexed,
                before=h4_opened,
            )
        side = side_cache[local.date()]
        if side is None:
            continue

        for offset in range(4):
            h1_opened = (
                h4_opened.astimezone(UTC)
                + timedelta(hours=offset)
            )
            h1_bar = h1.get(h1_opened)
            m5_inside = components.get(h1_opened)
            if h1_bar is None or m5_inside is None:
                continue
            pois = r88._h1_source_pois(
                h1=h1,
                h1_keys=h1_keys,
                components=components,
                before=h1_opened,
                side=side,
            )
            if not pois:
                continue
            for row in r88._m5_source_ps(
                symbol=symbol,
                h4_opened_at=h4_opened,
                h1_opened_at=h1_opened,
                side=side,
                pois=pois,
                m5_inside_h1=m5_inside,
                h1_bar=h1_bar,
            ):
                rows.setdefault(r92._nested_identity(row), row)

    return tuple(
        sorted(
            rows.values(),
            key=lambda row: (
                row.continuation_at,
                row.symbol,
                row.protected_swing,
            ),
        )
    )


def _load_native_m1_window(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol: str,
    symbol_id: int,
    start_date: date,
    end_date: date,
) -> tuple[dict[datetime, r91.NativeM1Payload], dict[str, Any]]:
    start = (
        datetime.combine(start_date, time.min, tzinfo=v7._NY)
        - timedelta(hours=1)
    ).astimezone(UTC)
    end = datetime.combine(
        end_date,
        time.min,
        tzinfo=v7._NY,
    ).astimezone(UTC)

    rows: dict[datetime, r91.NativeM1Payload] = {}
    cursor = start
    chunks = 0
    nonempty = 0
    identical_duplicates = 0

    while cursor < end:
        closed_at = min(
            cursor + timedelta(days=r91.CHUNK_DAYS),
            end,
        )
        chunk = r91._read_chunk(
            client,
            symbol=symbol,
            symbol_id=symbol_id,
            opened_at=cursor,
            closed_at=closed_at,
            chunk_index=chunks,
        )
        nonempty += int(bool(chunk))
        for row in chunk:
            prior = rows.get(row.opened_at)
            if prior is None:
                rows[row.opened_at] = row
            elif prior.identity() == row.identity():
                identical_duplicates += 1
            else:
                raise RuntimeError(
                    f"R93 contradictory native M1 at {row.opened_at}"
                )
        cursor = closed_at
        chunks += 1

    return rows, {
        "requested_start_utc": start.isoformat(),
        "requested_end_exclusive_utc": end.isoformat(),
        "chunk_days": r91.CHUNK_DAYS,
        "chunks_requested": chunks,
        "nonempty_chunks": nonempty,
        "retained_unique_m1": len(rows),
        "identical_duplicates": identical_duplicates,
        "contradictory_m1": 0,
        "synthetic_m1": 0,
        "interpolated_m1": 0,
    }


def _m15_m1_rows(
    *,
    symbol: str,
    m15: Sequence[Vt08IndexC2R1Bar],
    raw_m1: dict[datetime, r91.NativeM1Payload],
    start_date: date,
    end_date: date,
) -> tuple[r91.M15M1Executable, ...]:
    nested_m15, components = r91._complete_m15(raw_m1)
    m15_keys = tuple(sorted(nested_m15))
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in m15
    }
    h4 = v6._build_h4(indexed)
    side_cache: dict[date, DemoTradingSetupSide | None] = {}
    rows: dict[ExecutionIdentity, r91.M15M1Executable] = {}

    for h4_opened in sorted(h4):
        local = h4_opened.astimezone(v7._NY)
        if not (start_date <= local.date() < end_date):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local.date() not in side_cache:
            side_cache[local.date()] = v7._daily_bias(
                indexed,
                before=h4_opened,
            )
        side = side_cache[local.date()]
        if side is None:
            continue

        for offset in range(16):
            m15_opened = (
                h4_opened.astimezone(UTC)
                + timedelta(minutes=15 * offset)
            )
            current = nested_m15.get(m15_opened)
            current_components = components.get(m15_opened)
            if current is None or current_components is None:
                continue
            pois = r91._m15_source_pois(
                m15=nested_m15,
                m15_keys=m15_keys,
                components=components,
                before=m15_opened,
                side=side,
            )
            if not pois:
                continue
            for row in r91._m1_executables(
                symbol=symbol,
                h4_opened_at=h4_opened,
                m15_opened_at=m15_opened,
                side=side,
                pois=pois,
                m1=current_components,
                m15_bar=current,
            ):
                rows.setdefault(r92._nested_identity(row), row)

    return tuple(
        sorted(
            rows.values(),
            key=lambda row: (
                row.continuation_at,
                row.symbol,
                row.protected_swing,
            ),
        )
    )


def build_symbol_report(
    *,
    symbol: str,
    window_id: str,
    root: Path,
) -> dict[str, Any]:
    if window_id not in {"5Y", "2Y"}:
        raise ValueError("R93 window must be 5Y or 2Y")
    start_date, end_date, _reference = r74._window_contract(window_id)

    raw_m5, m5_provenance = r88._load_raw_m5(
        root,
        symbol=symbol,
    )
    m15 = _complete_m15_from_m5(raw_m5)
    canonical = _canonical_rows(
        symbol=symbol,
        m15=m15,
        start_date=start_date,
        end_date=end_date,
    )
    h1_m5 = _h1_m5_rows(
        symbol=symbol,
        m15=m15,
        raw_m5=raw_m5,
        start_date=start_date,
        end_date=end_date,
    )

    client = SpotwareCTraderOpenApiClient(
        credentials=r90._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(
                f"R93 cTrader DEMO authentication failed: {ready.error}"
            )
        provider_symbol, symbol_id = r90._discover_symbol(
            client,
            canonical_symbol=symbol,
        )
        raw_m1, m1_provenance = _load_native_m1_window(
            client,
            symbol=symbol,
            symbol_id=symbol_id,
            start_date=start_date,
            end_date=end_date,
        )
    finally:
        client.close()

    m15_m1 = _m15_m1_rows(
        symbol=symbol,
        m15=m15,
        raw_m1=raw_m1,
        start_date=start_date,
        end_date=end_date,
    )

    canonical_set = {r92._canonical_identity(row) for row in canonical}
    h1_m5_set = {r92._nested_identity(row) for row in h1_m5}
    m15_m1_set = {r92._nested_identity(row) for row in m15_m1}
    union = canonical_set | h1_m5_set | m15_m1_set

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r92_run_id": SOURCE_R92_RUN_ID,
        "symbol": symbol,
        "provider_symbol": provider_symbol,
        "window_id": window_id,
        "start_date": start_date.isoformat(),
        "end_date_exclusive": end_date.isoformat(),
        "layer_counts": {
            "h4_m15": len(canonical_set),
            "h1_m5": len(h1_m5_set),
            "m15_m1": len(m15_m1_set),
        },
        "exact_overlap_counts": {
            "h4_m15__h1_m5": len(canonical_set & h1_m5_set),
            "h4_m15__m15_m1": len(canonical_set & m15_m1_set),
            "h1_m5__m15_m1": len(h1_m5_set & m15_m1_set),
            "all_three": len(
                canonical_set
                & h1_m5_set
                & m15_m1_set
            ),
        },
        "exact_union_count": len(union),
        "m5_provenance": m5_provenance,
        "m1_provenance": m1_provenance,
        "governance": {
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "exact_r92_architecture_reused": True,
            "exact_dedup_only": True,
            "pnl_evaluated": False,
            "risk_changed": False,
            "target_changed": False,
            "anchors_changed": False,
            "candidate_created": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", choices=tuple(contract.MARKETS), required=True)
    parser.add_argument("--window", choices=("5Y", "2Y"), required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = build_symbol_report(
        symbol=args.symbol,
        window_id=args.window,
        root=args.root,
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
                "window_id": report["window_id"],
                "layer_counts": report["layer_counts"],
                "exact_overlap_counts": report["exact_overlap_counts"],
                "exact_union_count": report["exact_union_count"],
                "decision": "R93_SYMBOL_WINDOW_EXACT_CASCADE_DENSITY_COMPLETE",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
