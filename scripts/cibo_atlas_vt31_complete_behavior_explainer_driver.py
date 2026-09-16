"""Fail-closed driver for the CIBO Atlas complete behavior explainer.

Some consumed VT-31 evidence artifacts intentionally overlap calendar dates.
A market day must be counted once in Atlas. This driver deduplicates a repeated
(market, NY date) only when the provider and every M1 bar are byte-equivalent at
the semantic field level. Any mismatch fails closed.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import cibo_atlas_vt31_complete_behavior_explainer as lab
from qore.infrastructure.market_data import OhlcSnapshot


def bar_fingerprint(bar: OhlcSnapshot) -> tuple[str, ...]:
    return (
        str(bar.instrument),
        bar.opened_at.isoformat(),
        bar.closed_at.isoformat(),
        str(bar.open),
        str(bar.high),
        str(bar.low),
        str(bar.close),
    )


def series_fingerprint(bars: tuple[OhlcSnapshot, ...]) -> tuple[tuple[str, ...], ...]:
    return tuple(bar_fingerprint(bar) for bar in bars)


def safe_load_market_days(
    paths: dict[tuple[str, str], Path],
) -> tuple[dict[tuple[str, str], tuple[OhlcSnapshot, ...]], list[dict[str, Any]]]:
    bars_by_key: dict[tuple[str, str], tuple[OhlcSnapshot, ...]] = {}
    provider_by_key: dict[tuple[str, str], str] = {}
    partitions_by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
    rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    identical_overlap_events = 0

    for partition in lab.PARTITIONS:
        for market in lab.MARKETS:
            series, _, _, _, _, provider = lab.load_market_evidence(paths[(partition, market)])
            grouped: dict[object, list[OhlcSnapshot]] = defaultdict(list)
            for bar in series:
                grouped[lab._day(bar.opened_at)].append(bar)
            for local_day, bars in sorted(grouped.items()):
                key = (market, str(local_day))
                frozen = tuple(bars)
                if key in bars_by_key:
                    if provider_by_key[key] != provider:
                        raise ValueError(
                            f"overlapping consumed market day provider mismatch {key}: "
                            f"{provider_by_key[key]} != {provider}"
                        )
                    if series_fingerprint(bars_by_key[key]) != series_fingerprint(frozen):
                        raise ValueError(f"overlapping consumed market day M1 mismatch {key}")
                    partitions_by_key[key].add(partition)
                    identical_overlap_events += 1
                    continue

                bars_by_key[key] = frozen
                provider_by_key[key] = provider
                partitions_by_key[key].add(partition)
                row = lab.analyze_market_day(partition, market, provider, frozen)
                if row is not None:
                    rows_by_key[key] = row

    rows: list[dict[str, Any]] = []
    for key, row in sorted(rows_by_key.items()):
        enriched = dict(row)
        enriched["source_partitions"] = sorted(partitions_by_key[key])
        enriched["identical_consumed_overlap"] = len(partitions_by_key[key]) > 1
        rows.append(enriched)

    print(
        {
            "atlas_unique_market_days": len(rows),
            "identical_overlap_events_deduplicated": identical_overlap_events,
            "multi_partition_market_days": sum(
                len(partitions_by_key[key]) > 1 for key in rows_by_key
            ),
            "overlap_policy": "dedupe-only-if-provider-and-all-M1-bars-identical",
        }
    )
    return bars_by_key, rows


def self_test() -> None:
    assert lab.PARTITIONS == ("r5", "r6", "r8_fresh")
    print("CIBO Atlas complete behavior explainer overlap driver self-test PASS")


def main() -> None:
    self_test()
    lab.load_market_days = safe_load_market_days
    lab.main()


if __name__ == "__main__":
    main()
