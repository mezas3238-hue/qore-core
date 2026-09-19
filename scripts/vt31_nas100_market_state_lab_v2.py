"""Causal NAS100 market-state / sequence laboratory for VT31 Intelligence V2.

Research-only.  The lab reconstructs each source-valid VT31 setup incrementally
from M1 evidence, snapshots only information available at the setup decision,
and then attaches post-decision outcomes strictly as research labels.

No date-level outcome lookup is exposed to a runtime policy.  R5/R6/R8 are
already-consumed development folds; this module does not open a holdout.
"""
# ruff: noqa: B009,I001
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast
from zoneinfo import ZoneInfo

import vt31_nas100_r1_candidate as baseline
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.market_state_lab.v2"
MARKET = "NAS100"
NY = ZoneInfo("America/New_York")
FRICTION = Decimal("0.05")
CIBO_SCHEMA = "qore.cibo_atlas.vt31.eight_ledger_bundle.v1"
CIBO_ARTIFACT_ID = 10478487667
CIBO_DIGEST = "sha256:17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192"

RUNTIME_FEATURE_FIELDS = (
    "decision_time_bucket",
    "decision_minute_ny",
    "weekday",
    "side",
    "entry_family",
    "candidate_family_count",
    "reference_width",
    "first_breach_side",
    "first_breach_minute_ny",
    "double_sided_before_decision",
    "expected_side_breached",
    "minutes_raid_to_decision",
    "reference_reclaimed",
    "minutes_reclaim_to_decision",
    "raid_depth_ref",
    "session_range_ref",
    "recent_range_ref",
    "recent_path_efficiency",
    "recent_overlap_rate",
    "directional_progress_ref",
    "risk_ref",
    "planned_target_r",
    "remaining_minutes_to_16",
)

RESEARCH_LABEL_FIELDS = (
    "status",
    "exit_reason",
    "r_multiple",
    "mfe_r",
    "mae_r",
    "minutes_fill_to_mfe",
    "minutes_fill_to_exit",
)


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _minute(value: datetime) -> int:
    local = value.astimezone(NY)
    return local.hour * 60 + local.minute


def _wall(bar: object) -> tuple[int, int, int]:
    local = cast(datetime, getattr(bar, "opened_at")).astimezone(NY)
    return local.hour, local.minute, local.second


def _time_bucket(minute: int) -> str:
    if minute < 615:
        return "10:00-10:14"
    if minute < 630:
        return "10:15-10:29"
    if minute < 645:
        return "10:30-10:44"
    if minute < 660:
        return "10:45-10:59"
    return "11:00+"


def _bin(value: Decimal | None, cuts: tuple[Decimal, ...], labels: tuple[str, ...]) -> str:
    if value is None:
        return "unavailable"
    for cut, label in zip(cuts, labels, strict=False):
        if value < cut:
            return label
    return labels[-1]


def _median_decimal(values: list[Decimal]) -> str | None:
    return None if not values else format(median(values), "f")


def _ratio(n: int, d: int) -> str:
    return "0" if d == 0 else format(Decimal(n) / Decimal(d), "f")


def _cibo_research_priors(ledger_dir: Path) -> dict[str, object]:
    summary = json.loads(
        (ledger_dir / "CIBO_ATLAS_VT31_EIGHT_LEDGER_SUMMARY.json").read_text()
    )
    if summary.get("schema") != CIBO_SCHEMA or summary.get("research_only") is not True:
        raise ValueError("CIBO governance/schema mismatch")

    daily = [r for r in _jsonl(ledger_dir / "DAILY_PATH_LEDGER.jsonl") if r.get("market") == MARKET]
    departures = [
        r for r in _jsonl(ledger_dir / "DEPARTURE_TIMING_LEDGER.jsonl")
        if r.get("market") == MARKET
    ]
    sequences = [
        r for r in _jsonl(ledger_dir / "PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl")
        if r.get("market") == MARKET
    ]
    targets = [
        r for r in _jsonl(ledger_dir / "TARGET_DESTINATION_LEDGER.jsonl")
        if r.get("market") == MARKET
    ]
    trader = [
        r for r in _jsonl(ledger_dir / "TRADER_MARKET_SYNC_LEDGER.jsonl")
        if r.get("market") == MARKET
    ]
    if (len(daily), len(departures), len(sequences), len(targets), len(trader)) != (
        1591,
        547,
        547,
        1591,
        208,
    ):
        raise ValueError("unexpected NAS100 CIBO ledger counts")

    regime_by_partition: dict[str, Counter[str]] = defaultdict(Counter)
    objective_by_partition: dict[str, list[bool]] = defaultdict(list)
    for row in daily:
        partition = str(row["partition"])
        regime_by_partition[partition][str(row["day_regime"])] += 1
        objective_by_partition[partition].append(bool(row["opposite_boundary_hit_by_16"]))

    departure_minutes: dict[str, list[int]] = defaultdict(list)
    last_structure: dict[str, Counter[str]] = defaultdict(Counter)
    sequence_tail: dict[str, Counter[str]] = defaultdict(Counter)
    for row in departures:
        partition = str(row["partition"])
        departure_minutes[partition].append(
            _minute(datetime.fromisoformat(str(row["departure_at"])))
        )
        last_structure[partition][str(row["last_structure_before_departure"])] += 1
    for row in sequences:
        partition = str(row["partition"])
        events = [
            str(event["event"])
            for event in cast(list[dict[str, object]], row["event_sequence"])
            if not str(event["event"]).startswith("opposite_09_boundary")
            and str(event["event"]) != "departure_pivot"
        ]
        if events:
            sequence_tail[partition][events[-1]] += 1

    stop_mismatch: dict[str, dict[str, int]] = {}
    for partition in sorted({str(r["partition"]) for r in trader}):
        rows = [r for r in trader if str(r["partition"]) == partition]
        stop_rows = [
            r for r in rows
            if str(r.get("terminal_family")) in {"initial_stop", "protected_stop"}
        ]
        stop_mismatch[partition] = {
            "stop_roots": len(stop_rows),
            "stopped_before_eventual_source_objective": sum(
                bool(r.get("trader_stopped_before_eventual_source_objective"))
                for r in stop_rows
            ),
        }

    extension_levels = ("0.25", "0.5", "1", "1.5", "2")
    target_extension: dict[str, dict[str, str | int]] = {}
    for partition in sorted({str(r["partition"]) for r in targets}):
        rows = [r for r in targets if str(r["partition"]) == partition]
        hits = [r for r in rows if bool(r["opposite_boundary_hit_by_16"])]
        payload: dict[str, str | int] = {
            "market_days": len(rows),
            "boundary_hits": len(hits),
            "boundary_hit_rate": _ratio(len(hits), len(rows)),
        }
        for level in extension_levels:
            n = sum(bool(cast(dict[str, bool], r["post_boundary_ladder"])[level]) for r in hits)
            payload[f"extension_{level}_rate_after_boundary"] = _ratio(n, len(hits))
        target_extension[partition] = payload

    timing: dict[str, object] = {}
    for partition, values in sorted(departure_minutes.items()):
        ordered = sorted(values)
        last = len(ordered) - 1
        timing[partition] = {
            "n": len(ordered),
            "p25_minute_ny": ordered[last * 25 // 100],
            "p50_minute_ny": ordered[last * 50 // 100],
            "p75_minute_ny": ordered[last * 75 // 100],
        }

    return {
        "artifact_id": CIBO_ARTIFACT_ID,
        "digest": CIBO_DIGEST,
        "source_sha": (ledger_dir / "git-sha.txt").read_text().strip(),
        "post_outcome_research_only": True,
        "regime_counts_by_partition": {
            p: dict(sorted(c.items())) for p, c in sorted(regime_by_partition.items())
        },
        "objective_hit_rate_by_partition": {
            p: _ratio(sum(values), len(values))
            for p, values in sorted(objective_by_partition.items())
        },
        "departure_timing_by_partition": timing,
        "last_structure_before_departure_by_partition": {
            p: dict(sorted(c.items())) for p, c in sorted(last_structure.items())
        },
        "last_predeparture_event_by_partition": {
            p: dict(sorted(c.items())) for p, c in sorted(sequence_tail.items())
        },
        "stop_mismatch_by_partition": stop_mismatch,
        "target_extension_by_partition": target_extension,
    }


def _first_breaches(
    session_prefix: tuple[object, ...],
    reference_low: Decimal,
    reference_high: Decimal,
) -> tuple[str, datetime | None, bool]:
    first_side = "none"
    first_at: datetime | None = None
    high_seen = False
    low_seen = False
    for bar in session_prefix:
        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        bar_high = high > reference_high
        bar_low = low < reference_low
        high_seen = high_seen or bar_high
        low_seen = low_seen or bar_low
        if first_at is None and (bar_high or bar_low):
            first_at = cast(datetime, getattr(bar, "closed_at"))
            if bar_high and bar_low:
                first_side = "both"
            elif bar_high:
                first_side = "high"
            else:
                first_side = "low"
    return first_side, first_at, high_seen and low_seen


def _reference_reclaim(
    session_prefix: tuple[object, ...],
    source: Vt31R22SourceSetup,
) -> datetime | None:
    for bar in session_prefix:
        closed = cast(datetime, getattr(bar, "closed_at"))
        if closed < source.structure.raid_at:
            continue
        close = _d(getattr(bar, "close"))
        if source.side.value == "short" and close < source.reference.high:
            return closed
        if source.side.value == "long" and close > source.reference.low:
            return closed
    return None


def _recent_path_efficiency(bars: tuple[object, ...]) -> Decimal | None:
    if len(bars) < 2:
        return None
    closes = [_d(getattr(bar, "close")) for bar in bars]
    gross = sum((abs(b - a) for a, b in zip(closes, closes[1:], strict=False)), Decimal(0))
    if gross == 0:
        return Decimal(0)
    return abs(closes[-1] - closes[0]) / gross


def _recent_overlap_rate(bars: tuple[object, ...]) -> Decimal | None:
    if len(bars) < 2:
        return None
    overlaps = 0
    pairs = 0
    for previous, current in zip(bars, bars[1:], strict=False):
        prior_high = _d(getattr(previous, "high"))
        prior_low = _d(getattr(previous, "low"))
        high = _d(getattr(current, "high"))
        low = _d(getattr(current, "low"))
        overlaps += min(prior_high, high) >= max(prior_low, low)
        pairs += 1
    return Decimal(overlaps) / Decimal(pairs)


def _state_features(
    prefix: tuple[object, ...],
    source: Vt31R22SourceSetup,
    executable: Vt31R22ExecutableSetup,
) -> dict[str, object]:
    decision_at = executable.decision_at
    minute = _minute(decision_at)
    session_prefix = tuple(
        bar
        for bar in prefix
        if (10, 0, 0) <= _wall(bar) < (11, 0, 0)
        and cast(datetime, getattr(bar, "closed_at")) <= decision_at
    )
    reference_width = source.reference.high - source.reference.low
    first_side, first_at, double_sided = _first_breaches(
        session_prefix, source.reference.low, source.reference.high
    )
    reclaim_at = _reference_reclaim(session_prefix, source)

    if source.side.value == "long":
        expected_side = "low"
        raid_extreme = min(
            (_d(getattr(bar, "low")) for bar in session_prefix),
            default=source.reference.low,
        )
        raid_depth = max(Decimal(0), source.reference.low - raid_extreme)
        directional_progress = (
            _d(getattr(session_prefix[-1], "close")) - source.reference.low
            if session_prefix else Decimal(0)
        )
    else:
        expected_side = "high"
        raid_extreme = max(
            (_d(getattr(bar, "high")) for bar in session_prefix),
            default=source.reference.high,
        )
        raid_depth = max(Decimal(0), raid_extreme - source.reference.high)
        directional_progress = (
            source.reference.high - _d(getattr(session_prefix[-1], "close"))
            if session_prefix else Decimal(0)
        )

    highs = [_d(getattr(bar, "high")) for bar in session_prefix]
    lows = [_d(getattr(bar, "low")) for bar in session_prefix]
    session_range = max(highs) - min(lows) if highs else Decimal(0)
    recent = session_prefix[-15:]
    recent_highs = [_d(getattr(bar, "high")) for bar in recent]
    recent_lows = [_d(getattr(bar, "low")) for bar in recent]
    recent_range = (
        max(recent_highs) - min(recent_lows) if recent_highs else Decimal(0)
    )

    risk = executable.initial_risk
    target_r = (
        abs(executable.target_price - executable.entry_price) / risk
        if risk > 0
        else Decimal(0)
    )
    risk_ref = risk / reference_width if reference_width > 0 else None
    raid_depth_ref = raid_depth / reference_width if reference_width > 0 else None
    session_range_ref = session_range / reference_width if reference_width > 0 else None
    recent_range_ref = recent_range / reference_width if reference_width > 0 else None
    progress_ref = directional_progress / reference_width if reference_width > 0 else None

    return {
        "decision_time_bucket": _time_bucket(minute),
        "decision_minute_ny": minute,
        "weekday": decision_at.astimezone(NY).strftime("%A"),
        "side": source.side.value,
        "entry_family": executable.selected_family.value,
        "candidate_family_count": len(executable.candidate_families),
        "reference_width": format(reference_width, "f"),
        "first_breach_side": first_side,
        "first_breach_minute_ny": _minute(first_at) if first_at is not None else None,
        "double_sided_before_decision": double_sided,
        "expected_side_breached": first_side in {expected_side, "both"},
        "minutes_raid_to_decision": max(
            0, int((decision_at - source.structure.raid_at).total_seconds() // 60)
        ),
        "reference_reclaimed": reclaim_at is not None,
        "minutes_reclaim_to_decision": (
            max(0, int((decision_at - reclaim_at).total_seconds() // 60))
            if reclaim_at is not None else None
        ),
        "raid_depth_ref": format(raid_depth_ref, "f") if raid_depth_ref is not None else None,
        "session_range_ref": (
            format(session_range_ref, "f") if session_range_ref is not None else None
        ),
        "recent_range_ref": (
            format(recent_range_ref, "f") if recent_range_ref is not None else None
        ),
        "recent_path_efficiency": (
            format(_recent_path_efficiency(recent), "f")
            if _recent_path_efficiency(recent) is not None else None
        ),
        "recent_overlap_rate": (
            format(_recent_overlap_rate(recent), "f")
            if _recent_overlap_rate(recent) is not None else None
        ),
        "directional_progress_ref": (
            format(progress_ref, "f") if progress_ref is not None else None
        ),
        "risk_ref": format(risk_ref, "f") if risk_ref is not None else None,
        "planned_target_r": format(target_r, "f"),
        "remaining_minutes_to_16": max(0, 16 * 60 - minute),
    }


def _as_decimal(row: dict[str, object], field: str) -> Decimal | None:
    value = row.get(field)
    return None if value is None else Decimal(str(value))


def _decorate_bins(row: dict[str, object]) -> dict[str, object]:
    target_r = _as_decimal(row, "planned_target_r")
    risk_ref = _as_decimal(row, "risk_ref")
    raid_depth = _as_decimal(row, "raid_depth_ref")
    session_range = _as_decimal(row, "session_range_ref")
    recent_range = _as_decimal(row, "recent_range_ref")
    path_eff = _as_decimal(row, "recent_path_efficiency")
    overlap = _as_decimal(row, "recent_overlap_rate")
    latency = _as_decimal(row, "minutes_raid_to_decision")
    reclaim_latency = _as_decimal(row, "minutes_reclaim_to_decision")
    return {
        **row,
        "target_r_bin": _bin(
            target_r,
            (Decimal("2"), Decimal("4"), Decimal("6"), Decimal("8"), Decimal("12")),
            ("<2", "2-4", "4-6", "6-8", "8-12", "12+"),
        ),
        "risk_ref_bin": _bin(
            risk_ref,
            (Decimal("0.15"), Decimal("0.25"), Decimal("0.40"), Decimal("0.65")),
            ("<0.15", "0.15-0.25", "0.25-0.40", "0.40-0.65", "0.65+"),
        ),
        "raid_depth_ref_bin": _bin(
            raid_depth,
            (Decimal("0.10"), Decimal("0.25"), Decimal("0.50")),
            ("<0.10", "0.10-0.25", "0.25-0.50", "0.50+"),
        ),
        "session_range_ref_bin": _bin(
            session_range,
            (Decimal("0.75"), Decimal("1.0"), Decimal("1.5")),
            ("<0.75", "0.75-1.00", "1.00-1.50", "1.50+"),
        ),
        "recent_range_ref_bin": _bin(
            recent_range,
            (Decimal("0.25"), Decimal("0.50"), Decimal("0.75")),
            ("<0.25", "0.25-0.50", "0.50-0.75", "0.75+"),
        ),
        "path_efficiency_bin": _bin(
            path_eff,
            (Decimal("0.20"), Decimal("0.40"), Decimal("0.60")),
            ("<0.20", "0.20-0.40", "0.40-0.60", "0.60+"),
        ),
        "overlap_rate_bin": _bin(
            overlap,
            (Decimal("0.40"), Decimal("0.70"), Decimal("0.90")),
            ("<0.40", "0.40-0.70", "0.70-0.90", "0.90+"),
        ),
        "raid_latency_bin": _bin(
            latency,
            (Decimal("5"), Decimal("15"), Decimal("30")),
            ("<5", "5-14", "15-29", "30+"),
        ),
        "reclaim_latency_bin": _bin(
            reclaim_latency,
            (Decimal("3"), Decimal("8"), Decimal("15")),
            ("<3", "3-7", "8-14", "15+"),
        ),
    }


def _subset_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    terminal = [row for row in rows if row.get("status") == "terminal"]
    trades = [
        {
            "r_multiple": cast(str, row["r_multiple"]),
            "signal_at": cast(str, row["signal_at"]),
        }
        for row in terminal
    ]
    metrics = baseline._metrics(trades, friction=FRICTION)
    mfes = [Decimal(cast(str, row["mfe_r"])) for row in terminal]
    maes = [Decimal(cast(str, row["mae_r"])) for row in terminal]
    return {
        **metrics,
        "terminal_rate": _ratio(len(terminal), len(rows)),
        "structural_target_rate": _ratio(
            sum(row.get("exit_reason") == "structural-target" for row in terminal),
            len(terminal),
        ),
        "mfe_p50_r": _median_decimal(mfes),
        "mae_p50_r": _median_decimal(maes),
        "mfe_reach": {
            level: _ratio(
                sum(Decimal(cast(str, row["mfe_r"])) >= Decimal(level) for row in terminal),
                len(terminal),
            )
            for level in ("0.5", "1", "1.5", "2", "3")
        },
    }


def _group_summary(
    rows: list[dict[str, object]],
    field: str,
) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(field))].append(row)
    return {
        key: _subset_metrics(group)
        for key, group in sorted(groups.items())
    }


def replay(
    ledger_dir: Path,
    evidence_path: Path,
    partition: str,
) -> dict[str, object]:
    cibo_priors = _cibo_research_priors(ledger_dir)
    series, account, evidence, checked, evidence_sha, provider = (
        baseline.load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("market-state lab requires NAS100 evidence")

    by_day: dict[object, list[object]] = defaultdict(list)
    for bar in series:
        by_day[baseline._day(getattr(bar, "opened_at"))].append(bar)

    policy = Vt31R22ExecutionPolicy()
    rows: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = tuple(by_day[local_day])
        reference = tuple(
            bar
            for bar in day_bars
            if (9, 0, 0) <= baseline._wall(getattr(bar, "opened_at")) < (10, 0, 0)
        )
        session = tuple(
            bar
            for bar in day_bars
            if (10, 0, 0) <= baseline._wall(getattr(bar, "opened_at")) < (11, 0, 0)
        )
        if len(reference) != 60 or len(session) != 60:
            status_counts["incomplete-day"] += 1
            continue

        prefix = list(reference)
        source: Vt31R22SourceSetup | None = None
        executable: Vt31R22ExecutableSetup | None = None
        for bar in session:
            prefix.append(bar)
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                continue
            candidate, _ = make_executable_setup(evaluation.setup, policy)
            if candidate is None:
                status_counts["source-not-executable"] += 1
                break
            source = evaluation.setup
            executable = candidate
            break

        if source is None or executable is None:
            status_counts["no-source-setup"] += 1
            continue

        state = _state_features(tuple(prefix), source, executable)
        outcome = baseline._simulate(day_bars, executable)
        status = cast(str, outcome["status"])
        status_counts[status] += 1
        row: dict[str, object] = {
            "partition": partition,
            "local_date": baseline._day(executable.decision_at).isoformat(),
            "signal_at": executable.decision_at.astimezone(UTC).isoformat(),
            **state,
            "status": status,
        }
        for field in RESEARCH_LABEL_FIELDS:
            if field in outcome:
                row[field] = outcome[field]
        rows.append(_decorate_bins(row))

    summary_fields = (
        "decision_time_bucket",
        "weekday",
        "side",
        "entry_family",
        "candidate_family_count",
        "first_breach_side",
        "double_sided_before_decision",
        "expected_side_breached",
        "reference_reclaimed",
        "target_r_bin",
        "risk_ref_bin",
        "raid_depth_ref_bin",
        "session_range_ref_bin",
        "recent_range_ref_bin",
        "path_efficiency_bin",
        "overlap_rate_bin",
        "raid_latency_bin",
        "reclaim_latency_bin",
    )
    summaries = {field: _group_summary(rows, field) for field in summary_fields}

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "partition": partition,
        "research_only": True,
        "opens_new_holdout": False,
        "fresh_holdout_consumed": False,
        "live_authorized": False,
        "production_authorized": False,
        "causal_contract": {
            "runtime_features_are_predecision_only": True,
            "date_level_outcome_lookup": False,
            "future_bar_lookup": False,
            "cibo_post_outcome_fields_runtime_access": False,
            "runtime_feature_fields": list(RUNTIME_FEATURE_FIELDS),
            "research_label_fields": list(RESEARCH_LABEL_FIELDS),
        },
        "cibo_research_priors": cibo_priors,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
            "bar_count": len(series),
        },
        "status_counts": dict(sorted(status_counts.items())),
        "source_setup_rows": len(rows),
        "terminal_economics": _subset_metrics(rows),
        "feature_summaries": summaries,
        "state_matrix": rows,
        "next_gate": (
            "compare identical predeclared state bins across consumed R8/R6/R5; "
            "only mechanisms with stable direction and adequate sample may inform "
            "a deterministic Intelligence V2 policy"
        ),
    }


def self_test() -> None:
    assert _time_bucket(600) == "10:00-10:14"
    assert _time_bucket(629) == "10:15-10:29"
    assert _time_bucket(630) == "10:30-10:44"
    assert _time_bucket(659) == "10:45-10:59"
    assert _bin(
        Decimal("5"),
        (Decimal("2"), Decimal("4"), Decimal("6")),
        ("<2", "2-4", "4-6", "6+"),
    ) == "4-6"
    assert CIBO_ARTIFACT_ID == 10478487667
    assert SCHEMA.endswith(".v2")
    print("VT31_NAS100 market-state lab V2 self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--ledger-dir", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--partition")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if None in (args.ledger_dir, args.evidence, args.partition, args.output):
        parser.error("--ledger-dir --evidence --partition --output are required")
    payload = replay(args.ledger_dir, args.evidence, cast(str, args.partition))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "market": MARKET,
                "partition": payload["partition"],
                "source_setup_rows": payload["source_setup_rows"],
                "terminal_economics": payload["terminal_economics"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
