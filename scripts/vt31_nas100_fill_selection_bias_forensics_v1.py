"""Fill-selection bias forensics around frozen VT31 Silver Bullet.

Silver Bullet source identity is immutable.

This lab asks whether QORE's current source_rule=False midpoint/CE pending-entry
translation preferentially fills sources whose future journey invalidates first
while missing sources whose future journey completes the reversal.

At source confirmation, future journey is labelled research-only as:
- REVERSAL_COMPLETION,
- SOURCE_INVALIDATION_FIRST,
- CENSORED_SAME_BAR_STOP_TARGET,
- UNRESOLVED_BY_16.

The current QORE pending order is then observed causally:
- fill / no-fill before 11:00 NY;
- decision-to-fill delay;
- target/stop delivery before fill;
- fill-bar path censoring;
- terminal current-policy outcome.

No Silver Bullet rule is changed and no alternative execution is promoted.
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

import vt31_nas100_r1_candidate as baseline
import vt31_nas100_reversal_vs_expansion_forensics_v1 as reversal
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders import vt31_silver_bullet_r2_2 as silver
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.fill_selection_bias_forensics.v1"
IDENTITY = "VT31_NAS100_FILL_SELECTION_BIAS_FORENSICS_V1"
MARKET = "NAS100"
EXPECTED_SOURCE_SHA256 = (
    "bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf"
)
EXPECTED_METHODOLOGY_ID = "ttrades-am-silver-bullet-nq-r2.2"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _selected_source(
    day_bars: tuple[object, ...],
    *,
    evidence: str,
) -> tuple[Vt31R22SourceSetup, Vt31R22ExecutableSetup] | None:
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
        executable, _ = make_executable_setup(
            evaluation.setup,
            policy,
        )
        if executable is None:
            return None
        return evaluation.setup, executable
    return None


def _fill_index(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
) -> int | None:
    for index, bar in enumerate(day_bars):
        opened_at = cast(datetime, getattr(bar, "opened_at"))
        if opened_at < setup.decision_at:
            continue
        if specialist.baseline._local_minute(bar) >= 11 * 60:
            break
        low = _d(getattr(bar, "low"))
        high = _d(getattr(bar, "high"))
        if low <= setup.entry_price <= high:
            return index
    return None


def _pre_fill_state(
    day_bars: tuple[object, ...],
    *,
    source: Vt31R22SourceSetup,
    setup: Vt31R22ExecutableSetup,
    fill_index: int,
) -> dict[str, object]:
    target_before = False
    stop_before = False
    both_sides_before = False

    for bar in day_bars:
        opened_at = cast(datetime, getattr(bar, "opened_at"))
        if opened_at < setup.decision_at:
            continue
        if opened_at >= cast(
            datetime,
            getattr(day_bars[fill_index], "opened_at"),
        ):
            break

        if reversal._touches_target(
            bar,
            side=source.side.value,
            target=source.target_price,
        ):
            target_before = True
        if reversal._touches_stop(
            bar,
            side=source.side.value,
            stop=source.structure.swing_extreme,
        ):
            stop_before = True

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        if (
            high > source.reference.high
            and low < source.reference.low
        ):
            both_sides_before = True

    return {
        "target_before_fill": target_before,
        "stop_before_fill": stop_before,
        "both_sides_before_fill": both_sides_before,
    }


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    source_count = len(rows)
    fills = [row for row in rows if bool(row["filled"])]
    terminal = [
        row
        for row in fills
        if row.get("terminal_r") is not None
    ]
    nonloss = [
        row
        for row in terminal
        if _d(row["terminal_r"]) >= 0
    ]
    delays = [
        int(cast(int, row["decision_to_fill_minutes"]))
        for row in fills
        if row.get("decision_to_fill_minutes") is not None
    ]

    return {
        "source_count": source_count,
        "fill_count": len(fills),
        "fill_rate": (
            "0"
            if source_count == 0
            else format(
                Decimal(len(fills)) / Decimal(source_count),
                "f",
            )
        ),
        "no_fill_count": source_count - len(fills),
        "terminal_count": len(terminal),
        "nonloss_terminal_count": len(nonloss),
        "nonloss_rate_given_terminal": (
            "0"
            if not terminal
            else format(
                Decimal(len(nonloss)) / Decimal(len(terminal)),
                "f",
            )
        ),
        "median_decision_to_fill_minutes": (
            None if not delays else str(median(delays))
        ),
        "mean_decision_to_fill_minutes": (
            None
            if not delays
            else format(
                Decimal(sum(delays)) / Decimal(len(delays)),
                "f",
            )
        ),
        "target_before_fill_count": sum(
            bool(row["target_before_fill"])
            for row in fills
        ),
        "stop_before_fill_count": sum(
            bool(row["stop_before_fill"])
            for row in fills
        ),
        "both_sides_before_fill_count": sum(
            bool(row["both_sides_before_fill"])
            for row in fills
        ),
        "fill_bar_path_censored_count": sum(
            row.get("terminal_status") == "censored-fill-bar-path"
            for row in fills
        ),
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
        raise ValueError("fill selection forensics requires NAS100")

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
    status: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        selected = _selected_source(
            day_bars,
            evidence=evidence,
        )
        if selected is None:
            status["no-executable-source"] += 1
            continue

        source, setup = selected
        journey = reversal._future_journey(
            day_bars,
            source=source,
        )
        fill_index = _fill_index(day_bars, setup)

        row: dict[str, object] = {
            "partition": partition,
            "local_date": local_day.isoformat(),
            "journey_outcome": journey["journey_outcome"],
            "journey_label_research_only": True,
            "filled": fill_index is not None,
            "decision_to_fill_minutes": None,
            "target_before_fill": False,
            "stop_before_fill": False,
            "both_sides_before_fill": False,
            "terminal_status": None,
            "terminal_r": None,
            "entry_family": setup.selected_family.value,
        }

        if fill_index is None:
            status["no-fill"] += 1
            observations.append(row)
            continue

        fill_bar = day_bars[fill_index]
        fill_opened_at = cast(
            datetime,
            getattr(fill_bar, "opened_at"),
        )
        row["decision_to_fill_minutes"] = int(
            (fill_opened_at - setup.decision_at).total_seconds() // 60
        )
        row.update(
            _pre_fill_state(
                day_bars,
                source=source,
                setup=setup,
                fill_index=fill_index,
            )
        )

        outcome = baseline._simulate(day_bars, setup)
        row["terminal_status"] = outcome["status"]
        if outcome.get("status") == "terminal":
            row["terminal_r"] = outcome["r_multiple"]
            status["terminal"] += 1
        else:
            status[f"outcome-{outcome['status']}"] += 1

        observations.append(row)

    by_journey = {
        journey: _stats(
            [
                row
                for row in observations
                if row["journey_outcome"] == journey
            ]
        )
        for journey in (
            "REVERSAL_COMPLETION",
            "SOURCE_INVALIDATION_FIRST",
            "UNRESOLVED_BY_16",
            "CENSORED_SAME_BAR_STOP_TARGET",
        )
    }

    reversal_stats = by_journey["REVERSAL_COMPLETION"]
    invalidation_stats = by_journey["SOURCE_INVALIDATION_FIRST"]
    reversal_fill = Decimal(str(reversal_stats["fill_rate"]))
    invalidation_fill = Decimal(str(invalidation_stats["fill_rate"]))

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
        "overall": _stats(observations),
        "by_future_journey": by_journey,
        "selection_bias": {
            "invalidation_fill_rate_minus_reversal_fill_rate": format(
                invalidation_fill - reversal_fill,
                "f",
            ),
            "invalidation_to_reversal_fill_rate_ratio": (
                None
                if reversal_fill == 0
                else format(
                    invalidation_fill / reversal_fill,
                    "f",
                )
            ),
            "adverse_selection_present": (
                invalidation_fill > reversal_fill
            ),
        },
        "observations": observations,
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
            "current_qore_execution_policy_only": True,
            "journey_labels_research_only": True,
            "journey_labels_allowed_at_runtime": False,
            "terminal_pnl_used_as_runtime_feature": False,
            "consumed_evidence_only": True,
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
                "by_future_journey": payload["by_future_journey"],
                "selection_bias": payload["selection_bias"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
