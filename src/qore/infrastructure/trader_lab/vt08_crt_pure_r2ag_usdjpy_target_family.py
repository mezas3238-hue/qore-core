"""R2-AG USDJPY target-family laboratory.

Frozen entry population:
- USDJPY;
- EFF5D 0.10 <= efficiency < 0.20;
- R2-G NEWEST_SUPERSEDES_CONFIRMATION_FIRST;
- current midpoint geometry must be valid for every arm;
- current structural stop and C3-close expiry.

Only target/destination changes, reusing the exact R2-AF target family.
Consumed development window: 2014-2026.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    ARMS,
    TARGET_MULTIPLE,
    TargetArm,
    _resolve_fixed_target,
    _retag_control,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2q_usdjpy_multi_regime_atlas import (
    _context,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2AG_USDJPY_TARGET_FAMILY_001"
SCHEMA = "qore.vt08.crt_pure.r2ag_usdjpy_target_family.v1"
MARKET = CrtPureMarket.USDJPY
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST

START = datetime(2014, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
FETCH_START = START - timedelta(days=25)
YEAR_BOUNDARIES: tuple[datetime, ...] = tuple(
    datetime(year, 9, 21, 0, 0, tzinfo=UTC)
    for year in range(2014, 2027)
)

EFF5_LOW = Decimal("0.10")
EFF5_HIGH = Decimal("0.20")


def _window(
    rows: tuple[Model1LabTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[Model1LabTrade, ...]:
    return tuple(
        row
        for row in rows
        if start <= datetime.fromisoformat(row.entry_opened_at) < end
    )


def _annual(rows: tuple[Model1LabTrade, ...]) -> dict[str, dict[str, Any]]:
    return {
        f"{left.year}_{right.year}": _summary(_window(rows, left, right))
        for left, right in zip(
            YEAR_BOUNDARIES[:-1],
            YEAR_BOUNDARIES[1:],
            strict=True,
        )
    }


def run_lab() -> tuple[dict[TargetArm, tuple[Model1LabTrade, ...]], dict[str, Any]]:
    bars = load_m5_window(MARKET, start=FETCH_START, end_exclusive=END)
    parents = build_parent_crts_for_window(
        MARKET,
        bars,
        start=START,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    times = tuple(bar.opened_at for bar in m15)
    breaches = build_close_unmitigated_breach_groups(m15)

    rows: dict[TargetArm, list[Model1LabTrade]] = {
        arm: [] for arm in ARMS
    }
    diagnostics: dict[str, int] = defaultdict(int)

    for parent in parents:
        diagnostics["parent_count"] += 1
        context = _context(parent=parent, m15=m15, times=times)
        if context is None:
            diagnostics["insufficient_context"] += 1
            continue
        if not EFF5_LOW <= context[3] < EFF5_HIGH:
            diagnostics["outside_frozen_eff5_regime"] += 1
            continue

        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        selected = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        if selected is None:
            diagnostics["no_selected_hypothesis"] += 1
            continue

        observation, confirmation, entry = selected
        control = _resolve_trade(
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if control is None:
            diagnostics["midpoint_geometry_rejected"] += 1
            continue

        rows[TargetArm.MIDPOINT_CONTROL].append(_retag_control(control))
        for arm, multiple in TARGET_MULTIPLE.items():
            trade = _resolve_fixed_target(
                arm=arm,
                multiple=multiple,
                parent=parent,
                group=observation.group,
                confirmation=confirmation,
                entry_bar=entry,
                c3_m15=c3_m15,
            )
            if trade is None:
                raise RuntimeError(
                    "fixed target rejected a midpoint-eligible structural risk"
                )
            rows[arm].append(trade)
        diagnostics["entry_population_created"] += 1

    frozen = {
        arm: tuple(sorted(trades, key=lambda item: item.entry_opened_at))
        for arm, trades in rows.items()
    }
    arms: dict[str, Any] = {}
    annual_stable: list[str] = []
    for arm in ARMS:
        trades = frozen[arm]
        annual = _annual(trades)
        all_positive = all(float(item["total_r"]) > 0 for item in annual.values())
        if all_positive:
            annual_stable.append(arm.value)
        arms[arm.value] = {
            "full_12y": _summary(trades),
            "annual": annual,
            "all_annual_windows_positive": all_positive,
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "frozen_eff5_bounds": [str(EFF5_LOW), str(EFF5_HIGH)],
        "single_changed_dimension": "TARGET_DESTINATION",
        "same_entry_population_all_arms": True,
        "same_stop_all_arms": True,
        "same_expiry_all_arms": True,
        "stop_first_all_arms": True,
        "arms_frozen_before_results": [arm.value for arm in ARMS],
        "diagnostics": dict(diagnostics),
        "arms": arms,
        "annual_stable_arms": annual_stable,
        "automatic_winner_ranking": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    arms, report = run_lab()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for arm in ARMS:
            for trade in arms[arm]:
                row = asdict(trade)
                row["target_arm"] = arm.value
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2AG_USDJPY_TARGET_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
