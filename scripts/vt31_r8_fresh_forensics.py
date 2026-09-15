"""Consumed-only fresh-failure forensics for rejected VT-31 R8.

This module replays the exact R8 candidate over the already-consumed R5, R6,
and R8 fresh partitions. It reconstructs the first executable setup funnel and
measures only observables available by the R8 decision time. It never opens new
historical evidence and never mutates the rejected R8 identity.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_r5_candidate as r5
import vt31_r8_candidate as r8

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_6_composite_entry_research import (
    _evaluate,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    _detect_raid,
    _session_bars,
    _structure,
    build_reference_range,
)

PARTITIONS = ("r8_fresh", "r6", "r5")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _trade_key(item: dict[str, object]) -> tuple[str, str, str]:
    return (
        cast(str, item["market"]),
        cast(str, item["signal_at"]),
        cast(str, item["side"]),
    )


def _reference_bars(day_bars: tuple[object, ...]) -> tuple[object, ...]:
    return tuple(
        item
        for item in day_bars
        if (9, 0, 0) <= _wall(getattr(item, "opened_at")) < (10, 0, 0)
    )


def _session_indices(day_bars: tuple[object, ...]) -> list[tuple[int, object]]:
    return [
        (index, item)
        for index, item in enumerate(day_bars)
        if (10, 0, 0) <= _wall(getattr(item, "opened_at")) < (11, 0, 0)
    ]


def _setup_features(
    prefix: tuple[object, ...],
    setup: object,
    reference_bars: tuple[object, ...],
) -> dict[str, object] | None:
    if not reference_bars:
        return None
    signal_at = getattr(setup, "signal_at")
    instrument = getattr(prefix[0], "instrument")
    reference = build_reference_range(
        instrument=instrument,
        as_of=signal_at,
        bars=cast(object, prefix),
    )
    if reference is None:
        return None
    session = _session_bars(signal_at, cast(object, prefix))
    raid = _detect_raid(session, reference)
    if raid is None or (raid.high_taken and raid.low_taken):
        return None
    structure = _structure(session, raid)
    if structure is None:
        return None
    confirmation_index, extreme_index, _, _ = structure
    confirmation = session[confirmation_index]
    raid_bar = session[raid.index]

    ref_high = max(_d(getattr(item, "high")) for item in reference_bars)
    ref_low = min(_d(getattr(item, "low")) for item in reference_bars)
    ref_width = ref_high - ref_low
    if ref_width <= 0:
        return None

    raid_high = _d(getattr(raid_bar, "high"))
    raid_low = _d(getattr(raid_bar, "low"))
    raid_open = _d(getattr(raid_bar, "open"))
    raid_close = _d(getattr(raid_bar, "close"))
    raid_span = raid_high - raid_low
    if raid_span <= 0:
        return None

    opened = _d(getattr(confirmation, "open"))
    closed = _d(getattr(confirmation, "close"))
    high = _d(getattr(confirmation, "high"))
    low = _d(getattr(confirmation, "low"))
    confirmation_span = high - low
    if confirmation_span <= 0:
        return None

    side = getattr(setup, "side").value
    aligned = closed > opened if side == "long" else closed < opened
    risk = cast(Decimal, getattr(setup, "risk"))
    entry = cast(Decimal, getattr(setup, "entry"))
    local = signal_at.astimezone(r5.NY)
    signal_minute = local.hour * 60 + local.minute - 10 * 60
    if side == "long":
        raid_depth = max(Decimal(0), ref_low - raid_low) / ref_width
        entry_location = (entry - ref_low) / ref_width
    else:
        raid_depth = max(Decimal(0), raid_high - ref_high) / ref_width
        entry_location = (ref_high - entry) / ref_width

    return {
        "side": side,
        "signal_minute": signal_minute,
        "aligned": aligned,
        "raid_body_fraction": format(abs(raid_close - raid_open) / raid_span, "f"),
        "raid_to_extreme_bars": extreme_index - raid.index,
        "raid_to_confirmation_bars": confirmation_index - raid.index,
        "confirmation_body_fraction": format(abs(closed - opened) / confirmation_span, "f"),
        "risk_to_reference": format(risk / ref_width, "f"),
        "raid_depth_to_reference": format(raid_depth, "f"),
        "entry_location_to_reference": format(entry_location, "f"),
        "reference_width": format(ref_width, "f"),
    }


def _quality_reasons(features: dict[str, object] | None) -> list[str]:
    if features is None:
        return ["STRUCTURE_OR_REFERENCE_UNRESOLVED"]
    failed: list[str] = []
    if not cast(bool, features["aligned"]):
        failed.append("CONFIRMATION_NOT_ALIGNED")
    if _d(features["confirmation_body_fraction"]) < r8.MIN_CONFIRMATION_BODY_FRACTION:
        failed.append("CONFIRMATION_BODY_TOO_SMALL")
    if cast(int, features["signal_minute"]) > r8.MAX_SIGNAL_MINUTE:
        failed.append("SIGNAL_TOO_LATE")
    if _d(features["risk_to_reference"]) > r8.MAX_RISK_TO_REFERENCE:
        failed.append("RISK_TO_REFERENCE_TOO_LARGE")
    if _d(features["raid_body_fraction"]) < r8.MIN_RAID_BODY_FRACTION:
        failed.append("RAID_BODY_TOO_SMALL")
    if cast(int, features["raid_to_extreme_bars"]) > r8.MAX_RAID_TO_EXTREME_BARS:
        failed.append("RAID_RESOLUTION_TOO_SLOW")
    return failed


def _partition(
    name: str,
    evidence_paths: dict[str, Path],
) -> dict[str, object]:
    r8._configure_parent()
    exact = r8.replay(evidence_paths)
    expected = {
        _trade_key(item)
        for item in cast(list[dict[str, object]], exact["trades"])
    }
    reconstructed: list[dict[str, object]] = []
    funnel: dict[str, dict[str, object]] = {}

    for market in r8.MARKETS:
        series, _, _, _, _, _ = load_market_evidence(evidence_paths[market])
        by_day: dict[object, list[object]] = defaultdict(list)
        for bar in series:
            by_day[_day(bar.opened_at)].append(bar)

        counts: Counter[str] = Counter()
        failures: Counter[str] = Counter()
        for local_day in sorted(by_day):
            counts["days"] += 1
            day_bars = tuple(by_day[local_day])
            reference_bars = _reference_bars(day_bars)
            session = _session_indices(day_bars)
            if not reference_bars:
                counts["no_reference"] += 1
                continue
            counts["reference_days"] += 1
            if not session:
                counts["no_session"] += 1
                continue
            counts["session_days"] += 1
            ref_high = max(_d(getattr(item, "high")) for item in reference_bars)
            ref_low = min(_d(getattr(item, "low")) for item in reference_bars)
            if ref_high <= ref_low:
                counts["invalid_reference_width"] += 1
                continue

            prefix = list(reference_bars)
            selected = None
            selected_index: int | None = None
            selected_features: dict[str, object] | None = None
            selected_reasons: list[str] = []
            for global_index, bar in session:
                prefix.append(bar)
                candidate, _ = _evaluate(
                    instrument=getattr(bar, "instrument"),
                    as_of=getattr(bar, "closed_at"),
                    bars=cast(object, tuple(prefix)),
                    variant=r5.BASE_VARIANT,
                )
                if candidate is None:
                    continue
                counts["first_candidate_days"] += 1
                selected_features = _setup_features(
                    tuple(prefix), candidate, reference_bars
                )
                selected_reasons = _quality_reasons(selected_features)
                selected = candidate
                selected_index = global_index
                break

            if selected is None or selected_index is None:
                counts["no_candidate"] += 1
                continue
            if selected_reasons:
                counts["quality_rejected"] += 1
                failures.update(selected_reasons)
                continue
            counts["quality_accepted"] += 1
            simulated = r5._simulate(day_bars, selected_index, selected)
            if simulated is None:
                counts["execution_censored_or_unfilled"] += 1
                continue
            counts["executed"] += 1
            simulated["market"] = market
            simulated["partition"] = name
            if selected_features is not None:
                simulated.update(selected_features)
            filled = datetime.fromisoformat(cast(str, simulated["filled_at"]))
            signaled = datetime.fromisoformat(cast(str, simulated["signal_at"]))
            simulated["fill_delay_minutes"] = format(
                Decimal(str((filled - signaled).total_seconds() / 60)), "f"
            )
            reconstructed.append(simulated)

        funnel[market] = {
            "counts": dict(counts),
            "quality_failure_reasons": dict(failures),
            "bar_count": len(series),
        }

    reconstructed.sort(key=lambda item: (item["signal_at"], item["market"]))
    actual = {_trade_key(item) for item in reconstructed}
    if actual != expected:
        missing = sorted(expected - actual)[:10]
        extra = sorted(actual - expected)[:10]
        raise AssertionError(f"reconstruction mismatch missing={missing} extra={extra}")

    return {
        "name": name,
        "exact_replay": {
            "stress_0_05r": exact["stress_0_05r"],
            "market_stress": exact["market_stress"],
            "side_stress": exact["side_stress"],
            "quartiles": exact["quartiles"],
            "monte_carlo": exact["monte_carlo"],
            "monte_carlo_gates": exact["monte_carlo_gates"],
        },
        "funnel": funnel,
        "trades": reconstructed,
    }


def _group_metrics(
    rows: list[dict[str, object]],
    key_fn: Callable[[dict[str, object]], str],
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = key_fn(row)
        grouped[key].append(row)
    return {
        key: _metrics(items, friction=r8.FRICTION)
        for key, items in sorted(grouped.items())
    }


def _bucket(feature: str, row: dict[str, object]) -> str:
    value = _d(row[feature])
    if feature == "raid_body_fraction":
        if value < Decimal("0.45"):
            return "0.35-0.45"
        if value < Decimal("0.60"):
            return "0.45-0.60"
        return ">=0.60"
    if feature == "confirmation_body_fraction":
        if value < Decimal("0.60"):
            return "0.50-0.60"
        if value < Decimal("0.75"):
            return "0.60-0.75"
        return ">=0.75"
    if feature == "risk_to_reference":
        if value <= Decimal("0.075"):
            return "<=0.075"
        if value <= Decimal("0.125"):
            return "0.075-0.125"
        return "0.125-0.175"
    if feature == "raid_depth_to_reference":
        if value <= Decimal("0.025"):
            return "<=0.025"
        if value <= Decimal("0.075"):
            return "0.025-0.075"
        if value <= Decimal("0.15"):
            return "0.075-0.15"
        return ">0.15"
    if feature == "signal_minute":
        minute = int(value)
        if minute <= 5:
            return "00-05"
        if minute <= 10:
            return "06-10"
        if minute <= 15:
            return "11-15"
        return "16-20"
    if feature == "raid_to_extreme_bars":
        return str(int(value))
    if feature == "raid_to_confirmation_bars":
        bars = int(value)
        if bars <= 2:
            return "<=2"
        if bars <= 4:
            return "3-4"
        return ">=5"
    raise KeyError(feature)


def _feature_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    features = (
        "raid_body_fraction",
        "raid_to_extreme_bars",
        "raid_to_confirmation_bars",
        "confirmation_body_fraction",
        "risk_to_reference",
        "raid_depth_to_reference",
        "signal_minute",
    )
    report: dict[str, object] = {}
    for feature in features:
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            grouped[_bucket(feature, row)].append(row)
        report[feature] = {
            bucket: _metrics(items, friction=r8.FRICTION)
            for bucket, items in sorted(grouped.items())
        }
    return report


def _worst_drawdown(rows: list[dict[str, object]]) -> dict[str, object]:
    ordered = sorted(rows, key=lambda item: (item["signal_at"], item["market"]))
    equity = Decimal(0)
    peak = Decimal(0)
    peak_index = -1
    worst = Decimal(0)
    start = 0
    end = -1
    for index, row in enumerate(ordered):
        equity += _d(row["r_multiple"]) - r8.FRICTION
        if equity > peak:
            peak = equity
            peak_index = index
        drawdown = peak - equity
        if drawdown > worst:
            worst = drawdown
            start = peak_index + 1
            end = index
    episode = ordered[start : end + 1]
    return {
        "drawdown_r": format(worst, "f"),
        "trade_count": len(episode),
        "start": episode[0]["signal_at"] if episode else None,
        "end": episode[-1]["signal_at"] if episode else None,
        "markets": dict(Counter(cast(str, x["market"]) for x in episode)),
        "sides": dict(Counter(cast(str, x["side"]) for x in episode)),
        "partitions": dict(Counter(cast(str, x["partition"]) for x in episode)),
        "months": dict(Counter(cast(str, x["local_date"])[:7] for x in episode)),
    }


def _half_year(row: dict[str, object]) -> str:
    local_date = cast(str, row["local_date"])
    year = local_date[:4]
    month = int(local_date[5:7])
    return f"{year}-H{1 if month <= 6 else 2}"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 9:
        print(
            "usage: vt31_r8_fresh_forensics.py "
            "R5_NAS100 R5_SP500 R5_US30 "
            "R6_NAS100 R6_SP500 R6_US30 "
            "R8_NAS100 R8_SP500 R8_US30"
        )
        return 2

    tranches = {
        "r5": dict(zip(r8.MARKETS, map(Path, args[:3]), strict=True)),
        "r6": dict(zip(r8.MARKETS, map(Path, args[3:6]), strict=True)),
        "r8_fresh": dict(zip(r8.MARKETS, map(Path, args[6:]), strict=True)),
    }
    partitions = {
        name: _partition(name, tranches[name])
        for name in PARTITIONS
    }
    all_trades = [
        trade
        for partition in partitions.values()
        for trade in cast(list[dict[str, object]], partition["trades"])
    ]
    all_trades.sort(key=lambda item: (item["signal_at"], item["market"]))
    consumed = [item for item in all_trades if item["partition"] != "r8_fresh"]
    fresh = [item for item in all_trades if item["partition"] == "r8_fresh"]

    report = {
        "schema": "qore.trader_lab.vt31_r8_fresh_failure_forensics.v1",
        "candidate_id": r8.CANDIDATE_ID,
        "candidate_status": "REJECTED_FRESH_CONSUMED",
        "fresh_evidence_opened": True,
        "new_evidence_opened_by_forensics": False,
        "partitions": {
            name: {
                "exact_replay": partition["exact_replay"],
                "funnel": partition["funnel"],
            }
            for name, partition in partitions.items()
        },
        "cross_partition": {
            "partition": _group_metrics(all_trades, lambda x: cast(str, x["partition"])),
            "market_side": _group_metrics(
                all_trades,
                lambda x: f"{x['partition']}:{x['market']}:{x['side']}",
            ),
            "half_year": _group_metrics(all_trades, _half_year),
            "fresh_year_side": _group_metrics(
                fresh,
                lambda x: f"{cast(str, x['local_date'])[:4]}:{x['side']}",
            ),
            "fresh_month": _group_metrics(
                fresh, lambda x: cast(str, x["local_date"])[:7]
            ),
        },
        "predecision_features": {
            "consumed": _feature_metrics(consumed),
            "r8_fresh": _feature_metrics(fresh),
            "fresh_long": _feature_metrics(
                [item for item in fresh if item["side"] == "long"]
            ),
            "fresh_short": _feature_metrics(
                [item for item in fresh if item["side"] == "short"]
            ),
        },
        "tail": {
            "consumed_worst_drawdown": _worst_drawdown(consumed),
            "fresh_worst_drawdown": _worst_drawdown(fresh),
        },
        "forensic_questions": [
            "Which R8 quality gate explains the fresh SP500 signal-density collapse?",
            "Which predecision feature bins explain the fresh LONG sign reversal?",
            "Does the same feature remain directionally stable in R5 and R6 consumed evidence?",
            "Is the fresh p95 drawdown failure concentrated in a repeatable predecision geometry?",
            (
                "Can any proposed fix survive chronological walk-forward before a new "
                "identity is frozen?"
            ),
        ],
        "governance": {
            "r8_retuning_prohibited": True,
            "new_candidate_required_for_any_fix": True,
            "fresh_partition_is_consumed": True,
            "new_fresh_evidence_prohibited_during_forensics": True,
        },
    }
    Path("vt31-r8-fresh-failure-forensics.json").write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    )
    summary = {
        "candidate": r8.CANDIDATE_ID,
        "fresh": partitions["r8_fresh"]["exact_replay"],
        "fresh_funnel": partitions["r8_fresh"]["funnel"],
        "fresh_long": _metrics(
            [item for item in fresh if item["side"] == "long"],
            friction=r8.FRICTION,
        ),
        "fresh_short": _metrics(
            [item for item in fresh if item["side"] == "short"],
            friction=r8.FRICTION,
        ),
        "fresh_worst_drawdown": report["tail"]["fresh_worst_drawdown"],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
