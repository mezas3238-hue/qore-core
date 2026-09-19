"""Deep falsification of VT31 losing streaks against frozen Silver Bullet.

This lab freezes the TTrades AM Silver Bullet source model byte-for-byte and
asks whether long losing streaks already exist in the source/execution-policy
baseline, or whether they are introduced by VT31/QORE routing, reasoning,
rearm, allocation or management layers.

Silver Bullet is NOT modified.

Only native M1 / methodology-adjacent anatomy is used for primary causal
features:
- 09:00-10:00 NY frozen reference geometry;
- 10:00-11:00 NY raid/confirmation/decision timing;
- raid depth, confirmation latency and entry-family evidence;
- entry/stop/target geometry;
- candidate confluence;
- fill delay and same-source path;
- chronological side/family repetition and pre-existing loss-streak state.

Post-fill MFE/MAE/outcome fields are diagnostic labels only.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_r1_candidate as baseline
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    load_market_evidence,
)
from qore.infrastructure.traders import vt31_silver_bullet_r2_2 as silver
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22EntryEvidence,
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.silver_bullet_native_streak_falsification.v1"
IDENTITY = "VT31_NAS100_SILVER_BULLET_NATIVE_STREAK_FALSIFICATION_V1"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
EXPECTED_SOURCE_SHA256 = (
    "bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf"
)
EXPECTED_METHODOLOGY_ID = "ttrades-am-silver-bullet-nq-r2.2"

FEATURE_FIELDS = (
    "side",
    "entry_family",
    "candidate_combo",
    "candidate_count_bucket",
    "raid_minute_bucket",
    "confirmation_minute_bucket",
    "decision_minute_bucket",
    "raid_to_confirmation_bucket",
    "confirmation_to_decision_bucket",
    "fill_delay_bucket",
    "raid_depth_ref_bucket",
    "risk_ref_bucket",
    "planned_target_r_bucket",
    "entry_location_ref_bucket",
    "zone_width_ref_bucket",
    "extreme_body_fraction_bucket",
    "reference_width_pct_bucket",
    "same_side_as_previous",
    "same_family_as_previous",
    "pre_loss_streak_bucket",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _minute_10(value: datetime) -> int:
    local = value.astimezone(specialist._NY)
    return local.hour * 60 + local.minute - 10 * 60


def _bucket_minute(value: int) -> str:
    if value < 10:
        return "00_09"
    if value < 20:
        return "10_19"
    if value < 30:
        return "20_29"
    if value < 40:
        return "30_39"
    return "40_59"


def _bucket_delay(value: int) -> str:
    if value <= 1:
        return "0_1m"
    if value <= 3:
        return "2_3m"
    if value <= 5:
        return "4_5m"
    if value <= 10:
        return "6_10m"
    return "11m_plus"


def _bucket_ratio(value: Decimal | None) -> str:
    if value is None:
        return "missing"
    if value < Decimal("0.10"):
        return "lt_0_10"
    if value < Decimal("0.25"):
        return "0_10_0_25"
    if value < Decimal("0.50"):
        return "0_25_0_50"
    if value < Decimal("1.00"):
        return "0_50_1_00"
    return "ge_1_00"


def _bucket_target(value: Decimal) -> str:
    if value < Decimal("1.0"):
        return "lt_1R"
    if value < Decimal("2.0"):
        return "1_2R"
    if value < Decimal("3.0"):
        return "2_3R"
    return "ge_3R"


def _bucket_location(value: Decimal) -> str:
    if value < Decimal("0"):
        return "below_reference"
    if value <= Decimal("0.33"):
        return "lower_third"
    if value <= Decimal("0.67"):
        return "middle_third"
    if value <= Decimal("1"):
        return "upper_third"
    return "above_reference"


def _bucket_body(value: Decimal | None) -> str:
    if value is None:
        return "missing"
    if value < Decimal("0.25"):
        return "wick_dominant"
    if value < Decimal("0.60"):
        return "mixed_body"
    return "body_dominant"


def _bucket_ref_width_pct(value: Decimal) -> str:
    if value < Decimal("0.002"):
        return "lt_0_20pct"
    if value < Decimal("0.004"):
        return "0_20_0_40pct"
    if value < Decimal("0.006"):
        return "0_40_0_60pct"
    return "ge_0_60pct"


def _bucket_count(value: int) -> str:
    return "1" if value == 1 else "2" if value == 2 else "3_plus"


def _bucket_pre_streak(value: int) -> str:
    if value == 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    if value == 3:
        return "3"
    return "4_plus"


def _selected_candidate(
    source: Vt31R22SourceSetup,
    setup: Vt31R22ExecutableSetup,
) -> Vt31R22EntryEvidence | None:
    eligible = [
        item
        for item in source.candidates
        if item.family == setup.selected_family
        and item.formed_at <= setup.decision_at
    ]
    if not eligible:
        return None
    return sorted(
        eligible,
        key=lambda item: (item.formed_at, item.zone_lower, item.zone_upper),
    )[0]


def _loss_path(outcome: dict[str, object], net_r: Decimal) -> str:
    if net_r >= 0:
        return "NON_LOSS"
    mfe = _d(outcome.get("mfe_r", "0"))
    reason = str(outcome.get("exit_reason"))
    if reason == "breakeven-stop":
        return "BREAKEVEN_FRICTION_LOSS"
    if mfe >= Decimal("1.00"):
        return "GIVEBACK_AFTER_1R_PLUS"
    if reason == "initial-stop" and mfe < Decimal("0.50"):
        return "DEAD_ON_ARRIVAL"
    if reason == "initial-stop":
        return "WEAK_FOLLOW_THROUGH"
    if reason == "16:00-lifecycle":
        return "NEGATIVE_LIFECYCLE_CLOSE"
    return "OTHER_LOSS"


def _native_features(
    *,
    source: Vt31R22SourceSetup,
    setup: Vt31R22ExecutableSetup,
    outcome: dict[str, object],
) -> dict[str, object]:
    ref_width = source.reference.high - source.reference.low
    ref_mid = (source.reference.high + source.reference.low) / Decimal(2)
    selected_candidate = _selected_candidate(source, setup)

    if setup.side.value == "short":
        raid_depth = source.structure.swing_extreme - source.reference.high
    else:
        raid_depth = source.reference.low - source.structure.swing_extreme
    raid_depth_ref = (
        None if ref_width <= 0 else max(Decimal(0), raid_depth) / ref_width
    )
    risk_ref = (
        None if ref_width <= 0 else setup.initial_risk / ref_width
    )
    target_r = (
        abs(setup.target_price - setup.entry_price) / setup.initial_risk
        if setup.initial_risk > 0
        else Decimal(0)
    )
    entry_location = (
        (setup.entry_price - source.reference.low) / ref_width
        if ref_width > 0
        else Decimal(0)
    )

    zone_width_ref: Decimal | None = None
    if selected_candidate is not None and ref_width > 0:
        zone_width_ref = (
            selected_candidate.zone_upper - selected_candidate.zone_lower
        ) / ref_width

    extreme_range = (
        source.structure.extreme_candle_high
        - source.structure.extreme_candle_low
    )
    body_fraction = (
        None
        if extreme_range <= 0
        else abs(
            source.structure.extreme_candle_close
            - source.structure.extreme_candle_open
        )
        / extreme_range
    )

    raid_minute = _minute_10(source.structure.raid_at)
    confirmation_minute = _minute_10(source.structure.confirmation_at)
    decision_minute = _minute_10(setup.decision_at)
    raid_to_confirmation = int(
        (
            source.structure.confirmation_at - source.structure.raid_at
        ).total_seconds()
        // 60
    )
    confirmation_to_decision = int(
        (
            setup.decision_at - source.structure.confirmation_at
        ).total_seconds()
        // 60
    )
    fill_at = datetime.fromisoformat(cast(str, outcome["filled_at"]))
    fill_delay = int((fill_at - setup.decision_at).total_seconds() // 60)

    combo = "+".join(
        sorted(family.value for family in setup.candidate_families)
    )
    ref_width_pct = (
        ref_width / ref_mid if ref_mid > 0 else Decimal(0)
    )

    return {
        "raid_at": source.structure.raid_at.astimezone(UTC).isoformat(),
        "confirmation_at": (
            source.structure.confirmation_at.astimezone(UTC).isoformat()
        ),
        "raid_minute": raid_minute,
        "confirmation_minute": confirmation_minute,
        "decision_minute": decision_minute,
        "raid_minute_bucket": _bucket_minute(raid_minute),
        "confirmation_minute_bucket": _bucket_minute(confirmation_minute),
        "decision_minute_bucket": _bucket_minute(decision_minute),
        "raid_to_confirmation_minutes": raid_to_confirmation,
        "raid_to_confirmation_bucket": _bucket_delay(
            raid_to_confirmation
        ),
        "confirmation_to_decision_minutes": confirmation_to_decision,
        "confirmation_to_decision_bucket": _bucket_delay(
            confirmation_to_decision
        ),
        "fill_delay_minutes": fill_delay,
        "fill_delay_bucket": _bucket_delay(fill_delay),
        "raid_depth_ref": (
            None
            if raid_depth_ref is None
            else format(raid_depth_ref, "f")
        ),
        "raid_depth_ref_bucket": _bucket_ratio(raid_depth_ref),
        "risk_ref": None if risk_ref is None else format(risk_ref, "f"),
        "risk_ref_bucket": _bucket_ratio(risk_ref),
        "planned_target_r_native": format(target_r, "f"),
        "planned_target_r_bucket": _bucket_target(target_r),
        "entry_location_ref": format(entry_location, "f"),
        "entry_location_ref_bucket": _bucket_location(entry_location),
        "zone_width_ref": (
            None
            if zone_width_ref is None
            else format(zone_width_ref, "f")
        ),
        "zone_width_ref_bucket": _bucket_ratio(zone_width_ref),
        "extreme_body_fraction": (
            None
            if body_fraction is None
            else format(body_fraction, "f")
        ),
        "extreme_body_fraction_bucket": _bucket_body(body_fraction),
        "reference_width": format(ref_width, "f"),
        "reference_width_pct_mid": format(ref_width_pct, "f"),
        "reference_width_pct_bucket": _bucket_ref_width_pct(
            ref_width_pct
        ),
        "candidate_count": len(setup.candidate_families),
        "candidate_count_bucket": _bucket_count(
            len(setup.candidate_families)
        ),
        "candidate_combo": combo,
    }


def _profit_factor(values: list[Decimal]) -> Decimal | None:
    gains = sum((item for item in values if item > 0), Decimal(0))
    losses = -sum((item for item in values if item < 0), Decimal(0))
    if losses == 0:
        return None
    return gains / losses


def _group_stats(rows: list[dict[str, object]]) -> dict[str, object]:
    values = [_d(row["net_r_after_friction"]) for row in rows]
    losses = [row for row in rows if _d(row["net_r_after_friction"]) < 0]
    severe = [
        row
        for row in losses
        if bool(row.get("severe_loss_streak"))
    ]
    pf = _profit_factor(values)
    return {
        "sample": len(rows),
        "losses": len(losses),
        "loss_rate": (
            "0"
            if not rows
            else format(Decimal(len(losses)) / Decimal(len(rows)), "f")
        ),
        "total_r": format(sum(values, Decimal(0)), "f"),
        "mean_r": (
            "0"
            if not rows
            else format(sum(values, Decimal(0)) / Decimal(len(rows)), "f")
        ),
        "profit_factor": None if pf is None else format(pf, "f"),
        "severe_streak_loss_share": (
            "0"
            if not losses
            else format(Decimal(len(severe)) / Decimal(len(losses)), "f")
        ),
        "dead_on_arrival": sum(
            row["loss_path_class"] == "DEAD_ON_ARRIVAL"
            for row in losses
        ),
        "giveback_after_1r": sum(
            row["loss_path_class"] == "GIVEBACK_AFTER_1R_PLUS"
            for row in losses
        ),
    }


def _mark_sequence(rows: list[dict[str, object]]) -> None:
    rows.sort(key=lambda row: cast(str, row["signal_at"]))
    pre_loss_streak = 0
    same_side_run = 0
    same_family_run = 0
    previous_side: str | None = None
    previous_family: str | None = None

    for row in rows:
        side = cast(str, row["side"])
        family = cast(str, row["entry_family"])
        row["same_side_as_previous"] = (
            previous_side is not None and side == previous_side
        )
        row["same_family_as_previous"] = (
            previous_family is not None and family == previous_family
        )
        same_side_run = (
            same_side_run + 1 if side == previous_side else 1
        )
        same_family_run = (
            same_family_run + 1 if family == previous_family else 1
        )
        row["same_side_run_before"] = max(0, same_side_run - 1)
        row["same_family_run_before"] = max(0, same_family_run - 1)
        row["pre_loss_streak"] = pre_loss_streak
        row["pre_loss_streak_bucket"] = _bucket_pre_streak(
            pre_loss_streak
        )

        if _d(row["net_r_after_friction"]) < 0:
            pre_loss_streak += 1
        else:
            pre_loss_streak = 0
        previous_side = side
        previous_family = family

    streak_id = 0
    index = 0
    while index < len(rows):
        if _d(rows[index]["net_r_after_friction"]) >= 0:
            index += 1
            continue
        start = index
        while (
            index < len(rows)
            and _d(rows[index]["net_r_after_friction"]) < 0
        ):
            index += 1
        length = index - start
        streak_id += 1
        for row in rows[start:index]:
            row["loss_streak_id"] = streak_id
            row["loss_streak_length"] = length
            row["material_loss_streak"] = length >= 4
            row["severe_loss_streak"] = length >= 8


def _feature_diagnostics(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for field in FEATURE_FIELDS:
            grouped[f"{field}={row.get(field)}"].append(row)
    return {
        key: _group_stats(items)
        for key, items in sorted(grouped.items())
    }


def _streak_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    lengths: dict[int, int] = {}
    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        sid = row.get("loss_streak_id")
        if sid is None:
            continue
        grouped[int(cast(int, sid))].append(row)

    top: list[dict[str, object]] = []
    for sid, items in grouped.items():
        length = int(cast(int, items[0]["loss_streak_length"]))
        lengths[sid] = length
        if length < 4:
            continue
        top.append(
            {
                "streak_id": sid,
                "length": length,
                "start": items[0]["signal_at"],
                "end": items[-1]["signal_at"],
                "total_r": format(
                    sum(
                        (
                            _d(item["net_r_after_friction"])
                            for item in items
                        ),
                        Decimal(0),
                    ),
                    "f",
                ),
                "families": dict(
                    Counter(
                        cast(str, item["entry_family"])
                        for item in items
                    )
                ),
                "sides": dict(
                    Counter(cast(str, item["side"]) for item in items)
                ),
                "raid_minutes": dict(
                    Counter(
                        cast(str, item["raid_minute_bucket"])
                        for item in items
                    )
                ),
                "confirmation_delays": dict(
                    Counter(
                        cast(str, item["raid_to_confirmation_bucket"])
                        for item in items
                    )
                ),
                "loss_paths": dict(
                    Counter(
                        cast(str, item["loss_path_class"])
                        for item in items
                    )
                ),
            }
        )
    top.sort(key=lambda item: int(cast(int, item["length"])), reverse=True)
    return {
        "longest_losing_streak": max(lengths.values(), default=0),
        "material_streak_count": sum(value >= 4 for value in lengths.values()),
        "severe_streak_count": sum(value >= 8 for value in lengths.values()),
        "top_streaks": top[:20],
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    if silver.SOURCE_SHA256 != EXPECTED_SOURCE_SHA256:
        raise AssertionError("Silver Bullet source SHA changed")
    if silver.METHODOLOGY_ID != EXPECTED_METHODOLOGY_ID:
        raise AssertionError("Silver Bullet methodology identity changed")

    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("native streak falsification requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    policy = Vt31R22ExecutionPolicy()
    rows: list[dict[str, object]] = []
    status: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(
            day_bars,
            (9, 0, 0),
            (10, 0, 0),
        )
        session = specialist._slice(
            day_bars,
            (10, 0, 0),
            (11, 0, 0),
        )
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        prefix = list(reference)
        selected_source: Vt31R22SourceSetup | None = None
        selected_setup: Vt31R22ExecutableSetup | None = None

        for bar in session:
            prefix.append(bar)
            closed_at = cast(datetime, getattr(bar, "closed_at"))
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=closed_at,
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                if evaluation.both_sides_swept:
                    status["both-sides-swept"] += 1
                    break
                continue
            executable, _ = make_executable_setup(
                evaluation.setup,
                policy,
            )
            if executable is None:
                status["source-not-executable"] += 1
                break
            selected_source = evaluation.setup
            selected_setup = executable
            break

        if selected_source is None or selected_setup is None:
            status["no-executable-source"] += 1
            continue

        outcome = baseline._simulate(day_bars, selected_setup)
        outcome_status = cast(str, outcome["status"])
        status[f"outcome-{outcome_status}"] += 1
        if outcome_status != "terminal":
            continue

        raw_r = _d(outcome["r_multiple"])
        net_r = raw_r - FRICTION
        row = dict(outcome)
        row.update(
            _native_features(
                source=selected_source,
                setup=selected_setup,
                outcome=outcome,
            )
        )
        row.update(
            {
                "partition": partition,
                "source_only_silver_bullet": True,
                "vt31_reasoning_used": False,
                "vt31_secondary_used": False,
                "vt31_rearm_used": False,
                "vt31_alloc_g_used": False,
                "net_r_after_friction": format(net_r, "f"),
                "loss_path_class": _loss_path(outcome, net_r),
            }
        )
        rows.append(row)

    _mark_sequence(rows)
    metrics = _metrics(
        [{**row, "r_multiple": row["net_r_after_friction"]} for row in rows],
        friction=Decimal(0),
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "partition": partition,
        "market": MARKET,
        "silver_bullet_freeze": {
            "source_file": silver.SOURCE_FILE,
            "source_sha256": silver.SOURCE_SHA256,
            "methodology_id": silver.METHODOLOGY_ID,
            "source_fingerprint": silver.source_fingerprint(),
            "source_module_modified_by_lab": False,
        },
        "trade_count": len(rows),
        "metrics": metrics,
        "streak_summary": _streak_summary(rows),
        "feature_diagnostics": _feature_diagnostics(rows),
        "sequence_state": {
            bucket: _group_stats(
                [
                    row
                    for row in rows
                    if row["pre_loss_streak_bucket"] == bucket
                ]
            )
            for bucket in ("0", "1", "2", "3", "4_plus")
        },
        "loss_anatomy": {
            key: _group_stats(
                [
                    row
                    for row in rows
                    if row["loss_path_class"] == key
                ]
            )
            for key in (
                "DEAD_ON_ARRIVAL",
                "WEAK_FOLLOW_THROUGH",
                "GIVEBACK_AFTER_1R_PLUS",
                "BREAKEVEN_FRICTION_LOSS",
                "NEGATIVE_LIFECYCLE_CLOSE",
                "OTHER_LOSS",
            )
        },
        "status_counts": dict(sorted(status.items())),
        "trades": rows,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "silver_bullet_modified": False,
            "silver_bullet_source_frozen": True,
            "m1_only_source_replay": True,
            "h4_used_as_primary_causal_feature": False,
            "h1_trend_used_as_primary_causal_feature": False,
            "post_outcome_fields_diagnostic_only": True,
            "consumed_evidence_only": True,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_time_as_runtime_rule": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "trade_count": payload["trade_count"],
                "metrics": payload["metrics"],
                "streak_summary": payload["streak_summary"],
                "sequence_state": payload["sequence_state"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
