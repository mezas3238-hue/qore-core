"""R2-BE AUDUSD frozen-candidate 15Y robustness characterization.

Candidate is unchanged from R2-BB:
- ROLLING_H4
- FIXED_1_5R
- exclude confirmation overlap 0.50 <= overlap < 0.75
- BE_CLOSE_075
- C3-close expiry
- NEWEST_SUPERSEDES_CONFIRMATION_FIRST
- one selected hypothesis max per parent

Evidence window combines already-consumed development and passed untouched
historical holdout: 2011-09-21 -> 2026-09-21.

Robustness families:
- annual + rolling-2Y start-subwindows;
- deterministic per-trade cost perturbation: 0.02 / 0.05 / 0.10R;
- deterministic circular-block resampling: lengths 2 / 4 / 8, 5,000 draws.

No new candidate selection or certification threshold is introduced here.
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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2m_survivor_robustness import (
    _stress_summary,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2o_btcusd_block_robustness import (
    _distribution,
    _policy,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2BE_AUDUSD_FROZEN_CANDIDATE_ROBUSTNESS_001"
SCHEMA = "qore.vt08.crt_pure.r2be_audusd_frozen_candidate_robustness.v1"
MARKET = CrtPureMarket.AUDUSD
START = datetime(2011, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
YEARS = 15
ARM = TargetArm.FIXED_1_5R
MULTIPLE = TARGET_MULTIPLE[ARM]
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
PROTECTION = ProtectionPolicy.BE_CLOSE_075
EXCLUDED_DIMENSION = "confirmation_source_overlap"
EXCLUDED_LABEL = "CONFOVERLAP_0_50_TO_0_75"
COST_STRESS_R: tuple[float, ...] = (0.02, 0.05, 0.10)
BLOCK_LENGTHS: tuple[int, ...] = (2, 4, 8)


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


def build_populations() -> tuple[
    dict[str, tuple[Model1LabTrade, ...]],
    dict[str, int],
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
    diagnostics: dict[str, int] = defaultdict(int)
    diagnostics["parent_count"] = len(parents)
    control: list[Model1LabTrade] = []
    candidate: list[Model1LabTrade] = []

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
        trade = _resolve_fixed_target(
            arm=ARM,
            multiple=MULTIPLE,
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry_bar,
            c3_m15=c3_m15,
        )
        if trade is None:
            diagnostics["invalid_structural_geometry"] += 1
            continue

        managed = _simulate(
            trade=trade,
            bars=_lifecycle_bars(
                trade=trade,
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

    return (
        {
            "CONTROL_BE075": tuple(
                sorted(control, key=lambda trade: trade.entry_opened_at)
            ),
            "OVERLAP_CANDIDATE": tuple(
                sorted(candidate, key=lambda trade: trade.entry_opened_at)
            ),
        },
        dict(diagnostics),
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


def _subwindows(
    rows: tuple[Model1LabTrade, ...],
) -> tuple[dict[str, Any], dict[str, Any]]:
    annual: dict[str, Any] = {}
    rolling_2y: dict[str, Any] = {}
    for year in range(START.year, END.year):
        left = datetime(year, 9, 21, 0, 0, tzinfo=UTC)
        right = datetime(year + 1, 9, 21, 0, 0, tzinfo=UTC)
        annual[f"{year}_{year + 1}"] = _summary(_window(rows, left, right))
    for year in range(START.year, END.year - 1):
        left = datetime(year, 9, 21, 0, 0, tzinfo=UTC)
        right = datetime(year + 2, 9, 21, 0, 0, tzinfo=UTC)
        rolling_2y[f"{year}_{year + 2}"] = _summary(
            _window(rows, left, right)
        )
    return annual, rolling_2y


def _population_report(
    rows: tuple[Model1LabTrade, ...],
) -> dict[str, Any]:
    annual, rolling_2y = _subwindows(rows)
    return {
        "full_15y": _summary(rows),
        "trades_per_year": round(len(rows) / YEARS, 8),
        "start_subwindow": {
            "annual": annual,
            "rolling_2y": rolling_2y,
            "positive_annual_windows": sum(
                float(item["total_r"]) > 0 for item in annual.values()
            ),
            "annual_window_count": len(annual),
            "positive_rolling_2y_windows": sum(
                float(item["total_r"]) > 0 for item in rolling_2y.values()
            ),
            "rolling_2y_window_count": len(rolling_2y),
        },
        "cost_perturbation": {
            "costs_frozen_before_results": True,
            "stress": {
                f"COST_{cost:.2f}R": _stress_summary(rows, cost)
                for cost in COST_STRESS_R
            },
        },
        "block_bootstrap": {
            "resampling_engine": "QORE_RESEARCH_CIRCULAR_BLOCK_DRAW_STREAM",
            "block_lengths": list(BLOCK_LENGTHS),
            "resample_count": 5000,
            "policies": {
                f"BLOCK_{length}": _distribution(rows, _policy(length))
                for length in BLOCK_LENGTHS
            },
        },
    }


def run_robustness() -> tuple[
    dict[str, tuple[Model1LabTrade, ...]],
    dict[str, Any],
]:
    populations, diagnostics = build_populations()
    reports = {
        name: _population_report(rows)
        for name, rows in populations.items()
    }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "years": YEARS,
        "comparison_frozen_before_results": True,
        "control_definition": {
            "timing": "ROLLING_H4",
            "target": ARM.value,
            "competition": BASE_POLICY.value,
            "confirmation_exclusion": "NONE",
            "protection": PROTECTION.value,
            "expiry": "C3_CLOSE",
        },
        "candidate_frozen_from": "R2_BB",
        "candidate_definition": {
            "timing": "ROLLING_H4",
            "target": ARM.value,
            "competition": BASE_POLICY.value,
            "excluded_dimension": EXCLUDED_DIMENSION,
            "excluded_label": EXCLUDED_LABEL,
            "protection": PROTECTION.value,
            "expiry": "C3_CLOSE",
        },
        "diagnostics": diagnostics,
        "populations": reports,
        "automatic_winner_ranking": False,
        "qualification_thresholds_imposed": False,
        "candidate_certified": False,
        "research_only": True,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return populations, report

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    populations, report = run_robustness()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "source_trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for population, trades in populations.items():
            for trade in trades:
                row = asdict(trade)
                row["population"] = population
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2BE_ROBUSTNESS_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
