"""XAUUSD Market Intelligence Dossier over consumed CIBO evidence.

This layer is research-only. It describes XAUUSD behavior from the already
consumed ten-year corpus and Target Destination V2 without promoting a trading
rule. Unsupported concepts remain explicit unresolved states rather than being
filled with retrospective thresholds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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

IDENTITY = "CIBO_XAUUSD_MARKET_INTELLIGENCE_DOSSIER_V1"
SYMBOL = "XAUUSD"
SOURCE_M5_RUN_ID = 35166210458
SOURCE_M5_GIT_SHA = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
SOURCE_JOURNEY_RUN_ID = 35175979474
SOURCE_JOURNEY_GIT_SHA = "9cc0f17a2f30846d61b242132547f39391909656"
TARGET_IDENTITY = "CIBO_TARGET_DESTINATION_V2_SUPPORTED_REFERENCE_UNIVERSE"
EVIDENCE_TIER = "E1_ASSOCIATION_ONLY"


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
        raise ValueError(f"expected exactly one {name}, found {len(paths)}")
    return paths[0]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
        "evidence_tier": EVIDENCE_TIER,
        "reclaim_rate": _rate([item.same_source_reclaim for item in events]),
        "cisd_rate": _rate([item.cisd_confirmed for item in events]),
        "fvg_after_raid_rate": _rate([item.fvg_after_raid for item in events]),
        "opposite_source_boundary_hit_24h_rate": _rate(
            [item.opposite_reference_hit_24h for item in events]
        ),
        "exact_equal_liquidity_rate": _rate(
            [item.exact_equal_count > 1 for item in events]
        ),
        "exact_c2_eligible_prior_candle_events": len(c2),
        "exact_c2_closure_rate": _rate([bool(value) for value in c2]),
        "median_reclaim_latency_minutes": _median_int(reclaim_latencies),
        "median_cisd_latency_minutes": _median_int(cisd_latencies),
        "median_protected_swing_distance_ticks": _median_decimal(protected),
        "median_raid_depth_ticks": _median_decimal(
            [item.raid_depth_ticks for item in events]
        ),
        "median_mfe_240m_ticks": _median_decimal(
            [item.mfe_240m_ticks for item in events]
        ),
        "median_mae_240m_ticks": _median_decimal(
            [item.mae_240m_ticks for item in events]
        ),
        "median_mfe_1440m_ticks": _median_decimal(
            [item.mfe_1440m_ticks for item in events]
        ),
        "median_mae_1440m_ticks": _median_decimal(
            [item.mae_1440m_ticks for item in events]
        ),
    }


def _grouped(
    observations: Sequence[Observation],
    key: Callable[[Observation], str],
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[Observation]] = defaultdict(list)
    for row in observations:
        groups[key(row)].append(row)
    return {name: _observation_summary(rows) for name, rows in sorted(groups.items())}


def _target_summary(root: Path) -> dict[str, Any]:
    manifest = _read_json(_single(root, "target-destination-v2-manifest.json"))
    if manifest.get("identity") != TARGET_IDENTITY or manifest.get("symbol") != SYMBOL:
        raise ValueError("unexpected Target Destination V2 source")
    family_counts: Counter[str] = Counter()
    family_touches: Counter[str] = Counter()
    family_times: dict[str, list[int]] = defaultdict(list)
    family_distances: dict[str, list[Decimal]] = defaultdict(list)
    timeframe_counts: Counter[str] = Counter()
    timeframe_touches: Counter[str] = Counter()
    candidates: dict[str, tuple[str, str]] = {}
    for row in _read_jsonl(_single(root, "TARGET_DESTINATION_LEDGER_V2.jsonl")):
        kind = str(row["candidate_type"])
        timeframe = str(row["source_timeframe"])
        candidate_id = str(row["candidate_id"])
        candidates[candidate_id] = (kind, timeframe)
        family_counts[kind] += 1
        timeframe_counts[timeframe] += 1
        family_distances[kind].append(Decimal(str(row["candidate_distance_ticks"])))
        if bool(row["touch_within_24h"]):
            family_touches[kind] += 1
            timeframe_touches[timeframe] += 1
            family_times[kind].append(int(row["time_to_touch_minutes"]))
    first_family: Counter[str] = Counter()
    episodes = 0
    episodes_with_touch = 0
    tied_first = 0
    active_counts: list[int] = []
    for row in _read_jsonl(_single(root, "TARGET_DESTINATION_EPISODE_V2.jsonl")):
        episodes += 1
        active_counts.append(int(row["active_candidate_count"]))
        first_ids = [str(value) for value in row["first_touch_candidate_ids"]]
        if first_ids:
            episodes_with_touch += 1
        if bool(row["first_touch_tied"]):
            tied_first += 1
        for candidate_id in first_ids:
            kind, _ = candidates[candidate_id]
            first_family[kind] += 1
    families: dict[str, Any] = {}
    for kind in sorted(family_counts):
        count = family_counts[kind]
        touched = family_touches[kind]
        families[kind] = {
            "candidate_rows": count,
            "touch_rate_24h": touched / count,
            "median_time_to_touch_minutes": _median_int(family_times[kind]),
            "median_distance_ticks": _median_decimal(family_distances[kind]),
            "first_touch_memberships": first_family[kind],
            "evidence_tier": EVIDENCE_TIER,
        }
    timeframes: dict[str, Any] = {}
    for timeframe in sorted(timeframe_counts):
        count = timeframe_counts[timeframe]
        timeframes[timeframe] = {
            "candidate_rows": count,
            "touch_rate_24h": timeframe_touches[timeframe] / count,
            "evidence_tier": EVIDENCE_TIER,
        }
    return {
        "manifest": manifest,
        "episodes": episodes,
        "episodes_with_any_supported_target_touch_24h_rate": (
            episodes_with_touch / episodes if episodes else None
        ),
        "median_active_supported_targets_per_episode": _median_int(active_counts),
        "first_touch_tied_episode_rows": tied_first,
        "candidate_family": families,
        "timeframe": timeframes,
        "complete_all_dol_claim": False,
    }


def _daily_path_summary(root: Path) -> dict[str, Any]:
    rows = list(_read_jsonl(_single(root, "DAILY_PATH_LEDGER.jsonl")))
    efficiencies = [
        Decimal(str(row["path_efficiency"]))
        for row in rows
        if row.get("path_efficiency") is not None
    ]
    overlaps = [Decimal(str(row["overlap_fraction"])) for row in rows]
    years: Counter[str] = Counter(str(row["ny_date"])[:4] for row in rows)
    return {
        "days": len(rows),
        "median_path_efficiency": _median_decimal(efficiencies),
        "median_overlap_fraction": _median_decimal(overlaps),
        "days_by_year": dict(sorted(years.items())),
        "regime_detector_status": "UNRESOLVED_NO_FROZEN_GENERIC_REGIME_THRESHOLD",
        "evidence_tier": EVIDENCE_TIER,
    }


def _sequence_summary(root: Path) -> dict[str, Any]:
    signatures: Counter[str] = Counter()
    for row in _read_jsonl(_single(root, "PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl")):
        sequence = row.get("sequence", [])
        signature = " > ".join(str(item.get("state")) for item in sequence)
        signatures[signature] += 1
    return {
        "supported_sequence_signatures": dict(signatures.most_common()),
        "coverage": "DETERMINISTIC_SUPPORTED_SUBSET_FAIL_CLOSED",
        "evidence_tier": EVIDENCE_TIER,
    }


def build_dossier(
    raw_source: Path,
    journey_source: Path,
    target_source: Path,
    output: Path,
    *,
    target_workflow_run_id: int,
    target_git_sha: str,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_source)
    if evidence.symbol != SYMBOL:
        raise ValueError(f"expected {SYMBOL}, got {evidence.symbol}")
    journey_manifest = _read_json(_single(journey_source, "journey-manifest.json"))
    if journey_manifest.get("symbol") != SYMBOL:
        raise ValueError("unexpected Journey source symbol")
    if journey_manifest.get("source_run_id") != SOURCE_M5_RUN_ID:
        raise ValueError("unexpected Journey source run")

    fast.install()
    events = behavior.extract_events(
        evidence,
        asset_class="metal",
        provider=str(provenance["provider_symbol"]),
        evidence_id=f"xau-dossier:{SOURCE_M5_RUN_ID}:{SOURCE_M5_GIT_SHA}",
    )
    if len(events) != int(journey_manifest["behavior_event_count"]):
        raise ValueError("Behavior event count does not reproduce Journey evidence")

    frames = _frames(evidence.bars)
    frame_index = {
        timeframe: {candle.opened_at: candle for candle in candles}
        for timeframe, candles in frames.items()
    }
    observations = [
        Observation(item, _exact_c2_closure(item, frame_index)) for item in events
    ]
    exact_c2 = [row for row in observations if row.exact_c2_closure is True]
    exact_c2_cisd = [row for row in exact_c2 if row.event.cisd_confirmed]
    exact_c2_no_cisd = [row for row in exact_c2 if not row.event.cisd_confirmed]

    target = _target_summary(target_source)
    target_manifest = target["manifest"]
    resolved_departures = sum(item.cisd_confirmed for item in events)
    if int(target_manifest["resolved_departures"]) != resolved_departures:
        raise ValueError("Target V2 departure population does not match Behavior evidence")

    dossier: dict[str, Any] = {
        "schema": "qore.cibo.xauusd.market_intelligence_dossier.v1",
        "identity": IDENTITY,
        "symbol": SYMBOL,
        "evidence_status": "CONSUMED_RESEARCH_EVIDENCE",
        "source_m5_run_id": SOURCE_M5_RUN_ID,
        "source_m5_git_sha": SOURCE_M5_GIT_SHA,
        "source_journey_run_id": SOURCE_JOURNEY_RUN_ID,
        "source_journey_git_sha": SOURCE_JOURNEY_GIT_SHA,
        "source_target_workflow_run_id": target_workflow_run_id,
        "source_target_git_sha": target_git_sha,
        "retained_m5_bars": provenance["retained_bars"],
        "behavior_events": len(events),
        "overall": _observation_summary(observations),
        "by_timeframe": _grouped(observations, lambda row: row.event.timeframe),
        "by_reference_type": _grouped(observations, lambda row: row.event.reference_type),
        "by_side": _grouped(observations, lambda row: row.event.side),
        "by_session": _grouped(observations, lambda row: row.event.session_bucket),
        "by_weekday": _grouped(
            observations, lambda row: row.event.raid_at.strftime("%A")
        ),
        "by_year": _grouped(observations, lambda row: str(row.event.raid_at.year)),
        "by_quarter": _grouped(
            observations,
            lambda row: (
                f"{row.event.raid_at.year}-Q{((row.event.raid_at.month - 1) // 3) + 1}"
            ),
        ),
        "by_prior_body_alignment": _grouped(
            observations, lambda row: row.event.prior_body_alignment
        ),
        "equal_liquidity_association": _grouped(
            observations,
            lambda row: "EXACT_EQUAL" if row.event.exact_equal_count > 1 else "NOT_EXACT_EQUAL",
        ),
        "fvg_after_raid_association": _grouped(
            observations,
            lambda row: "FVG_PRESENT" if row.event.fvg_after_raid else "FVG_ABSENT",
        ),
        "exact_c2": {
            "definition": {
                "long": "source.low < prior.low and source.close > prior.low",
                "short": "source.high > prior.high and source.close < prior.high",
                "scope": "PRIOR_CANDLE_REFERENCE_ONLY",
            },
            "all_exact_c2": _observation_summary(exact_c2),
            "cisd_confirmed": _observation_summary(exact_c2_cisd),
            "cisd_not_confirmed": _observation_summary(exact_c2_no_cisd),
            "comparison_status": EVIDENCE_TIER,
            "c3_status": "UNRESOLVED_NO_FROZEN_C3_CONTRACT_IN_CURRENT_DOSSIER",
        },
        "target_destination_v2": target,
        "daily_path": _daily_path_summary(journey_source),
        "pre_departure_sequences": _sequence_summary(journey_source),
        "protected_swing_scope": (
            "DISTANCE_DISTRIBUTIONS_ONLY_NO_TRADER_STOP_CONTRACT_YET"
        ),
        "stop_recovery_scope": (
            "UNRESOLVED_UNTIL_TRADER_ENTRY_AND_STOP_CONTRACT_ARE_FROZEN"
        ),
        "regime_scope": "UNRESOLVED_NO_FROZEN_GENERIC_REGIME_DETECTOR",
        "hypothesis_status": {
            "exact_c2_plus_cisd": EVIDENCE_TIER,
            "exact_equal_liquidity": EVIDENCE_TIER,
            "fvg_after_raid": EVIDENCE_TIER,
            "prior_body_alignment": EVIDENCE_TIER,
            "supported_target_family": EVIDENCE_TIER,
        },
        "rule_promotion_allowed": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    path = output / "xauusd-market-intelligence-dossier-v1.json"
    path.write_text(json.dumps(dossier, indent=2, sort_keys=True) + "\n")
    manifest = {
        "identity": IDENTITY,
        "symbol": SYMBOL,
        "dossier_sha256": _sha256(path),
        "retained_m5_bars": provenance["retained_bars"],
        "behavior_events": len(events),
        "resolved_departures": resolved_departures,
        "target_workflow_run_id": target_workflow_run_id,
        "target_git_sha": target_git_sha,
        "evidence_status": "CONSUMED_RESEARCH_EVIDENCE",
        "highest_automatic_evidence_tier": EVIDENCE_TIER,
        "rule_promotion_allowed": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    manifest_path = output / "xauusd-market-intelligence-manifest-v1.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="CIBO XAUUSD Market Intelligence Dossier V1")
    parser.add_argument("raw_source", type=Path)
    parser.add_argument("journey_source", type=Path)
    parser.add_argument("target_source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--target-workflow-run-id", type=int, required=True)
    parser.add_argument("--target-git-sha", required=True)
    args = parser.parse_args()
    result = build_dossier(
        args.raw_source,
        args.journey_source,
        args.target_source,
        args.output,
        target_workflow_run_id=args.target_workflow_run_id,
        target_git_sha=args.target_git_sha,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
