"""Target truncation and structural expansion falsification for VT31_NAS100.

Diagnostic-only research over consumed R5/R6/R8/consumed evidence.

The current structural target remains untouched. This lab asks whether trades
that actually reached the structural target (DOL1) frequently continued into
deeper structural destinations before original methodological invalidation.

Runner-decision features are captured at the CLOSE of the M1 bar that touched
DOL1, therefore they are only eligible for a next-M1 decision. Future extension
is research-only and never a runtime feature.

Same-bar invalidation/extension ambiguity is censored conservatively.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
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

SCHEMA = "qore.vt31.nas100.target_structure_expansion_falsification.v1"
MARKET = "NAS100"
EXTENSIONS = (
    Decimal("0.25"),
    Decimal("0.50"),
    Decimal("1.00"),
    Decimal("1.50"),
    Decimal("2.00"),
)
MIN_STABLE_SAMPLE = 5


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


def _touches(
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


def _target_clock_bucket(value: datetime) -> str:
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
    if value <= 10:
        return "le_10m"
    if value <= 20:
        return "11_20m"
    if value <= 40:
        return "21_40m"
    if value <= 60:
        return "41_60m"
    return "gt_60m"


def _ratio_bucket(value: Decimal | None) -> str:
    if value is None:
        return "missing"
    if value < Decimal("0.25"):
        return "lt_0_25"
    if value < Decimal("0.50"):
        return "0_25_0_50"
    if value < Decimal("0.75"):
        return "0_50_0_75"
    return "ge_0_75"


def _giveback_bucket(value: Decimal) -> str:
    if value < Decimal("0.10"):
        return "lt_0_10R"
    if value < Decimal("0.25"):
        return "0_10_0_25R"
    if value < Decimal("0.50"):
        return "0_25_0_50R"
    return "ge_0_50R"


def _close_r(
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
    close: Decimal,
) -> Decimal:
    if side == "long":
        return (close - entry) / risk
    return (entry - close) / risk


def _overlap_rate(bars: tuple[object, ...]) -> Decimal | None:
    if len(bars) < 2:
        return None
    eligible = 0
    overlapping = 0
    for previous, current in zip(bars, bars[1:], strict=False):
        p_low = _d(getattr(previous, "low"))
        p_high = _d(getattr(previous, "high"))
        c_low = _d(getattr(current, "low"))
        c_high = _d(getattr(current, "high"))
        denominator = min(p_high - p_low, c_high - c_low)
        if denominator <= 0:
            continue
        eligible += 1
        overlap = max(
            Decimal(0),
            min(p_high, c_high) - max(p_low, c_low),
        )
        if overlap / denominator >= Decimal("0.50"):
            overlapping += 1
    if eligible == 0:
        return None
    return Decimal(overlapping) / Decimal(eligible)


def _path_efficiency(
    bars: tuple[object, ...],
    *,
    side: str,
) -> Decimal | None:
    if len(bars) < 2:
        return None
    closes = [_d(getattr(bar, "close")) for bar in bars]
    travelled = sum(
        (
            abs(closes[index] - closes[index - 1])
            for index in range(1, len(closes))
        ),
        Decimal(0),
    )
    if travelled <= 0:
        return None
    net = (
        closes[-1] - closes[0]
        if side == "long"
        else closes[0] - closes[-1]
    )
    return max(Decimal(0), net / travelled)


def _favorable_close_rate(
    bars: tuple[object, ...],
    *,
    side: str,
) -> Decimal | None:
    if not bars:
        return None
    favorable = 0
    for bar in bars:
        opened = _d(getattr(bar, "open"))
        closed = _d(getattr(bar, "close"))
        if (
            (side == "long" and closed > opened)
            or (side == "short" and closed < opened)
        ):
            favorable += 1
    return Decimal(favorable) / Decimal(len(bars))


def _consecutive_favorable_closes(
    bars: tuple[object, ...],
    *,
    side: str,
) -> int:
    count = 0
    for bar in reversed(bars):
        opened = _d(getattr(bar, "open"))
        closed = _d(getattr(bar, "close"))
        favorable = (
            (side == "long" and closed > opened)
            or (side == "short" and closed < opened)
        )
        if not favorable:
            break
        count += 1
    return count


def _target_snapshot(
    path: tuple[object, ...],
    *,
    target_index: int,
    side: str,
    entry: Decimal,
    risk: Decimal,
    target: Decimal,
    ref_width: Decimal,
) -> dict[str, object]:
    recent = path[max(0, target_index - 4) : target_index + 1]
    overlap = _overlap_rate(recent)
    efficiency = _path_efficiency(recent, side=side)
    favorable_rate = _favorable_close_rate(recent, side=side)

    close_rs = [
        _close_r(
            side=side,
            entry=entry,
            risk=risk,
            close=_d(getattr(bar, "close")),
        )
        for bar in recent
    ]
    peak_close = max(close_rs) if close_rs else Decimal(0)
    current_close = close_rs[-1] if close_rs else Decimal(0)
    giveback = max(Decimal(0), peak_close - current_close)

    target_bar = path[target_index]
    opened = _d(getattr(target_bar, "open"))
    closed = _d(getattr(target_bar, "close"))
    high = _d(getattr(target_bar, "high"))
    low = _d(getattr(target_bar, "low"))
    width = high - low
    body_fraction = (
        Decimal(0)
        if width <= 0
        else abs(closed - opened) / width
    )
    favorable_body = (
        (side == "long" and closed > opened)
        or (side == "short" and closed < opened)
    )
    close_beyond_target = (
        closed >= target
        if side == "long"
        else closed <= target
    )
    close_extension_ref = (
        max(Decimal(0), closed - target) / ref_width
        if side == "long"
        else max(Decimal(0), target - closed) / ref_width
    )

    return {
        "last5_overlap_rate": (
            None if overlap is None else format(overlap, "f")
        ),
        "last5_overlap_bucket": _ratio_bucket(overlap),
        "last5_path_efficiency": (
            None if efficiency is None else format(efficiency, "f")
        ),
        "last5_path_efficiency_bucket": _ratio_bucket(efficiency),
        "last5_favorable_close_rate": (
            None if favorable_rate is None else format(favorable_rate, "f")
        ),
        "last5_favorable_close_bucket": _ratio_bucket(favorable_rate),
        "close_giveback_from_recent_peak_r": format(giveback, "f"),
        "close_giveback_bucket": _giveback_bucket(giveback),
        "target_bar_body_fraction": format(body_fraction, "f"),
        "target_bar_body_bucket": _ratio_bucket(body_fraction),
        "target_bar_favorable_body": favorable_body,
        "target_bar_close_beyond_target": close_beyond_target,
        "target_bar_close_extension_ref": format(
            close_extension_ref,
            "f",
        ),
        "consecutive_favorable_closes": _consecutive_favorable_closes(
            recent,
            side=side,
        ),
        "runner_decision_effective_next_m1": True,
    }


def _future_extension(
    day_bars: tuple[object, ...],
    *,
    exit_at: datetime,
    side: str,
    target: Decimal,
    stop: Decimal,
    ref_width: Decimal,
) -> dict[str, object]:
    direction = Decimal(1) if side == "long" else Decimal(-1)
    levels = {
        extension: target + direction * ref_width * extension
        for extension in EXTENSIONS
    }

    reached: set[Decimal] = set()
    censored_same_bar = False
    ended_by = "16:00-lifecycle"

    for bar in day_bars:
        opened = cast(datetime, getattr(bar, "opened_at"))
        if opened < exit_at:
            continue
        if _wall(opened) >= (16, 0, 0):
            break

        stop_hit = _touches_stop(bar, side=side, stop=stop)
        bar_hits = {
            extension
            for extension, level in levels.items()
            if _touches(bar, side=side, level=level)
        }

        if stop_hit and bar_hits:
            censored_same_bar = True
            ended_by = "censored-same-bar-invalidation-extension"
            break
        if stop_hit:
            ended_by = "methodological-invalidation"
            break

        reached.update(bar_hits)

    max_extension = max(reached, default=Decimal(0))
    return {
        "post_target_max_extension_ref": format(max_extension, "f"),
        "post_target_reached_0_25": Decimal("0.25") in reached,
        "post_target_reached_0_50": Decimal("0.50") in reached,
        "post_target_reached_1_00": Decimal("1.00") in reached,
        "post_target_reached_1_50": Decimal("1.50") in reached,
        "post_target_reached_2_00": Decimal("2.00") in reached,
        "post_target_journey_end_reason": ended_by,
        "post_target_same_bar_ambiguity": censored_same_bar,
        "future_extension_research_only": True,
    }


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    n = len(rows)

    def rate(field: str) -> str:
        if n == 0:
            return "0"
        return format(
            Decimal(sum(bool(row[field]) for row in rows))
            / Decimal(n),
            "f",
        )

    return {
        "sample": n,
        "extension_0_25_rate": rate("post_target_reached_0_25"),
        "extension_0_50_rate": rate("post_target_reached_0_50"),
        "extension_1_00_rate": rate("post_target_reached_1_00"),
        "extension_1_50_rate": rate("post_target_reached_1_50"),
        "extension_2_00_rate": rate("post_target_reached_2_00"),
        "same_bar_ambiguity_rate": rate(
            "post_target_same_bar_ambiguity"
        ),
    }


def _feature_rows(
    rows: list[dict[str, object]],
    field: str,
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(field))].append(row)
    return {
        state: _stats(items)
        for state, items in sorted(grouped.items())
    }


FEATURES = (
    "entry_family",
    "tier",
    "side",
    "reference_volatility_state",
    "current_path_bucket",
    "risk_ref_bucket",
    "reclaim_age_bucket",
    "confirmation_latency_bucket",
    "target_clock_bucket",
    "fill_to_target_bucket",
    "last5_overlap_bucket",
    "last5_path_efficiency_bucket",
    "last5_favorable_close_bucket",
    "close_giveback_bucket",
    "target_bar_body_bucket",
    "target_bar_favorable_body",
    "target_bar_close_beyond_target",
    "consecutive_favorable_closes",
)


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
        raise ValueError("target expansion falsification requires NAS100")

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
    censored_geometry = 0
    for row in rows:
        if row.get("exit_reason") != "structural-target":
            continue
        if _d(row["capital_weighted_net_r"]) <= 0:
            continue

        entry = _opt_d(row.get("entry"))
        stop = _opt_d(row.get("initial_stop"))
        target = _opt_d(row.get("structural_target"))
        risk_ref = _opt_d(row.get("risk_ref"))
        if (
            entry is None
            or stop is None
            or target is None
            or risk_ref is None
            or risk_ref <= 0
        ):
            censored_geometry += 1
            continue

        risk = abs(entry - stop)
        if risk <= 0:
            censored_geometry += 1
            continue
        ref_width = risk / risk_ref
        if ref_width <= 0:
            censored_geometry += 1
            continue

        local_day = date.fromisoformat(str(row["local_date"]))
        day_bars = by_day.get(local_day)
        if not day_bars:
            censored_geometry += 1
            continue

        exit_at = _dt(row["exit_at"])
        filled_at = _dt(row["filled_at"])
        target_index = next(
            (
                index
                for index, bar in enumerate(day_bars)
                if cast(datetime, getattr(bar, "closed_at")) == exit_at
            ),
            None,
        )
        if target_index is None:
            censored_geometry += 1
            continue

        fill_index = next(
            (
                index
                for index, bar in enumerate(day_bars)
                if cast(datetime, getattr(bar, "closed_at")) == filled_at
            ),
            None,
        )
        if fill_index is None or fill_index > target_index:
            censored_geometry += 1
            continue

        side = str(row["side"])
        target_path = day_bars[fill_index : target_index + 1]
        target_local = exit_at
        fill_to_target = max(
            0,
            int((exit_at - filled_at).total_seconds() // 60),
        )

        updated = dict(row)
        updated["reference_width_reconstructed"] = format(
            ref_width,
            "f",
        )
        updated["target_clock_bucket"] = _target_clock_bucket(
            target_local
        )
        updated["fill_to_target_minutes"] = fill_to_target
        updated["fill_to_target_bucket"] = _minutes_bucket(
            fill_to_target
        )
        updated.update(
            _target_snapshot(
                target_path,
                target_index=len(target_path) - 1,
                side=side,
                entry=entry,
                risk=risk,
                target=target,
                ref_width=ref_width,
            )
        )
        updated.update(
            _future_extension(
                day_bars,
                exit_at=exit_at,
                side=side,
                target=target,
                stop=stop,
                ref_width=ref_width,
            )
        )
        observations.append(updated)

    feature_diagnostics = {
        field: _feature_rows(observations, field)
        for field in FEATURES
    }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "target_winner_count": len(observations),
        "overall": _stats(observations),
        "feature_diagnostics": feature_diagnostics,
        "observations": observations,
        "censored_geometry_count": censored_geometry,
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
            "current_structural_target_changed": False,
            "runner_policy_changed": False,
            "runner_decision_features_known_by_next_m1": True,
            "future_extension_runtime_input": False,
            "same_bar_ambiguity_censored": True,
            "trade_admission_changed": False,
            "risk_policy_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
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
                "target_winner_count": payload[
                    "target_winner_count"
                ],
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
