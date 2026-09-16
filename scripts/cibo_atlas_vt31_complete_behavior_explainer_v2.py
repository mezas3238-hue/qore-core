"""Fail-closed overlap-safe runner for the CIBO VT-31 complete explainer.

Consumed R5/R6/R8 evidence can share calendar boundary fragments because the
immutable acquisition windows are UTC while Atlas sessions are New York time.
The base explainer must not double-count those days. This adapter first rejects
any market/day that is not a complete Atlas 09:00-16:00 observation, then
deduplicates remaining overlaps only when provider and every M1 market
value/timestamp are identical. Any disagreement among complete days aborts.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import cibo_atlas_vt31_complete_behavior_explainer as base
from qore.infrastructure.market_data import OhlcSnapshot


def bar_fingerprint(bar: OhlcSnapshot) -> tuple[object, ...]:
    return (
        bar.instrument.symbol,
        bar.source.logical_values(),
        bar.timeframe.seconds,
        bar.opened_at.isoformat(),
        bar.closed_at.isoformat(),
        bar.open,
        bar.high,
        bar.low,
        bar.close,
    )


def series_fingerprint(bars: tuple[OhlcSnapshot, ...]) -> tuple[tuple[object, ...], ...]:
    return tuple(bar_fingerprint(bar) for bar in bars)


def overlap_safe_load_market_days(
    paths: dict[tuple[str, str], Path],
) -> tuple[dict[tuple[str, str], tuple[OhlcSnapshot, ...]], list[dict[str, Any]]]:
    bars_by_key: dict[tuple[str, str], tuple[OhlcSnapshot, ...]] = {}
    provider_by_key: dict[tuple[str, str], str] = {}
    partitions_by_key: dict[tuple[str, str], list[str]] = defaultdict(list)
    rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_count = 0
    incomplete_boundary_count = 0

    for partition in base.PARTITIONS:
        for market in base.MARKETS:
            series, _, _, _, _, provider = base.load_market_evidence(paths[(partition, market)])
            grouped: dict[object, list[OhlcSnapshot]] = defaultdict(list)
            for bar in series:
                grouped[base._day(bar.opened_at)].append(bar)

            for local_day, bars in sorted(grouped.items()):
                key = (market, str(local_day))
                frozen = tuple(bars)
                row = base.analyze_market_day(partition, market, provider, frozen)
                if row is None:
                    incomplete_boundary_count += 1
                    continue

                existing = bars_by_key.get(key)
                if existing is not None:
                    duplicate_count += 1
                    if provider_by_key[key] != provider:
                        raise ValueError(
                            f"complete overlap provider mismatch {key}: "
                            f"{provider_by_key[key]} != {provider}"
                        )
                    if series_fingerprint(existing) != series_fingerprint(frozen):
                        raise ValueError(f"complete overlap M1 mismatch for consumed market day {key}")
                    partitions_by_key[key].append(partition)
                    continue

                bars_by_key[key] = frozen
                provider_by_key[key] = provider
                partitions_by_key[key].append(partition)
                rows_by_key[key] = row

    rows: list[dict[str, Any]] = []
    for key, row in sorted(rows_by_key.items()):
        enriched = dict(row)
        enriched["source_partitions"] = partitions_by_key[key]
        enriched["overlap_deduplicated"] = len(partitions_by_key[key]) > 1
        rows.append(enriched)

    print(
        "CIBO overlap audit PASS: "
        f"unique_complete_market_days={len(bars_by_key)} "
        f"complete_duplicate_occurrences={duplicate_count} "
        f"incomplete_boundary_observations_excluded={incomplete_boundary_count}"
    )
    return bars_by_key, rows


def self_test() -> None:
    base.self_test()
    print("CIBO Atlas overlap-safe adapter self-test PASS")


def main() -> None:
    base.load_market_days = overlap_safe_load_market_days
    base.main()


if __name__ == "__main__":
    main()
