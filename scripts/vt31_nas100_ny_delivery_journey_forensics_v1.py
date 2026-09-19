"""M1-only New York delivery-journey forensics for VT31 NAS100.

Silver Bullet source identity is frozen and is not modified by this lab.

The lab observes what NAS100 actually does after a valid Silver Bullet fill
through 16:00 New York.  It measures structural destination depth, R-extension,
speed, overlap, pullback and continuation at fixed causal milestones.

This is market/trader understanding research.  Post-fill labels are never
runtime authorization inputs and no target/protection policy is selected here.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders import vt31_silver_bullet_r2_2 as silver
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.ny_delivery_journey_forensics.v1"
IDENTITY = "VT31_NAS100_NY_DELIVERY_JOURNEY_FORENSICS_V1"
MARKET = "NAS100"
LIFECYCLE_MINUTE = 16 * 60
EXPECTED_SOURCE_SHA256 = (
    "bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf"
)
EXPECTED_METHODOLOGY_ID = "ttrades-am-silver-bullet-nq-r2.2"
R_MILESTONES = tuple(
    Decimal(value)
    for value in ("0.5", "0.75", "1.0", "1.5", "2.0", "3.0", "4.0", "5.0")
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _median_decimal(values: list[Decimal]) -> str | None:
    if not values:
        return None
    return format(Decimal(str(median(values))), "f")


def _median_int(values: list[int]) -> str | None:
    if not values:
        return None
    return str(median(values))


def _rate(n: int, d: int) -> str | None:
    if d == 0:
        return None
    return format(Decimal(n) / Decimal(d), "f")


def _favorable_r(
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
    high: Decimal,
    low: Decimal,
) -> Decimal:
    if side == "long":
        return (high - entry) / risk
    return (entry - low) / risk


def _adverse_r(
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
    high: Decimal,
    low: Decimal,
) -> Decimal:
    if side == "long":
        return (entry - low) / risk
    return (high - entry) / risk


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


def _touches(
    *,
    side: str,
    high: Decimal,
    low: Decimal,
    level: Decimal,
) -> bool:
    if side == "long":
        return high >= level
    return low <= level


def _dol_ladder(
    setup: Vt31R22ExecutableSetup,
) -> tuple[tuple[str, Decimal], ...]:
    side = setup.side.value
    boundary = setup.target_price
    width = (
        setup.source_setup.reference.high
        - setup.source_setup.reference.low
    )
    direction = Decimal(1) if side == "long" else Decimal(-1)
    return (
        ("DOL1_BOUNDARY", boundary),
        ("DOL2_PLUS_0_25_REF", boundary + direction * width * Decimal("0.25")),
        ("DOL3_PLUS_0_50_REF", boundary + direction * width * Decimal("0.50")),
        ("DOL4_PLUS_1_00_REF", boundary + direction * width),
        ("DOL5_PLUS_1_50_REF", boundary + direction * width * Decimal("1.50")),
        ("DOL6_PLUS_2_00_REF", boundary + direction * width * Decimal("2.00")),
    )


def _overlap_rate(
    bars: tuple[object, ...],
) -> Decimal | None:
    if len(bars) < 2:
        return None
    overlaps = 0
    comparisons = 0
    for left, right in zip(bars, bars[1:], strict=False):
        left_low = _d(getattr(left, "low"))
        left_high = _d(getattr(left, "high"))
        right_low = _d(getattr(right, "low"))
        right_high = _d(getattr(right, "high"))
        union = max(left_high, right_high) - min(left_low, right_low)
        if union <= 0:
            continue
        intersection = max(
            Decimal(0),
            min(left_high, right_high) - max(left_low, right_low),
        )
        if intersection / union >= Decimal("0.25"):
            overlaps += 1
        comparisons += 1
    if comparisons == 0:
        return None
    return Decimal(overlaps) / Decimal(comparisons)


def _path_efficiency(
    bars: tuple[object, ...],
    *,
    side: str,
) -> Decimal | None:
    if len(bars) < 2:
        return None
    closes = [_d(getattr(bar, "close")) for bar in bars]
    net = (
        closes[-1] - closes[0]
        if side == "long"
        else closes[0] - closes[-1]
    )
    gross = sum(
        (abs(right - left) for left, right in zip(closes, closes[1:], strict=False)),
        Decimal(0),
    )
    if gross <= 0:
        return None
    return net / gross


def _continuation_close_rate(
    bars: tuple[object, ...],
    *,
    side: str,
) -> Decimal | None:
    if not bars:
        return None
    favorable = 0
    for bar in bars:
        opened = _d(getattr(bar, "open"))
        close = _d(getattr(bar, "close"))
        if (side == "long" and close > opened) or (
            side == "short" and close < opened
        ):
            favorable += 1
    return Decimal(favorable) / Decimal(len(bars))


def _milestone_snapshot(
    path: tuple[object, ...],
    *,
    reached_index: int,
    fill_index_local: int,
    side: str,
    entry: Decimal,
    risk: Decimal,
) -> dict[str, object]:
    start = max(fill_index_local, reached_index - 9)
    recent = path[start : reached_index + 1]
    last5 = recent[-5:]
    closes = [_d(getattr(bar, "close")) for bar in recent]
    close_rs = [
        _close_r(
            side=side,
            entry=entry,
            risk=risk,
            close=value,
        )
        for value in closes
    ]
    peak_close_r = max(close_rs) if close_rs else Decimal(0)
    current_close_r = close_rs[-1] if close_rs else Decimal(0)
    close_giveback = max(Decimal(0), peak_close_r - current_close_r)
    overlap = _overlap_rate(last5)
    efficiency = _path_efficiency(last5, side=side)
    continuation = _continuation_close_rate(last5, side=side)
    return {
        "recent_bar_count": len(last5),
        "last5_overlap_rate": None if overlap is None else format(overlap, "f"),
        "last5_path_efficiency": (
            None if efficiency is None else format(efficiency, "f")
        ),
        "last5_favorable_close_rate": (
            None if continuation is None else format(continuation, "f")
        ),
        "close_giveback_from_recent_peak_r": format(close_giveback, "f"),
        "current_close_r": format(current_close_r, "f"),
    }


def _select_setup(
    day_bars: tuple[object, ...],
    *,
    evidence: str,
) -> Vt31R22ExecutableSetup | None:
    reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
    session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
    if len(reference) != 60 or len(session) != 60:
        return None
    policy = Vt31R22ExecutionPolicy()
    prefix = list(reference)
    for bar in session:
        prefix.append(bar)
        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=getattr(bar, "closed_at"),
            m1_candles=cast(Any, tuple(prefix)),
            evidence_fingerprint=evidence,
        )
        if evaluation.setup is None:
            if evaluation.both_sides_swept:
                return None
            continue
        setup, _ = make_executable_setup(evaluation.setup, policy)
        return setup
    return None


def _journey(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
) -> dict[str, object]:
    fill_index = v2b._fill_index(day_bars, setup)
    if fill_index is None:
        return {"status": "no-fill"}

    side = setup.side.value
    entry = setup.entry_price
    stop = setup.stop_price
    risk = setup.initial_risk
    if risk <= 0:
        return {"status": "censored-invalid-risk"}

    eligible = tuple(
        bar
        for bar in day_bars[fill_index:]
        if specialist.baseline._local_minute(bar) < LIFECYCLE_MINUTE
    )
    if not eligible:
        return {"status": "censored-no-lifecycle"}

    first = eligible[0]
    first_high = _d(getattr(first, "high"))
    first_low = _d(getattr(first, "low"))
    stop_first = first_low <= stop if side == "long" else first_high >= stop
    if stop_first:
        return {"status": "censored-fill-bar-stop"}

    ladder = _dol_ladder(setup)
    milestone_hits: dict[str, dict[str, object]] = {}
    dol_hits: dict[str, str] = {}
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)
    max_close_r = Decimal("-999")
    max_close_r_index = 0
    terminal_reason = "16:00-lifecycle"
    terminal_index = len(eligible) - 1
    filled_at = cast(datetime, getattr(first, "closed_at"))

    for index, bar in enumerate(eligible):
        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        close = _d(getattr(bar, "close"))
        favorable = _favorable_r(
            side=side, entry=entry, risk=risk, high=high, low=low
        )
        adverse = _adverse_r(
            side=side, entry=entry, risk=risk, high=high, low=low
        )
        close_r = _close_r(
            side=side, entry=entry, risk=risk, close=close
        )
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)
        if close_r > max_close_r:
            max_close_r = close_r
            max_close_r_index = index

        for milestone in R_MILESTONES:
            key = format(milestone, "f")
            if key in milestone_hits or favorable < milestone:
                continue
            reached_at = cast(datetime, getattr(bar, "closed_at"))
            milestone_hits[key] = {
                "reached_at": reached_at.astimezone(UTC).isoformat(),
                "minutes_from_fill": int(
                    (reached_at - filled_at).total_seconds() // 60
                ),
                "bars_from_fill": index,
                **_milestone_snapshot(
                    eligible,
                    reached_index=index,
                    fill_index_local=0,
                    side=side,
                    entry=entry,
                    risk=risk,
                ),
            }

        for name, level in ladder:
            if name in dol_hits:
                continue
            if _touches(side=side, high=high, low=low, level=level):
                dol_hits[name] = (
                    cast(datetime, getattr(bar, "closed_at"))
                    .astimezone(UTC)
                    .isoformat()
                )

        stop_hit = low <= stop if side == "long" else high >= stop
        if stop_hit:
            terminal_reason = "methodological-invalidation"
            terminal_index = index
            break

    terminal_bar = eligible[terminal_index]
    terminal_at = cast(datetime, getattr(terminal_bar, "closed_at"))
    terminal_close = _d(getattr(terminal_bar, "close"))
    terminal_close_r = _close_r(
        side=side,
        entry=entry,
        risk=risk,
        close=terminal_close,
    )

    reached_1r = "1.0" in milestone_hits
    reached_3r = "3.0" in milestone_hits
    reached_5r = "5.0" in milestone_hits
    if reached_5r:
        journey_class = "EXTENDED_RUNNER_5R_PLUS"
    elif reached_3r:
        journey_class = "RUNNER_3R_PLUS"
    elif reached_1r and terminal_reason == "methodological-invalidation":
        journey_class = "GIVEBACK_AFTER_1R"
    elif reached_1r:
        journey_class = "PARTIAL_DELIVERY_1R_PLUS"
    elif terminal_reason == "methodological-invalidation":
        journey_class = "FAILED_BEFORE_1R"
    else:
        journey_class = "UNRESOLVED_LIFECYCLE"

    return {
        "status": "labeled",
        "filled_at": filled_at.astimezone(UTC).isoformat(),
        "journey_end_at": terminal_at.astimezone(UTC).isoformat(),
        "journey_end_reason": terminal_reason,
        "journey_class": journey_class,
        "side": side,
        "entry_family": setup.selected_family.value,
        "signal_at": setup.decision_at.astimezone(UTC).isoformat(),
        "max_favorable_r": format(max_favorable, "f"),
        "max_adverse_r": format(max_adverse, "f"),
        "max_close_r": format(max_close_r, "f"),
        "max_close_r_minutes_from_fill": int(
            (
                cast(datetime, getattr(eligible[max_close_r_index], "closed_at"))
                - filled_at
            ).total_seconds()
            // 60
        ),
        "terminal_close_r": format(terminal_close_r, "f"),
        "minutes_fill_to_end": int(
            (terminal_at - filled_at).total_seconds() // 60
        ),
        "milestones": milestone_hits,
        "dol_hits": dol_hits,
        "max_dol_rank": len(dol_hits),
        "reference_width": format(
            setup.source_setup.reference.high
            - setup.source_setup.reference.low,
            "f",
        ),
        "initial_risk": format(risk, "f"),
        "structural_boundary_r": format(
            abs(setup.target_price - entry) / risk,
            "f",
        ),
    }


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    labeled = [row for row in rows if row["status"] == "labeled"]
    classes = Counter(str(row["journey_class"]) for row in labeled)
    milestone_rates = {}
    for milestone in R_MILESTONES:
        key = format(milestone, "f")
        reached = [
            row for row in labeled
            if key in cast(dict[str, object], row["milestones"])
        ]
        times = [
            int(
                cast(dict[str, object], row["milestones"])[key][
                    "minutes_from_fill"
                ]
            )
            for row in reached
        ]
        milestone_rates[key] = {
            "reached": len(reached),
            "rate": _rate(len(reached), len(labeled)),
            "median_minutes_from_fill": _median_int(times),
        }

    dol_rates = {}
    for rank, name in enumerate(
        (
            "DOL1_BOUNDARY",
            "DOL2_PLUS_0_25_REF",
            "DOL3_PLUS_0_50_REF",
            "DOL4_PLUS_1_00_REF",
            "DOL5_PLUS_1_50_REF",
            "DOL6_PLUS_2_00_REF",
        ),
        start=1,
    ):
        reached = sum(
            name in cast(dict[str, object], row["dol_hits"])
            for row in labeled
        )
        dol_rates[str(rank)] = {
            "name": name,
            "reached": reached,
            "rate": _rate(reached, len(labeled)),
        }

    max_favorable = [
        _d(row["max_favorable_r"]) for row in labeled
    ]
    return {
        "observations": len(rows),
        "labeled": len(labeled),
        "journey_classes": dict(sorted(classes.items())),
        "milestone_rates": milestone_rates,
        "dol_rates": dol_rates,
        "median_max_favorable_r": _median_decimal(max_favorable),
    }


def _milestone_classification(
    rows: list[dict[str, object]],
    *,
    milestone: str,
) -> dict[str, object]:
    reached = [
        row for row in rows
        if row["status"] == "labeled"
        and milestone in cast(dict[str, object], row["milestones"])
    ]
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in reached:
        groups[str(row["journey_class"])].append(row)

    def metric(
        items: list[dict[str, object]],
        key: str,
    ) -> dict[str, object]:
        values = []
        for row in items:
            snap = cast(dict[str, Any], row["milestones"])[milestone]
            raw = snap.get(key)
            if raw is not None:
                values.append(Decimal(str(raw)))
        return {
            "n": len(items),
            "median": _median_decimal(values),
        }

    return {
        name: {
            "n": len(items),
            "overlap": metric(items, "last5_overlap_rate"),
            "efficiency": metric(items, "last5_path_efficiency"),
            "favorable_close_rate": metric(
                items, "last5_favorable_close_rate"
            ),
            "close_giveback": metric(
                items, "close_giveback_from_recent_peak_r"
            ),
            "minutes_from_fill": {
                "n": len(items),
                "median": _median_int(
                    [
                        int(
                            cast(dict[str, Any], row["milestones"])[milestone][
                                "minutes_from_fill"
                            ]
                        )
                        for row in items
                    ]
                ),
            },
        }
        for name, items in sorted(groups.items())
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
        raise ValueError("NY delivery journey requires NAS100")

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
        setup = _select_setup(day_bars, evidence=evidence)
        if setup is None:
            status["no-executable-setup"] += 1
            continue
        journey = _journey(day_bars, setup)
        status[f"journey-{journey['status']}"] += 1
        journey["local_date"] = local_day.isoformat()
        rows.append(journey)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "partition": partition,
        "market": MARKET,
        "silver_bullet_freeze": {
            "source_sha256": silver.SOURCE_SHA256,
            "methodology_id": silver.METHODOLOGY_ID,
            "source_module_modified": False,
        },
        "summary": _summary(rows),
        "milestone_0_5r_classes": _milestone_classification(
            rows, milestone="0.5"
        ),
        "milestone_1_0r_classes": _milestone_classification(
            rows, milestone="1.0"
        ),
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
            "silver_bullet_source_frozen": True,
            "m1_ny_session_only": True,
            "h4_primary_causal_feature": False,
            "h1_trend_primary_causal_feature": False,
            "extended_targets_are_labels_not_runtime_rules": True,
            "post_fill_journey_labels_runtime_authorization": False,
            "consumed_evidence_only": True,
            "policy_promoted": False,
            "opens_new_holdout": False,
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
                "summary": payload["summary"],
                "milestone_0_5r_classes": payload[
                    "milestone_0_5r_classes"
                ],
                "milestone_1_0r_classes": payload[
                    "milestone_1_0r_classes"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
