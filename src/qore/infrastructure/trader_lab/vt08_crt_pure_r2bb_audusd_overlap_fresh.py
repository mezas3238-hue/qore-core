"""R2-BB AUDUSD untouched historical validation of the frozen overlap candidate.

Candidate frozen from consumed 2016-2026 evidence before opening this holdout:

High-density core:
- ROLLING_H4
- FIXED_1_5R
- no EFF gate
- NEWEST_SUPERSEDES_CONFIRMATION_FIRST
- one selected hypothesis max per parent
- structural source stop

Selection:
- exclude confirmation_source_overlap == CONFOVERLAP_0_50_TO_0_75

Protection:
- BE_CLOSE_075 from R2-AZ
- close-confirmed, effective next M15 only
- stop never widens

Fresh historical validation window:
- 2011-09-21 -> 2016-09-21
- no thresholds or rules may be changed after results.

Research only.
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
    M15Bar,
    Model1LabTrade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TARGET_MULTIPLE,
    TargetArm,
    _resolve_fixed_target,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aq_high_density_historical_validation import (
    ValidationWindow,
    _rolling_parents,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ax_audusd_confirmation_geometry_atlas import (
    _features,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2az_audusd_protection_family import (
    ProtectionPolicy,
    _simulate,
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
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2BB_AUDUSD_OVERLAP_FRESH_2011_2016_001"
SCHEMA = "qore.vt08.crt_pure.r2bb_audusd_overlap_fresh_2011_2016.v1"
MARKET = CrtPureMarket.AUDUSD
START = datetime(2011, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2016, 9, 21, 0, 0, tzinfo=UTC)
ARM = TargetArm.FIXED_1_5R
MULTIPLE = TARGET_MULTIPLE[ARM]
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
PROTECTION = ProtectionPolicy.BE_CLOSE_075
EXCLUDED_DIMENSION = "confirmation_source_overlap"
EXCLUDED_LABEL = "CONFOVERLAP_0_50_TO_0_75"
YEARS = 5


def _lifecycle_bars(
    *,
    trade: Model1LabTrade,
    m15_by_time: dict[datetime, M15Bar],
) -> tuple[M15Bar, ...]:
    entry = datetime.fromisoformat(trade.entry_opened_at)
    c3_close = datetime.fromisoformat(trade.c3_opened_at) + timedelta(hours=4)
    return tuple(
        m15_by_time[opened_at]
        for opened_at in sorted(m15_by_time)
        if entry <= opened_at < c3_close
    )


def _annual(
    trades: tuple[Model1LabTrade, ...],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for year in range(START.year, END.year):
        left = datetime(year, 9, 21, 0, 0, tzinfo=UTC)
        right = datetime(year + 1, 9, 21, 0, 0, tzinfo=UTC)
        rows = tuple(
            trade
            for trade in trades
            if left <= datetime.fromisoformat(trade.entry_opened_at) < right
        )
        result[f"{year}_{year + 1}"] = _summary(rows)
    return result


def run_validation() -> tuple[
    tuple[Model1LabTrade, ...],
    tuple[Model1LabTrade, ...],
    dict[str, Any],
]:
    window = ValidationWindow(market=MARKET, start=START, end=END)
    bars = load_m5_window(
        MARKET,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=1),
    )
    parents = _rolling_parents(
        market=MARKET,
        bars=bars,
        window=window,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    control: list[Model1LabTrade] = []
    candidate: list[Model1LabTrade] = []
    diagnostics: dict[str, int] = defaultdict(int)
    diagnostics["parent_count"] = len(parents)

    for parent in parents:
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

        observation, confirmation, entry_bar = selected
        base_trade = _resolve_fixed_target(
            arm=ARM,
            multiple=MULTIPLE,
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry_bar,
            c3_m15=c3_m15,
        )
        if base_trade is None:
            diagnostics["invalid_structural_geometry"] += 1
            continue

        managed = _simulate(
            trade=base_trade,
            bars=_lifecycle_bars(
                trade=base_trade,
                m15_by_time=m15_by_time,
            ),
            policy=PROTECTION,
        )
        control.append(managed)
        diagnostics["control_trade_created"] += 1

        feature_map = dict(
            _features(
                parent=parent,
                source=observation.group.source_candle,
                confirmation=confirmation,
                entry_bar=entry_bar,
            )
        )
        if feature_map[EXCLUDED_DIMENSION] == EXCLUDED_LABEL:
            diagnostics["excluded_overlap_state"] += 1
            continue

        candidate.append(managed)
        diagnostics["candidate_trade_created"] += 1

    control_frozen = tuple(
        sorted(control, key=lambda trade: trade.entry_opened_at)
    )
    candidate_frozen = tuple(
        sorted(candidate, key=lambda trade: trade.entry_opened_at)
    )
    control_annual = _annual(control_frozen)
    candidate_annual = _annual(candidate_frozen)
    control_summary = _summary(control_frozen)
    candidate_summary = _summary(candidate_frozen)

    candidate_tpy = len(candidate_frozen) / YEARS
    positive_fraction = (
        sum(float(item["total_r"]) > 0 for item in candidate_annual.values())
        / YEARS
    )

    gate = {
        "density_pass": candidate_tpy >= 170,
        "pf_pass": (
            candidate_summary["profit_factor"] is not None
            and float(candidate_summary["profit_factor"]) >= 1.05
        ),
        "total_r_pass": float(candidate_summary["total_r"]) > 0,
        "temporal_breadth_pass": positive_fraction >= 0.60,
        "drawdown_pass": (
            float(candidate_summary["max_drawdown_r"])
            <= float(control_summary["max_drawdown_r"])
        ),
    }
    gate["all_pass"] = all(gate.values())

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "window_status": "UNTOUCHED_BEFORE_R2_BB",
        "candidate_frozen_before_holdout": True,
        "core": {
            "timing": "ROLLING_H4",
            "target": ARM.value,
            "competition": BASE_POLICY.value,
            "efficiency_filter": "OFF",
            "protection": PROTECTION.value,
        },
        "selection": {
            "exclude_dimension": EXCLUDED_DIMENSION,
            "exclude_label": EXCLUDED_LABEL,
            "provenance": "R2_AX_2016_2026_CONSUMED_ATLAS",
        },
        "diagnostics": dict(diagnostics),
        "control": {
            "full_5y": control_summary,
            "annual": control_annual,
            "trades_per_year": round(len(control_frozen) / YEARS, 8),
        },
        "candidate": {
            "full_5y": candidate_summary,
            "annual": candidate_annual,
            "trades_per_year": round(candidate_tpy, 8),
            "retention_vs_control": (
                None
                if not control_frozen
                else round(len(candidate_frozen) / len(control_frozen), 8)
            ),
            "positive_year_fraction": round(positive_fraction, 8),
        },
        "advancement_gate": gate,
        "automatic_promotion": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return control_frozen, candidate_frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    control, candidate, report = run_validation()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for population, trades in (
            ("CONTROL", control),
            ("CANDIDATE", candidate),
        ):
            for trade in trades:
                row = asdict(trade)
                row["population"] = population
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2BB_FRESH_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
