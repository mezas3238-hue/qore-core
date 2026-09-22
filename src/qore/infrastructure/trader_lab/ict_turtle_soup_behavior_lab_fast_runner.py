"""Performance-only runner for ICT Turtle Soup Behavior Lab V1.

This module replaces full-history scans with indexed time windows and computes
block-bootstrap confidence intervals from per-day counts. It does not change
event ontology, reference definitions, reclaim/CISD semantics, or output schema.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.deterministic_sampling import DeterministicChooser
from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab as lab
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar, Side

_CACHE: dict[int, tuple[Sequence[Bar], tuple[datetime, ...]]] = {}


def _window(bars: Sequence[Bar], start: datetime, end: datetime) -> Sequence[Bar]:
    key = id(bars)
    cached = _CACHE.get(key)
    if cached is None or cached[0] is not bars:
        cached = (bars, tuple(item.opened_at for item in bars))
        _CACHE[key] = cached
    opens = cached[1]
    left = bisect_left(opens, start)
    right = bisect_left(opens, end)
    return bars[left:right]


def _reclaim(
    bars: Sequence[Bar],
    ref: lab.Reference,
    raid_at: datetime,
    until: datetime,
    tick: Decimal,
) -> tuple[int | None, Decimal | None]:
    for bar in _window(bars, raid_at, until):
        if bar.closed_at > until:
            continue
        reclaimed = bar.close > ref.level if ref.side is Side.LONG else bar.close < ref.level
        if reclaimed:
            minutes = int((bar.closed_at - raid_at).total_seconds() // 60)
            depth = (
                (bar.close - ref.level) / tick
                if ref.side is Side.LONG
                else (ref.level - bar.close) / tick
            )
            return minutes, depth
    return None, None


def _forward_extremes(
    bars: Sequence[Bar],
    side: Side,
    anchor: Decimal,
    start: datetime,
    minutes: int,
    tick: Decimal,
) -> tuple[Decimal, Decimal]:
    sample = _window(bars, start, start + timedelta(minutes=minutes))
    if not sample:
        return Decimal(0), Decimal(0)
    if side is Side.LONG:
        mfe = (max(item.high for item in sample) - anchor) / tick
        mae = (anchor - min(item.low for item in sample)) / tick
    else:
        mfe = (anchor - min(item.low for item in sample)) / tick
        mae = (max(item.high for item in sample) - anchor) / tick
    return max(mfe, Decimal(0)), max(mae, Decimal(0))


def _fvg_after_raid(bars: Sequence[Bar], raid_at: datetime, side: Side) -> bool:
    sample = _window(bars, raid_at, raid_at + timedelta(minutes=90))
    for index in range(2, len(sample)):
        first, third = sample[index - 2], sample[index]
        if side is Side.LONG and third.low > first.high:
            return True
        if side is Side.SHORT and third.high < first.low:
            return True
    return False


def _opposite_hit(
    bars: Sequence[Bar], side: Side, level: Decimal, start: datetime
) -> tuple[bool, int | None]:
    for bar in _window(bars, start, start + timedelta(hours=24)):
        hit = bar.high >= level if side is Side.LONG else bar.low <= level
        if hit:
            return True, int((bar.opened_at - start).total_seconds() // 60)
    return False, None


def _bootstrap_ci(events: Sequence[lab.Event], attr: str) -> tuple[float | None, float | None]:
    if not events:
        return None, None
    blocks: dict[str, tuple[int, int]] = {}
    grouped: dict[str, list[lab.Event]] = defaultdict(list)
    for event in events:
        grouped[event.raid_at.date().isoformat()].append(event)
    for day, members in grouped.items():
        blocks[day] = (
            sum(bool(getattr(item, attr)) for item in members),
            len(members),
        )
    population = list(blocks.values())
    if len(population) < 2:
        successes, total = population[0]
        value = successes / total
        return value, value
    rng = DeterministicChooser(lab.BOOTSTRAP_SEED)
    estimates: list[float] = []
    for _ in range(400):
        successes = 0
        total = 0
        for _index in population:
            block_successes, block_total = rng.choice(population)
            successes += block_successes
            total += block_total
        estimates.append(successes / total)
    estimates.sort()
    low = estimates[max(0, int(len(estimates) * 0.025) - 1)]
    high = estimates[min(len(estimates) - 1, int(len(estimates) * 0.975))]
    return low, high


def install() -> None:
    lab._reclaim = _reclaim
    lab._forward_extremes = _forward_extremes
    lab._fvg_after_raid = _fvg_after_raid
    lab._opposite_hit = _opposite_hit
    lab._bootstrap_ci = _bootstrap_ci


def main() -> None:
    parser = argparse.ArgumentParser(description="Fast QORE Turtle Soup Behavior Lab V1")
    parser.add_argument("output", type=Path)
    parser.add_argument("evidence", nargs="+", type=Path)
    parser.add_argument("--asset-class", required=True)
    parser.add_argument("--provider", default="unknown")
    parser.add_argument("--evidence-prefix", default="consumed")
    args = parser.parse_args()
    install()
    result = lab.analyze_files(
        args.evidence,
        args.output,
        asset_class=args.asset_class,
        provider=args.provider,
        evidence_prefix=args.evidence_prefix,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
