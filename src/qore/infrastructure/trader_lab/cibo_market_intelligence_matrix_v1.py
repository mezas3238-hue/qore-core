"""CIBO 12-market intelligence matrix over consumed research evidence.

Research-only aggregation. The matrix compares already-consumed CIBO evidence
without promoting associations into operating rules. Unsupported concepts remain
explicitly unresolved.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab import cibo_market_atlas_journey_extractor_v1 as journey
from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab as behavior
from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab_fast_runner as fast
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Side,
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "CIBO_12_MARKET_INTELLIGENCE_MATRIX_V1"
SOURCE_M5_RUN_ID = 35166210458
SOURCE_M5_GIT_SHA = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
SOURCE_JOURNEY_RUN_ID = 35175979474
SOURCE_JOURNEY_GIT_SHA = "9cc0f17a2f30846d61b242132547f39391909656"
SOURCE_TARGET_RUN_ID = 35204892665
SOURCE_TARGET_GIT_SHA = "2f510461b3360e91d5ee70a72716a76cd6561f16"
TARGET_IDENTITY = "CIBO_TARGET_DESTINATION_V2_SUPPORTED_REFERENCE_UNIVERSE"
EVIDENCE_TIER = "E1_ASSOCIATION_ONLY"
SYMBOLS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
    "NAS100",
    "SP500",
    "US30",
    "XAUUSD",
    "XAGUSD",
)
TARGET_FAMILIES = (
    "SOURCE_OPPOSITE_BOUNDARY",
    "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY",
    "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
)


@dataclass(frozen=True, slots=True)
class Observation:
    event: behavior.Event
    exact_c2_closure: bool | None


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected object in {path}")
    return payload


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError(f"expected object row in {path}")
                yield payload


def _single(root: Path, name: str) -> Path:
    paths = list(root.rglob(name))
    if len(paths) != 1:
        raise ValueError(f"expected exactly one {name} under {root}, found {len(paths)}")
    return paths[0]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact_dir(root: Path, symbol: str, required_name: str) -> Path:
    candidates: list[Path] = []
    for path in root.rglob(required_name):
        if symbol.lower() in str(path.parent).lower():
            candidates.append(path.parent)
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        exact = [p for p in candidates if f"-{symbol.lower()}-" in str(p).lower()]
        if len(exact) == 1:
            return exact[0]
    raise ValueError(
        f"cannot uniquely locate {required_name} for {symbol} under {root}; "
        f"candidates={len(candidates)}"
    )


def _asset_class(symbol: str) -> str:
    if symbol in {"NAS100", "SP500", "US30"}:
        return "index"
    if symbol in {"XAUUSD", "XAGUSD"}:
        return "metal"
    if symbol in {"AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD", "USDCAD", "USDJPY"}:
        return "forex"
    raise ValueError(f"unsupported symbol: {symbol}")


def _frames(bars: tuple[Bar, ...]) -> dict[str, tuple[SourceCandle, ...]]:
    h4 = build_h4(bars)
    return {"H1": build_h1(bars), "H4": h4, "D1": build_daily(h4)}


def _exact_c2_closure(
    event: behavior.Event,
    frame_index: dict[str, dict[datetime, SourceCandle]],
) -> bool | None:
    if event.reference_type != "prior-candle":
        return None
    source = frame_index.get(event.timeframe, {}).get(event.source_opened_at)
    if source is None:
        raise ValueError("source candle missing for prior-candle event")
    if event.side == Side.LONG.value:
        return source.low < event.reference_level and source.close > event.reference_level
    if event.side == Side.SHORT.value:
        return source.high > event.reference_level and source.close < event.reference_level
    raise ValueError(f"unsupported side: {event.side}")


def _rate(values: Sequence[bool]) -> float | None:
    return None if not values else sum(values) / len(values)


def _median_decimal(values: Sequence[Decimal]) -> str | None:
    return None if not values else str(median(values))


def _median_int(values: Sequence[int]) -> float | None:
    return None if not values else float(median(values))


def _observation_summary(rows: Sequence[Observation]) -> dict[str, Any]:
    events = [row.event for row in rows]
    c2 = [row.exact_c2_closure for row in rows if row.exact_c2_closure is not None]
    reclaim_latencies = [
        item.reclaim_latency_minutes
        for item in events
        if item.reclaim_latency_minutes is not None
    ]
    cisd_latencies = [
        item.cisd_latency_minutes for item in events if item.cisd_latency_minutes is not None
    ]
    protected = [
        item.protected_swing_distance_ticks
        for item in events
        if item.protected_swing_distance_ticks is not None
    ]
    return {
        "events": len(events),
        "reclaim_rate": _rate([item.same_source_reclaim for item in events]),
        "cisd_rate": _rate([item.cisd_confirmed for item in events]),
        "fvg_after_raid_rate": _rate([item.fvg_after_raid for item in events]),
        "opposite_source_boundary_hit_24h_rate": _rate(
            [item.opposite_reference_hit_24h for item in events]
        ),
        "exact_equal_liquidity_rate": _rate([item.exact_equal_count > 1 for item in events]),
        "exact_c2_eligible_prior_candle_events": len(c2),
        "exact_c2_closure_rate": _rate([bool(value) for value in c2]),
        "median_reclaim_latency_minutes": _median_int(reclaim_latencies),
        "median_cisd_latency_minutes": _median_int(cisd_latencies),
        "median_protected_swing_distance_ticks": _median_decimal(protected),
        "median_raid_depth_ticks": _median_decimal([item.raid_depth_ticks for item in events]),
        "median_mfe_240m_ticks": _median_decimal([item.mfe_240m_ticks for item in events]),
        "median_mae_240m_ticks": _median_decimal([item.mae_240m_ticks for item in events]),
        "median_mfe_1440m_ticks": _median_decimal([item.mfe_1440m_ticks for item in events]),
        "median_mae_1440m_ticks": _median_decimal([item.mae_1440m_ticks for item in events]),
        "evidence_tier": EVIDENCE_TIER,
    }


def _grouped(
    observations: Sequence[Observation], key: Callable[[Observation], str]
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[Observation]] = defaultdict(list)
    for row in observations:
        groups[key(row)].append(row)
    return {name: _observation_summary(rows) for name, rows in sorted(groups.items())}


def _target_summary(root: Path, symbol: str) -> dict[str, Any]:
    manifest = _read_json(_single(root, "target-destination-v2-manifest.json"))
    if manifest.get("identity") != TARGET_IDENTITY or manifest.get("symbol") != symbol:
        raise ValueError(f"unexpected Target Destination V2 source for {symbol}")
    family_counts: Counter[str] = Counter()
    family_touches: Counter[str] = Counter()
    family_times: dict[str, list[int]] = defaultdict(list)
    family_distances: dict[str, list[Decimal]] = defaultdict(list)
    active_counts: list[int] = []
    episodes = 0
    episodes_with_touch = 0
    for row in _read_jsonl(_single(root, "TARGET_DESTINATION_LEDGER_V2.jsonl")):
        kind = str(row["candidate_type"])
        family_counts[kind] += 1
        family_distances[kind].append(Decimal(str(row["candidate_distance_ticks"])))
        if bool(row["touch_within_24h"]):
            family_touches[kind] += 1
            family_times[kind].append(int(row["time_to_touch_minutes"]))
    for row in _read_jsonl(_single(root, "TARGET_DESTINATION_EPISODE_V2.jsonl")):
        episodes += 1
        active_counts.append(int(row["active_candidate_count"]))
        if row["first_touch_candidate_ids"]:
            episodes_with_touch += 1
    families: dict[str, dict[str, Any]] = {}
    for kind in sorted(family_counts):
        count = family_counts[kind]
        families[kind] = {
            "candidate_rows": count,
            "touch_rate_24h": family_touches[kind] / count,
            "median_time_to_touch_minutes": _median_int(family_times[kind]),
            "median_distance_ticks": _median_decimal(family_distances[kind]),
            "evidence_tier": EVIDENCE_TIER,
        }
    return {
        "episodes": episodes,
        "episodes_with_any_supported_target_touch_24h_rate": (
            episodes_with_touch / episodes if episodes else None
        ),
        "median_active_supported_targets_per_episode": _median_int(active_counts),
        "candidate_family": families,
        "complete_all_dol_claim": False,
    }


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _scalar(group: dict[str, dict[str, Any]], key: str, metric: str) -> Any:
    return group.get(key, {}).get(metric)


def _target_scalar(target: dict[str, Any], family: str, metric: str) -> Any:
    families = target.get("candidate_family", {})
    if not isinstance(families, dict):
        return None
    row = families.get(family, {})
    return row.get(metric) if isinstance(row, dict) else None


def _headline_row(
    symbol: str,
    retained_bars: int,
    observations: Sequence[Observation],
    groups: dict[str, dict[str, dict[str, Any]]],
    target: dict[str, Any],
) -> dict[str, Any]:
    overall = _observation_summary(observations)
    row: dict[str, Any] = {
        "symbol": symbol,
        "asset_class": _asset_class(symbol),
        "retained_m5_bars": retained_bars,
        "behavior_events": overall["events"],
        "long_events": _scalar(groups["side"], "long", "events"),
        "short_events": _scalar(groups["side"], "short", "events"),
        "long_cisd_rate": _scalar(groups["side"], "long", "cisd_rate"),
        "short_cisd_rate": _scalar(groups["side"], "short", "cisd_rate"),
        "h1_events": _scalar(groups["timeframe"], "H1", "events"),
        "h4_events": _scalar(groups["timeframe"], "H4", "events"),
        "d1_events": _scalar(groups["timeframe"], "D1", "events"),
        "asia_events": _scalar(groups["session"], "asia", "events"),
        "london_events": _scalar(groups["session"], "london", "events"),
        "new_york_events": _scalar(groups["session"], "new-york", "events"),
        "other_session_events": _scalar(groups["session"], "other", "events"),
        "median_raid_depth_ticks": overall["median_raid_depth_ticks"],
        "median_reclaim_latency_minutes": overall["median_reclaim_latency_minutes"],
        "median_cisd_latency_minutes": overall["median_cisd_latency_minutes"],
        "median_protected_swing_distance_ticks": overall["median_protected_swing_distance_ticks"],
        "fvg_after_raid_rate": overall["fvg_after_raid_rate"],
        "median_mfe_240m_ticks": overall["median_mfe_240m_ticks"],
        "median_mae_240m_ticks": overall["median_mae_240m_ticks"],
        "median_mfe_1440m_ticks": overall["median_mfe_1440m_ticks"],
        "median_mae_1440m_ticks": overall["median_mae_1440m_ticks"],
        "exact_c2_eligible_events": overall["exact_c2_eligible_prior_candle_events"],
        "exact_c2_closure_rate": overall["exact_c2_closure_rate"],
        "c3_status": "UNRESOLVED_NO_FROZEN_C3_CONTRACT",
        "target_any_supported_touch_24h_rate": target[
            "episodes_with_any_supported_target_touch_24h_rate"
        ],
        "median_active_supported_targets": target["median_active_supported_targets_per_episode"],
        "evidence_tier": EVIDENCE_TIER,
        "rule_promotion_allowed": False,
    }
    for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"):
        row[f"weekday_{day.lower()}_events"] = _scalar(groups["weekday"], day, "events") or 0
        row[f"weekday_{day.lower()}_cisd_rate"] = _scalar(groups["weekday"], day, "cisd_rate")
    for family in TARGET_FAMILIES:
        prefix = _slug(family)
        row[f"target_{prefix}_touch_rate_24h"] = _target_scalar(target, family, "touch_rate_24h")
        row[f"target_{prefix}_median_distance_ticks"] = _target_scalar(target, family, "median_distance_ticks")
        row[f"target_{prefix}_median_time_to_touch_minutes"] = _target_scalar(
            target, family, "median_time_to_touch_minutes"
        )
    for alignment, summary in groups["prior_body_alignment"].items():
        prefix = _slug(alignment)
        row[f"prior_body_{prefix}_events"] = summary["events"]
        row[f"prior_body_{prefix}_cisd_rate"] = summary["cisd_rate"]
    return row


def _write_csv(rows: Sequence[dict[str, Any]], path: Path) -> None:
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_matrix(raw_root: Path, journey_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    fast.install()
    headline_rows: list[dict[str, Any]] = []
    market_detail: dict[str, Any] = {}
    for symbol in SYMBOLS:
        raw_source = _artifact_dir(raw_root, symbol, "manifest.json")
        journey_source = _artifact_dir(journey_root, symbol, "journey-manifest.json")
        target_source = _artifact_dir(target_root, symbol, "target-destination-v2-manifest.json")
        evidence, provenance = journey.load_raw_m5(raw_source)
        if evidence.symbol != symbol:
            raise ValueError(f"raw symbol mismatch for {symbol}: {evidence.symbol}")
        journey_manifest = _read_json(_single(journey_source, "journey-manifest.json"))
        if journey_manifest.get("symbol") != symbol:
            raise ValueError(f"journey symbol mismatch for {symbol}")
        if journey_manifest.get("source_run_id") != SOURCE_M5_RUN_ID:
            raise ValueError(f"journey source run mismatch for {symbol}")
        events = behavior.extract_events(
            evidence,
            asset_class=_asset_class(symbol),
            provider=str(provenance["provider_symbol"]),
            evidence_id=f"cibo-matrix:{symbol}:{SOURCE_M5_RUN_ID}:{SOURCE_M5_GIT_SHA}",
        )
        if len(events) != int(journey_manifest["behavior_event_count"]):
            raise ValueError(f"Behavior event count mismatch for {symbol}")
        frames = _frames(evidence.bars)
        frame_index = {
            timeframe: {candle.opened_at: candle for candle in candles}
            for timeframe, candles in frames.items()
        }
        observations = [
            Observation(item, _exact_c2_closure(item, frame_index)) for item in events
        ]
        groups = {
            "side": _grouped(observations, lambda row: row.event.side),
            "timeframe": _grouped(observations, lambda row: row.event.timeframe),
            "session": _grouped(observations, lambda row: row.event.session_bucket),
            "weekday": _grouped(observations, lambda row: row.event.raid_at.strftime("%A")),
            "year": _grouped(observations, lambda row: str(row.event.raid_at.year)),
            "quarter": _grouped(
                observations,
                lambda row: f"{row.event.raid_at.year}-Q{((row.event.raid_at.month - 1) // 3) + 1}",
            ),
            "prior_body_alignment": _grouped(
                observations, lambda row: row.event.prior_body_alignment
            ),
            "fvg": _grouped(
                observations,
                lambda row: "FVG_PRESENT" if row.event.fvg_after_raid else "FVG_ABSENT",
            ),
        }
        target = _target_summary(target_source, symbol)
        resolved_departures = sum(item.cisd_confirmed for item in events)
        target_manifest = _read_json(_single(target_source, "target-destination-v2-manifest.json"))
        if int(target_manifest["resolved_departures"]) != resolved_departures:
            raise ValueError(f"Target V2 departure mismatch for {symbol}")
        overall = _observation_summary(observations)
        detail = {
            "symbol": symbol,
            "asset_class": _asset_class(symbol),
            "retained_m5_bars": int(provenance["retained_bars"]),
            "overall": overall,
            "by_side": groups["side"],
            "by_timeframe": groups["timeframe"],
            "by_session": groups["session"],
            "by_weekday": groups["weekday"],
            "by_year": groups["year"],
            "by_quarter": groups["quarter"],
            "by_prior_body_alignment": groups["prior_body_alignment"],
            "by_fvg_presence": groups["fvg"],
            "target_destination_v2": target,
            "exact_c2_definition": {
                "long": "C2.low < C1.low and C2.close > C1.low",
                "short": "C2.high > C1.high and C2.close < C1.high",
                "scope": "PRIOR_CANDLE_REFERENCE_ONLY",
            },
            "c3_status": "UNRESOLVED_NO_FROZEN_C3_CONTRACT",
            "protected_swing_scope": "DISTANCE_DISTRIBUTIONS_ONLY_NO_TRADER_STOP_CONTRACT",
            "evidence_tier": EVIDENCE_TIER,
            "rule_promotion_allowed": False,
        }
        market_detail[symbol] = detail
        headline_rows.append(
            _headline_row(
                symbol,
                int(provenance["retained_bars"]),
                observations,
                groups,
                target,
            )
        )
    output.mkdir(parents=True, exist_ok=True)
    matrix = {
        "schema": "qore.cibo_market_intelligence.matrix.v1",
        "identity": IDENTITY,
        "evidence_status": "CONSUMED_RESEARCH_EVIDENCE",
        "evidence_tier": EVIDENCE_TIER,
        "source_m5_run_id": SOURCE_M5_RUN_ID,
        "source_m5_git_sha": SOURCE_M5_GIT_SHA,
        "source_journey_run_id": SOURCE_JOURNEY_RUN_ID,
        "source_journey_git_sha": SOURCE_JOURNEY_GIT_SHA,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_git_sha": SOURCE_TARGET_GIT_SHA,
        "symbols": list(SYMBOLS),
        "headline_rows": headline_rows,
        "market_detail": market_detail,
        "c3_status": "UNRESOLVED_NO_FROZEN_C3_CONTRACT",
        "rule_promotion_allowed": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    json_path = output / "cibo-12-market-intelligence-matrix-v1.json"
    csv_path = output / "cibo-12-market-intelligence-matrix-v1.csv"
    json_path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n")
    _write_csv(headline_rows, csv_path)
    manifest = {
        "identity": IDENTITY,
        "markets": len(headline_rows),
        "symbols": list(SYMBOLS),
        "json_sha256": _sha256(json_path),
        "csv_sha256": _sha256(csv_path),
        "source_m5_run_id": SOURCE_M5_RUN_ID,
        "source_journey_run_id": SOURCE_JOURNEY_RUN_ID,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "evidence_status": "CONSUMED_RESEARCH_EVIDENCE",
        "highest_automatic_evidence_tier": EVIDENCE_TIER,
        "c3_status": "UNRESOLVED_NO_FROZEN_C3_CONTRACT",
        "rule_promotion_allowed": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    manifest_path = output / "cibo-12-market-intelligence-matrix-v1-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="CIBO 12-Market Intelligence Matrix V1")
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_matrix(args.raw_root, args.journey_root, args.target_root, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
