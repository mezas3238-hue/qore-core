"""Post-1R closed-bar persistence forensics for VT31 NAS100.

Research-only experiment over consumed NAS100 M1 evidence.

The experiment does NOT protect immediately at the first 1R touch. Instead it
predeclares three observation horizons -- 2, 3, and 5 fully closed M1 bars
after an unambiguous 1R touch -- and asks whether the causal post-touch state
separates future giveback from deeper delivery.

No threshold, stop policy, target policy, or runtime action is selected here.
Future journey class and deeper delivery are labels for consumed-evidence
research only.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

import vt31_nas100_ny_delivery_journey_forensics_v1 as journey

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.post_1r_persistence_forensics.v1"
IDENTITY = "VT31_NAS100_POST_1R_PERSISTENCE_FORENSICS_V1"
MARKET = "NAS100"
HORIZONS = (2, 3, 5)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _rate(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    return format(Decimal(numerator) / Decimal(denominator), "f")


def _median_decimal(values: Sequence[Decimal]) -> str | None:
    if not values:
        return None
    return format(Decimal(str(median(values))), "f")


def _touches_initial_stop(
    bar: object,
    *,
    side: str,
    stop: Decimal,
) -> bool:
    high = _d(getattr(bar, "high"))
    low = _d(getattr(bar, "low"))
    return low <= stop if side == "long" else high >= stop


def _favorable_r(
    bar: object,
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    return journey._favorable_r(
        side=side,
        entry=entry,
        risk=risk,
        high=_d(getattr(bar, "high")),
        low=_d(getattr(bar, "low")),
    )


def _close_r(
    bar: object,
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    return journey._close_r(
        side=side,
        entry=entry,
        risk=risk,
        close=_d(getattr(bar, "close")),
    )


def _persistence_state(closes_r: Sequence[Decimal]) -> str:
    if not closes_r:
        raise ValueError("persistence state requires closed bars")
    current = closes_r[-1]
    if current >= Decimal(1) and all(
        value >= Decimal(1) for value in closes_r
    ):
        return "PERSISTENT_1R_FLOOR"
    if current >= Decimal(1):
        return "RECOVERED_1R_FLOOR"
    if current > 0:
        return "POSITIVE_BELOW_1R"
    return "ENTRY_OR_WORSE"


def _dol_rank_through(
    bars: Sequence[object],
    *,
    side: str,
    ladder: Sequence[tuple[str, Decimal]],
) -> int:
    rank = 0
    for bar in bars:
        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        for candidate_rank, (_, level) in enumerate(ladder, start=1):
            if journey._touches(
                side=side,
                high=high,
                low=low,
                level=level,
            ):
                rank = max(rank, candidate_rank)
    return rank


def _first_unambiguous_1r_touch(
    bars: Sequence[object],
    *,
    side: str,
    entry: Decimal,
    stop: Decimal,
    risk: Decimal,
) -> tuple[int | None, str]:
    for index, bar in enumerate(bars):
        stop_hit = _touches_initial_stop(
            bar,
            side=side,
            stop=stop,
        )
        one_r_hit = _favorable_r(
            bar,
            side=side,
            entry=entry,
            risk=risk,
        ) >= Decimal(1)

        if one_r_hit and stop_hit:
            return None, "censored-same-bar-1r-vs-stop"
        if stop_hit:
            return None, "invalidated-before-1r"
        if one_r_hit:
            return index, "observed"
    return None, "no-1r-before-lifecycle"


def _observation(
    *,
    partition: str,
    local_day: date,
    setup: Any,
    eligible: tuple[object, ...],
    touch_index: int,
    horizon: int,
    journey_row: Mapping[str, object],
) -> tuple[dict[str, object] | None, str]:
    end_index = touch_index + horizon
    if end_index >= len(eligible):
        return None, "insufficient-bars-after-1r"

    side = str(setup.side.value)
    entry = _d(setup.entry_price)
    stop = _d(setup.stop_price)
    risk = _d(setup.initial_risk)
    post_touch = eligible[touch_index + 1 : end_index + 1]

    for bar in post_touch:
        if _touches_initial_stop(
            bar,
            side=side,
            stop=stop,
        ):
            return None, "methodological-invalidation-before-horizon"

    closes_r = [
        _close_r(
            bar,
            side=side,
            entry=entry,
            risk=risk,
        )
        for bar in post_touch
    ]
    favorable_to_horizon = [
        _favorable_r(
            bar,
            side=side,
            entry=entry,
            risk=risk,
        )
        for bar in eligible[touch_index : end_index + 1]
    ]
    peak_favorable = max(favorable_to_horizon)
    current_close = closes_r[-1]
    giveback = max(Decimal(0), peak_favorable - current_close)
    above_1r = sum(value >= Decimal(1) for value in closes_r)
    positive = sum(value > 0 for value in closes_r)

    overlap = journey._overlap_rate(post_touch)
    efficiency = journey._path_efficiency(
        post_touch,
        side=side,
    )
    favorable_close_rate = journey._continuation_close_rate(
        post_touch,
        side=side,
    )
    ladder = journey._dol_ladder(setup)
    rank = _dol_rank_through(
        eligible[: end_index + 1],
        side=side,
        ladder=ladder,
    )
    observed_bar = eligible[end_index]
    observed_at = cast(datetime, getattr(observed_bar, "closed_at"))

    journey_class = str(journey_row["journey_class"])
    eventual_max_favorable = _d(journey_row["max_favorable_r"])
    return (
        {
            "partition": partition,
            "local_date": local_day.isoformat(),
            "signal_at": cast(str, journey_row["signal_at"]),
            "filled_at": cast(str, journey_row["filled_at"]),
            "side": side,
            "entry_family": str(journey_row["entry_family"]),
            "one_r_touch_at": cast(
                datetime,
                getattr(eligible[touch_index], "closed_at"),
            ).astimezone(UTC).isoformat(),
            "observation_at": observed_at.astimezone(UTC).isoformat(),
            "horizon_closed_bars": horizon,
            "persistence_state": _persistence_state(closes_r),
            "current_close_r": format(current_close, "f"),
            "post_1r_close_above_1r_fraction": format(
                Decimal(above_1r) / Decimal(horizon),
                "f",
            ),
            "post_1r_positive_close_fraction": format(
                Decimal(positive) / Decimal(horizon),
                "f",
            ),
            "post_1r_favorable_candle_fraction": _fmt(
                favorable_close_rate
            ),
            "post_1r_overlap_rate": _fmt(overlap),
            "post_1r_path_efficiency": _fmt(efficiency),
            "peak_favorable_r_to_observation": format(
                peak_favorable,
                "f",
            ),
            "giveback_from_peak_to_observation_r": format(
                giveback,
                "f",
            ),
            "max_dol_rank_at_observation": rank,
            "future_label_journey_class": journey_class,
            "future_label_eventual_max_favorable_r": format(
                eventual_max_favorable,
                "f",
            ),
            "future_label_eventual_3r_plus": (
                eventual_max_favorable >= Decimal(3)
            ),
            "future_label_eventual_5r_plus": (
                eventual_max_favorable >= Decimal(5)
            ),
            "future_label_giveback_after_1r": (
                journey_class == "GIVEBACK_AFTER_1R"
            ),
            "future_labels_used_for_runtime_decision": False,
        },
        "observed",
    )


def _state_summary(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    states: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        states[str(row["persistence_state"])].append(row)

    result: dict[str, object] = {}
    for state, items in sorted(states.items()):
        classes = Counter(
            str(item["future_label_journey_class"])
            for item in items
        )
        current = [_d(item["current_close_r"]) for item in items]
        above = [
            _d(item["post_1r_close_above_1r_fraction"])
            for item in items
        ]
        giveback = [
            _d(item["giveback_from_peak_to_observation_r"])
            for item in items
        ]
        result[state] = {
            "n": len(items),
            "journey_class_counts": dict(sorted(classes.items())),
            "eventual_3r_plus_rate": _rate(
                sum(bool(item["future_label_eventual_3r_plus"]) for item in items),
                len(items),
            ),
            "eventual_5r_plus_rate": _rate(
                sum(bool(item["future_label_eventual_5r_plus"]) for item in items),
                len(items),
            ),
            "giveback_after_1r_rate": _rate(
                sum(
                    bool(item["future_label_giveback_after_1r"])
                    for item in items
                ),
                len(items),
            ),
            "median_current_close_r": _median_decimal(current),
            "median_close_above_1r_fraction": _median_decimal(above),
            "median_giveback_from_peak_r": _median_decimal(giveback),
        }
    return result


def replay(
    path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    if journey.silver.SOURCE_SHA256 != journey.EXPECTED_SOURCE_SHA256:
        raise AssertionError("Silver Bullet source SHA changed")
    if journey.silver.METHODOLOGY_ID != journey.EXPECTED_METHODOLOGY_ID:
        raise AssertionError("Silver Bullet methodology identity changed")

    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("post-1R persistence forensics requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    rows: list[dict[str, object]] = []
    status: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        setup = journey._select_setup(
            day_bars,
            evidence=evidence,
        )
        if setup is None:
            status["no-executable-setup"] += 1
            continue

        journey_row = journey._journey(day_bars, setup)
        if journey_row.get("status") != "labeled":
            status[f"journey-{journey_row.get('status')}"] += 1
            continue

        fill_index = journey.v2b._fill_index(day_bars, setup)
        if fill_index is None:
            status["no-fill"] += 1
            continue

        eligible = tuple(
            bar
            for bar in day_bars[fill_index:]
            if journey.specialist.baseline._local_minute(bar)
            < journey.LIFECYCLE_MINUTE
        )
        if not eligible:
            status["no-lifecycle-bars"] += 1
            continue

        side = setup.side.value
        entry = _d(setup.entry_price)
        stop = _d(setup.stop_price)
        risk = _d(setup.initial_risk)
        if risk <= 0:
            status["invalid-risk"] += 1
            continue

        touch_index, touch_status = _first_unambiguous_1r_touch(
            eligible,
            side=side,
            entry=entry,
            stop=stop,
            risk=risk,
        )
        status[f"one-r-{touch_status}"] += 1
        if touch_index is None:
            continue

        for horizon in HORIZONS:
            observation, observation_status = _observation(
                partition=partition,
                local_day=local_day,
                setup=setup,
                eligible=eligible,
                touch_index=touch_index,
                horizon=horizon,
                journey_row=journey_row,
            )
            status[f"h{horizon}-{observation_status}"] += 1
            if observation is not None:
                rows.append(observation)

    by_horizon = {
        str(horizon): [
            row
            for row in rows
            if int(row["horizon_closed_bars"]) == horizon
        ]
        for horizon in HORIZONS
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "partition": partition,
        "market": MARKET,
        "predeclared_horizons_closed_m1": list(HORIZONS),
        "summary": {
            str(horizon): {
                "observations": len(items),
                "states": _state_summary(items),
            }
            for horizon, items in (
                (horizon, by_horizon[str(horizon)])
                for horizon in HORIZONS
            )
        },
        "rows": rows,
        "status_counts": dict(sorted(status.items())),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "silver_bullet_modified": False,
            "m1_only": True,
            "first_1r_touch_triggers_runtime_action": False,
            "same_bar_1r_stop_ambiguity_censored": True,
            "future_labels_research_only": True,
            "best_horizon_selected": False,
            "threshold_selected": False,
            "runtime_policy_promoted": False,
            "consumed_evidence_only": True,
            "opens_new_holdout": False,
            "candidate_frozen": False,
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

    payload = replay(
        args.evidence,
        partition=args.partition,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "summary": payload["summary"],
                "status_counts": payload["status_counts"],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
