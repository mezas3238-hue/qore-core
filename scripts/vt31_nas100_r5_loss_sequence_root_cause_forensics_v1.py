"""Loss-sequence root-cause forensics for VT31 NAS100 ALLOC_G.

Consumed evidence only. This module does not change the trading policy.

It decomposes losing streaks into:
- pre-entry market/trader state,
- routing tier and entry family,
- path anatomy after fill (MFE/MAE and exit reason),
- state transitions at the onset of material streaks,
- contexts over-represented inside severe losing sequences.

Post-outcome fields are diagnostic labels only and are never runtime inputs.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.loss_sequence_root_cause_forensics.v1"
MARKET = "NAS100"
PROFILE_NAME = "ALLOC_G_CORE_FAMILY_050"

MATERIAL_STREAK = 4
SEVERE_STREAK = 8

FEATURE_FIELDS = (
    "tier",
    "entry_family",
    "side",
    "h1_state",
    "h4_state",
    "reference_volatility_state",
    "prior_day_state",
    "premarket_state",
    "cash_open_state",
    "last_structure_event_family",
    "current_path_bucket",
    "risk_ref_bucket",
    "reclaim_age_bucket",
    "confirmation_latency_bucket",
    "authorization_reason",
)

CONSUMED_BLOCKS = {
    "Y1_WEAK_2022-07-18_2023-07-18": (
        date(2022, 7, 18),
        date(2023, 7, 18),
    ),
    "Y2_RECOVERY_2023-07-18_2024-07-18": (
        date(2023, 7, 18),
        date(2024, 7, 18),
    ),
}


def _decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _bucket_ratio(value: object) -> str:
    number = _decimal(value)
    if number is None:
        return "missing"
    if number < Decimal("0.75"):
        return "low"
    if number <= Decimal("1.25"):
        return "mid"
    return "high"


def _bucket_risk_ref(value: object) -> str:
    number = _decimal(value)
    if number is None:
        return "missing"
    if number < Decimal("0.30"):
        return "low"
    if number <= Decimal("0.70"):
        return "mid"
    return "high"


def _bucket_reclaim_age(value: object) -> str:
    if value is None:
        return "missing"
    age = int(value)
    if age <= 4:
        return "0_4m"
    if age <= 9:
        return "5_9m"
    if age <= 19:
        return "10_19m"
    return "20m_plus"


def _bucket_latency(value: object) -> str:
    if value is None:
        return "missing"
    latency = int(value)
    if latency <= 2:
        return "0_2m"
    if latency <= 5:
        return "3_5m"
    if latency <= 10:
        return "6_10m"
    return "11m_plus"


def _path_class(row: dict[str, object]) -> str:
    value = Decimal(cast(str, row["capital_weighted_net_r"]))
    if value >= 0:
        return "NON_LOSS"

    mfe = _decimal(row.get("mfe_r")) or Decimal(0)
    reason = str(row.get("exit_reason"))

    if reason == "breakeven-stop":
        return "BREAKEVEN_FRICTION_LOSS"
    if mfe >= Decimal("1.00"):
        return "GIVEBACK_AFTER_1R_PLUS"
    if reason == "initial-stop" and mfe < Decimal("0.50"):
        return "DEAD_ON_ARRIVAL"
    if reason == "initial-stop" and mfe < Decimal("1.00"):
        return "WEAK_FOLLOW_THROUGH"
    if reason == "16:00-lifecycle":
        return "NEGATIVE_LIFECYCLE_CLOSE"
    return "OTHER_LOSS"


def _decorate(row: dict[str, object]) -> dict[str, object]:
    updated = dict(row)
    updated["current_path_bucket"] = _bucket_ratio(
        row.get("current_path_vs_previous")
    )
    updated["risk_ref_bucket"] = _bucket_risk_ref(row.get("risk_ref"))
    updated["reclaim_age_bucket"] = _bucket_reclaim_age(
        row.get("reference_reclaim_age_minutes")
    )
    updated["confirmation_latency_bucket"] = _bucket_latency(
        row.get("confirmation_latency_minutes")
    )
    updated["loss_path_class"] = _path_class(updated)
    return updated


def _sorted(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(rows, key=lambda row: cast(str, row["signal_at"]))


def _is_loss(row: dict[str, object]) -> bool:
    return Decimal(cast(str, row["capital_weighted_net_r"])) < 0


def _mode(items: list[dict[str, object]], field: str) -> dict[str, object]:
    counts = Counter(str(item.get(field)) for item in items)
    if not counts:
        return {"value": "missing", "count": 0, "share": "0"}
    value, count = counts.most_common(1)[0]
    return {
        "value": value,
        "count": count,
        "share": format(Decimal(count) / Decimal(len(items)), "f"),
    }


def _mark_streaks(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    ordered = _sorted(rows)
    streak_ranges: list[tuple[int, int]] = []
    start: int | None = None

    for index, row in enumerate(ordered):
        if _is_loss(row):
            if start is None:
                start = index
            continue
        if start is not None:
            streak_ranges.append((start, index))
            start = None
    if start is not None:
        streak_ranges.append((start, len(ordered)))

    marked = [dict(row) for row in ordered]
    summaries: list[dict[str, object]] = []

    for streak_id, (begin, end) in enumerate(streak_ranges, start=1):
        items = marked[begin:end]
        length = len(items)
        total_r = sum(
            (Decimal(cast(str, item["capital_weighted_net_r"])) for item in items),
            Decimal(0),
        )
        mfes = [
            _decimal(item.get("mfe_r")) or Decimal(0)
            for item in items
        ]
        for item in items:
            item["loss_streak_id"] = streak_id
            item["loss_streak_length"] = length
            item["material_loss_streak"] = length >= MATERIAL_STREAK
            item["severe_loss_streak"] = length >= SEVERE_STREAK

        summaries.append(
            {
                "streak_id": streak_id,
                "start_signal_at": items[0]["signal_at"],
                "end_signal_at": items[-1]["signal_at"],
                "length": length,
                "cumulative_r": format(total_r, "f"),
                "mean_mfe_r": format(
                    sum(mfes, Decimal(0)) / Decimal(length),
                    "f",
                ),
                "max_mfe_r": format(max(mfes), "f"),
                "tier_mode": _mode(items, "tier"),
                "family_mode": _mode(items, "entry_family"),
                "side_mode": _mode(items, "side"),
                "h1_mode": _mode(items, "h1_state"),
                "premarket_mode": _mode(items, "premarket_state"),
                "cash_open_mode": _mode(items, "cash_open_state"),
                "path_class_counts": dict(
                    Counter(
                        str(item["loss_path_class"])
                        for item in items
                    )
                ),
                "exit_reason_counts": dict(
                    Counter(str(item.get("exit_reason")) for item in items)
                ),
            }
        )

    return marked, summaries


def _loss_anatomy(rows: list[dict[str, object]]) -> dict[str, object]:
    losses = [row for row in rows if _is_loss(row)]
    counts = Counter(str(row["loss_path_class"]) for row in losses)
    total_by_class: dict[str, Decimal] = defaultdict(Decimal)
    mfe_by_class: dict[str, list[Decimal]] = defaultdict(list)

    for row in losses:
        key = str(row["loss_path_class"])
        total_by_class[key] += Decimal(
            cast(str, row["capital_weighted_net_r"])
        )
        mfe_by_class[key].append(
            _decimal(row.get("mfe_r")) or Decimal(0)
        )

    classes: dict[str, object] = {}
    for key in sorted(counts):
        mfes = mfe_by_class[key]
        classes[key] = {
            "count": counts[key],
            "share_of_losses": format(
                Decimal(counts[key]) / Decimal(len(losses)),
                "f",
            )
            if losses
            else "0",
            "total_r": format(total_by_class[key], "f"),
            "mean_mfe_r": format(
                sum(mfes, Decimal(0)) / Decimal(len(mfes)),
                "f",
            )
            if mfes
            else "0",
        }

    return {
        "loss_count": len(losses),
        "classes": classes,
    }


def _feature_diagnostics(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for field in FEATURE_FIELDS:
            grouped[f"{field}={row.get(field)}"].append(row)

    result: dict[str, dict[str, object]] = {}
    for key, items in sorted(grouped.items()):
        values = [
            Decimal(cast(str, item["capital_weighted_net_r"]))
            for item in items
        ]
        losses = [item for item in items if _is_loss(item)]
        severe = [
            item
            for item in losses
            if bool(item.get("severe_loss_streak"))
        ]
        mfes = [
            _decimal(item.get("mfe_r")) or Decimal(0)
            for item in losses
        ]
        path_counts = Counter(
            str(item["loss_path_class"]) for item in losses
        )
        result[key] = {
            "sample": len(items),
            "losses": len(losses),
            "wins_or_flats": len(items) - len(losses),
            "loss_rate": format(
                Decimal(len(losses)) / Decimal(len(items)),
                "f",
            ),
            "total_r": format(sum(values, Decimal(0)), "f"),
            "mean_r": format(
                sum(values, Decimal(0)) / Decimal(len(items)),
                "f",
            ),
            "severe_streak_loss_count": len(severe),
            "severe_streak_loss_share": format(
                Decimal(len(severe)) / Decimal(len(losses)),
                "f",
            )
            if losses
            else "0",
            "loss_mean_mfe_r": format(
                sum(mfes, Decimal(0)) / Decimal(len(mfes)),
                "f",
            )
            if mfes
            else "0",
            "loss_path_counts": dict(path_counts),
        }
    return result


def _onset_transitions(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    ordered = _sorted(rows)
    transitions: Counter[str] = Counter()
    onset_states: Counter[str] = Counter()
    material_streaks = 0

    index = 0
    while index < len(ordered):
        if not _is_loss(ordered[index]):
            index += 1
            continue
        start = index
        while index < len(ordered) and _is_loss(ordered[index]):
            index += 1
        length = index - start
        if length < MATERIAL_STREAK:
            continue
        material_streaks += 1
        current = ordered[start]
        previous = ordered[start - 1] if start > 0 else None
        for field in FEATURE_FIELDS:
            current_value = str(current.get(field))
            onset_states[f"{field}={current_value}"] += 1
            if previous is None:
                continue
            previous_value = str(previous.get(field))
            if previous_value != current_value:
                transitions[
                    f"{field}:{previous_value}->{current_value}"
                ] += 1

    return {
        "material_streak_count": material_streaks,
        "top_onset_states": [
            {"state": key, "count": count}
            for key, count in onset_states.most_common(30)
        ],
        "top_state_transitions": [
            {"transition": key, "count": count}
            for key, count in transitions.most_common(30)
        ],
    }


def _analyze(rows: list[dict[str, object]]) -> dict[str, object]:
    marked, streaks = _mark_streaks(rows)
    metrics = engine._capital_metrics(marked)
    losses = [row for row in marked if _is_loss(row)]
    severe_losses = [
        row for row in losses if bool(row.get("severe_loss_streak"))
    ]

    longest = max((int(item["length"]) for item in streaks), default=0)
    material = [item for item in streaks if int(item["length"]) >= MATERIAL_STREAK]
    severe = [item for item in streaks if int(item["length"]) >= SEVERE_STREAK]

    return {
        "trade_count": len(marked),
        "metrics": metrics,
        "loss_anatomy": _loss_anatomy(marked),
        "streak_summary": {
            "longest_losing_streak": longest,
            "material_streak_threshold": MATERIAL_STREAK,
            "severe_streak_threshold": SEVERE_STREAK,
            "material_streak_count": len(material),
            "severe_streak_count": len(severe),
            "severe_streak_loss_count": len(severe_losses),
            "severe_streak_loss_share": format(
                Decimal(len(severe_losses)) / Decimal(len(losses)),
                "f",
            )
            if losses
            else "0",
            "top_streaks": sorted(
                streaks,
                key=lambda item: (
                    int(item["length"]),
                    -Decimal(cast(str, item["cumulative_r"])),
                ),
                reverse=True,
            )[:20],
        },
        "feature_diagnostics": _feature_diagnostics(marked),
        "onset_transitions": _onset_transitions(marked),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("loss-sequence forensics requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    first_rows, first_diag = corrective._first_rows(
        by_day,
        context_by_day,
        evidence=evidence,
        alt_partial_r=None,
        secondary_route_policy="ORIGINAL",
    )
    rearm_rows, rearm_diag = corrective._rearm_rows(
        by_day,
        context_by_day,
        first_rows,
        evidence=evidence,
        rearm_partial_r=None,
    )
    nominal = _sorted([*first_rows, *rearm_rows])
    alloc_g = [
        _decorate(row)
        for row in allocation._apply_profile(
            nominal,
            profile=allocation.PROFILES[PROFILE_NAME],
        )
    ]

    consumed_blocks: dict[str, object] = {}
    if partition == "consumed_holdout":
        for name, (start, end) in CONSUMED_BLOCKS.items():
            selected = [
                row
                for row in alloc_g
                if start
                <= date.fromisoformat(cast(str, row["local_date"]))
                < end
            ]
            consumed_blocks[name] = {
                "start": start.isoformat(),
                "end_exclusive": end.isoformat(),
                **_analyze(selected),
            }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "allocation_profile": PROFILE_NAME,
        "overall": _analyze(alloc_g),
        "consumed_blocks": consumed_blocks,
        "diagnostics": {
            "first": first_diag,
            "rearm": rearm_diag,
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "post_outcome_fields_diagnostic_only": True,
            "decision_time_context_separated_from_outcome_labels": True,
            "trade_authorization_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "allocation_profile_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_time_at_runtime": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
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
                "overall": payload["overall"],
                "consumed_blocks": payload["consumed_blocks"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
