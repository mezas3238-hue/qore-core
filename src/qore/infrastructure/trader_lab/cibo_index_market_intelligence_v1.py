"""Full CIBO market-intelligence dossiers for NAS100, SP500 and US30.

The dossiers are market-first and independent of VT08 outcomes. They bind the
validated 12-market matrix to the retained 10Y Journey ledgers and Target
Destination V2 evidence for each index.

The module summarizes retained machine evidence without creating trading rules.
All source observations remain available in their immutable GitHub artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

SCHEMA = "qore.cibo.index_market_intelligence_dossier.v1"
MANIFEST_SCHEMA = "qore.cibo.index_market_intelligence_manifest.v1"
PACKAGE_IDENTITY = "CIBO_INDEX_MARKET_INTELLIGENCE_DOSSIER_V1"
MATRIX_IDENTITY = "CIBO_12_MARKET_INTELLIGENCE_MATRIX_V1"
JOURNEY_IDENTITY = "CIBO_MARKET_JOURNEY_LAYER_V1"
JOURNEY_SUMMARY_IDENTITY = "CIBO_MARKET_JOURNEY_SUMMARY_V1"
TARGET_IDENTITY = "CIBO_TARGET_DESTINATION_V2_SUPPORTED_REFERENCE_UNIVERSE"
EVIDENCE_TIER = "E1_ASSOCIATION_ONLY"

SOURCE_M5_RUN_ID = 35166210458
SOURCE_M5_GIT_SHA = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
SOURCE_JOURNEY_RUN_ID = 35175979474
SOURCE_JOURNEY_GIT_SHA = "9cc0f17a2f30846d61b242132547f39391909656"
SOURCE_TARGET_RUN_ID = 35204892665
SOURCE_TARGET_GIT_SHA = "2f510461b3360e91d5ee70a72716a76cd6561f16"
SOURCE_MATRIX_RUN_ID = 35235739642
SOURCE_MATRIX_GIT_SHA = "0bb28ade6d66de32dfb5390b2c66d318159ad082"
SOURCE_SUMMARY_RUN_ID = 35200408430
SOURCE_SUMMARY_GIT_SHA = "2bdd2fb3e050322fea49b2030e6844e3c9a1f289"

SYMBOLS = ("NAS100", "SP500", "US30")
EXPECTED = {
    "NAS100": {
        "m5": 701457,
        "events": 110471,
        "resolved_departures": 39060,
        "journey_artifact_id": 10479150314,
        "journey_artifact_digest": (
            "sha256:614371a9064f597762985ec1170a80e8a4def763dcb6e813b5f25fc18cc7445e"
        ),
        "target_artifact_id": 10489955740,
        "target_artifact_digest": (
            "sha256:e1f4485d0edcd369983c3ad735235d9a4091e180b219ec4b1ff7a54610e3a86d"
        ),
    },
    "SP500": {
        "m5": 693064,
        "events": 102863,
        "resolved_departures": 31445,
        "journey_artifact_id": 10479255223,
        "journey_artifact_digest": (
            "sha256:2a1403f4705c04f971a09989f62b53064cdb77de381f558b2207265a636ff88b"
        ),
        "target_artifact_id": 10489343403,
        "target_artifact_digest": (
            "sha256:add8dda5afa546072f53e69770ca7e29650714e8f3a2ae123bfd56f49d2961bc"
        ),
    },
    "US30": {
        "m5": 700856,
        "events": 109341,
        "resolved_departures": 38053,
        "journey_artifact_id": 10478955724,
        "journey_artifact_digest": (
            "sha256:6aec5fb866eb4a781f4a6f83edde78762d82fffd7c70c4081e99cb8f49f83796"
        ),
        "target_artifact_id": 10489104194,
        "target_artifact_digest": (
            "sha256:fcd074ba6f8cfffbebd2f273ced6f73822f1f232dc10a2453f4484e852b64629"
        ),
    },
}

JOURNEY_LEDGER_FILES = {
    "market_journey": "MARKET_JOURNEY_LEDGER.jsonl",
    "structure_touch": "STRUCTURE_TOUCH_LEDGER.jsonl",
    "departure_timing": "DEPARTURE_TIMING_LEDGER.jsonl",
    "pre_departure_sequence": "PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl",
    "target_destination_v1": "TARGET_DESTINATION_LEDGER.jsonl",
    "daily_path": "DAILY_PATH_LEDGER.jsonl",
    "trader_market_sync": "TRADER_MARKET_SYNC_LEDGER.jsonl",
}


def _single(root: Path, name: str) -> Path:
    paths = list(root.rglob(name))
    if len(paths) != 1:
        raise ValueError(f"expected exactly one {name} under {root}, got {len(paths)}")
    return paths[0]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return cast(dict[str, Any], payload)


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"expected JSON object row in {path}")
            yield cast(dict[str, Any], payload)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _int(value: object) -> int:
    return int(str(value))


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _fmt(value: Decimal) -> str:
    return format(value, "f")


def _quantiles(values: Sequence[Decimal]) -> dict[str, object]:
    if not values:
        return {"n": 0, "median": None, "p25": None, "p75": None, "p90": None}
    ordered = sorted(values)

    def at(fraction: Decimal) -> Decimal:
        index = int((Decimal(len(ordered) - 1) * fraction).to_integral_value())
        return ordered[index]

    return {
        "n": len(ordered),
        "median": _fmt(Decimal(str(median(ordered)))),
        "p25": _fmt(at(Decimal("0.25"))),
        "p75": _fmt(at(Decimal("0.75"))),
        "p90": _fmt(at(Decimal("0.90"))),
    }


def _rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0"
    return _fmt(Decimal(numerator) / Decimal(denominator))


def _counter_payload(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def _validate_matrix(
    matrix_root: Path,
    journey_summary_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    matrix = _read_json(_single(matrix_root, "cibo-12-market-intelligence-matrix-v1.json"))
    matrix_manifest = _read_json(
        _single(matrix_root, "cibo-12-market-intelligence-matrix-v1-manifest.json")
    )
    summary = _read_json(_single(journey_summary_root, "cibo-journey-10y-summary.json"))
    if matrix.get("identity") != MATRIX_IDENTITY:
        raise ValueError("matrix identity drift")
    if matrix_manifest.get("identity") != MATRIX_IDENTITY:
        raise ValueError("matrix manifest identity drift")
    if summary.get("identity") != JOURNEY_SUMMARY_IDENTITY:
        raise ValueError("journey summary identity drift")
    if matrix.get("evidence_tier") != EVIDENCE_TIER:
        raise ValueError("matrix evidence tier drift")
    if matrix_manifest.get("highest_automatic_evidence_tier") != EVIDENCE_TIER:
        raise ValueError("matrix automatic evidence tier drift")
    if bool(matrix.get("rule_promotion_allowed")):
        raise ValueError("matrix unexpectedly allows rule promotion")
    if bool(matrix_manifest.get("rule_promotion_allowed")):
        raise ValueError("matrix manifest unexpectedly allows rule promotion")
    if bool(summary.get("rule_promotion_allowed")):
        raise ValueError("journey summary unexpectedly allows rule promotion")
    if _int(matrix.get("source_m5_run_id", 0)) != SOURCE_M5_RUN_ID:
        raise ValueError("matrix M5 source drift")
    if _int(matrix.get("source_journey_run_id", 0)) != SOURCE_JOURNEY_RUN_ID:
        raise ValueError("matrix Journey source drift")
    if _int(matrix.get("source_target_run_id", 0)) != SOURCE_TARGET_RUN_ID:
        raise ValueError("matrix Target source drift")
    if _int(summary.get("source_run_id", 0)) != SOURCE_JOURNEY_RUN_ID:
        raise ValueError("journey summary source drift")
    if summary.get("cross_index_evidence_tier") != EVIDENCE_TIER:
        raise ValueError("cross-index evidence tier drift")
    return matrix, matrix_manifest, summary


def _validate_journey(
    root: Path,
    *,
    symbol: str,
) -> dict[str, Any]:
    manifest = _read_json(_single(root, "journey-manifest.json"))
    expected = EXPECTED[symbol]
    if manifest.get("identity") != JOURNEY_IDENTITY:
        raise ValueError(f"Journey identity drift for {symbol}")
    if manifest.get("symbol") != symbol:
        raise ValueError(f"Journey symbol drift for {symbol}")
    if int(manifest.get("source_run_id", 0)) != SOURCE_M5_RUN_ID:
        raise ValueError(f"Journey M5 source drift for {symbol}")
    if manifest.get("source_git_sha") != SOURCE_M5_GIT_SHA:
        raise ValueError(f"Journey M5 SHA drift for {symbol}")
    if _int(manifest.get("retained_m5_bars", 0)) != _int(expected["m5"]):
        raise ValueError(f"retained M5 count drift for {symbol}")
    if _int(manifest.get("behavior_event_count", 0)) != _int(expected["events"]):
        raise ValueError(f"behavior event count drift for {symbol}")
    if manifest.get("structure_coverage") != "DETERMINISTIC_SUPPORTED_SUBSET_FAIL_CLOSED":
        raise ValueError(f"Journey structure coverage drift for {symbol}")
    if manifest.get("trader_sync_status") != "UNLINKED_NO_TRADER_DECISION_STREAM":
        raise ValueError(f"Journey trader-sync status drift for {symbol}")

    ledger_counts = cast(dict[str, Any], manifest["ledger_counts"])
    if _int(ledger_counts.get("MARKET_JOURNEY_LEDGER", 0)) != _int(expected["events"]):
        raise ValueError(f"market Journey ledger count drift for {symbol}")
    if _int(ledger_counts.get("TRADER_MARKET_SYNC_LEDGER", -1)) != 0:
        raise ValueError(f"general Journey unexpectedly contains trader sync for {symbol}")

    ledger_hashes = cast(dict[str, Any], manifest["ledger_sha256"])
    for ledger, file_name in JOURNEY_LEDGER_FILES.items():
        manifest_key = {
            "market_journey": "MARKET_JOURNEY_LEDGER",
            "structure_touch": "STRUCTURE_TOUCH_LEDGER",
            "departure_timing": "DEPARTURE_TIMING_LEDGER",
            "pre_departure_sequence": "PRE_DEPARTURE_SEQUENCE_LEDGER",
            "target_destination_v1": "TARGET_DESTINATION_LEDGER",
            "daily_path": "DAILY_PATH_LEDGER",
            "trader_market_sync": "TRADER_MARKET_SYNC_LEDGER",
        }[ledger]
        path = _single(root, file_name)
        if _sha256(path) != str(ledger_hashes[manifest_key]):
            raise ValueError(f"Journey ledger digest drift for {symbol} {manifest_key}")
    return manifest


def _validate_target(root: Path, *, symbol: str) -> dict[str, Any]:
    manifest = _read_json(_single(root, "target-destination-v2-manifest.json"))
    expected = EXPECTED[symbol]
    if manifest.get("identity") != TARGET_IDENTITY:
        raise ValueError(f"Target V2 identity drift for {symbol}")
    if manifest.get("symbol") != symbol:
        raise ValueError(f"Target V2 symbol drift for {symbol}")
    if _int(manifest.get("source_journey_run_id", 0)) != SOURCE_JOURNEY_RUN_ID:
        raise ValueError(f"Target V2 Journey source drift for {symbol}")
    if manifest.get("source_journey_git_sha") != SOURCE_JOURNEY_GIT_SHA:
        raise ValueError(f"Target V2 Journey SHA drift for {symbol}")
    if _int(manifest.get("source_m5_run_id", 0)) != SOURCE_M5_RUN_ID:
        raise ValueError(f"Target V2 M5 source drift for {symbol}")
    if _int(manifest.get("retained_m5_bars", 0)) != _int(expected["m5"]):
        raise ValueError(f"Target V2 M5 count drift for {symbol}")
    if _int(manifest.get("market_journey_rows", 0)) != _int(expected["events"]):
        raise ValueError(f"Target V2 Journey row drift for {symbol}")
    if _int(manifest.get("resolved_departures", 0)) != _int(
        expected["resolved_departures"]
    ):
        raise ValueError(f"Target V2 departure count drift for {symbol}")
    if bool(manifest.get("complete_all_dol_claim")):
        raise ValueError(f"Target V2 unexpectedly claims complete DOL universe for {symbol}")
    if bool(manifest.get("rule_promotion_allowed")):
        raise ValueError(f"Target V2 unexpectedly allows rule promotion for {symbol}")

    ledger_path = _single(root, "TARGET_DESTINATION_LEDGER_V2.jsonl")
    episode_path = _single(root, "TARGET_DESTINATION_EPISODE_V2.jsonl")
    if _sha256(ledger_path) != str(manifest["target_ledger_sha256"]):
        raise ValueError(f"Target V2 ledger digest drift for {symbol}")
    if _sha256(episode_path) != str(manifest["episode_ledger_sha256"]):
        raise ValueError(f"Target V2 episode digest drift for {symbol}")
    return manifest


def _journey_summary(root: Path) -> dict[str, Any]:
    rows = 0
    resolved = 0
    by_timeframe: Counter[str] = Counter()
    by_side: Counter[str] = Counter()
    by_session: Counter[str] = Counter()
    by_source_type: Counter[str] = Counter()
    for row in _read_jsonl(_single(root, "MARKET_JOURNEY_LEDGER.jsonl")):
        rows += 1
        if row.get("departure_at") is not None:
            resolved += 1
        by_timeframe[str(row.get("source_timeframe"))] += 1
        by_side[str(row.get("side"))] += 1
        by_session[str(row.get("session_bucket"))] += 1
        by_source_type[str(row.get("source_boundary_type"))] += 1
    return {
        "rows": rows,
        "resolved_departures": resolved,
        "resolved_departure_rate": _rate(resolved, rows),
        "by_timeframe": _counter_payload(by_timeframe),
        "by_side": _counter_payload(by_side),
        "by_session": _counter_payload(by_session),
        "by_source_boundary_type": _counter_payload(by_source_type),
    }


def _structure_touch_summary(root: Path) -> dict[str, Any]:
    rows = 0
    last_before_departure = 0
    by_type: Counter[str] = Counter()
    by_reclaim: Counter[str] = Counter()
    by_timeframe: Counter[str] = Counter()
    dwell: list[Decimal] = []
    penetration: list[Decimal] = []
    for row in _read_jsonl(_single(root, "STRUCTURE_TOUCH_LEDGER.jsonl")):
        rows += 1
        by_type[str(row.get("structure_type"))] += 1
        by_reclaim[str(row.get("reclaim_state"))] += 1
        by_timeframe[str(row.get("source_timeframe"))] += 1
        if bool(row.get("last_structure_before_departure")):
            last_before_departure += 1
        if row.get("dwell_minutes") is not None:
            dwell.append(_decimal(row["dwell_minutes"]))
        if row.get("penetration_depth_ticks") is not None:
            penetration.append(_decimal(row["penetration_depth_ticks"]))
    return {
        "rows": rows,
        "last_structure_before_departure_rows": last_before_departure,
        "by_structure_type": _counter_payload(by_type),
        "by_reclaim_state": _counter_payload(by_reclaim),
        "by_timeframe": _counter_payload(by_timeframe),
        "dwell_minutes": _quantiles(dwell),
        "penetration_depth_ticks": _quantiles(penetration),
    }


def _departure_summary(root: Path) -> dict[str, Any]:
    rows = 0
    by_session: Counter[str] = Counter()
    by_weekday: Counter[str] = Counter()
    cisd: list[Decimal] = []
    reclaim: list[Decimal] = []
    source_to_departure: list[Decimal] = []
    creation_to_touch: list[Decimal] = []
    for row in _read_jsonl(_single(root, "DEPARTURE_TIMING_LEDGER.jsonl")):
        rows += 1
        by_session[str(row.get("session_bucket"))] += 1
        by_weekday[str(row.get("weekday"))] += 1
        for key, target in (
            ("cisd_latency_minutes", cisd),
            ("reclaim_latency_minutes", reclaim),
            ("minutes_source_event_to_departure", source_to_departure),
            ("minutes_structure_creation_to_first_touch", creation_to_touch),
        ):
            if row.get(key) is not None:
                target.append(_decimal(row[key]))
    return {
        "rows": rows,
        "by_session": _counter_payload(by_session),
        "by_weekday": _counter_payload(by_weekday),
        "cisd_latency_minutes": _quantiles(cisd),
        "reclaim_latency_minutes": _quantiles(reclaim),
        "source_event_to_departure_minutes": _quantiles(source_to_departure),
        "structure_creation_to_first_touch_minutes": _quantiles(creation_to_touch),
    }


def _sequence_summary(root: Path) -> dict[str, Any]:
    rows = 0
    by_status: Counter[str] = Counter()
    fingerprints: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    lengths: Counter[str] = Counter()
    for row in _read_jsonl(_single(root, "PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl")):
        rows += 1
        by_status[str(row.get("sequence_status"))] += 1
        sequence = cast(list[dict[str, Any]], row.get("sequence", []))
        states = [str(item.get("state")) for item in sequence]
        fingerprints[">".join(states) if states else "EMPTY"] += 1
        lengths[str(len(states))] += 1
        for left, right in zip(states, states[1:], strict=False):
            transitions[f"{left}>{right}"] += 1
    return {
        "rows": rows,
        "sequence_status": _counter_payload(by_status),
        "sequence_length": _counter_payload(lengths),
        "fingerprints": _counter_payload(fingerprints),
        "transitions": _counter_payload(transitions),
    }


def _daily_path_summary(root: Path) -> dict[str, Any]:
    rows = 0
    by_weekday: Counter[str] = Counter()
    regime: Counter[str] = Counter()
    path_efficiency: list[Decimal] = []
    overlap: list[Decimal] = []
    total_range: list[Decimal] = []
    displacement: list[Decimal] = []
    close_location: list[Decimal] = []
    for row in _read_jsonl(_single(root, "DAILY_PATH_LEDGER.jsonl")):
        rows += 1
        by_weekday[str(row.get("weekday"))] += 1
        regime[str(row.get("regime_state"))] += 1
        for key, target in (
            ("path_efficiency", path_efficiency),
            ("overlap_fraction", overlap),
            ("total_range", total_range),
            ("directional_displacement", displacement),
            ("close_location", close_location),
        ):
            if row.get(key) is not None:
                target.append(_decimal(row[key]))
    return {
        "rows": rows,
        "by_weekday": _counter_payload(by_weekday),
        "regime_state": _counter_payload(regime),
        "path_efficiency": _quantiles(path_efficiency),
        "overlap_fraction": _quantiles(overlap),
        "total_range": _quantiles(total_range),
        "directional_displacement": _quantiles(displacement),
        "close_location": _quantiles(close_location),
    }


def _journey_target_summary(root: Path) -> dict[str, Any]:
    rows = 0
    touched = 0
    by_type: Counter[str] = Counter()
    time_to_touch: list[Decimal] = []
    mfe: list[Decimal] = []
    mae: list[Decimal] = []
    distance: list[Decimal] = []
    for row in _read_jsonl(_single(root, "TARGET_DESTINATION_LEDGER.jsonl")):
        rows += 1
        by_type[str(row.get("candidate_type"))] += 1
        if bool(row.get("first_objective_touched_24h")):
            touched += 1
        for key, target in (
            ("time_to_first_objective_minutes", time_to_touch),
            ("mfe_24h_ticks", mfe),
            ("mae_24h_ticks", mae),
            ("candidate_distance_ticks", distance),
        ):
            if row.get(key) is not None:
                target.append(_decimal(row[key]))
    return {
        "rows": rows,
        "first_objective_touched_24h": touched,
        "first_objective_touch_rate_24h": _rate(touched, rows),
        "by_candidate_type": _counter_payload(by_type),
        "time_to_first_objective_minutes": _quantiles(time_to_touch),
        "mfe_24h_ticks": _quantiles(mfe),
        "mae_24h_ticks": _quantiles(mae),
        "candidate_distance_ticks": _quantiles(distance),
    }


def _target_v2_summary(root: Path) -> dict[str, Any]:
    rows = 0
    touched = 0
    active = 0
    ambiguous = 0
    by_type: Counter[str] = Counter()
    by_timeframe: Counter[str] = Counter()
    distance: list[Decimal] = []
    touch_minutes: list[Decimal] = []
    for row in _read_jsonl(_single(root, "TARGET_DESTINATION_LEDGER_V2.jsonl")):
        rows += 1
        by_type[str(row.get("candidate_type"))] += 1
        by_timeframe[str(row.get("source_timeframe"))] += 1
        if bool(row.get("active_untouched_at_departure")):
            active += 1
        if bool(row.get("touch_within_24h")):
            touched += 1
        if bool(row.get("touch_order_ambiguous_within_m5")):
            ambiguous += 1
        if row.get("candidate_distance_ticks") is not None:
            distance.append(_decimal(row["candidate_distance_ticks"]))
        if row.get("time_to_touch_minutes") is not None:
            touch_minutes.append(_decimal(row["time_to_touch_minutes"]))

    episode_rows = 0
    touched_candidates: list[Decimal] = []
    active_candidates: list[Decimal] = []
    tied = 0
    for row in _read_jsonl(_single(root, "TARGET_DESTINATION_EPISODE_V2.jsonl")):
        episode_rows += 1
        active_candidates.append(_decimal(row.get("active_candidate_count", 0)))
        touched_candidates.append(_decimal(row.get("touched_candidate_count_24h", 0)))
        if bool(row.get("first_touch_tied")):
            tied += 1
    return {
        "candidate_rows": rows,
        "episode_rows": episode_rows,
        "active_untouched_rows": active,
        "touch_within_24h_rows": touched,
        "touch_within_24h_rate": _rate(touched, rows),
        "touch_order_ambiguous_rows": ambiguous,
        "touch_order_ambiguous_rate": _rate(ambiguous, touched),
        "by_candidate_type": _counter_payload(by_type),
        "by_source_timeframe": _counter_payload(by_timeframe),
        "candidate_distance_ticks": _quantiles(distance),
        "time_to_touch_minutes": _quantiles(touch_minutes),
        "active_candidate_count_per_episode": _quantiles(active_candidates),
        "touched_candidate_count_24h_per_episode": _quantiles(touched_candidates),
        "first_touch_tied_episodes": tied,
        "first_touch_tied_rate": _rate(tied, episode_rows),
        "complete_all_dol_claim": False,
    }


def _cross_index_summary(summary: Mapping[str, Any], symbol: str) -> dict[str, Any]:
    cross = cast(dict[str, Any], summary["cross_index"])
    pairs = [
        row
        for row in cast(list[dict[str, Any]], cross.get("ordered_pairs", []))
        if row.get("source") == symbol or row.get("peer") == symbol
    ]
    return {
        "rows": cross.get("rows"),
        "evidence_tier": EVIDENCE_TIER,
        "ordered_pairs_involving_symbol": pairs,
        "causal_leader_claim": False,
    }


def _market_matrix_detail(matrix: Mapping[str, Any], symbol: str) -> dict[str, Any]:
    details = cast(dict[str, Any], matrix["market_detail"])
    detail = cast(dict[str, Any], details.get(symbol))
    if not detail or detail.get("symbol") != symbol:
        raise ValueError(f"matrix detail missing for {symbol}")
    expected = EXPECTED[symbol]
    if detail.get("evidence_tier") != EVIDENCE_TIER:
        raise ValueError(f"matrix detail evidence tier drift for {symbol}")
    if bool(detail.get("rule_promotion_allowed")):
        raise ValueError(f"matrix detail unexpectedly promotes rules for {symbol}")
    if _int(detail.get("retained_m5_bars", 0)) != _int(expected["m5"]):
        raise ValueError(f"matrix detail retained M5 drift for {symbol}")
    overall = cast(dict[str, Any], detail["overall"])
    if _int(overall.get("events", 0)) != _int(expected["events"]):
        raise ValueError(f"matrix detail event count drift for {symbol}")
    return detail


def _source_refs(symbol: str) -> dict[str, Any]:
    expected = EXPECTED[symbol]
    return {
        "matrix": {
            "run_id": SOURCE_MATRIX_RUN_ID,
            "git_sha": SOURCE_MATRIX_GIT_SHA,
        },
        "m5": {
            "run_id": SOURCE_M5_RUN_ID,
            "git_sha": SOURCE_M5_GIT_SHA,
        },
        "journey": {
            "run_id": SOURCE_JOURNEY_RUN_ID,
            "git_sha": SOURCE_JOURNEY_GIT_SHA,
            "artifact_id": expected["journey_artifact_id"],
            "artifact_digest": expected["journey_artifact_digest"],
        },
        "target_destination_v2": {
            "run_id": SOURCE_TARGET_RUN_ID,
            "git_sha": SOURCE_TARGET_GIT_SHA,
            "artifact_id": expected["target_artifact_id"],
            "artifact_digest": expected["target_artifact_digest"],
        },
        "journey_summary": {
            "run_id": SOURCE_SUMMARY_RUN_ID,
            "git_sha": SOURCE_SUMMARY_GIT_SHA,
        },
    }


def build_market_dossier(
    *,
    symbol: str,
    matrix: Mapping[str, Any],
    journey_summary: Mapping[str, Any],
    journey_root: Path,
    target_root: Path,
) -> dict[str, Any]:
    if symbol not in SYMBOLS:
        raise ValueError(f"unsupported index symbol: {symbol}")
    journey_manifest = _validate_journey(journey_root, symbol=symbol)
    target_manifest = _validate_target(target_root, symbol=symbol)
    detail = _market_matrix_detail(matrix, symbol)
    expected = EXPECTED[symbol]

    journey = _journey_summary(journey_root)
    if _int(journey["rows"]) != _int(expected["events"]):
        raise ValueError(f"Journey stream row count drift for {symbol}")
    if _int(journey["resolved_departures"]) != _int(expected["resolved_departures"]):
        raise ValueError(f"resolved departure stream count drift for {symbol}")

    dossier = {
        "schema": SCHEMA,
        "identity": f"CIBO_{symbol}_MARKET_INTELLIGENCE_DOSSIER_V1",
        "package_identity": PACKAGE_IDENTITY,
        "symbol": symbol,
        "asset_class": "index",
        "evidence_status": "CONSUMED_RESEARCH_EVIDENCE",
        "evidence_tier": EVIDENCE_TIER,
        "source_refs": _source_refs(symbol),
        "retained_m5_bars": expected["m5"],
        "behavior_events": expected["events"],
        "resolved_departures": expected["resolved_departures"],
        "market_matrix": detail,
        "journey_manifest": journey_manifest,
        "journey": journey,
        "structure_touch": _structure_touch_summary(journey_root),
        "departure_timing": _departure_summary(journey_root),
        "pre_departure_sequences": _sequence_summary(journey_root),
        "daily_path": _daily_path_summary(journey_root),
        "target_destination_v1": _journey_target_summary(journey_root),
        "target_destination_v2": {
            "manifest": target_manifest,
            "summary": _target_v2_summary(target_root),
        },
        "cross_index": _cross_index_summary(journey_summary, symbol),
        "knowledge_gaps": (
            "universal-order-block-breaker-fvg-chronology-not-complete",
            "dedicated-equal-liquidity-chronology-not-complete",
            "generic-regime-thresholds-not-frozen",
            "target-v2-supported-reference-universe-is-not-all-dols",
            "cross-index-nearest-departure-is-association-not-causal-leadership",
            "general-market-atlas-has-no-trader-decision-stream",
        ),
        "memory_role": "general-market-memory-independent-of-vt08-outcomes",
        "rule_promotion_allowed": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return cast(dict[str, Any], dossier)


def build_package(
    *,
    matrix_root: Path,
    journey_summary_root: Path,
    journey_roots: Mapping[str, Path],
    target_roots: Mapping[str, Path],
    output: Path,
) -> dict[str, Any]:
    matrix, matrix_manifest, summary = _validate_matrix(
        matrix_root,
        journey_summary_root,
    )
    output.mkdir(parents=True, exist_ok=True)

    manifests: dict[str, Any] = {}
    dossiers: dict[str, Any] = {}
    for symbol in SYMBOLS:
        dossier = build_market_dossier(
            symbol=symbol,
            matrix=matrix,
            journey_summary=summary,
            journey_root=journey_roots[symbol],
            target_root=target_roots[symbol],
        )
        path = output / f"{symbol.lower()}-market-intelligence-dossier-v1.json"
        path.write_text(json.dumps(dossier, indent=2, sort_keys=True) + "\n")
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "identity": dossier["identity"],
            "package_identity": PACKAGE_IDENTITY,
            "symbol": symbol,
            "dossier_sha256": _sha256(path),
            "retained_m5_bars": dossier["retained_m5_bars"],
            "behavior_events": dossier["behavior_events"],
            "resolved_departures": dossier["resolved_departures"],
            "source_refs": dossier["source_refs"],
            "evidence_status": "CONSUMED_RESEARCH_EVIDENCE",
            "highest_automatic_evidence_tier": EVIDENCE_TIER,
            "rule_promotion_allowed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        }
        manifest_path = output / f"{symbol.lower()}-market-intelligence-manifest-v1.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        manifests[symbol] = manifest
        dossiers[symbol] = dossier

    package = {
        "schema": MANIFEST_SCHEMA,
        "identity": PACKAGE_IDENTITY,
        "symbols": list(SYMBOLS),
        "market_matrix_identity": matrix.get("identity"),
        "market_matrix_json_sha256": matrix_manifest.get("json_sha256"),
        "source_refs": {
            "matrix_run_id": SOURCE_MATRIX_RUN_ID,
            "matrix_git_sha": SOURCE_MATRIX_GIT_SHA,
            "m5_run_id": SOURCE_M5_RUN_ID,
            "m5_git_sha": SOURCE_M5_GIT_SHA,
            "journey_run_id": SOURCE_JOURNEY_RUN_ID,
            "journey_git_sha": SOURCE_JOURNEY_GIT_SHA,
            "target_run_id": SOURCE_TARGET_RUN_ID,
            "target_git_sha": SOURCE_TARGET_GIT_SHA,
            "journey_summary_run_id": SOURCE_SUMMARY_RUN_ID,
            "journey_summary_git_sha": SOURCE_SUMMARY_GIT_SHA,
        },
        "total_retained_m5_bars": sum(_int(EXPECTED[s]["m5"]) for s in SYMBOLS),
        "total_behavior_events": sum(_int(EXPECTED[s]["events"]) for s in SYMBOLS),
        "total_resolved_departures": sum(
            _int(EXPECTED[s]["resolved_departures"]) for s in SYMBOLS
        ),
        "market_manifests": manifests,
        "full_market_memory_ready": True,
        "vt08_outcomes_used": False,
        "evidence_tier": EVIDENCE_TIER,
        "rule_promotion_allowed": False,
        "fresh_holdout_opened": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    package_path = output / "CIBO_INDEX_MARKET_INTELLIGENCE_PACKAGE_V1.json"
    package_path.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    return package


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-root", type=Path, required=True)
    parser.add_argument("--journey-summary-root", type=Path, required=True)
    parser.add_argument("--nas100-journey-root", type=Path, required=True)
    parser.add_argument("--sp500-journey-root", type=Path, required=True)
    parser.add_argument("--us30-journey-root", type=Path, required=True)
    parser.add_argument("--nas100-target-root", type=Path, required=True)
    parser.add_argument("--sp500-target-root", type=Path, required=True)
    parser.add_argument("--us30-target-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_package(
        matrix_root=args.matrix_root,
        journey_summary_root=args.journey_summary_root,
        journey_roots={
            "NAS100": args.nas100_journey_root,
            "SP500": args.sp500_journey_root,
            "US30": args.us30_journey_root,
        },
        target_roots={
            "NAS100": args.nas100_target_root,
            "SP500": args.sp500_target_root,
            "US30": args.us30_target_root,
        },
        output=args.output,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
