"""VT08 Index R14 frozen candidate — recent 2Y no-retuning replay.

Replays the exact frozen R14 candidate on:
    2024-09-15 <= New York source date < 2026-09-15

This is a robustness/reproduction replay, not a fresh certification holdout,
because this historical region was touched by earlier VT08 research.

No entry, target, POI, rearm, context-weight or rolling-governor parameter may
be changed by this module.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round1 as r1
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.trader_lab import vt08_index_r13_rolling_drawdown_governor as r13
from qore.infrastructure.trader_lab import vt08_index_r14_candidate_freeze as freeze
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r14_recent_2y_replay.v1"
IDENTITY = "VT08_INDEX_R14_ROLLING_1574_RECENT_2Y_REPLAY_001"
START_DATE = date(2024, 9, 15)
END_DATE_EXCLUSIVE = date(2026, 9, 15)
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
REFERENCE_DENSITY_MIN = 600
REFERENCE_DENSITY_MAX = 700
_NY = ZoneInfo("America/New_York")


def _load_cibo_m15_2y(
    root: Path,
    *,
    symbol: str,
) -> tuple[tuple[Vt08IndexC2R1Bar, ...], dict[str, Any]]:
    manifest = r1._read_json(r1._single(root, "symbol-consumption-manifest.json"))
    if manifest.get("identity") != r1.SOURCE_IDENTITY:
        raise ValueError(f"CIBO source identity drift for {symbol}")
    if manifest.get("canonical_symbol") != symbol:
        raise ValueError(f"CIBO canonical symbol drift for {symbol}")
    if not bool(manifest.get("read_only")):
        raise ValueError(f"CIBO source must be read-only for {symbol}")
    if bool(manifest.get("live_authorized")) or bool(
        manifest.get("real_capital_authorized")
    ):
        raise ValueError(f"CIBO source authority drift for {symbol}")

    context_start_local = datetime.combine(
        START_DATE - timedelta(days=7),
        time.min,
        tzinfo=_NY,
    )
    end_local = datetime.combine(
        END_DATE_EXCLUSIVE,
        time.min,
        tzinfo=_NY,
    )
    start_dt = context_start_local.astimezone(UTC)
    end_dt = end_local.astimezone(UTC)

    buckets: dict[datetime, list[tuple[datetime, dict[str, Any]]]] = defaultdict(list)
    retained_rows = 0
    for year in range(start_dt.year, end_dt.year + 1):
        path = root / "RAW_M5_LEDGER" / f"{year}.jsonl"
        if not path.is_file():
            raise ValueError(f"missing raw CIBO M5 partition {year} for {symbol}")
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                decoded = json.loads(line)
                if not isinstance(decoded, dict):
                    raise ValueError("raw CIBO M5 row must be an object")
                row = cast(dict[str, Any], decoded)
                if row.get("schema") != r1.RAW_SCHEMA:
                    raise ValueError(f"raw CIBO schema drift for {symbol}")
                if row.get("identity") != r1.SOURCE_IDENTITY:
                    raise ValueError(f"raw CIBO identity drift for {symbol}")
                if row.get("canonical_symbol") != symbol:
                    raise ValueError(f"raw CIBO symbol drift for {symbol}")
                opened = r1._parse_time(row.get("opened_at"))
                if opened < start_dt or opened >= end_dt:
                    continue
                if opened.minute % 5 != 0 or opened.second != 0:
                    raise ValueError(f"unaligned raw M5 timestamp for {symbol}")
                retained_rows += 1
                bucket = opened.replace(
                    minute=(opened.minute // 15) * 15,
                    second=0,
                    microsecond=0,
                )
                buckets[bucket].append((opened, row))

    bars: list[Vt08IndexC2R1Bar] = []
    bucket_sizes: dict[str, int] = {"1": 0, "2": 0, "3": 0}
    for bucket in sorted(buckets):
        entries = sorted(buckets[bucket], key=lambda item: item[0])
        if len(entries) not in (1, 2, 3):
            raise ValueError(f"unexpected M5 multiplicity in {symbol} M15 bucket")
        bucket_sizes[str(len(entries))] += 1
        rows = [item[1] for item in entries]
        opens = [r1._price(row["open_relative"]) for row in rows]
        highs = [r1._price(row["high_relative"]) for row in rows]
        lows = [r1._price(row["low_relative"]) for row in rows]
        closes = [r1._price(row["close_relative"]) for row in rows]
        bars.append(
            Vt08IndexC2R1Bar(
                opened_at=bucket,
                closed_at=bucket + timedelta(minutes=15),
                open=opens[0],
                high=max(highs),
                low=min(lows),
                close=closes[-1],
            )
        )

    if not bars:
        raise ValueError(f"no reconstructed recent 2Y M15 bars for {symbol}")

    return tuple(bars), {
        "source_run_id": r1.SOURCE_CIBO_RUN_ID,
        "source_git_sha": r1.SOURCE_CIBO_GIT_SHA,
        "source_identity": r1.SOURCE_IDENTITY,
        "reconstruction_policy": (
            "RECENT_2Y_AGGREGATE_ALL_OBSERVED_PROVIDER_M5_WITHIN_M15_NO_INTERPOLATION"
        ),
        "context_start_utc": start_dt.isoformat(),
        "end_utc_exclusive": end_dt.isoformat(),
        "raw_m5_rows_loaded": retained_rows,
        "m15_buckets": len(bars),
        "m15_bucket_size_counts": bucket_sizes,
        "synthetic_prices": 0,
        "interpolated_prices": 0,
        "first_m15": bars[0].opened_at.isoformat(),
        "last_m15": bars[-1].opened_at.isoformat(),
    }


def _opportunities_2y(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> tuple[r4.ExpandedOpportunity, ...]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[date, DemoTradingSetupSide | None] = {}
    result: list[r4.ExpandedOpportunity] = []

    for opened in h4_keys:
        local = opened.astimezone(_NY)
        local_date = local.date()
        if not (START_DATE <= local_date < END_DATE_EXCLUSIVE):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(indexed, before=opened)
        side = side_cache[local_date]
        if side is None:
            continue
        result.extend(
            r8._priority_rearm_for_h4(
                symbol=symbol,
                indexed=indexed,
                h4=h4,
                h4_keys=h4_keys,
                h4_opened_at=opened,
                side=side,
            )
        )

    result.sort(
        key=lambda item: (
            item.signal.signal_at,
            item.signal.symbol,
            item.signal.entry,
            item.signal.stop,
            item.rearm_index,
        )
    )
    return tuple(result)


def _build_stream(
    *,
    opportunities_by_symbol: dict[str, tuple[r4.ExpandedOpportunity, ...]],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[tuple[r4.ExpandedOpportunity, Any], ...]:
    selected: list[tuple[r4.ExpandedOpportunity, Any]] = []
    target = Decimal(freeze.TARGET_R)
    for symbol in ("NAS100", "SP500", "US30"):
        selected.extend(
            r8._sequential(
                opportunities_by_symbol[symbol],
                bars=bars_by_symbol[symbol],
                target=target,
            )
        )
    selected.sort(
        key=lambda item: (item[0].signal.signal_at, item[0].signal.symbol)
    )
    return tuple(selected)


def _period_breakdown(
    stream: Sequence[tuple[r4.ExpandedOpportunity, Any]],
    values: Sequence[Decimal],
) -> dict[str, Any]:
    by_year: dict[str, list[Decimal]] = defaultdict(list)
    by_quarter: dict[str, list[Decimal]] = defaultdict(list)
    for (opportunity, _outcome), value in zip(stream, values, strict=True):
        local = opportunity.signal.signal_at.astimezone(_NY)
        by_year[str(local.year)].append(value)
        quarter = (local.month - 1) // 3 + 1
        by_quarter[f"{local.year}-Q{quarter}"].append(value)

    midpoint = len(values) // 2
    return {
        "by_year": {
            key: fx._metrics(tuple(rows))
            for key, rows in sorted(by_year.items())
        },
        "by_quarter": {
            key: fx._metrics(tuple(rows))
            for key, rows in sorted(by_quarter.items())
        },
        "halves": {
            "first": fx._metrics(tuple(values[:midpoint])),
            "second": fx._metrics(tuple(values[midpoint:])),
        },
    }


def _market_breakdown(
    stream: Sequence[tuple[r4.ExpandedOpportunity, Any]],
    values: Sequence[Decimal],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for symbol in ("NAS100", "SP500", "US30"):
        subset = tuple(
            value
            for (opportunity, _outcome), value in zip(
                stream,
                values,
                strict=True,
            )
            if opportunity.signal.symbol == symbol
        )
        result[symbol] = fx._metrics(subset)
    return result


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    indexed_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]] = {}
    opportunities_by_symbol: dict[str, tuple[r4.ExpandedOpportunity, ...]] = {}
    provenance: dict[str, Any] = {}

    for symbol in ("NAS100", "SP500", "US30"):
        bars, source = _load_cibo_m15_2y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        indexed_by_symbol[symbol] = {
            bar.opened_at.astimezone(UTC): bar for bar in bars
        }
        opportunities_by_symbol[symbol] = _opportunities_2y(
            symbol=symbol,
            bars=bars,
        )
        provenance[symbol] = source

    stream = _build_stream(
        opportunities_by_symbol=opportunities_by_symbol,
        bars_by_symbol=bars_by_symbol,
    )
    contexts = tuple(
        r10._context(
            opportunity,
            indexed=indexed_by_symbol[opportunity.signal.symbol],
        )
        for opportunity, _outcome in stream
    )
    outcomes = tuple(outcome for _opportunity, outcome in stream)
    scheme = freeze.frozen_refined_scheme().as_r13()

    primary_values, primary_diag = r13._weighted_values(
        outcomes,
        contexts,
        scheme=scheme,
        stress=PRIMARY_STRESS,
    )
    secondary_values, secondary_diag = r13._weighted_values(
        outcomes,
        contexts,
        scheme=scheme,
        stress=SECONDARY_STRESS,
    )

    primary = fx._metrics(primary_values)
    secondary = fx._metrics(secondary_values)
    sample = len(stream)
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "rule_fingerprint": freeze.RULE_FINGERPRINT,
            "source_5y_run_id": freeze.SOURCE_RUN_ID,
            "source_5y_artifact_id": freeze.SOURCE_ARTIFACT_ID,
            "frozen_scheme_id": freeze.SCHEME_ID,
        },
        "window": {
            "start_date": START_DATE.isoformat(),
            "end_date_exclusive": END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_ROBUSTNESS_REPLAY",
            "fresh_certification_holdout": False,
        },
        "sample": sample,
        "reference_density_range": {
            "minimum": REFERENCE_DENSITY_MIN,
            "maximum": REFERENCE_DENSITY_MAX,
            "pass": REFERENCE_DENSITY_MIN <= sample <= REFERENCE_DENSITY_MAX,
        },
        "primary": primary,
        "secondary": secondary,
        "primary_diagnostics": primary_diag,
        "secondary_diagnostics": secondary_diag,
        "market_breakdown_primary": _market_breakdown(stream, primary_values),
        "period_breakdown_primary": _period_breakdown(stream, primary_values),
        "raw_opportunity_count_by_market": {
            symbol: len(opportunities_by_symbol[symbol])
            for symbol in ("NAS100", "SP500", "US30")
        },
        "executed_trade_count_by_market": {
            symbol: sum(
                opportunity.signal.symbol == symbol
                for opportunity, _outcome in stream
            )
            for symbol in ("NAS100", "SP500", "US30")
        },
        "rearm_trade_count": sum(
            int(opportunity.rearm_index) > 0
            for opportunity, _outcome in stream
        ),
        "provenance": provenance,
        "governance": {
            "no_retuning": True,
            "frozen_candidate_replayed": True,
            "historical_window_previously_consumed": True,
            "fresh_holdout_claim": False,
            "candidate_rules_changed": False,
            "zero_risk_allowed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
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
                "candidate": report["candidate"],
                "sample": report["sample"],
                "reference_density_range": report["reference_density_range"],
                "primary": report["primary"],
                "secondary": report["secondary"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
