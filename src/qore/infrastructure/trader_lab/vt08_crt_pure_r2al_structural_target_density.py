"""R2-AL structural-target geometry recovery for VT08 CRT PURE FX.

Problem isolated:
R2-AF/R2-AG only evaluated fixed-R targets after requiring the C1 midpoint
target itself to be geometrically valid. That can discard a structurally valid
entry simply because the midpoint lies behind the entry, even though a fixed
1R/1.5R/2R destination is perfectly well-defined.

R2-AL removes only that cross-arm midpoint precondition.

Common contract:
- existing non-overlapping FX H4 timing;
- no EFF regime filter;
- R2-G NEWEST_SUPERSEDES_CONFIRMATION_FIRST;
- max one selected hypothesis per parent;
- source-candle structural stop;
- C3-close expiry;
- STOP_FIRST;
- same confirmation and entry timing.

Arms:
- MIDPOINT_CONTROL: requires midpoint geometry, unchanged.
- FIXED_1R / FIXED_1_5R / FIXED_2R: require only valid structural stop geometry.

Consumed 2020-2026 research window. No automatic promotion.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TARGET_MULTIPLE,
    TargetArm,
    _resolve_fixed_target,
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
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2AL_STRUCTURAL_TARGET_DENSITY_001"
SCHEMA = "qore.vt08.crt_pure.r2al_structural_target_density.v1"
START = datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
FX_MARKETS = (CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY)

ARMS: tuple[TargetArm, ...] = (
    TargetArm.MIDPOINT_CONTROL,
    TargetArm.FIXED_1R,
    TargetArm.FIXED_1_5R,
    TargetArm.FIXED_2R,
)

YEAR_BOUNDARIES: tuple[datetime, ...] = tuple(
    datetime(year, 9, 21, 0, 0, tzinfo=UTC)
    for year in range(2020, 2027)
)


def _retag(
    trade: Model1LabTrade,
    *,
    arm: TargetArm,
) -> Model1LabTrade:
    return Model1LabTrade(
        schema=SCHEMA,
        identity=f"{IDENTITY}:{arm.value}",
        market=trade.market,
        reference_policy=trade.reference_policy,
        reference_count=trade.reference_count,
        reference_ids=trade.reference_ids,
        parent_direction=trade.parent_direction,
        timing_triplet=trade.timing_triplet,
        c3_opened_at=trade.c3_opened_at,
        source_opened_at=trade.source_opened_at,
        confirmation_opened_at=trade.confirmation_opened_at,
        entry_opened_at=trade.entry_opened_at,
        entry_price_relative=trade.entry_price_relative,
        stop_price_relative=trade.stop_price_relative,
        target_price_relative=trade.target_price_relative,
        exit_price_relative=trade.exit_price_relative,
        exit_reason=trade.exit_reason,
        r_multiple=trade.r_multiple,
        research_only=True,
        promotion_forbidden_from_lab_pnl=True,
    )


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


def run_lab(
    market: CrtPureMarket,
) -> tuple[dict[TargetArm, tuple[Model1LabTrade, ...]], dict[str, Any]]:
    if market not in FX_MARKETS:
        raise ValueError("R2-AL is FX-only")

    bars = load_m5_window(
        market,
        start=START - timedelta(days=1),
        end_exclusive=END + timedelta(days=1),
    )
    parents = build_parent_crts_for_window(
        market,
        bars,
        start=START,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    rows: dict[TargetArm, list[Model1LabTrade]] = {
        arm: [] for arm in ARMS
    }
    diagnostics: dict[str, int] = defaultdict(int)

    for parent in parents:
        diagnostics["parent_count"] += 1
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

        diagnostics["selected_hypothesis"] += 1
        observation, confirmation, entry = selected

        midpoint = _resolve_trade(
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if midpoint is None:
            diagnostics["midpoint_geometry_rejected"] += 1
        else:
            diagnostics["midpoint_trade_created"] += 1
            rows[TargetArm.MIDPOINT_CONTROL].append(
                _retag(midpoint, arm=TargetArm.MIDPOINT_CONTROL)
            )

        fixed_created = 0
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
                diagnostics[f"{arm.value}_structural_geometry_rejected"] += 1
                continue
            rows[arm].append(_retag(trade, arm=arm))
            diagnostics[f"{arm.value}_trade_created"] += 1
            fixed_created += 1

        if fixed_created:
            diagnostics["parent_with_any_fixed_target_trade"] += 1
        if midpoint is None and fixed_created:
            diagnostics["midpoint_rejected_but_fixed_recovered"] += 1

    frozen = {
        arm: tuple(sorted(trades, key=lambda item: item.entry_opened_at))
        for arm, trades in rows.items()
    }

    arm_reports: dict[str, Any] = {}
    for arm in ARMS:
        trades = frozen[arm]
        annual = _annual(trades)
        arm_reports[arm.value] = {
            "full_6y": _summary(trades),
            "annual": annual,
            "trades_per_year": round(len(trades) / 6, 8),
            "positive_annual_windows": sum(
                float(summary["total_r"]) > 0
                for summary in annual.values()
            ),
        }

    midpoint_count = len(frozen[TargetArm.MIDPOINT_CONTROL])
    fixed_1r_count = len(frozen[TargetArm.FIXED_1R])
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "efficiency_regime_filter": "OFF",
        "timing_lattice": "CONTROL_NON_OVERLAP",
        "single_question": "DOES_MIDPOINT_GEOMETRY_ARTIFICIALLY_KILL_FIXED_TARGET_DENSITY",
        "fixed_targets_require_midpoint_geometry": False,
        "same_source_stop_and_c3_expiry": True,
        "arms_frozen_before_results": [arm.value for arm in ARMS],
        "diagnostics": dict(diagnostics),
        "arms": arm_reports,
        "fixed_1r_vs_midpoint_trade_multiplier": (
            None
            if midpoint_count == 0
            else round(fixed_1r_count / midpoint_count, 8)
        ),
        "automatic_winner_selection": False,
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
    parser.add_argument("market", choices=[item.value for item in FX_MARKETS])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    arms, report = run_lab(market)
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
    print("CRT_R2AL_STRUCTURAL_TARGET_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
