"""CIBO Target Destination V2 over consumed Journey evidence.

This research-only layer expands the single opposite-source-boundary study into
a bounded, explicit candidate universe known at causal departure time:

- the episode's opposite source boundary;
- the previous completed candle's directional boundary on H1/H4/D1;
- the latest active completed three-candle swing boundary on H1/H4/D1.

A candidate must still be directionally ahead of departure price and must not
have been touched before departure. No post-departure information participates
in candidate selection. Outcome touch order is retained at M5 resolution; two
objectives touched in the same M5 bar remain tied rather than being ordered by
assumption. This is not a claim of complete ICT/DOL coverage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import cibo_market_atlas_journey_extractor_v1 as journey
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Side,
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "CIBO_TARGET_DESTINATION_V2_SUPPORTED_REFERENCE_UNIVERSE"
SOURCE_JOURNEY_IDENTITY = journey.IDENTITY
SOURCE_JOURNEY_RUN_ID = 35175979474
SOURCE_JOURNEY_GIT_SHA = "9cc0f17a2f30846d61b242132547f39391909656"
SOURCE_M5_RUN_ID = journey.SOURCE_RUN_ID
SOURCE_M5_GIT_SHA = journey.SOURCE_GIT_SHA
CANDIDATE_UNIVERSE = "SUPPORTED_REFERENCE_FAMILY_V2_BOUNDED"
TARGET_SCHEMA = "qore.cibo_market_atlas.target_destination.v2"
EPISODE_SCHEMA = "qore.cibo_market_atlas.target_destination_episode.v2"
MANIFEST_SCHEMA = "qore.cibo_market_atlas.target_destination_manifest.v2"


@dataclass(frozen=True, slots=True)
class SwingCandidate:
    timeframe: str
    kind: str
    level: Decimal
    pivot_opened_at: datetime
    known_at: datetime
    touch_at: datetime | None


@dataclass(frozen=True, slots=True)
class Candidate:
    kind: str
    timeframe: str
    level: Decimal
    structural_opened_at: datetime
    known_at: datetime


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _side(value: str) -> Side:
    return Side.LONG if value == Side.LONG.value else Side.SHORT


def _tick_size(digits: int) -> Decimal:
    return Decimal(1).scaleb(-digits)


def _directional_level(candle: SourceCandle, side: Side) -> Decimal:
    return candle.high if side is Side.LONG else candle.low


def _ahead(level: Decimal, anchor: Decimal, side: Side) -> bool:
    return level > anchor if side is Side.LONG else level < anchor


def _touched(bar: Bar, level: Decimal, side: Side) -> bool:
    return bar.high >= level if side is Side.LONG else bar.low <= level


def _first_touch(
    bars: Sequence[Bar],
    opens: Sequence[datetime],
    *,
    level: Decimal,
    side: Side,
    start: datetime,
    end: datetime,
) -> Bar | None:
    left = bisect_left(opens, start)
    right = bisect_left(opens, end)
    for bar in bars[left:right]:
        if _touched(bar, level, side):
            return bar
    return None


def _departure_anchor(
    bars: Sequence[Bar], opens: Sequence[datetime], departure: datetime
) -> Decimal | None:
    index = bisect_left(opens, departure) - 1
    if index < 0:
        return None
    bar = bars[index]
    if bar.closed_at != departure:
        return None
    return bar.close


def _containing_frame_index(
    candles: Sequence[SourceCandle], opens: Sequence[datetime], moment: datetime
) -> int | None:
    index = bisect_right(opens, moment) - 1
    if index < 0:
        return None
    candle = candles[index]
    if candle.opened_at <= moment < candle.closed_at:
        return index
    if index + 1 < len(candles) and candles[index + 1].opened_at == moment:
        return index + 1
    return None


def _next_high_touch_indices(candles: Sequence[SourceCandle]) -> list[int | None]:
    result: list[int | None] = [None] * len(candles)
    stack: list[int] = []
    for index in range(len(candles) - 1, -1, -1):
        while stack and candles[stack[-1]].high < candles[index].high:
            stack.pop()
        result[index] = None if not stack else stack[-1]
        stack.append(index)
    return result


def _next_low_touch_indices(candles: Sequence[SourceCandle]) -> list[int | None]:
    result: list[int | None] = [None] * len(candles)
    stack: list[int] = []
    for index in range(len(candles) - 1, -1, -1):
        while stack and candles[stack[-1]].low > candles[index].low:
            stack.pop()
        result[index] = None if not stack else stack[-1]
        stack.append(index)
    return result


def _exact_touch_at(
    candle: SourceCandle, level: Decimal, side: Side
) -> datetime | None:
    for bar in candle.m5:
        if _touched(bar, level, side):
            return bar.opened_at
    return None


def _swing_candidates(
    candles: Sequence[SourceCandle], timeframe: str
) -> dict[Side, tuple[SwingCandidate, ...]]:
    high_next = _next_high_touch_indices(candles)
    low_next = _next_low_touch_indices(candles)
    highs: list[SwingCandidate] = []
    lows: list[SwingCandidate] = []
    for index in range(1, len(candles) - 1):
        left, pivot, right = candles[index - 1], candles[index], candles[index + 1]
        if pivot.high > left.high and pivot.high > right.high:
            touch_index = high_next[index]
            touch_at = (
                None
                if touch_index is None
                else _exact_touch_at(candles[touch_index], pivot.high, Side.LONG)
            )
            highs.append(
                SwingCandidate(
                    timeframe=timeframe,
                    kind="ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
                    level=pivot.high,
                    pivot_opened_at=pivot.opened_at,
                    known_at=right.closed_at,
                    touch_at=touch_at,
                )
            )
        if pivot.low < left.low and pivot.low < right.low:
            touch_index = low_next[index]
            touch_at = (
                None
                if touch_index is None
                else _exact_touch_at(candles[touch_index], pivot.low, Side.SHORT)
            )
            lows.append(
                SwingCandidate(
                    timeframe=timeframe,
                    kind="ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
                    level=pivot.low,
                    pivot_opened_at=pivot.opened_at,
                    known_at=right.closed_at,
                    touch_at=touch_at,
                )
            )
    return {Side.LONG: tuple(highs), Side.SHORT: tuple(lows)}


def _latest_active_swing(
    candidates: Sequence[SwingCandidate],
    known_times: Sequence[datetime],
    *,
    departure: datetime,
    anchor: Decimal,
    side: Side,
) -> Candidate | None:
    cursor = bisect_right(known_times, departure) - 1
    while cursor >= 0:
        item = candidates[cursor]
        if _ahead(item.level, anchor, side) and (
            item.touch_at is None or item.touch_at >= departure
        ):
            return Candidate(
                kind=item.kind,
                timeframe=item.timeframe,
                level=item.level,
                structural_opened_at=item.pivot_opened_at,
                known_at=item.known_at,
            )
        cursor -= 1
    return None


def _candidate_id(episode_id: str, candidate: Candidate) -> str:
    raw = "|".join(
        (
            episode_id,
            candidate.kind,
            candidate.timeframe,
            str(candidate.level),
            candidate.known_at.isoformat(),
        )
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _load_market_journeys(root: Path) -> list[dict[str, Any]]:
    paths = list(root.rglob("MARKET_JOURNEY_LEDGER.jsonl"))
    if len(paths) != 1:
        raise ValueError("expected exactly one MARKET_JOURNEY_LEDGER")
    return journey._read_jsonl(paths[0])


def _frames(evidence_bars: tuple[Bar, ...]) -> dict[str, tuple[SourceCandle, ...]]:
    h4 = build_h4(evidence_bars)
    return {
        "H1": build_h1(evidence_bars),
        "H4": h4,
        "D1": build_daily(h4),
    }


def _supported_candidates(
    row: dict[str, Any],
    *,
    departure: datetime,
    anchor: Decimal,
    side: Side,
    bars: Sequence[Bar],
    bar_opens: Sequence[datetime],
    frames: dict[str, tuple[SourceCandle, ...]],
    frame_opens: dict[str, tuple[datetime, ...]],
    swings: dict[str, dict[Side, tuple[SwingCandidate, ...]]],
    swing_known: dict[str, dict[Side, tuple[datetime, ...]]],
) -> list[Candidate]:
    result: list[Candidate] = []
    raid_at = _dt(str(row["liquidity_raid_at"]))
    opposite = Decimal(str(row["opposite_boundary"]))
    if _ahead(opposite, anchor, side) and _first_touch(
        bars,
        bar_opens,
        level=opposite,
        side=side,
        start=raid_at,
        end=departure,
    ) is None:
        result.append(
            Candidate(
                kind="SOURCE_OPPOSITE_BOUNDARY",
                timeframe=str(row["source_timeframe"]),
                level=opposite,
                structural_opened_at=_dt(str(row["source_boundary_created_at"])),
                known_at=raid_at,
            )
        )

    for timeframe, candles in frames.items():
        index = _containing_frame_index(candles, frame_opens[timeframe], departure)
        if index is None or index <= 0:
            continue
        current = candles[index]
        prior = candles[index - 1]
        level = _directional_level(prior, side)
        if _ahead(level, anchor, side) and _first_touch(
            bars,
            bar_opens,
            level=level,
            side=side,
            start=current.opened_at,
            end=departure,
        ) is None:
            result.append(
                Candidate(
                    kind="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY",
                    timeframe=timeframe,
                    level=level,
                    structural_opened_at=prior.opened_at,
                    known_at=prior.closed_at,
                )
            )
        swing = _latest_active_swing(
            swings[timeframe][side],
            swing_known[timeframe][side],
            departure=departure,
            anchor=anchor,
            side=side,
        )
        if swing is not None:
            result.append(swing)

    deduped: dict[tuple[str, str, Decimal, datetime], Candidate] = {}
    for candidate in result:
        deduped[
            (
                candidate.kind,
                candidate.timeframe,
                candidate.level,
                candidate.known_at,
            )
        ] = candidate
    return list(deduped.values())


def _apply_outcomes(
    episode_id: str,
    symbol: str,
    departure: datetime,
    anchor: Decimal,
    side: Side,
    candidates: Sequence[Candidate],
    bars: Sequence[Bar],
    bar_opens: Sequence[datetime],
    tick: Decimal,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    end = departure + timedelta(hours=24)
    left = bisect_left(bar_opens, departure)
    right = bisect_left(bar_opens, end)
    pending = set(range(len(candidates)))
    touch_at: dict[int, datetime] = {}
    touch_close: dict[int, datetime] = {}
    for bar in bars[left:right]:
        if not pending:
            break
        touched_now = [
            index
            for index in pending
            if _touched(bar, candidates[index].level, side)
        ]
        for index in touched_now:
            touch_at[index] = bar.opened_at
            touch_close[index] = bar.closed_at
            pending.remove(index)

    unique_touch_times = sorted(set(touch_at.values()))
    group_by_time = {moment: rank + 1 for rank, moment in enumerate(unique_touch_times)}
    rows: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        opened = touch_at.get(index)
        group = None if opened is None else group_by_time[opened]
        same_bar_count = (
            0
            if opened is None
            else sum(moment == opened for moment in touch_at.values())
        )
        rows.append(
            {
                "schema": TARGET_SCHEMA,
                "identity": IDENTITY,
                "episode_id": episode_id,
                "candidate_id": _candidate_id(episode_id, candidate),
                "symbol": symbol,
                "side": side.value,
                "departure_at": departure.isoformat(),
                "departure_anchor_price": str(anchor),
                "candidate_universe": CANDIDATE_UNIVERSE,
                "candidate_type": candidate.kind,
                "source_timeframe": candidate.timeframe,
                "candidate_price": str(candidate.level),
                "candidate_structural_opened_at": candidate.structural_opened_at.isoformat(),
                "candidate_known_at": candidate.known_at.isoformat(),
                "active_untouched_at_departure": True,
                "candidate_distance_ticks": str(abs(candidate.level - anchor) / tick),
                "causal_feature": True,
                "touch_within_24h": opened is not None,
                "touch_m5_opened_at": None if opened is None else opened.isoformat(),
                "touch_m5_closed_at": (
                    None if opened is None else touch_close[index].isoformat()
                ),
                "time_to_touch_minutes": (
                    None
                    if opened is None
                    else int((opened - departure).total_seconds() // 60)
                ),
                "touch_order_group": group,
                "touch_order_ambiguous_within_m5": same_bar_count > 1,
                "result_fields_outcome_only": True,
                "outcome_only": False,
            }
        )

    first_group = 1 if unique_touch_times else None
    first_ids = [
        rows[index]["candidate_id"]
        for index, moment in touch_at.items()
        if group_by_time[moment] == first_group
    ] if first_group is not None else []
    episode = {
        "schema": EPISODE_SCHEMA,
        "identity": IDENTITY,
        "episode_id": episode_id,
        "symbol": symbol,
        "side": side.value,
        "departure_at": departure.isoformat(),
        "departure_anchor_price": str(anchor),
        "candidate_universe": CANDIDATE_UNIVERSE,
        "active_candidate_count": len(candidates),
        "touched_candidate_count_24h": len(touch_at),
        "first_touch_candidate_ids": first_ids,
        "first_touch_m5_opened_at": (
            None if not unique_touch_times else unique_touch_times[0].isoformat()
        ),
        "first_touch_tied": len(first_ids) > 1,
        "complete_all_dol_claim": False,
        "causal_candidate_selection": True,
        "outcomes_are_post_departure": True,
    }
    return rows, episode


def build_target_destination_v2(
    raw_source: Path, journey_source: Path, output: Path
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_source)
    market_rows = _load_market_journeys(journey_source)
    frames = _frames(evidence.bars)
    frame_opens = {
        timeframe: tuple(candle.opened_at for candle in candles)
        for timeframe, candles in frames.items()
    }
    swings = {
        timeframe: _swing_candidates(candles, timeframe)
        for timeframe, candles in frames.items()
    }
    swing_known = {
        timeframe: {
            side: tuple(item.known_at for item in candidates)
            for side, candidates in by_side.items()
        }
        for timeframe, by_side in swings.items()
    }
    bars = evidence.bars
    bar_opens = tuple(bar.opened_at for bar in bars)
    tick = _tick_size(evidence.digits)

    target_rows: list[dict[str, Any]] = []
    episode_rows: list[dict[str, Any]] = []
    resolved_departures = 0
    anchor_failures = 0
    for row in market_rows:
        raw_departure = row.get("departure_at")
        if raw_departure is None:
            continue
        resolved_departures += 1
        departure = _dt(str(raw_departure))
        anchor = _departure_anchor(bars, bar_opens, departure)
        if anchor is None:
            anchor_failures += 1
            continue
        side = _side(str(row["side"]))
        candidates = _supported_candidates(
            row,
            departure=departure,
            anchor=anchor,
            side=side,
            bars=bars,
            bar_opens=bar_opens,
            frames=frames,
            frame_opens=frame_opens,
            swings=swings,
            swing_known=swing_known,
        )
        rows, episode = _apply_outcomes(
            str(row["episode_id"]),
            evidence.symbol,
            departure,
            anchor,
            side,
            candidates,
            bars,
            bar_opens,
            tick,
        )
        target_rows.extend(rows)
        episode_rows.append(episode)

    output.mkdir(parents=True, exist_ok=True)
    target_path = output / "TARGET_DESTINATION_LEDGER_V2.jsonl"
    episode_path = output / "TARGET_DESTINATION_EPISODE_V2.jsonl"
    target_count = journey._write_jsonl(target_path, target_rows)
    episode_count = journey._write_jsonl(episode_path, episode_rows)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "identity": IDENTITY,
        "source_journey_identity": SOURCE_JOURNEY_IDENTITY,
        "source_journey_run_id": SOURCE_JOURNEY_RUN_ID,
        "source_journey_git_sha": SOURCE_JOURNEY_GIT_SHA,
        "source_m5_run_id": SOURCE_M5_RUN_ID,
        "source_m5_git_sha": SOURCE_M5_GIT_SHA,
        "symbol": evidence.symbol,
        "provider_symbol": provenance["provider_symbol"],
        "retained_m5_bars": provenance["retained_bars"],
        "market_journey_rows": len(market_rows),
        "resolved_departures": resolved_departures,
        "anchor_failures": anchor_failures,
        "episode_rows": episode_count,
        "candidate_rows": target_count,
        "candidate_universe": CANDIDATE_UNIVERSE,
        "candidate_types": [
            "SOURCE_OPPOSITE_BOUNDARY",
            "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY",
            "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
        ],
        "source_timeframes": ["H1", "H4", "D1"],
        "active_untouched_required": True,
        "outcome_horizon_hours": 24,
        "touch_resolution": "M5_INTERVAL_FAIL_CLOSED_ON_WITHIN_BAR_ORDER",
        "complete_all_dol_claim": False,
        "research_evidence_consumed": True,
        "rule_promotion_allowed": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "target_ledger_sha256": journey._sha256(target_path),
        "episode_ledger_sha256": journey._sha256(episode_path),
    }
    (output / "target-destination-v2-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="CIBO Target Destination V2")
    parser.add_argument("raw_source", type=Path)
    parser.add_argument("journey_source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build_target_destination_v2(
        args.raw_source, args.journey_source, args.output
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
