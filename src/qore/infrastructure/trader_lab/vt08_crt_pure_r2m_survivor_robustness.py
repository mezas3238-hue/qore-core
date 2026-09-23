"""R2-M robustness characterization for R2-J survivor candidates.

This lab reuses QORE Trader Lab robustness family identities for two concrete
market-specific evaluators:

- START_SUBWINDOW: annual and rolling-2Y slices over the four consumed years;
- COST_PERTURBATION: deterministic per-trade R deductions.

Candidate definitions are imported unchanged from R2-J. No survivor properties
are combined and no winner ranking is performed.

Research only. This is not Trader Lab certification and grants no capital/runtime
authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.robustness import TraderLabRobustnessFamily
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    BASE_POLICY,
    CandidateContext,
    CandidateId,
    _accept,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2M_SURVIVOR_ROBUSTNESS_001"
SCHEMA = "qore.vt08.crt_pure.r2m_survivor_robustness.v1"

START = datetime(2022, 9, 21, 0, 0, tzinfo=UTC)
Y1_END = datetime(2023, 9, 21, 0, 0, tzinfo=UTC)
Y2_END = datetime(2024, 9, 21, 0, 0, tzinfo=UTC)
Y3_END = datetime(2025, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)

SURVIVORS: dict[CrtPureMarket, tuple[CandidateId, ...]] = {
    CrtPureMarket.AUDUSD: (CandidateId.AUD_G1,),
    CrtPureMarket.BTCUSD: (
        CandidateId.CONTROL,
        CandidateId.BTC_BEARISH,
        CandidateId.BTC_BODY_GE_050,
        CandidateId.BTC_REF2_PLUS,
    ),
}

START_SUBWINDOWS: tuple[tuple[str, datetime, datetime], ...] = (
    ("Y2022_23", START, Y1_END),
    ("Y2023_24", Y1_END, Y2_END),
    ("Y2024_25", Y2_END, Y3_END),
    ("Y2025_26", Y3_END, END),
    ("ROLL2_2022_24", START, Y2_END),
    ("ROLL2_2023_25", Y1_END, Y3_END),
    ("ROLL2_2024_26", Y2_END, END),
)

COST_STRESS_R: tuple[float, ...] = (0.02, 0.05, 0.10)


def _candidate_trades(
    market: CrtPureMarket,
) -> dict[CandidateId, tuple[Model1LabTrade, ...]]:
    bars = load_m5_window(market, start=START, end_exclusive=END)
    parents = build_parent_crts_for_window(
        market,
        bars,
        start=START,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    rows: dict[CandidateId, list[Model1LabTrade]] = {
        candidate: [] for candidate in SURVIVORS[market]
    }

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
            continue
        observation, confirmation, entry = selected
        context = CandidateContext(
            parent=parent,
            observation=observation,
            confirmation=confirmation,
            entry=entry,
            generation=observations.index(observation) + 1,
        )
        trade = _resolve_trade(
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if trade is None:
            continue
        for candidate in SURVIVORS[market]:
            if _accept(candidate, context):
                rows[candidate].append(trade)

    return {
        candidate: tuple(sorted(trades, key=lambda trade: trade.entry_opened_at))
        for candidate, trades in rows.items()
    }


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


def _stress_summary(
    rows: tuple[Model1LabTrade, ...],
    cost_r: float,
) -> dict[str, Any]:
    values = tuple(float(row.r_multiple) - cost_r for row in rows)
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    flat = len(values) - wins - losses
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    profit_factor = None if gross_loss == 0 else gross_profit / gross_loss

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    streak = 0
    longest_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if value < 0:
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0

    return {
        "trades": len(values),
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "profit_factor": None if profit_factor is None else round(profit_factor, 8),
        "total_r": round(sum(values), 8),
        "mean_r": 0.0 if not values else round(sum(values) / len(values), 8),
        "max_drawdown_r": round(max_drawdown, 8),
        "longest_losing_streak": longest_streak,
        "cost_r_per_trade": cost_r,
    }


def run_robustness(
    market: CrtPureMarket,
) -> tuple[dict[CandidateId, tuple[Model1LabTrade, ...]], dict[str, Any]]:
    if market not in SURVIVORS:
        raise ValueError(f"market has no R2-J survivor family: {market.value}")

    candidates = _candidate_trades(market)
    reports: dict[str, Any] = {}

    for candidate, rows in candidates.items():
        windows = {
            label: _summary(_window(rows, start, end))
            for label, start, end in START_SUBWINDOWS
        }
        annual_labels = ("Y2022_23", "Y2023_24", "Y2024_25", "Y2025_26")
        rolling_labels = (
            "ROLL2_2022_24",
            "ROLL2_2023_25",
            "ROLL2_2024_26",
        )
        annual_positive = sum(
            float(windows[label]["total_r"]) > 0 for label in annual_labels
        )
        rolling_positive = sum(
            float(windows[label]["total_r"]) > 0 for label in rolling_labels
        )

        reports[candidate.value] = {
            "full_4y": _summary(rows),
            "start_subwindow": {
                "family": TraderLabRobustnessFamily.START_SUBWINDOW.value,
                "windows": windows,
                "positive_annual_windows": annual_positive,
                "annual_window_count": len(annual_labels),
                "positive_rolling_2y_windows": rolling_positive,
                "rolling_2y_window_count": len(rolling_labels),
                "automatic_qualification": False,
            },
            "cost_perturbation": {
                "family": TraderLabRobustnessFamily.COST_PERTURBATION.value,
                "stress": {
                    f"COST_{cost_r:.2f}R": _stress_summary(rows, cost_r)
                    for cost_r in COST_STRESS_R
                },
                "costs_frozen_before_results": True,
                "automatic_qualification": False,
            },
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "candidate_family": [candidate.value for candidate in SURVIVORS[market]],
        "candidate_definitions_reused_from_r2j": True,
        "candidate_properties_combined": False,
        "start_subwindows_frozen_before_results": True,
        "cost_stress_r": list(COST_STRESS_R),
        "candidates": reports,
        "automatic_winner_ranking": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return candidates, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "market",
        choices=[market.value for market in SURVIVORS],
    )
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    candidates, report = run_robustness(market)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for candidate in SURVIVORS[market]:
            for trade in candidates[candidate]:
                row = asdict(trade)
                row["candidate_id"] = candidate.value
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2M_ROBUSTNESS_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
