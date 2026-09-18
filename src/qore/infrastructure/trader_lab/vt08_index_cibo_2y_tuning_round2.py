"""VT08 Index CIBO 2Y tuning lab — Round 2 provider-available M15.

Round 2 keeps the Round-1 frozen V7 mechanics and search space, but tests a
more faithful aggregation of the raw CIBO M5 provider stream: an M15 bar is
formed from every observed M5 bar inside its quarter-hour bucket. No missing
price is interpolated and no synthetic OHLC is invented.

This is still consumed tuning evidence, not certification.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round1 as r1
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_cibo_2y_tuning_round2.v1"
IDENTITY = "VT08_INDEX_CIBO_2Y_TUNING_ROUND2_PROVIDER_AVAILABLE_M15"


def _load_cibo_m15_available(
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

    start_dt = datetime.combine(r1.START_DATE, datetime.min.time(), tzinfo=UTC)
    end_dt = datetime.combine(r1.END_DATE_EXCLUSIVE, datetime.min.time(), tzinfo=UTC)
    buckets: dict[datetime, list[tuple[datetime, dict[str, Any]]]] = defaultdict(list)
    retained_rows = 0
    for year in (2016, 2017, 2018):
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
        raise ValueError(f"no reconstructed M15 bars for {symbol}")
    return tuple(bars), {
        "source_run_id": r1.SOURCE_CIBO_RUN_ID,
        "source_git_sha": r1.SOURCE_CIBO_GIT_SHA,
        "source_identity": r1.SOURCE_IDENTITY,
        "reconstruction_policy": (
            "AGGREGATE_ALL_OBSERVED_PROVIDER_M5_WITHIN_M15_NO_INTERPOLATION"
        ),
        "raw_m5_rows_in_window": retained_rows,
        "m15_buckets": len(bars),
        "m15_bucket_size_counts": bucket_sizes,
        "partial_m15_buckets": bucket_sizes["1"] + bucket_sizes["2"],
        "synthetic_prices": 0,
        "interpolated_prices": 0,
        "first_m15": bars[0].opened_at.isoformat(),
        "last_m15": bars[-1].opened_at.isoformat(),
    }


def _benchmark(
    rows: Sequence[r1.TradeSurfaceRow],
    *,
    name: str,
    targets: dict[str, str | None],
    anchors: tuple[int, ...] = (2, 6, 10),
    sides: tuple[str, ...] = ("long", "short"),
) -> dict[str, Any]:
    result = r1._candidate_report(
        rows,
        targets=targets,
        anchors=anchors,
        sides=sides,
    )
    result["benchmark_name"] = name
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
    provenance: dict[str, Any] = {}
    market_diagnostics: dict[str, Any] = {}
    all_rows: list[r1.TradeSurfaceRow] = []
    for symbol in r1.SYMBOLS:
        bars, source = _load_cibo_m15_available(roots[symbol], symbol=symbol)
        rows, diagnostics = r1._surface_rows(symbol=symbol, bars=bars)
        provenance[symbol] = source
        market_diagnostics[symbol] = diagnostics
        all_rows.extend(rows)
    all_rows.sort(key=lambda row: (row.signal_at, row.symbol))

    candidates: list[dict[str, Any]] = []
    for targets in r1._target_maps():
        for anchors in r1._anchor_sets():
            for sides in r1._side_sets():
                report = r1._candidate_report(
                    all_rows,
                    targets=targets,
                    anchors=anchors,
                    sides=sides,
                )
                sample = int(cast(dict[str, Any], report["primary_stress"])["sample"])
                if sample < 100:
                    continue
                candidates.append(report)
    candidates.sort(key=r1._sort_key, reverse=True)

    high_activity = [
        candidate
        for candidate in candidates
        if int(cast(dict[str, Any], candidate["primary_stress"])["sample"]) >= 400
    ]
    stable_high_activity = [
        candidate
        for candidate in high_activity
        if int(candidate["positive_halves"]) == 2
        and int(candidate["positive_quarters"]) >= 6
    ]
    goal = [
        candidate
        for candidate in stable_high_activity
        if Decimal(
            str(cast(dict[str, Any], candidate["primary_stress"])["profit_factor"])
        )
        >= Decimal("1.15")
        and Decimal(
            str(cast(dict[str, Any], candidate["primary_stress"])["max_drawdown_r"])
        )
        <= Decimal("12")
    ]

    all_15: dict[str, str | None] = {symbol: "1.5" for symbol in r1.SYMBOLS}
    all_20: dict[str, str | None] = {symbol: "2.0" for symbol in r1.SYMBOLS}
    nas_us_15: dict[str, str | None] = {
        "NAS100": "1.5",
        "SP500": None,
        "US30": "1.5",
    }
    benchmarks = [
        _benchmark(
            all_rows,
            name="V7_ALL_MARKETS_TARGET_2R_ALL_ANCHORS_BOTH_SIDES",
            targets=all_20,
        ),
        _benchmark(
            all_rows,
            name="ALL_MARKETS_TARGET_1_5R_ALL_ANCHORS_BOTH_SIDES",
            targets=all_15,
        ),
        _benchmark(
            all_rows,
            name="ALL_MARKETS_TARGET_1_5R_ANCHORS_6_10_BOTH_SIDES",
            targets=all_15,
            anchors=(6, 10),
        ),
        _benchmark(
            all_rows,
            name="ALL_MARKETS_TARGET_1_5R_ANCHORS_6_10_LONG",
            targets=all_15,
            anchors=(6, 10),
            sides=("long",),
        ),
        _benchmark(
            all_rows,
            name="NAS_US_TARGET_1_5R_ANCHORS_6_10_LONG",
            targets=nas_us_15,
            anchors=(6, 10),
            sides=("long",),
        ),
    ]

    best = goal[0] if goal else (
        stable_high_activity[0]
        if stable_high_activity
        else (high_activity[0] if high_activity else (candidates[0] if candidates else None))
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window": {
            "window_id": r1.WINDOW_ID,
            "start_date": r1.START_DATE.isoformat(),
            "end_date_exclusive": r1.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_TUNING",
            "fresh_certification_holdout": False,
        },
        "strategy": {
            "base_candidate_id": v7.CANDIDATE_ID,
            "base_rule_fingerprint": v7.RULE_FINGERPRINT,
            "v7_setup_identity_changed": False,
            "stop_changed": False,
            "lifecycle_changed": False,
            "market_data_reconstruction_changed": True,
        },
        "reconstruction": {
            "policy": "PROVIDER_AVAILABLE_M15_NO_INTERPOLATION",
            "synthetic_prices": False,
            "interpolation": False,
        },
        "provenance": provenance,
        "market_diagnostics": market_diagnostics,
        "surface_trade_count": len(all_rows),
        "candidate_count": len(candidates),
        "high_activity_candidate_count": len(high_activity),
        "stable_high_activity_candidate_count": len(stable_high_activity),
        "goal_candidate_count": len(goal),
        "best_candidate": best,
        "benchmarks": benchmarks,
        "top_25": candidates[:25],
        "governance": {
            "research_only": True,
            "tuning_window_consumed": True,
            "fresh_holdout_claim": False,
            "rule_promotion_automatic": False,
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
    best = cast(dict[str, Any] | None, report["best_candidate"])
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "surface_trade_count": report["surface_trade_count"],
                "high_activity_candidate_count": report["high_activity_candidate_count"],
                "stable_high_activity_candidate_count": report[
                    "stable_high_activity_candidate_count"
                ],
                "goal_candidate_count": report["goal_candidate_count"],
                "best_candidate_id": best["candidate_id"] if best else None,
                "best_primary": best["primary_stress"] if best else None,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
