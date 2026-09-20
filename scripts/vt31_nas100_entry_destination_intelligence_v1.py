"""Entry-to-destination structural target intelligence for VT31_NAS100.

Diagnostic-only research over the current causal stack.

For every executed trade this lab freezes the information available at entry
and independently reconstructs the maximum structural destination reached
before original methodological invalidation or the 16:00 NY lifecycle.

It does NOT use the current trade outcome to choose an entry or target.
Future journey depth is a research-only label.

Destination ladder:
- DOL0: invalidated before current structural boundary
- DOL1: current structural boundary
- DOL2: DOL1 + 0.25 reference width
- DOL3: DOL1 + 0.50 reference width
- DOL4: DOL1 + 1.00 reference width
- DOL5: DOL1 + 1.50 reference width
- DOL6: DOL1 + 2.00 reference width

Same-M1 stop/deeper-DOL ambiguity is censored conservatively.
Silver Bullet, entry, stop, current target, risk and lifecycle remain unchanged.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.entry_destination_intelligence.v1"
MARKET = "NAS100"

DOL_EXTENSIONS = (
    ("DOL1_BOUNDARY", Decimal("0.00")),
    ("DOL2_PLUS_0_25_REF", Decimal("0.25")),
    ("DOL3_PLUS_0_50_REF", Decimal("0.50")),
    ("DOL4_PLUS_1_00_REF", Decimal("1.00")),
    ("DOL5_PLUS_1_50_REF", Decimal("1.50")),
    ("DOL6_PLUS_2_00_REF", Decimal("2.00")),
)

ENTRY_FEATURES = (
    "tier",
    "entry_family",
    "side",
    "reference_volatility_state",
    "prior_day_state",
    "premarket_state",
    "cash_open_state",
    "last_structure_event_family",
    "current_path_bucket",
    "risk_ref_bucket",
    "reclaim_age_bucket",
    "confirmation_latency_bucket",
)

PAIR_FEATURES = (
    ("entry_family", "current_path_bucket"),
    ("entry_family", "risk_ref_bucket"),
    ("entry_family", "confirmation_latency_bucket"),
    ("tier", "entry_family"),
    ("tier", "current_path_bucket"),
    ("reference_volatility_state", "current_path_bucket"),
    ("premarket_state", "cash_open_state"),
    ("last_structure_event_family", "entry_family"),
)

TRIPLE_FEATURES = (
    ("tier", "entry_family", "current_path_bucket"),
    ("entry_family", "risk_ref_bucket", "confirmation_latency_bucket"),
    ("reference_volatility_state", "entry_family", "current_path_bucket"),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _opt_d(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _dt(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _touches_level(
    bar: object,
    *,
    side: str,
    level: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def _touches_stop(
    bar: object,
    *,
    side: str,
    stop: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "low")) <= stop
    return _d(getattr(bar, "high")) >= stop


def _destination_levels(
    *,
    side: str,
    target: Decimal,
    ref_width: Decimal,
) -> tuple[tuple[int, str, Decimal], ...]:
    direction = Decimal(1) if side == "long" else Decimal(-1)
    return tuple(
        (
            rank,
            name,
            target + direction * ref_width * extension,
        )
        for rank, (name, extension) in enumerate(
            DOL_EXTENSIONS,
            start=1,
        )
    )


def _journey_capacity(
    day_bars: tuple[object, ...],
    *,
    filled_at: datetime,
    side: str,
    initial_stop: Decimal,
    levels: tuple[tuple[int, str, Decimal], ...],
) -> dict[str, object]:
    start_index = next(
        (
            index
            for index, bar in enumerate(day_bars)
            if cast(datetime, getattr(bar, "closed_at")) == filled_at
        ),
        None,
    )
    if start_index is None:
        return {"status": "censored-fill-bar-not-found"}

    max_rank = 0
    reached_at: dict[int, str] = {}
    invalidated_at: str | None = None
    end_reason = "16:00-lifecycle"
    same_bar_ambiguity = False

    for index in range(start_index, len(day_bars)):
        bar = day_bars[index]
        opened = cast(datetime, getattr(bar, "opened_at"))
        if _wall(opened) >= (16, 0, 0):
            break

        stop_hit = _touches_stop(
            bar,
            side=side,
            stop=initial_stop,
        )
        bar_ranks = [
            rank
            for rank, _, level in levels
            if _touches_level(bar, side=side, level=level)
        ]
        new_rank = max(bar_ranks, default=0)

        if stop_hit and new_rank > max_rank:
            same_bar_ambiguity = True
            return {
                "status": "censored-same-bar-stop-deeper-dol",
                "max_dol_rank_before_ambiguity": max_rank,
                "same_bar_candidate_rank": new_rank,
                "same_bar_ambiguity": True,
            }

        for rank in sorted(bar_ranks):
            if rank > max_rank:
                max_rank = rank
                reached_at[rank] = cast(
                    datetime,
                    getattr(bar, "closed_at"),
                ).isoformat()

        if stop_hit:
            invalidated_at = cast(
                datetime,
                getattr(bar, "closed_at"),
            ).isoformat()
            end_reason = "methodological-invalidation"
            break

    return {
        "status": "labeled",
        "max_dol_rank": max_rank,
        "max_dol_name": (
            "DOL0_PRE_BOUNDARY_INVALIDATION"
            if max_rank == 0
            else levels[max_rank - 1][1]
        ),
        "dol1_reached": max_rank >= 1,
        "dol2_reached": max_rank >= 2,
        "dol3_reached": max_rank >= 3,
        "dol4_plus_reached": max_rank >= 4,
        "dol5_plus_reached": max_rank >= 5,
        "dol6_reached": max_rank >= 6,
        "reached_at": {
            str(rank): when
            for rank, when in sorted(reached_at.items())
        },
        "journey_end_reason": end_reason,
        "invalidated_at": invalidated_at,
        "same_bar_ambiguity": same_bar_ambiguity,
    }


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    labeled = [
        row
        for row in rows
        if row["capacity_status"] == "labeled"
    ]
    n = len(labeled)

    def count_at_least(rank: int) -> int:
        return sum(
            int(row["max_dol_rank"]) >= rank
            for row in labeled
        )

    def rate_at_least(rank: int) -> str:
        if n == 0:
            return "0"
        return format(
            Decimal(count_at_least(rank)) / Decimal(n),
            "f",
        )

    rank_counts = Counter(
        str(row["max_dol_name"])
        for row in labeled
    )
    invalidated = sum(
        row["journey_end_reason"] == "methodological-invalidation"
        for row in labeled
    )

    return {
        "observations": len(rows),
        "labeled": n,
        "censored": len(rows) - n,
        "dol0_count": sum(
            int(row["max_dol_rank"]) == 0
            for row in labeled
        ),
        "dol1_plus_rate": rate_at_least(1),
        "dol2_plus_rate": rate_at_least(2),
        "dol3_plus_rate": rate_at_least(3),
        "dol4_plus_rate": rate_at_least(4),
        "dol5_plus_rate": rate_at_least(5),
        "dol6_rate": rate_at_least(6),
        "journey_depth_counts": dict(sorted(rank_counts.items())),
        "methodological_invalidation_rate": (
            "0"
            if n == 0
            else format(
                Decimal(invalidated) / Decimal(n),
                "f",
            )
        ),
    }


def _group(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = "|".join(
            f"{field}={row.get(field)}"
            for field in fields
        )
        grouped[key].append(row)
    return {
        key: _summary(items)
        for key, items in sorted(grouped.items())
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, source_stats = alt._current_rows(path)

    (
        series,
        account,
        fingerprint,
        checked,
        evidence_sha,
        provider,
    ) = load_market_evidence(path)
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("entry-destination intelligence requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    observations: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()

    for row in rows:
        updated = {
            key: row.get(key)
            for key in (
                "local_date",
                "signal_at",
                "filled_at",
                "tier",
                "entry_family",
                "side",
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
        }

        entry = _opt_d(row.get("entry"))
        initial_stop = _opt_d(row.get("initial_stop"))
        target = _opt_d(row.get("structural_target"))
        risk_ref = _opt_d(row.get("risk_ref"))
        filled_at_raw = row.get("filled_at")

        if (
            entry is None
            or initial_stop is None
            or target is None
            or risk_ref is None
            or risk_ref <= 0
            or filled_at_raw is None
        ):
            updated["capacity_status"] = "censored-missing-geometry"
            status_counts["censored-missing-geometry"] += 1
            observations.append(updated)
            continue

        risk = abs(entry - initial_stop)
        if risk <= 0:
            updated["capacity_status"] = "censored-invalid-risk"
            status_counts["censored-invalid-risk"] += 1
            observations.append(updated)
            continue

        local_day = date.fromisoformat(str(row["local_date"]))
        day_bars = by_day.get(local_day)
        if not day_bars:
            updated["capacity_status"] = "censored-missing-day"
            status_counts["censored-missing-day"] += 1
            observations.append(updated)
            continue

        ref_width = risk / risk_ref
        levels = _destination_levels(
            side=str(row["side"]),
            target=target,
            ref_width=ref_width,
        )
        capacity = _journey_capacity(
            day_bars,
            filled_at=_dt(filled_at_raw),
            side=str(row["side"]),
            initial_stop=initial_stop,
            levels=levels,
        )

        updated["entry_price"] = format(entry, "f")
        updated["initial_stop"] = format(initial_stop, "f")
        updated["current_structural_target"] = format(target, "f")
        updated["reference_width_reconstructed"] = format(
            ref_width,
            "f",
        )
        updated["destination_ladder"] = [
            {
                "rank": rank,
                "name": name,
                "price": format(level, "f"),
            }
            for rank, name, level in levels
        ]
        updated["capacity_status"] = capacity["status"]
        if capacity["status"] == "labeled":
            updated.update(capacity)
        else:
            updated["capacity_diagnostic"] = capacity

        status_counts[str(capacity["status"])] += 1
        observations.append(updated)

    dimensions = {
        field: _group(observations, (field,))
        for field in ENTRY_FEATURES
    }
    pairs = {
        " x ".join(fields): _group(observations, fields)
        for fields in PAIR_FEATURES
    }
    triples = {
        " x ".join(fields): _group(observations, fields)
        for fields in TRIPLE_FEATURES
    }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "overall": _summary(observations),
        "dimensions": dimensions,
        "pairs": pairs,
        "triples": triples,
        "observations": observations,
        "status_counts": dict(sorted(status_counts.items())),
        "source_stats": source_stats,
        "diagnostics": diagnostics,
        "evidence": {
            **evidence,
            "account_fingerprint": account,
            "evidence_fingerprint": fingerprint,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "entry_state_frozen_before_outcome": True,
            "future_journey_is_research_label_only": True,
            "same_bar_stop_dol_ambiguity_censored": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "current_target_changed": False,
            "risk_policy_changed": False,
            "silver_bullet_changed": False,
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
                "status_counts": payload["status_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
