"""R2-AE older validation for frozen USDJPY reclaim candidate.

Candidate frozen before this window:
- EFF5D 0.10 <= efficiency < 0.20;
- exclude reclaim depth 0.25 <= depth < 0.50;
- R2-G NEWEST_SUPERSEDES_CONFIRMATION_FIRST.

Validation window: 2014-09-21 -> 2018-09-21.
No neighbor thresholds or fallback candidates are evaluated.
"""

from __future__ import annotations

import argparse
import json
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

IDENTITY = "VT08_CRT_PURE_R2AE_USDJPY_RECLAIM_VALIDATION_001"
SCHEMA = "qore.vt08.crt_pure.r2ae_usdjpy_reclaim_validation.v1"
CANDIDATE = "USD_EFF5D_010_020_EXCLUDE_RECLAIM_025_050"
MARKET = CrtPureMarket.USDJPY
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST

START = datetime(2014, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2018, 9, 21, 0, 0, tzinfo=UTC)
FETCH_START = START - timedelta(days=25)
YEAR_BOUNDARIES: tuple[datetime, ...] = tuple(
    datetime(year, 9, 21, 0, 0, tzinfo=UTC)
    for year in range(2014, 2019)
)

EFF5_LOW = Decimal("0.10")
EFF5_HIGH = Decimal("0.20")
RECLAIM_LOW = Decimal("0.25")
RECLAIM_HIGH = Decimal("0.50")

MIN_TRADES = 12
MIN_PF = 1.05
MAX_DD_R = 8.0


def _accepted_context(context: tuple[Any, ...]) -> bool:
    efficiency_5d = context[3]
    reclaim_depth = context[13]
    in_eff = EFF5_LOW <= efficiency_5d < EFF5_HIGH
    excluded_reclaim = RECLAIM_LOW <= reclaim_depth < RECLAIM_HIGH
    return bool(in_eff and not excluded_reclaim)


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


def _gate(
    full: dict[str, Any],
    annual: dict[str, dict[str, Any]],
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
    return not failures, tuple(failures)


def run_validation() -> tuple[tuple[Model1LabTrade, ...], dict[str, Any]]:
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

    rows: list[Model1LabTrade] = []
    diagnostics = {
        "parent_count": 0,
        "insufficient_context": 0,
        "rejected_by_frozen_context": 0,
        "no_selected_hypothesis": 0,
        "invalid_risk_geometry": 0,
        "trade_created": 0,
    }

    for parent in parents:
        diagnostics["parent_count"] += 1
        context = _context(parent=parent, m15=m15, times=times)
        if context is None:
            diagnostics["insufficient_context"] += 1
            continue
        if not _accepted_context(context):
            diagnostics["rejected_by_frozen_context"] += 1
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
        rows.append(trade)
        diagnostics["trade_created"] += 1

    frozen = tuple(sorted(rows, key=lambda item: item.entry_opened_at))
    full = _summary(frozen)
    annual = _annual(frozen)
    survived, failures = _gate(full, annual)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": CANDIDATE,
        "market": MARKET.value,
        "validation_start": START.isoformat(),
        "validation_end_exclusive": END.isoformat(),
        "candidate_frozen_before_validation_results": True,
        "eff5_bounds": [str(EFF5_LOW), str(EFF5_HIGH)],
        "excluded_reclaim_bounds": [str(RECLAIM_LOW), str(RECLAIM_HIGH)],
        "neighbor_replacement_forbidden": True,
        "diagnostics": diagnostics,
        "full_4y": full,
        "annual": annual,
        "research_gate": {
            "min_trades": MIN_TRADES,
            "min_profit_factor": MIN_PF,
            "max_drawdown_r": MAX_DD_R,
            "all_annual_windows_positive": True,
        },
        "survived_research_gate": survived,
        "gate_failures": list(failures),
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

    trades, report = run_validation()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")
    print("CRT_R2AE_USDJPY_VALIDATION_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
