"""R2-AA historical validation of the AUDUSD one-day-efficiency regime.

Frozen before 2018-2020 outcomes are observed.

Primary:
    0.10 <= one-day trend efficiency < 0.20

No neighboring band is evaluated. Failure of the primary reopens AUDUSD regime
research rather than moving the threshold.

CRT execution methodology and R2-G competition are unchanged.
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

IDENTITY = "VT08_CRT_PURE_R2AA_AUDUSD_EFF1D_VALIDATION_001"
SCHEMA = "qore.vt08.crt_pure.r2aa_audusd_eff1d_validation.v1"
MARKET = CrtPureMarket.AUDUSD
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST

START = datetime(2018, 9, 21, 0, 0, tzinfo=UTC)
FOLD = datetime(2019, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
FETCH_START = START - timedelta(days=25)

LOW = Decimal("0.10")
HIGH = Decimal("0.20")

MIN_TRADES = 24
MIN_PF = 1.05
MAX_DD_R = 12.0


def _accept(efficiency_1d: Decimal) -> bool:
    return LOW <= efficiency_1d < HIGH


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


def _gate(
    full: dict[str, Any],
    year_1: dict[str, Any],
    year_2: dict[str, Any],
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
    if float(year_1["total_r"]) <= 0:
        failures.append("YEAR1_R")
    if float(year_2["total_r"]) <= 0:
        failures.append("YEAR2_R")
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
        "no_selected_hypothesis": 0,
        "invalid_risk_geometry": 0,
        "rejected_by_eff1d": 0,
        "trade_created": 0,
    }

    for parent in parents:
        diagnostics["parent_count"] += 1
        context = _context(parent=parent, m15=m15, times=times)
        if context is None:
            diagnostics["insufficient_context"] += 1
            continue
        if not _accept(context[2]):
            diagnostics["rejected_by_eff1d"] += 1
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
    year_1 = _summary(_window(frozen, START, FOLD))
    year_2 = _summary(_window(frozen, FOLD, END))
    survived, failures = _gate(full, year_1, year_2)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "validation_start": START.isoformat(),
        "validation_fold": FOLD.isoformat(),
        "validation_end_exclusive": END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "candidate": "AUD_EFF1D_010_020",
        "efficiency_bounds": [str(LOW), str(HIGH)],
        "candidate_frozen_before_validation_results": True,
        "neighbor_replacement_forbidden": True,
        "research_gate": {
            "min_trades": MIN_TRADES,
            "min_profit_factor": MIN_PF,
            "max_drawdown_r": MAX_DD_R,
            "total_r_must_be_positive": True,
            "each_year_total_r_must_be_positive": True,
        },
        "diagnostics": diagnostics,
        "full_2y": full,
        "year_1": year_1,
        "year_2": year_2,
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
    print("CRT_R2AA_AUDUSD_VALIDATION_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
