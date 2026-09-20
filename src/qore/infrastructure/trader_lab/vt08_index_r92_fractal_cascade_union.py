"""VT08 Index R92 — exact fractal cascade union on consumed R66.

R92 combines the three source-faithful execution surfaces already established:

- H4 -> M15 canonical source surface (R66/R6)
- H1 -> M5 nested source surface (R88)
- M15 -> M1 native nested source surface (R91)

All three surfaces share the same mechanical execution identity:

    (symbol, continuation_at, side, entry, protected_swing)

Therefore R92 can compute an exact set union without time tolerances, fuzzy
matching, outcome information, or arbitrary clustering.

R92 remains a no-PnL consumed-evidence census. Passing density only authorizes
the next research stage; it does not create or certify a trader.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
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
    vt08_index_r66_fresh_historical_holdout as r66,
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

SCHEMA = "qore.trader_lab.vt08_index_r92_fractal_cascade_union.v1"
IDENTITY = "VT08_INDEX_R92_R66_EXACT_FRACTAL_CASCADE_UNION_001"

SOURCE_R88_RUN_ID = 35526661105
SOURCE_R91_RUN_ID = 35528095177

ExecutionIdentity = tuple[
    str,
    datetime,
    str,
    object,
    object,
]


def _canonical_identity(item: Any) -> ExecutionIdentity:
    signal = item.signal
    return (
        signal.symbol,
        signal.signal_at.astimezone(UTC),
        signal.side.value,
        signal.entry,
        signal.stop,
    )


def _nested_identity(item: Any) -> ExecutionIdentity:
    identity = item.identity()
    return (
        str(identity[0]),
        identity[1],
        str(identity[2]),
        identity[3],
        identity[4],
    )


def _h1_m5_rows(
    *,
    symbol: str,
    cibo_m15: Sequence[Vt08IndexC2R1Bar],
    raw_m5: Sequence[Vt08IndexC2R1Bar],
) -> tuple[r88.NestedExecutable, ...]:
    h1, h1_components = r88._complete_h1(raw_m5)
    h1_keys = tuple(sorted(h1))
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in cibo_m15
    }
    h4 = v6._build_h4(indexed)
    rows: dict[ExecutionIdentity, r88.NestedExecutable] = {}
    side_cache: dict[Any, DemoTradingSetupSide | None] = {}

    for h4_opened in sorted(h4):
        local = h4_opened.astimezone(v7._NY)
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
                indexed,
                before=h4_opened,
            )
        side = side_cache[local_date]
        if side is None:
            continue

        for hour_offset in range(4):
            h1_opened = (
                h4_opened.astimezone(UTC)
                + timedelta(hours=hour_offset)
            )
            h1_bar = h1.get(h1_opened)
            m5_inside = h1_components.get(h1_opened)
            if h1_bar is None or m5_inside is None:
                continue

            pois = r88._h1_source_pois(
                h1=h1,
                h1_keys=h1_keys,
                components=h1_components,
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
                rows.setdefault(_nested_identity(row), row)

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


def _m15_m1_rows(
    *,
    symbol: str,
    cibo_m15: Sequence[Vt08IndexC2R1Bar],
    raw_m1: dict[datetime, r91.NativeM1Payload],
) -> tuple[r91.M15M1Executable, ...]:
    m15, components = r91._complete_m15(raw_m1)
    m15_keys = tuple(sorted(m15))
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in cibo_m15
    }
    h4 = v6._build_h4(indexed)
    rows: dict[ExecutionIdentity, r91.M15M1Executable] = {}
    side_cache: dict[Any, DemoTradingSetupSide | None] = {}

    for h4_opened in sorted(h4):
        local = h4_opened.astimezone(v7._NY)
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
                indexed,
                before=h4_opened,
            )
        side = side_cache[local_date]
        if side is None:
            continue

        for offset in range(16):
            m15_opened = (
                h4_opened.astimezone(UTC)
                + timedelta(minutes=15 * offset)
            )
            current = m15.get(m15_opened)
            current_components = components.get(m15_opened)
            if current is None or current_components is None:
                continue
            pois = r91._m15_source_pois(
                m15=m15,
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
                rows.setdefault(_nested_identity(row), row)

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


def _symbol_report(
    *,
    symbol: str,
    m15_root: Path,
) -> dict[str, Any]:
    cibo_m15, cibo_provenance = r66._load_cibo_m15_holdout(
        m15_root,
        symbol=symbol,
    )
    canonical = r66._build_surface(
        symbol=symbol,
        bars=cibo_m15,
    )

    raw_m5, raw_m5_provenance = r88._load_raw_m5(
        m15_root,
        symbol=symbol,
    )
    h1_m5 = _h1_m5_rows(
        symbol=symbol,
        cibo_m15=cibo_m15,
        raw_m5=raw_m5,
    )

    client = SpotwareCTraderOpenApiClient(
        credentials=r90._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(
                f"R92 cTrader DEMO authentication failed: {ready.error}"
            )
        provider_symbol, symbol_id = r90._discover_symbol(
            client,
            canonical_symbol=symbol,
        )
        raw_m1, raw_m1_provenance = r91._load_native_m1(
            client,
            symbol=symbol,
            symbol_id=symbol_id,
        )
    finally:
        client.close()

    m15_m1 = _m15_m1_rows(
        symbol=symbol,
        cibo_m15=cibo_m15,
        raw_m1=raw_m1,
    )

    canonical_set = {
        _canonical_identity(item)
        for item in canonical
    }
    h1_m5_set = {
        _nested_identity(item)
        for item in h1_m5
    }
    m15_m1_set = {
        _nested_identity(item)
        for item in m15_m1
    }
    union = canonical_set | h1_m5_set | m15_m1_set

    overlap_counts = {
        "h4_m15__h1_m5": len(canonical_set & h1_m5_set),
        "h4_m15__m15_m1": len(canonical_set & m15_m1_set),
        "h1_m5__m15_m1": len(h1_m5_set & m15_m1_set),
        "all_three": len(
            canonical_set
            & h1_m5_set
            & m15_m1_set
        ),
    }
    unique_by_layer = {
        "h4_m15_only": len(
            canonical_set
            - h1_m5_set
            - m15_m1_set
        ),
        "h1_m5_only": len(
            h1_m5_set
            - canonical_set
            - m15_m1_set
        ),
        "m15_m1_only": len(
            m15_m1_set
            - canonical_set
            - h1_m5_set
        ),
    }

    by_anchor: Counter[str] = Counter()
    for item in union:
        continuation = item[1]
        by_anchor[str(continuation.astimezone(v7._NY).hour)] += 1

    return {
        "symbol": symbol,
        "provider_symbol": provider_symbol,
        "layer_counts": {
            "h4_m15": len(canonical_set),
            "h1_m5": len(h1_m5_set),
            "m15_m1": len(m15_m1_set),
        },
        "exact_overlap_counts": overlap_counts,
        "exclusive_counts": unique_by_layer,
        "exact_union_count": len(union),
        "union_by_continuation_hour_ny": dict(sorted(by_anchor.items())),
        "cibo_m15_provenance": cibo_provenance,
        "raw_m5_provenance": raw_m5_provenance,
        "raw_m1_provenance": raw_m1_provenance,
    }


def build_report(
    *,
    symbol: str,
    m15_root: Path,
) -> dict[str, Any]:
    if symbol not in contract.MARKETS:
        raise ValueError(f"R92 symbol outside VT08 Index scope: {symbol}")
    if r88.IDENTITY != (
        "VT08_INDEX_R88_NESTED_H1_M5_SOURCE_DENSITY_CENSUS_001"
    ):
        raise ValueError("R92 R88 identity drift")
    if r91.IDENTITY != (
        "VT08_INDEX_R91_R66_NATIVE_M1_M15_M1_DENSITY_CENSUS_001"
    ):
        raise ValueError("R92 R91 identity drift")
    if 14 in r4.V7_ANCHORS or 18 in r4.V7_ANCHORS:
        raise ValueError("R92 executable anchor contract drift")

    result = _symbol_report(
        symbol=symbol,
        m15_root=m15_root,
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_runs": {
            "r88": SOURCE_R88_RUN_ID,
            "r91": SOURCE_R91_RUN_ID,
        },
        "window": {
            "id": "R66_CONSUMED",
            "start_date": r66.START_DATE.isoformat(),
            "end_date_exclusive": r66.END_DATE_EXCLUSIVE.isoformat(),
            "fresh_holdout_claim": False,
        },
        "exact_identity_contract": [
            "symbol",
            "continuation_at_utc",
            "side",
            "entry",
            "protected_swing",
        ],
        "market": result,
        "decision": "R92_SYMBOL_EXACT_FRACTAL_UNION_COMPLETE_NO_PNL",
        "governance": {
            "consumed_r66_only": True,
            "exact_dedup_only": True,
            "fuzzy_time_tolerance_used": False,
            "outcome_information_used": False,
            "pnl_evaluated": False,
            "target_changed": False,
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
        choices=tuple(contract.MARKETS),
        required=True,
    )
    parser.add_argument("--m15-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
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
                "symbol": args.symbol,
                "layer_counts": report["market"]["layer_counts"],
                "exact_overlap_counts": report["market"][
                    "exact_overlap_counts"
                ],
                "exact_union_count": report["market"][
                    "exact_union_count"
                ],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
