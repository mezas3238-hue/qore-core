"""Turtle Soup EURUSD Specialist Memory V1.

Creates a derived, trader-specific copy of the immutable CIBO EURUSD 10Y
master memory.

The CIBO master artifacts are READ ONLY and never rewritten.  This module
creates two new layers:

1. SPECIALIST RAW MEMORY
   - one snapshot row for every CIBO EURUSD behavior event;
   - provenance back to the immutable CIBO episode;
   - marks whether the event binds to an exact reproducible Turtle Soup setup;
   - retains the complete master-event payload.

2. SPECIALIST COGNITIVE MEMORY
   - for every reproducible Turtle Soup setup, uses the trader's actual
     NEXT_SOURCE_OPEN entry and exact Protected Swing;
   - rebuilds the active CIBO DOL ladder;
   - simulates STATIC / LET_RUN / PROTECT lifecycles for DOL ranks 1..3;
   - indexes those outcomes by Turtle-specific situation fingerprints.

No R11/R16/R17/R20/R21/R22/R23 memory or labels are inputs.
"""
from __future__ import annotations

import json
import shutil
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import (
    cibo_eurusd_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab as behavior
from qore.infrastructure.trader_lab import (
    ict_turtle_soup_behavior_lab_fast_runner as fast,
)
from qore.infrastructure.trader_lab import turtle_soup_eurusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_eurusd_r2_cibo_full as r2
from qore.infrastructure.trader_lab import turtle_soup_eurusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Side

IDENTITY = "TURTLE_SOUP_EURUSD_SPECIALIST_MEMORY_V1"
RAW_IDENTITY = "TURTLE_SOUP_EURUSD_SPECIALIST_RAW_MEMORY_V1"
COGNITIVE_IDENTITY = "TURTLE_SOUP_EURUSD_SPECIALIST_COGNITIVE_MEMORY_V1"

MASTER_RAW_RUN_ID = 35166210458
MASTER_RAW_ARTIFACT_ID = 10475354631
MASTER_JOURNEY_RUN_ID = 35175979474
MASTER_TARGET_RUN_ID = 35204892665
MASTER_TARGET_ARTIFACT_ID = 10489596583

MAX_TARGET_RANK = 3
MIN_PERIOD_N = 8

AUTHORITATIVE_LEVELS = ("exact", "causal_core", "anatomy")
CONTEXT_ONLY_LEVELS = ("compact_anatomy",)

FINGERPRINT_LEVELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "exact",
        (
            "timeframe",
            "side",
            "session",
            "weekday",
            "prior_body_alignment",
            "fvg_before_entry",
            "exact_equal_liquidity",
            "raid_depth_range_bucket",
            "reclaim_latency_bucket",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "source_range_state_bucket",
            "body_fraction_bucket",
            "rejection_wick_bucket",
            "close_location_bucket",
            "target_rank",
            "target_route",
            "rr_bucket",
        ),
    ),
    (
        "causal_core",
        (
            "timeframe",
            "side",
            "session",
            "prior_body_alignment",
            "fvg_before_entry",
            "exact_equal_liquidity",
            "reclaim_latency_bucket",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "source_range_state_bucket",
            "target_rank",
            "target_route",
            "rr_bucket",
        ),
    ),
    (
        "anatomy",
        (
            "timeframe",
            "prior_body_alignment",
            "fvg_before_entry",
            "reclaim_latency_bucket",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "source_range_state_bucket",
            "target_rank",
            "target_route",
            "rr_bucket",
        ),
    ),
    (
        "compact_anatomy",
        (
            "timeframe",
            "fvg_before_entry",
            "cisd_progress_bucket",
            "protected_risk_range_bucket",
            "target_rank",
            "rr_bucket",
        ),
    ),
)


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(rows)


def _load_target_rows(root: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    path = _single(root, "TARGET_DESTINATION_LEDGER_V2.jsonl")
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                result[str(row["episode_id"])].append(row)
    return dict(result)


def _active_ladder(
    rows: Sequence[dict[str, Any]],
    *,
    at: datetime,
    side: Side,
    entry: Decimal,
    tick: Decimal,
) -> list[native.NativeTarget]:
    by_price: dict[Decimal, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        known_at = _dt(str(row["candidate_known_at"]))
        if known_at > at:
            continue
        touched_at = (
            None
            if row.get("touch_m5_opened_at") is None
            else _dt(str(row["touch_m5_opened_at"]))
        )
        if touched_at is not None and touched_at < at:
            continue
        level = Decimal(str(row["candidate_price"]))
        ahead = level > entry if side is Side.LONG else level < entry
        if ahead:
            by_price[level].append(row)

    grouped = sorted(by_price.items(), key=lambda item: abs(item[0] - entry))
    ladder: list[native.NativeTarget] = []
    for rank, (level, members) in enumerate(grouped, start=1):
        if rank > MAX_TARGET_RANK:
            break
        touched_rows = [
            row for row in members if row.get("touch_m5_opened_at") is not None
        ]
        touch_at = (
            None
            if not touched_rows
            else min(_dt(str(row["touch_m5_opened_at"])) for row in touched_rows)
        )
        ladder.append(
            native.NativeTarget(
                rank=rank,
                level=level,
                route=native._route(members),
                distance_ticks=abs(level - entry) / tick,
                touched=bool(touched_rows),
                touch_at=touch_at,
            )
        )
    return ladder


def _period(year: int) -> str:
    if 2016 <= year <= 2020:
        return "early_2016_2020"
    if 2021 <= year <= 2023:
        return "transition_2021_2023"
    if 2024 <= year <= 2026:
        return "recent_2024_2026"
    return "outside"


def _setup_context(setup: r3.Setup) -> dict[str, Any]:
    context = setup.context
    return {
        "timeframe": context.timeframe,
        "side": context.side,
        "session": context.session,
        "weekday": context.weekday,
        "prior_body_alignment": context.prior_body_alignment,
        "fvg_before_entry": context.fvg_before_entry,
        "exact_equal_liquidity": context.exact_equal_liquidity,
        "raid_depth_range_bucket": context.raid_depth_range_bucket,
        "reclaim_latency_bucket": context.reclaim_latency_bucket,
        "cisd_progress_bucket": context.cisd_progress_bucket,
        "protected_risk_range_bucket": context.protected_risk_range_bucket,
        "source_range_state_bucket": context.source_range_state_bucket,
        "body_fraction_bucket": context.body_fraction_bucket,
        "rejection_wick_bucket": context.rejection_wick_bucket,
        "close_location_bucket": context.close_location_bucket,
        "strategy_projected_r_bucket": context.projected_r_bucket,
        "strategy_target_distance_range_bucket": (
            context.target_distance_range_bucket
        ),
    }


def _key(row: dict[str, Any], fields: Sequence[str]) -> str:
    return "|".join(str(row[field]) for field in fields)


def _summary(rows: Sequence[dict[str, Any]], posture: str) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    gross = [Decimal(str(row[f"{posture}_gross_r"])) for row in rows]
    net005 = [Decimal(str(row[f"{posture}_net_005_r"])) for row in rows]
    net010 = [Decimal(str(row[f"{posture}_net_010_r"])) for row in rows]
    n = len(rows)
    gains = sum((value for value in net010 if value > 0), Decimal(0))
    losses = -sum((value for value in net010 if value < 0), Decimal(0))
    pf = None if losses == 0 else str(gains / losses)
    return {
        "n": n,
        "mean_gross_r": str(sum(gross, Decimal(0)) / Decimal(n)),
        "mean_net_005_r": str(sum(net005, Decimal(0)) / Decimal(n)),
        "mean_net_010_r": str(sum(net010, Decimal(0)) / Decimal(n)),
        "median_net_010_r": str(median(net010)),
        "profit_factor_010": pf,
        "target_rate": str(
            Decimal(sum(bool(row[f"{posture}_target_reached"]) for row in rows))
            / Decimal(n)
        ),
        "protected_exit_rate": str(
            Decimal(sum(bool(row[f"{posture}_protected_exit"]) for row in rows))
            / Decimal(n)
        ),
        "positive_net_010_rate": str(
            Decimal(sum(value > 0 for value in net010)) / Decimal(n)
        ),
    }


def _classify(rows: Sequence[dict[str, Any]], posture: str) -> dict[str, Any]:
    periods = (
        "early_2016_2020",
        "transition_2021_2023",
        "recent_2024_2026",
    )
    by_period = {
        period: [row for row in rows if row["period"] == period]
        for period in periods
    }
    period_profiles = {
        period: _summary(items, posture) for period, items in by_period.items()
    }
    sufficient = all(
        int(profile.get("n", 0)) >= MIN_PERIOD_N
        for profile in period_profiles.values()
    )
    combined = _summary(rows, posture)
    if not sufficient:
        classification = "UNRESOLVED"
    else:
        means = [
            Decimal(str(period_profiles[period]["mean_net_010_r"]))
            for period in periods
        ]
        combined_mean = Decimal(str(combined["mean_net_010_r"]))
        positive_periods = sum(value > 0 for value in means)
        if positive_periods == 3 and combined_mean > 0:
            classification = "ROBUST_POSITIVE_010"
        elif positive_periods >= 2 and combined_mean > 0:
            classification = "MAJORITY_POSITIVE_010"
        elif combined_mean <= 0:
            classification = "NEGATIVE_010"
        else:
            classification = "UNRESOLVED"
    return {
        "classification": classification,
        "combined": combined,
        "periods": period_profiles,
    }


def _best_posture(models: dict[str, dict[str, Any]]) -> str | None:
    positive_order = (
        "ROBUST_POSITIVE_010",
        "MAJORITY_POSITIVE_010",
    )
    for classification in positive_order:
        candidates = [
            posture
            for posture, model in models.items()
            if model["classification"] == classification
        ]
        if candidates:
            # No fixed LET_RUN preference.  Prefer the posture with the highest
            # combined 0.10R mean inside the same confidence class.
            return max(
                candidates,
                key=lambda posture: Decimal(
                    str(models[posture]["combined"]["mean_net_010_r"])
                ),
            )
    return None


def _build_cognitive(
    observations: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    hierarchy: dict[str, Any] = {}
    for level_name, fields in FINGERPRINT_LEVELS:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in observations:
            grouped[_key(row, fields)].append(row)

        signatures: dict[str, Any] = {}
        for signature, rows in sorted(grouped.items()):
            models = {
                posture: _classify(rows, posture)
                for posture in native.POSTURES
            }
            preferred = _best_posture(models)
            signatures[signature] = {
                "fields": list(fields),
                "values": {field: rows[0][field] for field in fields},
                "observations": len(rows),
                "decision_authority": (
                    "AUTHORITATIVE"
                    if level_name in AUTHORITATIVE_LEVELS
                    else "CONTEXT_ONLY"
                ),
                "postures": models,
                "preferred_posture": preferred,
                "target_hit_rate": str(
                    Decimal(sum(bool(row["target_touched_24h"]) for row in rows))
                    / Decimal(len(rows))
                ),
                "median_planned_rr": str(
                    median(Decimal(str(row["planned_rr"])) for row in rows)
                ),
            }

        hierarchy[level_name] = {
            "fields": list(fields),
            "decision_authority": (
                "AUTHORITATIVE"
                if level_name in AUTHORITATIVE_LEVELS
                else "CONTEXT_ONLY"
            ),
            "signatures": signatures,
            "preferred_posture_counts": dict(
                Counter(
                    str(item["preferred_posture"])
                    for item in signatures.values()
                    if item["preferred_posture"] is not None
                )
            ),
            "classification_counts": {
                posture: dict(
                    Counter(
                        str(item["postures"][posture]["classification"])
                        for item in signatures.values()
                    )
                )
                for posture in native.POSTURES
            },
        }
    return hierarchy


def resolve_authoritative(
    hierarchy: dict[str, Any],
    row: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    for level_name, fields in FINGERPRINT_LEVELS:
        signature = _key(row, fields)
        item = cast(dict[str, Any], hierarchy[level_name]["signatures"]).get(
            signature
        )
        if item is None:
            continue
        if item["decision_authority"] != "AUTHORITATIVE":
            continue
        if item["preferred_posture"] is None:
            continue
        return item, level_name, signature
    return None, None, None


def build(
    raw_root: Path,
    journey_root: Path,
    target_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "EURUSD" or int(provenance["retained_bars"]) != 745458:
        raise ValueError("unexpected EURUSD corpus")

    journey_manifest = json.loads(
        _single(journey_root, "journey-manifest.json").read_text()
    )
    target_manifest = json.loads(
        _single(target_root, "target-destination-v2-manifest.json").read_text()
    )
    if journey_manifest["identity"] != "CIBO_MARKET_JOURNEY_LAYER_V1":
        raise ValueError("unexpected Journey V1 identity")
    if (
        target_manifest["identity"]
        != "CIBO_TARGET_DESTINATION_V2_SUPPORTED_REFERENCE_UNIVERSE"
    ):
        raise ValueError("unexpected Target Destination V2 identity")

    fast.install()
    events = behavior.extract_events(
        evidence,
        asset_class="metal",
        provider=str(provenance["provider_symbol"]),
        evidence_id="turtle-soup-specialist-memory-v1",
    )
    if len(events) != 126098:
        raise ValueError("master behavior event reproduction drift")

    target_rows = _load_target_rows(target_root)
    _episodes, source_index = repair._load_targets_fail_closed(target_root)

    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close

    setup_by_episode: dict[str, r3.Setup] = {}
    for setup in setups:
        signal = setup.context.signal
        episode_id = source_index.get(
            (
                signal.cisd_at,
                signal.side.value,
                setup.context.timeframe,
                signal.target,
            )
        )
        if episode_id is not None:
            setup_by_episode[episode_id] = setup

    raw_rows: list[dict[str, Any]] = []
    for event in events:
        episode_id = journey._episode_id(event)
        setup_match = setup_by_episode.get(episode_id)
        raw_rows.append(
            {
                "schema": "qore.turtle_soup_eurusd.specialist_raw_memory.v1",
                "identity": RAW_IDENTITY,
                "master_episode_id": episode_id,
                "master_event_id": journey._event_id(event),
                "master_source_run_id": MASTER_RAW_RUN_ID,
                "master_source_artifact_id": MASTER_RAW_ARTIFACT_ID,
                "master_journey_run_id": MASTER_JOURNEY_RUN_ID,
                "master_target_run_id": MASTER_TARGET_RUN_ID,
                "master_target_artifact_id": MASTER_TARGET_ARTIFACT_ID,
                "turtle_setup_recognized": setup_match is not None,
                "specialist_role": (
                    "TURTLE_SETUP"
                    if setup_match is not None
                    else "MARKET_CONTEXT"
                ),
                "master_event": behavior.event_dict(event),
                "turtle_context": (
                    None if setup_match is None else _setup_context(setup_match)
                ),
            }
        )

    opens = tuple(bar.opened_at for bar in evidence.bars)
    tick = Decimal(1).scaleb(-evidence.digits)
    observations: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()

    for episode_id, setup in sorted(
        setup_by_episode.items(),
        key=lambda item: item[1].context.signal.entry_at,
    ):
        fill = r3._entry(setup, evidence, opens, "NEXT_SOURCE_OPEN")
        if fill is None:
            counters["NO_ENTRY"] += 1
            continue
        entry_at, entry = fill
        side = setup.context.signal.side
        stop = setup.context.signal.protected_swing
        risk = entry - stop if side is Side.LONG else stop - entry
        if risk <= 0:
            counters["INVALID_RISK"] += 1
            continue

        ladder = _active_ladder(
            target_rows.get(episode_id, ()),
            at=entry_at,
            side=side,
            entry=entry,
            tick=tick,
        )
        if not ladder:
            counters["NO_ACTIVE_DOL"] += 1
            continue

        for target in ladder:
            reward = (
                target.level - entry
                if side is Side.LONG
                else entry - target.level
            )
            if reward <= 0:
                continue
            rr = reward / risk
            lifecycles = {
                posture: native._simulate(
                    posture=posture,
                    side=side,
                    entry_at=entry_at,
                    entry=entry,
                    risk_price=risk,
                    target=target,
                    ladder=ladder,
                    bars=evidence.bars,
                    opens=opens,
                )
                for posture in native.POSTURES
            }
            row: dict[str, Any] = {
                "schema": "qore.turtle_soup_eurusd.specialist_decision_observation.v1",
                "identity": COGNITIVE_IDENTITY,
                "master_episode_id": episode_id,
                "strategy_entry_at": entry_at.isoformat(),
                "year": entry_at.year,
                "period": _period(entry_at.year),
                **_setup_context(setup),
                "target_rank": target.rank,
                "target_route": target.route,
                "target_level": str(target.level),
                "planned_rr": str(rr),
                "rr_bucket": r2._bucket(rr, native.RR_CUTS),
                "target_touched_24h": target.touched,
                "target_touch_at": (
                    None if target.touch_at is None else target.touch_at.isoformat()
                ),
            }
            for posture, result in lifecycles.items():
                row[f"{posture}_gross_r"] = str(result.gross_r)
                row[f"{posture}_net_005_r"] = str(
                    result.gross_r - Decimal("0.05")
                )
                row[f"{posture}_net_010_r"] = str(result.net_010_r)
                row[f"{posture}_exit_reason"] = result.exit_reason
                row[f"{posture}_target_reached"] = result.target_reached
                row[f"{posture}_protected_exit"] = result.protected_exit
                row[f"{posture}_stop_exit"] = result.stop_exit
                row[f"{posture}_trail_moves"] = result.trail_moves
            observations.append(row)
            counters["OBSERVATION"] += 1

    cognitive = _build_cognitive(observations)

    resolved_counts: Counter[str] = Counter()
    for row in observations:
        item, level, _signature = resolve_authoritative(cognitive, row)
        if item is None or level is None:
            resolved_counts["NO_AUTHORITATIVE_MEMORY"] += 1
        else:
            resolved_counts[f"{level}:{item['preferred_posture']}"] += 1

    output.mkdir(parents=True, exist_ok=True)

    # Physical snapshot of the CIBO master-memory ledgers used to derive this
    # specialist memory.  Originals remain immutable; only these derived-copy
    # files may be reorganized by later specialist-memory versions.
    snapshot = output / "master-snapshot"
    snapshot.mkdir(parents=True, exist_ok=True)
    snapshot_files: list[str] = []
    for name in (
        "MARKET_JOURNEY_LEDGER.jsonl",
        "STRUCTURE_TOUCH_LEDGER.jsonl",
        "PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl",
        "DEPARTURE_TIMING_LEDGER.jsonl",
        "TARGET_DESTINATION_LEDGER.jsonl",
        "DAILY_PATH_LEDGER.jsonl",
        "TRADER_MARKET_SYNC_LEDGER.jsonl",
        "journey-manifest.json",
    ):
        source = _single(journey_root, name)
        destination = snapshot / f"journey-{name}"
        shutil.copy2(source, destination)
        snapshot_files.append(destination.name)
    for name in (
        "TARGET_DESTINATION_LEDGER_V2.jsonl",
        "TARGET_DESTINATION_EPISODE_V2.jsonl",
        "target-destination-v2-manifest.json",
    ):
        source = _single(target_root, name)
        destination = snapshot / f"target-{name}"
        shutil.copy2(source, destination)
        snapshot_files.append(destination.name)

    raw_path = output / "turtle-soup-eurusd-specialist-raw-memory.jsonl"
    observation_path = output / "turtle-soup-eurusd-specialist-observations.jsonl"
    _write_jsonl(raw_path, raw_rows)
    _write_jsonl(observation_path, observations)
    (output / "turtle-soup-eurusd-specialist-cognitive-memory.json").write_text(
        json.dumps(cognitive, indent=2, sort_keys=True) + "\n"
    )

    report = {
        "schema": "qore.turtle_soup_eurusd.specialist_memory_report.v1",
        "identity": IDENTITY,
        "raw_identity": RAW_IDENTITY,
        "cognitive_identity": COGNITIVE_IDENTITY,
        "master_memory_contract": {
            "master_is_immutable": True,
            "master_modified": False,
            "derived_copy_only": True,
            "raw_m5_run_id": MASTER_RAW_RUN_ID,
            "raw_m5_artifact_id": MASTER_RAW_ARTIFACT_ID,
            "journey_run_id": MASTER_JOURNEY_RUN_ID,
            "target_run_id": MASTER_TARGET_RUN_ID,
            "target_artifact_id": MASTER_TARGET_ARTIFACT_ID,
            "physical_master_snapshot_in_specialist_artifact": True,
            "snapshot_files": snapshot_files,
        },
        "specialist_contract": {
            "strategy": "TURTLE_SOUP_EURUSD",
            "actual_strategy_entry_used": True,
            "exact_protected_swing_used": True,
            "active_cibo_dol_ladder_rebuilt": True,
            "postures": list(native.POSTURES),
            "friction_005_modeled": True,
            "friction_010_modeled": True,
            "authoritative_levels": list(AUTHORITATIVE_LEVELS),
            "context_only_levels": list(CONTEXT_ONLY_LEVELS),
            "generic_destination_fallback_authorizes_trade": False,
            "r11_memory_used": False,
            "r16_memory_used": False,
            "r17_memory_used": False,
            "r20_memory_used": False,
            "r21_memory_used": False,
            "r22_memory_used": False,
            "r23_memory_used": False,
            "r25_result_used_as_training_label": False,
        },
        "reproduction": {
            "retained_m5_bars": int(provenance["retained_bars"]),
            "master_behavior_events_copied": len(raw_rows),
            "turtle_setups_10y": len(setups),
            "turtle_setup_episode_bindings": len(setup_by_episode),
            "specialist_decision_observations": len(observations),
            "counters": dict(counters),
            "funnel": funnel,
        },
        "cognitive_summary": {
            level: {
                "decision_authority": payload["decision_authority"],
                "signatures": len(payload["signatures"]),
                "preferred_posture_counts": payload["preferred_posture_counts"],
                "classification_counts": payload["classification_counts"],
            }
            for level, payload in cognitive.items()
        },
        "authoritative_resolution_counts": dict(resolved_counts),
        "governance": {
            "research_memory_only": True,
            "fresh_holdout_consumed": False,
            "candidate_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    (output / "turtle-soup-eurusd-specialist-memory-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: module RAW_ROOT JOURNEY_ROOT TARGET_ROOT OUTPUT_DIR"
        )
    print(
        json.dumps(
            build(
                Path(sys.argv[1]),
                Path(sys.argv[2]),
                Path(sys.argv[3]),
                Path(sys.argv[4]),
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
