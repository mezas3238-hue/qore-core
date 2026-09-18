"""CIBO Market Atlas Journey Layer V1 extractor.

Research-only transformation of the retained ten-year M5 corpus into auditable
journey ledgers. Frozen Behavior Lab raid/reclaim/CISD semantics are reused and
unsupported structures fail closed as UNRESOLVED_STRUCTURE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab as behavior
from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab_fast_runner as fast
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar, Evidence

IDENTITY = "CIBO_MARKET_JOURNEY_LAYER_V1"
SOURCE_IDENTITY = "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1"
SOURCE_RUN_ID = 35166210458
SOURCE_GIT_SHA = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
PRICE_SCALE = Decimal(100_000)
NY = ZoneInfo("America/New_York")

MARKET_JOURNEY_SCHEMA = "qore.cibo_market_atlas.market_journey.v1"
STRUCTURE_TOUCH_SCHEMA = "qore.cibo_market_atlas.structure_touch.v1"
PRE_DEPARTURE_SCHEMA = "qore.cibo_market_atlas.pre_departure_sequence.v1"
DEPARTURE_TIMING_SCHEMA = "qore.cibo_market_atlas.departure_timing.v1"
TARGET_DESTINATION_SCHEMA = "qore.cibo_market_atlas.target_destination.v1"
CROSS_INDEX_SCHEMA = "qore.cibo_market_atlas.cross_index_journey.v1"
DAILY_PATH_SCHEMA = "qore.cibo_market_atlas.daily_path.v1"
TRADER_SYNC_SCHEMA = "qore.cibo_market_atlas.trader_market_sync.v1"
MANIFEST_SCHEMA = "qore.cibo_market_atlas.journey_manifest.v1"

LEDGER_NAMES = (
    "MARKET_JOURNEY_LEDGER",
    "STRUCTURE_TOUCH_LEDGER",
    "PRE_DEPARTURE_SEQUENCE_LEDGER",
    "DEPARTURE_TIMING_LEDGER",
    "TARGET_DESTINATION_LEDGER",
    "DAILY_PATH_LEDGER",
    "TRADER_MARKET_SYNC_LEDGER",
)

ASSET_CLASS = {
    "AUDJPY": "fx",
    "AUDUSD": "fx",
    "EURUSD": "fx",
    "GBPJPY": "fx",
    "GBPUSD": "fx",
    "USDCAD": "fx",
    "USDJPY": "fx",
    "NAS100": "index",
    "SP500": "index",
    "US30": "index",
    "XAUUSD": "metal",
    "XAGUSD": "metal",
}


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"unsupported JSON value: {type(value)!r}")


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _event_id(event: behavior.Event) -> str:
    raw = "|".join(
        (
            event.symbol,
            event.timeframe,
            event.reference_type,
            event.side,
            event.reference_opened_at.isoformat(),
            event.source_opened_at.isoformat(),
            event.raid_at.isoformat(),
        )
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _episode_id(event: behavior.Event) -> str:
    return f"{event.symbol}:{_event_id(event)}"


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, default=_json_default) + "\n")
            count += 1
    return count


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _price(relative: int, digits: int) -> Decimal:
    if relative <= 0 or digits <= 0:
        raise ValueError("invalid relative price or digits")
    return (Decimal(relative) / PRICE_SCALE).quantize(Decimal(1).scaleb(-digits))


def load_raw_m5(root: Path) -> tuple[Evidence, dict[str, Any]]:
    files = sorted(root.rglob("RAW_M5_LEDGER/*.jsonl"))
    if not files:
        raise ValueError("RAW_M5_LEDGER partitions not found")
    bars: dict[datetime, Bar] = {}
    symbol: str | None = None
    provider_symbol: str | None = None
    digits: int | None = None
    pip_position: int | None = None
    for path in files:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                item = json.loads(line)
                if item.get("identity") != SOURCE_IDENTITY:
                    raise ValueError("unexpected source corpus identity")
                current_symbol = str(item["canonical_symbol"])
                current_provider = str(item["provider_symbol"])
                current_digits = int(item["digits"])
                current_pip = item.get("pip_position")
                if symbol is None:
                    symbol = current_symbol
                    provider_symbol = current_provider
                    digits = current_digits
                    pip_position = None if current_pip is None else int(current_pip)
                if (
                    symbol != current_symbol
                    or provider_symbol != current_provider
                    or digits != current_digits
                ):
                    raise ValueError("mixed symbol payload in source artifact")
                opened_at = _dt(str(item["opened_at"]))
                bar = Bar(
                    opened_at=opened_at,
                    closed_at=opened_at + timedelta(minutes=5),
                    open=_price(int(item["open_relative"]), current_digits),
                    high=_price(int(item["high_relative"]), current_digits),
                    low=_price(int(item["low_relative"]), current_digits),
                    close=_price(int(item["close_relative"]), current_digits),
                )
                existing = bars.get(opened_at)
                if existing is not None and existing != bar:
                    raise ValueError("contradictory M5 bar across partitions")
                bars[opened_at] = bar
    if symbol is None or provider_symbol is None or digits is None or not bars:
        raise ValueError("empty source artifact")
    ordered = tuple(bars[key] for key in sorted(bars))
    return Evidence(symbol=symbol, digits=digits, bars=ordered), {
        "canonical_symbol": symbol,
        "provider_symbol": provider_symbol,
        "digits": digits,
        "pip_position": pip_position,
        "partitions": len(files),
        "retained_bars": len(ordered),
        "earliest_observed_m5": ordered[0].opened_at.isoformat(),
        "latest_observed_m5": ordered[-1].opened_at.isoformat(),
    }


def departure_at(event: behavior.Event) -> datetime | None:
    if not event.cisd_confirmed or event.cisd_latency_minutes is None:
        return None
    return event.source_opened_at + timedelta(minutes=event.cisd_latency_minutes)


def event_ledgers(event: behavior.Event) -> dict[str, list[dict[str, Any]]]:
    episode_id = _episode_id(event)
    event_id = _event_id(event)
    departure = departure_at(event)
    reclaim_at = (
        None
        if event.reclaim_latency_minutes is None
        else event.raid_at + timedelta(minutes=event.reclaim_latency_minutes)
    )
    opposite_hit_at = (
        None
        if event.opposite_reference_hit_minutes is None
        else event.raid_at + timedelta(minutes=event.opposite_reference_hit_minutes)
    )
    reference_structure = (
        "PRIOR_HIGH_LOW"
        if event.reference_type == "prior-candle"
        else "SWING_HIGH_LOW"
        if event.reference_type == "swing-3"
        else "UNRESOLVED_STRUCTURE"
    )
    final_structure = (
        "CISD_RELATED_STRUCTURE"
        if departure is not None
        else "LIQUIDITY_RAID_RECLAIM"
        if event.same_source_reclaim
        else "UNRESOLVED_STRUCTURE"
    )
    market = {
        "schema": MARKET_JOURNEY_SCHEMA,
        "identity": IDENTITY,
        "episode_id": episode_id,
        "event_id": event_id,
        "symbol": event.symbol,
        "asset_class": event.asset_class,
        "provider": event.provider,
        "side": event.side,
        "source_timeframe": event.timeframe,
        "source_boundary_type": reference_structure,
        "source_boundary": str(event.reference_level),
        "opposite_boundary": str(event.opposite_reference),
        "source_boundary_created_at": event.reference_opened_at.isoformat(),
        "liquidity_raid_at": event.raid_at.isoformat(),
        "reclaim_at": None if reclaim_at is None else reclaim_at.isoformat(),
        "departure_at": None if departure is None else departure.isoformat(),
        "departure_detector": "CAUSAL_CISD_V1" if departure else "UNRESOLVED_DEPARTURE",
        "last_structure_before_departure": final_structure,
        "session_bucket": event.session_bucket,
        "ny_minute_of_day": event.ny_minute_of_day,
        "causal_feature": True,
        "outcome_only": False,
        "source_run_id": SOURCE_RUN_ID,
        "source_git_sha": SOURCE_GIT_SHA,
    }
    source_touch = {
        "schema": STRUCTURE_TOUCH_SCHEMA,
        "identity": IDENTITY,
        "episode_id": episode_id,
        "event_id": event_id,
        "symbol": event.symbol,
        "side": event.side,
        "structure_type": reference_structure,
        "detector_version": "ICT_TS_BEHAVIOR_LAB_V1",
        "source_timeframe": event.timeframe,
        "structure_created_at": event.reference_opened_at.isoformat(),
        "first_touch_at": event.raid_at.isoformat(),
        "last_touch_at": event.raid_at.isoformat(),
        "price_low": str(event.reference_level),
        "price_high": str(event.reference_level),
        "penetration_depth_ticks": str(event.raid_depth_ticks),
        "reclaim_state": (
            "RECLAIMED" if event.same_source_reclaim else "NOT_RECLAIMED_IN_SOURCE_CANDLE"
        ),
        "dwell_minutes": event.reclaim_latency_minutes,
        "revisit_count": None,
        "last_structure_before_departure": departure is None,
        "causal_feature": True,
        "outcome_only": False,
    }
    structures = [source_touch]
    sequence = [
        {
            "order": 1,
            "structure_type": reference_structure,
            "timestamp": event.raid_at.isoformat(),
            "state": "LIQUIDITY_RAID",
        }
    ]
    if reclaim_at is not None:
        structures.append(
            {
                **source_touch,
                "structure_type": "LIQUIDITY_RAID_RECLAIM",
                "structure_created_at": event.raid_at.isoformat(),
                "first_touch_at": reclaim_at.isoformat(),
                "last_touch_at": reclaim_at.isoformat(),
                "reclaim_state": "RECLAIMED",
                "last_structure_before_departure": departure is None,
            }
        )
        sequence.append(
            {
                "order": len(sequence) + 1,
                "structure_type": "LIQUIDITY_RAID_RECLAIM",
                "timestamp": reclaim_at.isoformat(),
                "state": "RECLAIM",
            }
        )
    if departure is not None:
        structures.append(
            {
                **source_touch,
                "structure_type": "CISD_RELATED_STRUCTURE",
                "detector_version": "CAUSAL_CISD_V1",
                "structure_created_at": event.source_opened_at.isoformat(),
                "first_touch_at": departure.isoformat(),
                "last_touch_at": departure.isoformat(),
                "price_low": None,
                "price_high": None,
                "penetration_depth_ticks": None,
                "reclaim_state": "CISD_CONFIRMED",
                "dwell_minutes": event.cisd_latency_minutes,
                "last_structure_before_departure": True,
            }
        )
        sequence.append(
            {
                "order": len(sequence) + 1,
                "structure_type": "CISD_RELATED_STRUCTURE",
                "timestamp": departure.isoformat(),
                "state": "DEPARTURE_CONFIRMATION",
            }
        )
    pre_departure = {
        "schema": PRE_DEPARTURE_SCHEMA,
        "identity": IDENTITY,
        "episode_id": episode_id,
        "event_id": event_id,
        "symbol": event.symbol,
        "sequence": sequence,
        "sequence_status": "DETERMINISTIC_SUPPORTED_SUBSET",
        "unsupported_structure_policy": "UNRESOLVED_STRUCTURE",
        "causal_feature": True,
        "outcome_only": False,
    }
    timing = {
        "schema": DEPARTURE_TIMING_SCHEMA,
        "identity": IDENTITY,
        "episode_id": episode_id,
        "event_id": event_id,
        "symbol": event.symbol,
        "structure_appearance_at": event.reference_opened_at.isoformat(),
        "first_touch_at": event.raid_at.isoformat(),
        "departure_at": None if departure is None else departure.isoformat(),
        "minutes_structure_creation_to_first_touch": int(
            (event.raid_at - event.reference_opened_at).total_seconds() // 60
        ),
        "minutes_source_event_to_departure": (
            None
            if departure is None
            else int((departure - event.raid_at).total_seconds() // 60)
        ),
        "reclaim_latency_minutes": event.reclaim_latency_minutes,
        "cisd_latency_minutes": event.cisd_latency_minutes,
        "ny_minute_of_day": event.ny_minute_of_day,
        "weekday": event.raid_at.astimezone(NY).strftime("%A"),
        "session_bucket": event.session_bucket,
        "causal_feature": True,
        "outcome_only": False,
    }
    target = {
        "schema": TARGET_DESTINATION_SCHEMA,
        "identity": IDENTITY,
        "episode_id": episode_id,
        "event_id": event_id,
        "symbol": event.symbol,
        "candidate_known_at_raid": True,
        "candidate_type": "OPPOSITE_SOURCE_BOUNDARY",
        "candidate_price": str(event.opposite_reference),
        "candidate_distance_ticks": str(
            abs(event.opposite_reference - event.reference_level) / event.tick_size
        ),
        "first_objective_touched_24h": event.opposite_reference_hit_24h,
        "first_objective_touch_at": (
            None if opposite_hit_at is None else opposite_hit_at.isoformat()
        ),
        "time_to_first_objective_minutes": event.opposite_reference_hit_minutes,
        "mfe_24h_ticks": str(event.mfe_1440m_ticks),
        "mae_24h_ticks": str(event.mae_1440m_ticks),
        "candidate_fields_causal": True,
        "result_fields_outcome_only": True,
        "causal_feature": False,
        "outcome_only": True,
    }
    return {
        "MARKET_JOURNEY_LEDGER": [market],
        "STRUCTURE_TOUCH_LEDGER": structures,
        "PRE_DEPARTURE_SEQUENCE_LEDGER": [pre_departure],
        "DEPARTURE_TIMING_LEDGER": [timing],
        "TARGET_DESTINATION_LEDGER": [target],
    }


def _ny_day(moment: datetime) -> date:
    return moment.astimezone(NY).date()


def daily_path_rows(evidence: Evidence) -> list[dict[str, Any]]:
    grouped: dict[date, list[Bar]] = defaultdict(list)
    for bar in evidence.bars:
        grouped[_ny_day(bar.opened_at)].append(bar)
    rows: list[dict[str, Any]] = []
    for day, raw in sorted(grouped.items()):
        bars = sorted(raw, key=lambda item: item.opened_at)
        high_bar = max(bars, key=lambda item: item.high)
        low_bar = min(bars, key=lambda item: item.low)
        total_path = sum(
            (
                abs(right.close - left.close)
                for left, right in zip(bars, bars[1:], strict=False)
            ),
            Decimal(0),
        )
        displacement = bars[-1].close - bars[0].open
        overlap_count = sum(
            min(left.high, right.high) >= max(left.low, right.low)
            for left, right in zip(bars, bars[1:], strict=False)
        )
        span = high_bar.high - low_bar.low
        rows.append(
            {
                "schema": DAILY_PATH_SCHEMA,
                "identity": IDENTITY,
                "symbol": evidence.symbol,
                "ny_date": day.isoformat(),
                "weekday": day.strftime("%A"),
                "bars": len(bars),
                "open": str(bars[0].open),
                "high": str(high_bar.high),
                "low": str(low_bar.low),
                "close": str(bars[-1].close),
                "total_range": str(span),
                "directional_displacement": str(displacement),
                "path_efficiency": (
                    None if total_path == 0 else str(abs(displacement) / total_path)
                ),
                "overlap_fraction": overlap_count / max(len(bars) - 1, 1),
                "realized_close_to_close_path": str(total_path),
                "daily_high_at": high_bar.opened_at.isoformat(),
                "daily_low_at": low_bar.opened_at.isoformat(),
                "close_location": (
                    None if span == 0 else str((bars[-1].close - low_bar.low) / span)
                ),
                "compression_duration_minutes": None,
                "expansion_duration_minutes": None,
                "first_material_expansion_at": None,
                "regime_state": "UNRESOLVED_STRUCTURE",
                "categorical_state_reason": "NO_FROZEN_GENERIC_REGIME_THRESHOLD",
                "causal_feature": False,
                "outcome_only": True,
            }
        )
    return rows


def build_symbol_journey(source: Path, output: Path) -> dict[str, Any]:
    evidence, provenance = load_raw_m5(source)
    fast.install()
    events = behavior.extract_events(
        evidence,
        asset_class=ASSET_CLASS[evidence.symbol],
        provider=str(provenance["provider_symbol"]),
        evidence_id=f"atlas10y:{SOURCE_RUN_ID}:{SOURCE_GIT_SHA}:{evidence.symbol}",
    )
    ledgers: dict[str, list[dict[str, Any]]] = {name: [] for name in LEDGER_NAMES}
    for event in events:
        for name, rows in event_ledgers(event).items():
            ledgers[name].extend(rows)
    ledgers["DAILY_PATH_LEDGER"] = daily_path_rows(evidence)
    ledgers["TRADER_MARKET_SYNC_LEDGER"] = []
    output.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    hashes: dict[str, str] = {}
    for name in LEDGER_NAMES:
        path = output / f"{name}.jsonl"
        counts[name] = _write_jsonl(path, ledgers[name])
        hashes[name] = _sha256(path)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "identity": IDENTITY,
        "source_identity": SOURCE_IDENTITY,
        "source_run_id": SOURCE_RUN_ID,
        "source_git_sha": SOURCE_GIT_SHA,
        "symbol": evidence.symbol,
        "provider_symbol": provenance["provider_symbol"],
        "digits": provenance["digits"],
        "pip_position": provenance["pip_position"],
        "retained_m5_bars": provenance["retained_bars"],
        "earliest_observed_m5": provenance["earliest_observed_m5"],
        "latest_observed_m5": provenance["latest_observed_m5"],
        "behavior_event_count": len(events),
        "ledger_counts": counts,
        "ledger_sha256": hashes,
        "structure_coverage": "DETERMINISTIC_SUPPORTED_SUBSET_FAIL_CLOSED",
        "unsupported_structure_policy": "UNRESOLVED_STRUCTURE",
        "trader_sync_status": "UNLINKED_NO_TRADER_DECISION_STREAM",
        "research_evidence_consumed": True,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    (output / "journey-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _parse_departure(row: dict[str, Any]) -> datetime | None:
    raw = row.get("departure_at")
    return None if raw is None else _dt(str(raw))


def cross_index_rows(
    nas100: Sequence[dict[str, Any]],
    sp500: Sequence[dict[str, Any]],
    us30: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    populations = {"NAS100": nas100, "SP500": sp500, "US30": us30}
    indexed: dict[str, list[tuple[datetime, dict[str, Any]]]] = {}
    for symbol, rows in populations.items():
        indexed[symbol] = sorted(
            (
                (departure, row)
                for row in rows
                if (departure := _parse_departure(row)) is not None
            ),
            key=lambda pair: pair[0],
        )
    result: list[dict[str, Any]] = []
    for symbol, pairs in indexed.items():
        for departure, row in pairs:
            peers: dict[str, Any] = {}
            for peer_symbol, peer_pairs in indexed.items():
                if peer_symbol == symbol or not peer_pairs:
                    continue
                nearest_at, nearest = min(
                    peer_pairs,
                    key=lambda pair: abs((pair[0] - departure).total_seconds()),
                )
                delta = int((nearest_at - departure).total_seconds() // 60)
                within = abs(delta) <= 120
                peers[peer_symbol] = {
                    "episode_id": nearest["episode_id"] if within else None,
                    "departure_at": nearest_at.isoformat() if within else None,
                    "lead_lag_minutes": delta if within else None,
                    "agreement": row.get("side") == nearest.get("side") if within else None,
                    "comparison_window_minutes": 120,
                }
            result.append(
                {
                    "schema": CROSS_INDEX_SCHEMA,
                    "identity": IDENTITY,
                    "episode_id": row["episode_id"],
                    "symbol": symbol,
                    "departure_at": departure.isoformat(),
                    "side": row.get("side"),
                    "peer_states": peers,
                    "association_only": True,
                    "causal_feature": False,
                    "outcome_only": True,
                }
            )
    result.sort(key=lambda item: (item["departure_at"], item["symbol"]))
    return result


def build_cross_index(
    nas100: Path, sp500: Path, us30: Path, output: Path
) -> dict[str, Any]:
    rows = cross_index_rows(
        _read_jsonl(nas100), _read_jsonl(sp500), _read_jsonl(us30)
    )
    output.mkdir(parents=True, exist_ok=True)
    path = output / "CROSS_INDEX_JOURNEY_LEDGER.jsonl"
    count = _write_jsonl(path, rows)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "identity": IDENTITY,
        "source_run_id": SOURCE_RUN_ID,
        "source_git_sha": SOURCE_GIT_SHA,
        "ledger": "CROSS_INDEX_JOURNEY_LEDGER",
        "rows": count,
        "sha256": _sha256(path),
        "lead_lag_evidence_tier": "E1_ASSOCIATION_ONLY",
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    (output / "cross-index-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="QORE CIBO Market Journey Layer V1")
    sub = parser.add_subparsers(dest="command", required=True)
    symbol = sub.add_parser("symbol")
    symbol.add_argument("source", type=Path)
    symbol.add_argument("output", type=Path)
    cross = sub.add_parser("cross-index")
    cross.add_argument("nas100", type=Path)
    cross.add_argument("sp500", type=Path)
    cross.add_argument("us30", type=Path)
    cross.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "symbol":
        result = build_symbol_journey(args.source, args.output)
    else:
        result = build_cross_index(args.nas100, args.sp500, args.us30, args.output)
    print(json.dumps(result, sort_keys=True, default=_json_default))


if __name__ == "__main__":
    main()
