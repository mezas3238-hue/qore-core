"""Cross-market Turtle Soup behavior laboratory.

Research-only engine: liquidity reference -> raid -> rejection/acceptance ->
CISD/protected swing -> forward response. Session/time are diagnostics only.
Source-underdefined numeric properties remain continuous measurements.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.deterministic_sampling import DeterministicChooser
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
    Side,
    SourceCandle,
    _session_bucket,
    build_daily,
    build_h1,
    build_h4,
    build_m15,
    causal_cisd,
)

IDENTITY = "ICT_TS_BEHAVIOR_LAB_V1"
ONTOLOGY_VERSION = "qore.ict_ts_behavior_lab.event.v1"
BOOTSTRAP_SEED = 20260916
HORIZONS = (15, 30, 60, 240, 1440)


class ReferenceType(StrEnum):
    PRIOR_CANDLE = "prior-candle"
    SWING_3 = "swing-3"


@dataclass(frozen=True, slots=True)
class Reference:
    timeframe: str
    kind: ReferenceType
    side: Side
    level: Decimal
    opposite: Decimal
    opened_at: datetime
    closed_at: datetime
    age_bars: int
    exact_equal_count: int
    nearest_peer_ticks: Decimal | None


@dataclass(frozen=True, slots=True)
class Event:
    evidence_id: str
    symbol: str
    asset_class: str
    provider: str
    timeframe: str
    reference_type: str
    side: str
    reference_opened_at: datetime
    source_opened_at: datetime
    raid_at: datetime
    reference_level: Decimal
    opposite_reference: Decimal
    tick_size: Decimal
    reference_age_bars: int
    exact_equal_count: int
    nearest_peer_ticks: Decimal | None
    raid_depth_ticks: Decimal
    raid_depth_pct: Decimal
    raid_depth_range_units: Decimal | None
    source_range_ticks: Decimal
    body_fraction: Decimal
    rejection_wick_fraction: Decimal
    close_location: Decimal
    prior_body_alignment: str
    session_bucket: str
    ny_minute_of_day: int
    same_source_reclaim: bool
    reclaim_latency_minutes: int | None
    reclaim_depth_ticks: Decimal | None
    cisd_confirmed: bool
    cisd_latency_minutes: int | None
    protected_swing_distance_ticks: Decimal | None
    fvg_after_raid: bool
    opposite_reference_hit_24h: bool
    opposite_reference_hit_minutes: int | None
    mfe_15m_ticks: Decimal
    mae_15m_ticks: Decimal
    mfe_30m_ticks: Decimal
    mae_30m_ticks: Decimal
    mfe_60m_ticks: Decimal
    mae_60m_ticks: Decimal
    mfe_240m_ticks: Decimal
    mae_240m_ticks: Decimal
    mfe_1440m_ticks: Decimal
    mae_1440m_ticks: Decimal
    outcome: str


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _tick_size(digits: int) -> Decimal:
    return Decimal(1).scaleb(-digits)


def load_evidence(path: Path) -> tuple[Evidence, dict[str, Any]]:
    payload = json.loads(path.read_text())
    symbol_payload = payload.get("symbol", {})
    symbol = str(symbol_payload.get("symbol_name") or payload.get("symbol") or "")
    digits = int(symbol_payload.get("digits", payload.get("digits", 0)))
    periods = payload.get("periods", {})
    raw = periods.get("M5")
    if not symbol or digits <= 0 or not isinstance(raw, list) or not raw:
        raise ValueError("invalid market evidence")
    bars = tuple(
        Bar(
            opened_at=_dt(str(item["opened_at"])),
            closed_at=_dt(str(item["closed_at"])),
            open=Decimal(str(item["open"])),
            high=Decimal(str(item["high"])),
            low=Decimal(str(item["low"])),
            close=Decimal(str(item["close"])),
        )
        for item in raw
    )
    return Evidence(symbol=symbol, digits=digits, bars=bars), payload


def _m5_sources(bars: Sequence[Bar]) -> tuple[SourceCandle, ...]:
    return tuple(
        SourceCandle(b.opened_at, b.closed_at, b.open, b.high, b.low, b.close, (b,)) for b in bars
    )


def _level(candle: SourceCandle, side: Side) -> Decimal:
    return candle.high if side is Side.SHORT else candle.low


def _opposite(candle: SourceCandle, side: Side) -> Decimal:
    return candle.low if side is Side.SHORT else candle.high


def _is_swing(candles: Sequence[SourceCandle], index: int, side: Side) -> bool:
    if index <= 0 or index + 1 >= len(candles):
        return False
    left, pivot, right = candles[index - 1], candles[index], candles[index + 1]
    if side is Side.SHORT:
        return pivot.high > left.high and pivot.high > right.high
    return pivot.low < left.low and pivot.low < right.low


def _peer_stats(
    candles: Sequence[SourceCandle], index: int, side: Side, tick: Decimal
) -> tuple[int, Decimal | None]:
    level = _level(candles[index], side)
    prior = [_level(item, side) for item in candles[max(0, index - 20) : index]]
    if not prior:
        return 1, None
    distances = [abs(level - item) / tick for item in prior]
    exact = 1 + sum(value == 0 for value in distances)
    positive = [value for value in distances if value > 0]
    return exact, min(positive) if positive else None


def _references(
    candles: Sequence[SourceCandle], timeframe: str, index: int, tick: Decimal
) -> tuple[Reference, ...]:
    if index <= 0:
        return ()
    result: list[Reference] = []
    for side in (Side.LONG, Side.SHORT):
        prior_index = index - 1
        exact, peer = _peer_stats(candles, prior_index, side, tick)
        prior = candles[prior_index]
        result.append(
            Reference(
                timeframe,
                ReferenceType.PRIOR_CANDLE,
                side,
                _level(prior, side),
                _opposite(prior, side),
                prior.opened_at,
                prior.closed_at,
                1,
                exact,
                peer,
            )
        )
        swing_index = next(
            (cursor for cursor in range(index - 2, 0, -1) if _is_swing(candles, cursor, side)),
            None,
        )
        if swing_index is not None:
            swing = candles[swing_index]
            exact, peer = _peer_stats(candles, swing_index, side, tick)
            result.append(
                Reference(
                    timeframe,
                    ReferenceType.SWING_3,
                    side,
                    _level(swing, side),
                    _opposite(swing, side),
                    swing.opened_at,
                    swing.closed_at,
                    index - swing_index,
                    exact,
                    peer,
                )
            )
    return tuple(result)


def _raided(candle: SourceCandle, ref: Reference) -> bool:
    if ref.side is Side.LONG:
        return candle.low < ref.level
    return candle.high > ref.level


def _first_raid(candle: SourceCandle, ref: Reference) -> Bar | None:
    for bar in candle.m5:
        if ref.side is Side.LONG and bar.low < ref.level:
            return bar
        if ref.side is Side.SHORT and bar.high > ref.level:
            return bar
    return None


def _range_mean(candles: Sequence[SourceCandle], index: int, lookback: int = 20) -> Decimal | None:
    sample = candles[max(0, index - lookback) : index]
    if not sample:
        return None
    return sum((item.high - item.low for item in sample), Decimal(0)) / len(sample)


def _geometry(candle: SourceCandle, side: Side) -> tuple[Decimal, Decimal, Decimal]:
    span = candle.high - candle.low
    if span <= 0:
        return Decimal(0), Decimal(0), Decimal("0.5")
    body = abs(candle.close - candle.open) / span
    if side is Side.LONG:
        wick = (min(candle.open, candle.close) - candle.low) / span
        close_location = (candle.close - candle.low) / span
    else:
        wick = (candle.high - max(candle.open, candle.close)) / span
        close_location = (candle.high - candle.close) / span
    return body, max(wick, Decimal(0)), close_location


def _prior_alignment(previous: SourceCandle, side: Side) -> str:
    if previous.close == previous.open:
        return "doji"
    aligned = (
        previous.close > previous.open if side is Side.LONG else previous.close < previous.open
    )
    return "aligned" if aligned else "opposed"


def _reclaim(
    bars: Sequence[Bar],
    ref: Reference,
    raid_at: datetime,
    until: datetime,
    tick: Decimal,
) -> tuple[int | None, Decimal | None]:
    for bar in bars:
        if bar.opened_at < raid_at or bar.closed_at > until:
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
    end = start + timedelta(minutes=minutes)
    sample = [bar for bar in bars if start <= bar.opened_at < end]
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
    sample = [bar for bar in bars if raid_at <= bar.opened_at < raid_at + timedelta(minutes=90)]
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
    for bar in bars:
        if not start <= bar.opened_at < start + timedelta(hours=24):
            continue
        hit = bar.high >= level if side is Side.LONG else bar.low <= level
        if hit:
            return True, int((bar.opened_at - start).total_seconds() // 60)
    return False, None


def _cisd(
    candle: SourceCandle, timeframe: str, side: Side, tick: Decimal
) -> tuple[bool, int | None, Decimal | None]:
    if timeframe == "D1":
        lower = build_h1(candle.m5)
    elif timeframe == "H4":
        lower = build_m15(candle.m5)
    elif timeframe == "H1":
        lower = _m5_sources(candle.m5)
    else:
        return False, None, None
    extreme = candle.low if side is Side.LONG else candle.high
    found = causal_cisd(lower, side=side, extreme=extreme)
    if found is None or found.confirmed_at > candle.closed_at:
        return False, None, None
    latency = int((found.confirmed_at - candle.opened_at).total_seconds() // 60)
    distance = abs(found.protected_swing - found.threshold) / tick
    return True, latency, distance


def _ny_minute(moment: datetime) -> int:
    from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import NY

    local = moment.astimezone(NY)
    return local.hour * 60 + local.minute


def _make_event(
    evidence: Evidence,
    candles: Sequence[SourceCandle],
    index: int,
    ref: Reference,
    asset_class: str,
    provider: str,
    evidence_id: str,
) -> Event | None:
    candle = candles[index]
    if not _raided(candle, ref):
        return None
    raid = _first_raid(candle, ref)
    if raid is None:
        return None
    tick = _tick_size(evidence.digits)
    extreme = candle.low if ref.side is Side.LONG else candle.high
    depth = abs(extreme - ref.level)
    prior_mean = _range_mean(candles, index)
    body, wick, close_location = _geometry(candle, ref.side)
    reclaim_latency, reclaim_depth = _reclaim(
        evidence.bars, ref, raid.opened_at, candle.closed_at, tick
    )
    cisd, cisd_latency, protected_distance = _cisd(candle, ref.timeframe, ref.side, tick)
    hit, hit_minutes = _opposite_hit(evidence.bars, ref.side, ref.opposite, raid.opened_at)
    forward = {
        horizon: _forward_extremes(
            evidence.bars, ref.side, ref.level, raid.opened_at, horizon, tick
        )
        for horizon in HORIZONS
    }
    pct = Decimal(0) if ref.level == 0 else depth / abs(ref.level) * Decimal(100)
    if prior_mean is None or prior_mean == 0:
        range_units = None
    else:
        range_units = depth / prior_mean
    reclaimed = reclaim_latency is not None
    if reclaimed and cisd:
        outcome = "rejection-with-cisd"
    elif reclaimed:
        outcome = "rejection-without-cisd"
    else:
        outcome = "acceptance-or-delayed-reclaim"
    return Event(
        evidence_id=evidence_id,
        symbol=evidence.symbol,
        asset_class=asset_class,
        provider=provider,
        timeframe=ref.timeframe,
        reference_type=ref.kind.value,
        side=ref.side.value,
        reference_opened_at=ref.opened_at,
        source_opened_at=candle.opened_at,
        raid_at=raid.opened_at,
        reference_level=ref.level,
        opposite_reference=ref.opposite,
        tick_size=tick,
        reference_age_bars=ref.age_bars,
        exact_equal_count=ref.exact_equal_count,
        nearest_peer_ticks=ref.nearest_peer_ticks,
        raid_depth_ticks=depth / tick,
        raid_depth_pct=pct,
        raid_depth_range_units=range_units,
        source_range_ticks=(candle.high - candle.low) / tick,
        body_fraction=body,
        rejection_wick_fraction=wick,
        close_location=close_location,
        prior_body_alignment=_prior_alignment(candles[index - 1], ref.side),
        session_bucket=_session_bucket(raid.opened_at),
        ny_minute_of_day=_ny_minute(raid.opened_at),
        same_source_reclaim=reclaimed,
        reclaim_latency_minutes=reclaim_latency,
        reclaim_depth_ticks=reclaim_depth,
        cisd_confirmed=cisd,
        cisd_latency_minutes=cisd_latency,
        protected_swing_distance_ticks=protected_distance,
        fvg_after_raid=_fvg_after_raid(evidence.bars, raid.opened_at, ref.side),
        opposite_reference_hit_24h=hit,
        opposite_reference_hit_minutes=hit_minutes,
        mfe_15m_ticks=forward[15][0],
        mae_15m_ticks=forward[15][1],
        mfe_30m_ticks=forward[30][0],
        mae_30m_ticks=forward[30][1],
        mfe_60m_ticks=forward[60][0],
        mae_60m_ticks=forward[60][1],
        mfe_240m_ticks=forward[240][0],
        mae_240m_ticks=forward[240][1],
        mfe_1440m_ticks=forward[1440][0],
        mae_1440m_ticks=forward[1440][1],
        outcome=outcome,
    )


def extract_events(
    evidence: Evidence, *, asset_class: str, provider: str, evidence_id: str
) -> list[Event]:
    h4 = build_h4(evidence.bars)
    frames: tuple[tuple[str, Sequence[SourceCandle]], ...] = (
        ("D1", build_daily(h4)),
        ("H4", h4),
        ("H1", build_h1(evidence.bars)),
    )
    tick = _tick_size(evidence.digits)
    events: list[Event] = []
    seen: set[tuple[Any, ...]] = set()
    for timeframe, candles in frames:
        for index in range(1, len(candles)):
            for ref in _references(candles, timeframe, index, tick):
                event = _make_event(
                    evidence,
                    candles,
                    index,
                    ref,
                    asset_class,
                    provider,
                    evidence_id,
                )
                if event is None:
                    continue
                key = (
                    event.symbol,
                    event.timeframe,
                    event.reference_type,
                    event.side,
                    event.source_opened_at,
                    event.reference_opened_at,
                )
                if key not in seen:
                    seen.add(key)
                    events.append(event)
    events.sort(key=lambda item: (item.raid_at, item.symbol, item.timeframe))
    return events


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    return value


def event_dict(event: Event) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in asdict(event).items()}


def _rate(values: Sequence[bool]) -> float | None:
    return None if not values else sum(values) / len(values)


def _med(values: Sequence[Decimal]) -> str | None:
    return None if not values else str(median(values))


def summarize(events: Sequence[Event]) -> dict[str, Any]:
    return {
        "events": len(events),
        "reclaim_rate": _rate([item.same_source_reclaim for item in events]),
        "cisd_rate": _rate([item.cisd_confirmed for item in events]),
        "fvg_rate": _rate([item.fvg_after_raid for item in events]),
        "opposite_hit_24h_rate": _rate([item.opposite_reference_hit_24h for item in events]),
        "median_raid_depth_ticks": _med([item.raid_depth_ticks for item in events]),
        "median_raid_depth_range_units": _med(
            [
                item.raid_depth_range_units
                for item in events
                if item.raid_depth_range_units is not None
            ]
        ),
        "median_mfe_240m_ticks": _med([item.mfe_240m_ticks for item in events]),
        "median_mae_240m_ticks": _med([item.mae_240m_ticks for item in events]),
        "median_mfe_1440m_ticks": _med([item.mfe_1440m_ticks for item in events]),
        "median_mae_1440m_ticks": _med([item.mae_1440m_ticks for item in events]),
    }


def _bootstrap_ci(events: Sequence[Event], attr: str) -> tuple[float | None, float | None]:
    if not events:
        return None, None
    blocks: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        blocks[event.raid_at.date().isoformat()].append(event)
    populations = list(blocks.values())
    if len(populations) < 2:
        value = _rate([bool(getattr(item, attr)) for item in events])
        return value, value
    rng = DeterministicChooser(BOOTSTRAP_SEED)
    estimates: list[float] = []
    for _ in range(400):
        sample: list[Event] = []
        for _index in populations:
            sample.extend(rng.choice(populations))
        estimate = _rate([bool(getattr(item, attr)) for item in sample])
        if estimate is not None:
            estimates.append(estimate)
    estimates.sort()
    low = estimates[max(0, int(len(estimates) * 0.025) - 1)]
    high = estimates[min(len(estimates) - 1, int(len(estimates) * 0.975))]
    return low, high


def group_rows(events: Sequence[Event]) -> list[dict[str, Any]]:
    dimensions: dict[str, Callable[[Event], str]] = {
        "asset_class": lambda item: item.asset_class,
        "symbol": lambda item: item.symbol,
        "timeframe": lambda item: item.timeframe,
        "reference_type": lambda item: item.reference_type,
        "side": lambda item: item.side,
        "session": lambda item: item.session_bucket,
        "year": lambda item: str(item.raid_at.year),
        "quarter": lambda item: f"{item.raid_at.year}-Q{(item.raid_at.month - 1) // 3 + 1}",
    }
    rows: list[dict[str, Any]] = []
    for dimension, getter in dimensions.items():
        grouped: dict[str, list[Event]] = defaultdict(list)
        for event in events:
            grouped[getter(event)].append(event)
        for value, members in sorted(grouped.items()):
            low, high = _bootstrap_ci(members, "same_source_reclaim")
            rows.append(
                {
                    "dimension": dimension,
                    "value": value,
                    **summarize(members),
                    "reclaim_ci_low": low,
                    "reclaim_ci_high": high,
                }
            )
    return rows


def quantile_rows(events: Sequence[Event]) -> list[dict[str, Any]]:
    usable = [item for item in events if item.raid_depth_range_units is not None]
    usable.sort(key=lambda item: item.raid_depth_range_units or Decimal(0))
    if len(usable) < 5:
        return []
    rows: list[dict[str, Any]] = []
    for bucket in range(5):
        start = bucket * len(usable) // 5
        end = (bucket + 1) * len(usable) // 5
        members = usable[start:end]
        values = [
            item.raid_depth_range_units
            for item in members
            if item.raid_depth_range_units is not None
        ]
        if not members or not values:
            continue
        rows.append(
            {
                "feature": "raid_depth_range_units",
                "quantile": bucket + 1,
                "min": str(min(values)),
                "max": str(max(values)),
                **summarize(members),
            }
        )
    return rows


def survival_rows(events: Sequence[Event]) -> list[dict[str, Any]]:
    known = [item for item in events if item.reclaim_latency_minutes is not None]
    result: list[dict[str, Any]] = []
    for minutes in (5, 15, 30, 60, 240):
        reached = sum((item.reclaim_latency_minutes or 0) <= minutes for item in known)
        result.append(
            {
                "event": "reclaim",
                "minutes": minutes,
                "known_reclaims": len(known),
                "cumulative": reached,
                "fraction": None if not known else reached / len(known),
            }
        )
    return result


def leave_one_out_rows(events: Sequence[Event]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol in sorted({item.symbol for item in events}):
        remaining = [item for item in events if item.symbol != symbol]
        rows.append({"leave_out": f"symbol:{symbol}", **summarize(remaining)})
    quarters = sorted(
        {f"{item.raid_at.year}-Q{(item.raid_at.month - 1) // 3 + 1}" for item in events}
    )
    for quarter in quarters:
        remaining = [
            item
            for item in events
            if f"{item.raid_at.year}-Q{(item.raid_at.month - 1) // 3 + 1}" != quarter
        ]
        rows.append({"leave_out": f"quarter:{quarter}", **summarize(remaining)})
    return rows


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(
    events: Sequence[Event], output: Path, evidence_ids: Sequence[str]
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    payloads = [event_dict(item) for item in events]
    (output / "events.json").write_text(json.dumps(payloads, indent=2, sort_keys=True) + "\n")
    _write_csv(output / "events.csv", payloads)
    _write_csv(output / "group_stats.csv", group_rows(events))
    _write_csv(output / "quantile_response.csv", quantile_rows(events))
    _write_csv(output / "survival.csv", survival_rows(events))
    _write_csv(output / "leave_one_out.csv", leave_one_out_rows(events))
    summary = {
        "schema": "qore.ict_ts_behavior_lab.summary.v1",
        "identity": IDENTITY,
        "ontology_version": ONTOLOGY_VERSION,
        "evidence_ids": list(evidence_ids),
        "evidence_status": "CONSUMED_DIAGNOSTIC_ONLY",
        "event_count": len(events),
        "overall": summarize(events),
        "outcomes": dict(sorted(Counter(item.outcome for item in events).items())),
        "timeframes": dict(sorted(Counter(item.timeframe for item in events).items())),
        "reference_types": dict(sorted(Counter(item.reference_type for item in events).items())),
        "symbols": dict(sorted(Counter(item.symbol for item in events).items())),
        "session_filter_applied": False,
        "pnl_used_for_filter_selection": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def analyze_files(
    paths: Sequence[Path],
    output: Path,
    *,
    asset_class: str,
    provider: str,
    evidence_prefix: str,
) -> dict[str, Any]:
    events: list[Event] = []
    evidence_ids: list[str] = []
    for path in paths:
        evidence, payload = load_evidence(path)
        source_id = str(payload.get("holdout_id") or payload.get("evidence_id") or path.stem)
        evidence_id = f"{evidence_prefix}:{source_id}:{evidence.symbol}"
        evidence_ids.append(evidence_id)
        events.extend(
            extract_events(
                evidence,
                asset_class=asset_class,
                provider=provider,
                evidence_id=evidence_id,
            )
        )
    events.sort(key=lambda item: (item.raid_at, item.symbol, item.timeframe))
    return write_outputs(events, output, evidence_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="QORE Turtle Soup Behavior Lab V1")
    parser.add_argument("output", type=Path)
    parser.add_argument("evidence", nargs="+", type=Path)
    parser.add_argument("--asset-class", required=True)
    parser.add_argument("--provider", default="unknown")
    parser.add_argument("--evidence-prefix", default="consumed")
    args = parser.parse_args()
    result = analyze_files(
        args.evidence,
        args.output,
        asset_class=args.asset_class,
        provider=args.provider,
        evidence_prefix=args.evidence_prefix,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
