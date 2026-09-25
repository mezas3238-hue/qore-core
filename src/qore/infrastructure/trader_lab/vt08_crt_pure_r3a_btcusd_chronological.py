"""R3-A chronological certification replay for frozen BTCUSD REF2_PLUS.

Exact candidate:
- CRT PURE parent/execution methodology unchanged;
- R2-G NEWEST_SUPERSEDES_CONFIRMATION_FIRST competition;
- selected Model #1 source has reference_count >= 2.

The candidate was frozen before this 9Y aggregate certification replay. All
underlying periods have already been individually consumed; this run verifies
chronological consistency and the predeclared engineering certification gate.

Research/certification only. No runtime or capital authority.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2m_survivor_robustness import (
    _stress_summary,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_BTCUSD_R3A_CHRONOLOGICAL_001"
CANDIDATE_IDENTITY = "VT08_CRT_PURE_BTCUSD_R3_REF2_PLUS_001"
SCHEMA = "qore.vt08.crt_pure.r3a_btcusd_chronological.v1"
MARKET = CrtPureMarket.BTCUSD
BINDING = CandidateId.BTC_REF2_PLUS

START = datetime(2017, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)

YEAR_BOUNDARIES: tuple[datetime, ...] = tuple(
    datetime(year, 9, 21, 0, 0, tzinfo=UTC)
    for year in range(2017, 2027)
)

MIN_TRADES = 250
MIN_PF = 1.40
MAX_DD_R = 8.0
COST_005_MIN_PF = 1.20


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


def _annual_windows(rows: tuple[Model1LabTrade, ...]) -> dict[str, dict[str, Any]]:
    return {
        f"{left.year}_{right.year}": _summary(_window(rows, left, right))
        for left, right in zip(
            YEAR_BOUNDARIES[:-1],
            YEAR_BOUNDARIES[1:],
            strict=True,
        )
    }


def _rolling_2y(rows: tuple[Model1LabTrade, ...]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index in range(len(YEAR_BOUNDARIES) - 2):
        left = YEAR_BOUNDARIES[index]
        right = YEAR_BOUNDARIES[index + 2]
        result[f"{left.year}_{right.year}"] = _summary(_window(rows, left, right))
    return result


def _retag(trade: Model1LabTrade) -> Model1LabTrade:
    return Model1LabTrade(
        schema=SCHEMA,
        identity=CANDIDATE_IDENTITY,
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


def _chronological_gate(
    *,
    full: dict[str, Any],
    annual: dict[str, dict[str, Any]],
    rolling: dict[str, dict[str, Any]],
    cost_005: dict[str, Any],
    cost_010: dict[str, Any],
) -> tuple[bool, tuple[str, ...]]:
    failures: list[str] = []
    if int(full["trades"]) < MIN_TRADES:
        failures.append("MIN_TRADES")
    pf = full["profit_factor"]
    if pf is None or float(pf) < MIN_PF:
        failures.append("MIN_PF")
    if float(full["total_r"]) <= 0:
        failures.append("TOTAL_R")
    if float(full["max_drawdown_r"]) > MAX_DD_R:
        failures.append("MAX_DD")
    if any(float(item["total_r"]) <= 0 for item in annual.values()):
        failures.append("ANNUAL_STABILITY")
    if any(float(item["total_r"]) <= 0 for item in rolling.values()):
        failures.append("ROLLING_2Y_STABILITY")
    pf005 = cost_005["profit_factor"]
    if (
        float(cost_005["total_r"]) <= 0
        or pf005 is None
        or float(pf005) < COST_005_MIN_PF
    ):
        failures.append("COST_005")
    if float(cost_010["total_r"]) <= 0:
        failures.append("COST_010")
    return not failures, tuple(failures)


def run_replay() -> tuple[tuple[Model1LabTrade, ...], dict[str, Any]]:
    bars = load_m5_window(MARKET, start=START, end_exclusive=END)
    parents = build_parent_crts_for_window(
        MARKET,
        bars,
        start=START,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    trades: list[Model1LabTrade] = []
    diagnostics = {
        "parent_count": 0,
        "no_selected_hypothesis": 0,
        "invalid_risk_geometry": 0,
        "candidate_rejected": 0,
        "trade_created": 0,
    }

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

        observation, confirmation, entry = selected
        context = CandidateContext(
            parent=parent,
            observation=observation,
            confirmation=confirmation,
            entry=entry,
            generation=observations.index(observation) + 1,
        )
        if not _accept(BINDING, context):
            diagnostics["candidate_rejected"] += 1
            continue

        trade = _resolve_trade(
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if trade is None:
            diagnostics["invalid_risk_geometry"] += 1
            continue
        trades.append(_retag(trade))
        diagnostics["trade_created"] += 1

    frozen = tuple(sorted(trades, key=lambda item: item.entry_opened_at))
    full = _summary(frozen)
    annual = _annual_windows(frozen)
    rolling = _rolling_2y(frozen)
    cost_002 = _stress_summary(frozen, 0.02)
    cost_005 = _stress_summary(frozen, 0.05)
    cost_010 = _stress_summary(frozen, 0.10)
    passed, failures = _chronological_gate(
        full=full,
        annual=annual,
        rolling=rolling,
        cost_005=cost_005,
        cost_010=cost_010,
    )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate_identity": CANDIDATE_IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "candidate_binding": BINDING.value,
        "candidate_frozen_before_r3": True,
        "diagnostics": diagnostics,
        "full_9y": full,
        "annual": annual,
        "rolling_2y": rolling,
        "cost_stress": {
            "COST_0_02R": cost_002,
            "COST_0_05R": cost_005,
            "COST_0_10R": cost_010,
        },
        "chronological_gate": {
            "min_trades": MIN_TRADES,
            "min_profit_factor": MIN_PF,
            "max_drawdown_r": MAX_DD_R,
            "all_annual_windows_positive": True,
            "all_rolling_2y_windows_positive": True,
            "cost_0_05_min_pf": COST_005_MIN_PF,
            "cost_0_05_total_r_positive": True,
            "cost_0_10_total_r_positive": True,
        },
        "chronological_gate_passed": passed,
        "chronological_gate_failures": list(failures),
        "block_bootstrap_required_next": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "research_only": True,
    }
    return frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    trades, report = run_replay()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")
    print("CRT_R3A_BTC_CHRONO_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
