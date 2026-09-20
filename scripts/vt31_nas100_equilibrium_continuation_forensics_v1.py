"""Equilibrium continuation vs exhaustion forensics for VT31_NAS100.

Diagnostic-only research.

For trades where the frozen 09:00-10:00 reference equilibrium is a forward
structural milestone and is touched before the original terminal event, freeze
a causal snapshot at the CLOSE of the first M1 that touches equilibrium.

The research label asks whether DOL1 (the opposite reference boundary) is
reached on a STRICTLY LATER M1 before the original trade terminal.

Thus:
- equilibrium-touch-bar information is known before the decision;
- any decision would only become effective on the next M1;
- same-bar equilibrium + DOL1 is classified separately, never credited as a
  predictable continuation;
- future DOL1 reach is research-only and prohibited from runtime input.

No trade policy is changed.
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
import vt31_nas100_target_structure_expansion_falsification_v1 as journey

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.equilibrium_continuation_forensics.v1"
MARKET = "NAS100"
MIN_STABLE_SAMPLE = 5

ENTRY_FIELDS = (
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

EQ_FIELDS = (
    "eq_clock_bucket",
    "fill_to_eq_bucket",
    "eq_bar_close_beyond",
    "eq_bar_favorable_body",
    "eq_bar_body_bucket",
    "eq_last5_overlap_bucket",
    "eq_last5_path_efficiency_bucket",
    "eq_last5_favorable_close_bucket",
    "eq_close_giveback_bucket",
    "eq_consecutive_favorable_closes",
)

PAIR_FIELDS = (
    ("entry_family", "eq_bar_close_beyond"),
    ("reference_volatility_state", "eq_bar_close_beyond"),
    ("current_path_bucket", "eq_bar_close_beyond"),
    ("eq_last5_path_efficiency_bucket", "eq_last5_overlap_bucket"),
    ("eq_bar_close_beyond", "eq_last5_path_efficiency_bucket"),
    ("eq_bar_close_beyond", "eq_last5_favorable_close_bucket"),
    ("eq_bar_close_beyond", "eq_close_giveback_bucket"),
    ("tier", "entry_family"),
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


def _forward(*, side: str, entry: Decimal, level: Decimal) -> bool:
    return level > entry if side == "long" else level < entry


def _touches(bar: object, *, side: str, level: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def _clock_bucket(value: datetime) -> str:
    minute = value.hour * 60 + value.minute
    if minute < 11 * 60:
        return "10_00_10_59"
    if minute < 12 * 60:
        return "11_00_11_59"
    if minute < 13 * 60:
        return "12_00_12_59"
    if minute < 14 * 60:
        return "13_00_13_59"
    if minute < 15 * 60:
        return "14_00_14_59"
    return "15_00_15_59"


def _minutes_bucket(value: int) -> str:
    if value <= 5:
        return "le_5m"
    if value <= 10:
        return "6_10m"
    if value <= 20:
        return "11_20m"
    if value <= 40:
        return "21_40m"
    return "gt_40m"


def _eq_snapshot(
    path: tuple[object, ...],
    *,
    eq_index: int,
    side: str,
    entry: Decimal,
    risk: Decimal,
    equilibrium: Decimal,
    ref_width: Decimal,
) -> dict[str, object]:
    snapshot = journey._target_snapshot(
        path,
        target_index=eq_index,
        side=side,
        entry=entry,
        risk=risk,
        target=equilibrium,
        ref_width=ref_width,
    )
    return {
        "eq_last5_overlap_rate": snapshot["last5_overlap_rate"],
        "eq_last5_overlap_bucket": snapshot["last5_overlap_bucket"],
        "eq_last5_path_efficiency": snapshot["last5_path_efficiency"],
        "eq_last5_path_efficiency_bucket": snapshot[
            "last5_path_efficiency_bucket"
        ],
        "eq_last5_favorable_close_rate": snapshot[
            "last5_favorable_close_rate"
        ],
        "eq_last5_favorable_close_bucket": snapshot[
            "last5_favorable_close_bucket"
        ],
        "eq_close_giveback_from_recent_peak_r": snapshot[
            "close_giveback_from_recent_peak_r"
        ],
        "eq_close_giveback_bucket": snapshot["close_giveback_bucket"],
        "eq_bar_body_fraction": snapshot["target_bar_body_fraction"],
        "eq_bar_body_bucket": snapshot["target_bar_body_bucket"],
        "eq_bar_favorable_body": snapshot["target_bar_favorable_body"],
        "eq_bar_close_beyond": snapshot["target_bar_close_beyond_target"],
        "eq_bar_close_extension_ref": snapshot[
            "target_bar_close_extension_ref"
        ],
        "eq_consecutive_favorable_closes": snapshot[
            "consecutive_favorable_closes"
        ],
        "decision_effective_next_m1": True,
    }


def _continuation_label(
    bars: tuple[object, ...],
    *,
    eq_index: int,
    terminal_at: datetime,
    side: str,
    dol1: Decimal,
) -> tuple[str, int | None]:
    eq_bar = bars[eq_index]
    if _touches(eq_bar, side=side, level=dol1):
        return "DOL1_SAME_EQ_BAR", 0

    eq_close = cast(datetime, getattr(eq_bar, "closed_at"))
    for bar in bars[eq_index + 1 :]:
        opened = cast(datetime, getattr(bar, "opened_at"))
        closed = cast(datetime, getattr(bar, "closed_at"))
        if opened >= terminal_at or closed > terminal_at:
            break
        if _wall(opened) >= (16, 0, 0):
            break
        if _touches(bar, side=side, level=dol1):
            minutes = max(
                0,
                int((closed - eq_close).total_seconds() // 60),
            )
            return "DOL1_LATER_REACHED", minutes
    return "DOL1_NOT_REACHED_BEFORE_TERMINAL", None


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    usable = [
        row
        for row in rows
        if row["continuation_label"] != "DOL1_SAME_EQ_BAR"
    ]
    n = len(usable)
    later = sum(
        row["continuation_label"] == "DOL1_LATER_REACHED"
        for row in usable
    )
    same_bar = sum(
        row["continuation_label"] == "DOL1_SAME_EQ_BAR"
        for row in rows
    )
    return {
        "observations": len(rows),
        "usable_sample": n,
        "same_eq_bar_dol1_count": same_bar,
        "later_dol1_count": later,
        "later_dol1_rate": (
            "0"
            if n == 0
            else format(Decimal(later) / Decimal(n), "f")
        ),
        "label_counts": dict(
            sorted(
                Counter(
                    str(row["continuation_label"])
                    for row in rows
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
        key: _stats(items)
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
        raise ValueError("equilibrium continuation requires NAS100")

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
    censored = 0

    for row in rows:
        entry = _opt_d(row.get("entry"))
        stop = _opt_d(row.get("initial_stop"))
        dol1 = _opt_d(row.get("structural_target"))
        filled_at_raw = row.get("filled_at")
        terminal_at_raw = row.get("exit_at")
        if (
            entry is None
            or stop is None
            or dol1 is None
            or filled_at_raw is None
            or terminal_at_raw is None
        ):
            censored += 1
            continue

        risk = abs(entry - stop)
        if risk <= 0:
            censored += 1
            continue

        local_day = date.fromisoformat(str(row["local_date"]))
        day_bars = by_day.get(local_day)
        if not day_bars:
            censored += 1
            continue

        reference = tuple(
            bar
            for bar in day_bars
            if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0)
        )
        if len(reference) != 60:
            censored += 1
            continue

        ref_high = max(_d(getattr(bar, "high")) for bar in reference)
        ref_low = min(_d(getattr(bar, "low")) for bar in reference)
        ref_width = ref_high - ref_low
        equilibrium = (ref_high + ref_low) / Decimal("2")
        side = str(row["side"])
        if (
            ref_width <= 0
            or not _forward(
                side=side,
                entry=entry,
                level=equilibrium,
            )
        ):
            continue

        filled_at = _dt(filled_at_raw)
        terminal_at = _dt(terminal_at_raw)
        fill_index = next(
            (
                index
                for index, bar in enumerate(day_bars)
                if cast(datetime, getattr(bar, "closed_at")) == filled_at
            ),
            None,
        )
        if fill_index is None:
            censored += 1
            continue

        eq_index = next(
            (
                index
                for index in range(fill_index, len(day_bars))
                if cast(datetime, getattr(day_bars[index], "closed_at"))
                < terminal_at
                and _wall(getattr(day_bars[index], "opened_at")) < (16, 0, 0)
                and _touches(
                    day_bars[index],
                    side=side,
                    level=equilibrium,
                )
            ),
            None,
        )
        if eq_index is None:
            continue

        eq_bar = day_bars[eq_index]
        eq_close = cast(datetime, getattr(eq_bar, "closed_at"))
        fill_to_eq = max(
            0,
            int((eq_close - filled_at).total_seconds() // 60),
        )

        updated = dict(row)
        updated["equilibrium_price"] = format(equilibrium, "f")
        updated["reference_width"] = format(ref_width, "f")
        updated["eq_clock_bucket"] = _clock_bucket(eq_close)
        updated["fill_to_eq_minutes"] = fill_to_eq
        updated["fill_to_eq_bucket"] = _minutes_bucket(fill_to_eq)
        updated.update(
            _eq_snapshot(
                day_bars[fill_index : eq_index + 1],
                eq_index=eq_index - fill_index,
                side=side,
                entry=entry,
                risk=risk,
                equilibrium=equilibrium,
                ref_width=ref_width,
            )
        )

        label, minutes = _continuation_label(
            day_bars,
            eq_index=eq_index,
            terminal_at=terminal_at,
            side=side,
            dol1=dol1,
        )
        updated["continuation_label"] = label
        updated["eq_to_dol1_minutes"] = minutes
        updated["future_continuation_research_only"] = True
        observations.append(updated)

    dimensions = {
        field: _group(observations, (field,))
        for field in ENTRY_FIELDS + EQ_FIELDS
    }
    pairs = {
        " x ".join(fields): _group(observations, fields)
        for fields in PAIR_FIELDS
    }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "overall": _stats(observations),
        "dimensions": dimensions,
        "pairs": pairs,
        "observations": observations,
        "censored_geometry_count": censored,
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
            "equilibrium_known_before_trade": True,
            "snapshot_at_closed_eq_m1": True,
            "decision_effective_next_m1": True,
            "same_bar_eq_dol1_not_predictive": True,
            "future_continuation_runtime_input": False,
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
                "censored_geometry_count": payload[
                    "censored_geometry_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
