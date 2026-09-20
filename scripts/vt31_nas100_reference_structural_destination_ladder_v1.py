"""Reference structural destination ladder for VT31_NAS100.

Diagnostic-only root-cause research.

The current Silver Bullet target is the opposite frozen 09:00-10:00 reference
boundary. This lab reconstructs a structural ladder that exists BEFORE outcome:

LONG after low raid:
  swept-side reference low -> reference equilibrium (50%) -> opposite high
SHORT after high raid:
  swept-side reference high -> reference equilibrium (50%) -> opposite low

Only forward levels from the actual entry are eligible. After the opposite
boundary, the existing DOL extensions are also tracked.

Purpose:
- determine whether the current opposite-boundary target is too ambitious for
  specific entry states;
- distinguish trades capable only of reference re-entry / equilibrium from
  trades capable of full boundary traversal and deeper expansion;
- never use future reach as a runtime input.

Same-M1 stop/deeper-destination ambiguity is censored.
No policy is changed.
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

SCHEMA = "qore.vt31.nas100.reference_structural_destination_ladder.v1"
MARKET = "NAS100"

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
    ("entry_family", "confirmation_latency_bucket"),
    ("last_structure_event_family", "entry_family"),
    ("premarket_state", "cash_open_state"),
    ("reference_volatility_state", "current_path_bucket"),
    ("tier", "entry_family"),
    ("entry_family", "risk_ref_bucket"),
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


def _slice(
    bars: tuple[object, ...],
    start: tuple[int, int, int],
    end: tuple[int, int, int],
) -> tuple[object, ...]:
    return tuple(
        bar
        for bar in bars
        if start <= _wall(getattr(bar, "opened_at")) < end
    )


def _forward(
    *,
    side: str,
    entry: Decimal,
    level: Decimal,
) -> bool:
    return level > entry if side == "long" else level < entry


def _touches(
    bar: object,
    *,
    side: str,
    level: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def _stop_hit(
    bar: object,
    *,
    side: str,
    stop: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "low")) <= stop
    return _d(getattr(bar, "high")) >= stop


def _ladder(
    *,
    side: str,
    entry: Decimal,
    reference_high: Decimal,
    reference_low: Decimal,
) -> tuple[tuple[str, Decimal], ...]:
    midpoint = (reference_high + reference_low) / Decimal("2")
    width = reference_high - reference_low

    if side == "long":
        raw = (
            ("REFERENCE_REENTRY", reference_low),
            ("REFERENCE_EQUILIBRIUM", midpoint),
            ("OPPOSITE_BOUNDARY_DOL1", reference_high),
            ("DOL2_PLUS_0_25_REF", reference_high + width * Decimal("0.25")),
            ("DOL3_PLUS_0_50_REF", reference_high + width * Decimal("0.50")),
            ("DOL4_PLUS_1_00_REF", reference_high + width),
        )
    else:
        raw = (
            ("REFERENCE_REENTRY", reference_high),
            ("REFERENCE_EQUILIBRIUM", midpoint),
            ("OPPOSITE_BOUNDARY_DOL1", reference_low),
            ("DOL2_PLUS_0_25_REF", reference_low - width * Decimal("0.25")),
            ("DOL3_PLUS_0_50_REF", reference_low - width * Decimal("0.50")),
            ("DOL4_PLUS_1_00_REF", reference_low - width),
        )

    return tuple(
        (name, level)
        for name, level in raw
        if _forward(side=side, entry=entry, level=level)
    )


def _capacity(
    bars: tuple[object, ...],
    *,
    filled_at: datetime,
    side: str,
    stop: Decimal,
    ladder: tuple[tuple[str, Decimal], ...],
) -> dict[str, object]:
    start_index = next(
        (
            index
            for index, bar in enumerate(bars)
            if cast(datetime, getattr(bar, "closed_at")) == filled_at
        ),
        None,
    )
    if start_index is None:
        return {"status": "censored-fill-not-found"}

    reached: list[str] = []
    reached_at: dict[str, str] = {}
    invalidated = False

    for bar in bars[start_index:]:
        opened = cast(datetime, getattr(bar, "opened_at"))
        if _wall(opened) >= (16, 0, 0):
            break

        stop_hit = _stop_hit(bar, side=side, stop=stop)
        new_levels = [
            name
            for name, level in ladder
            if name not in reached
            and _touches(bar, side=side, level=level)
        ]
        if stop_hit and new_levels:
            return {
                "status": "censored-same-bar-stop-destination",
                "reached_before_ambiguity": reached,
                "ambiguous_new_levels": new_levels,
            }

        for name in new_levels:
            reached.append(name)
            reached_at[name] = cast(
                datetime,
                getattr(bar, "closed_at"),
            ).isoformat()

        if stop_hit:
            invalidated = True
            break

    deepest = reached[-1] if reached else "NO_FORWARD_DESTINATION_REACHED"
    return {
        "status": "labeled",
        "deepest_destination": deepest,
        "reached_destinations": reached,
        "reached_at": reached_at,
        "reference_reentry_reached": "REFERENCE_REENTRY" in reached,
        "equilibrium_reached": "REFERENCE_EQUILIBRIUM" in reached,
        "dol1_reached": "OPPOSITE_BOUNDARY_DOL1" in reached,
        "dol2_reached": "DOL2_PLUS_0_25_REF" in reached,
        "dol3_reached": "DOL3_PLUS_0_50_REF" in reached,
        "dol4_reached": "DOL4_PLUS_1_00_REF" in reached,
        "invalidated": invalidated,
    }


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    labeled = [row for row in rows if row["ladder_status"] == "labeled"]
    n = len(labeled)

    def rate(field: str) -> str:
        if n == 0:
            return "0"
        return format(
            Decimal(sum(bool(row.get(field)) for row in labeled))
            / Decimal(n),
            "f",
        )

    return {
        "observations": len(rows),
        "labeled": n,
        "censored": len(rows) - n,
        "reference_reentry_rate": rate("reference_reentry_reached"),
        "equilibrium_rate": rate("equilibrium_reached"),
        "dol1_rate": rate("dol1_reached"),
        "dol2_rate": rate("dol2_reached"),
        "dol3_rate": rate("dol3_reached"),
        "dol4_rate": rate("dol4_reached"),
        "invalidated_rate": rate("invalidated"),
        "deepest_destination_counts": dict(
            sorted(
                Counter(
                    str(row["deepest_destination"])
                    for row in labeled
                ).items()
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
        raise ValueError("reference destination ladder requires NAS100")

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
    statuses: Counter[str] = Counter()

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
            )
        }

        entry = _opt_d(row.get("entry"))
        stop = _opt_d(row.get("initial_stop"))
        filled_at_raw = row.get("filled_at")
        if entry is None or stop is None or filled_at_raw is None:
            updated["ladder_status"] = "censored-missing-geometry"
            statuses["censored-missing-geometry"] += 1
            observations.append(updated)
            continue

        local_day = date.fromisoformat(str(row["local_date"]))
        day_bars = by_day.get(local_day)
        if not day_bars:
            updated["ladder_status"] = "censored-missing-day"
            statuses["censored-missing-day"] += 1
            observations.append(updated)
            continue

        reference = _slice(day_bars, (9, 0, 0), (10, 0, 0))
        if len(reference) != 60:
            updated["ladder_status"] = "censored-reference-incomplete"
            statuses["censored-reference-incomplete"] += 1
            observations.append(updated)
            continue

        reference_high = max(_d(getattr(bar, "high")) for bar in reference)
        reference_low = min(_d(getattr(bar, "low")) for bar in reference)
        ladder = _ladder(
            side=str(row["side"]),
            entry=entry,
            reference_high=reference_high,
            reference_low=reference_low,
        )
        capacity = _capacity(
            day_bars,
            filled_at=_dt(filled_at_raw),
            side=str(row["side"]),
            stop=stop,
            ladder=ladder,
        )

        updated["entry_price"] = format(entry, "f")
        updated["reference_high"] = format(reference_high, "f")
        updated["reference_low"] = format(reference_low, "f")
        updated["reference_equilibrium"] = format(
            (reference_high + reference_low) / Decimal("2"),
            "f",
        )
        updated["eligible_destination_ladder"] = [
            {"name": name, "price": format(level, "f")}
            for name, level in ladder
        ]
        updated["ladder_status"] = capacity["status"]
        if capacity["status"] == "labeled":
            updated.update(capacity)
        else:
            updated["ladder_diagnostic"] = capacity

        statuses[str(capacity["status"])] += 1
        observations.append(updated)

    dimensions = {
        field: _group(observations, (field,))
        for field in ENTRY_FEATURES
    }
    pairs = {
        " x ".join(fields): _group(observations, fields)
        for fields in PAIR_FEATURES
    }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "overall": _summary(observations),
        "dimensions": dimensions,
        "pairs": pairs,
        "observations": observations,
        "status_counts": dict(sorted(statuses.items())),
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
            "diagnostic_only": True,
            "entry_state_frozen_before_outcome": True,
            "reference_range_frozen_before_trade": True,
            "future_reach_research_label_only": True,
            "same_bar_stop_destination_ambiguity_censored": True,
            "trade_policy_changed": False,
            "target_changed": False,
            "stop_changed": False,
            "risk_changed": False,
            "silver_bullet_changed": False,
            "opens_new_holdout": False,
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
