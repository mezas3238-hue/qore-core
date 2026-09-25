"""R2-W historical validation of the USDJPY five-day-efficiency regime.

Frozen before 2018-2020 outcomes are observed.

Primary:
    0.10 <= five-day trend efficiency < 0.20

Neighborhoods are predeclared only to test boundary sensitivity. A neighbor
cannot replace a failed primary candidate.

The CRT execution methodology and R2-G competition policy are unchanged.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
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

IDENTITY = "VT08_CRT_PURE_R2W_USDJPY_EFF5D_VALIDATION_001"
SCHEMA = "qore.vt08.crt_pure.r2w_usdjpy_eff5d_validation.v1"
MARKET = CrtPureMarket.USDJPY
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST

START = datetime(2018, 9, 21, 0, 0, tzinfo=UTC)
FOLD = datetime(2019, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
FETCH_START = START - timedelta(days=25)

MIN_TRADES = 12
MIN_PF = 1.05
MAX_DD_R = 12.0


class Candidate(StrEnum):
    CONTROL = "CONTROL"
    EFF5D_010_020_PRIMARY = "EFF5D_010_020_PRIMARY"
    EFF5D_008_020 = "EFF5D_008_020"
    EFF5D_010_022 = "EFF5D_010_022"
    EFF5D_008_022 = "EFF5D_008_022"


FAMILY: tuple[Candidate, ...] = (
    Candidate.CONTROL,
    Candidate.EFF5D_010_020_PRIMARY,
    Candidate.EFF5D_008_020,
    Candidate.EFF5D_010_022,
    Candidate.EFF5D_008_022,
)

BOUNDS: dict[Candidate, tuple[Decimal, Decimal] | None] = {
    Candidate.CONTROL: None,
    Candidate.EFF5D_010_020_PRIMARY: (Decimal("0.10"), Decimal("0.20")),
    Candidate.EFF5D_008_020: (Decimal("0.08"), Decimal("0.20")),
    Candidate.EFF5D_010_022: (Decimal("0.10"), Decimal("0.22")),
    Candidate.EFF5D_008_022: (Decimal("0.08"), Decimal("0.22")),
}


def _bounds_text(candidate: Candidate) -> str:
    bounds = BOUNDS[candidate]
    if bounds is None:
        return f"{candidate.value}:ALL"
    low, high = bounds
    return f"{candidate.value}:{low}:{high}"


FAMILY_MANIFEST = "|".join(_bounds_text(candidate) for candidate in FAMILY)
FAMILY_DIGEST = sha256(FAMILY_MANIFEST.encode("utf-8")).hexdigest()


def _accept(candidate: Candidate, efficiency: Decimal) -> bool:
    bounds = BOUNDS[candidate]
    if bounds is None:
        return True
    low, high = bounds
    return low <= efficiency < high


def _retag(trade: Model1LabTrade, candidate: Candidate) -> Model1LabTrade:
    return Model1LabTrade(
        schema=SCHEMA,
        identity=f"{IDENTITY}:{candidate.value}",
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


def _bounds_payload(candidate: Candidate) -> list[str] | None:
    bounds = BOUNDS[candidate]
    if bounds is None:
        return None
    low, high = bounds
    return [str(low), str(high)]


def run_validation() -> tuple[
    dict[Candidate, tuple[Model1LabTrade, ...]],
    dict[str, Any],
]:
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

    rows: dict[Candidate, list[Model1LabTrade]] = {
        candidate: [] for candidate in FAMILY
    }
    diagnostics: dict[str, int] = {
        "parent_count": 0,
        "insufficient_context": 0,
        "no_selected_hypothesis": 0,
        "invalid_risk_geometry": 0,
        "trade_classified": 0,
    }

    for parent in parents:
        diagnostics["parent_count"] += 1
        context = _context(parent=parent, m15=m15, times=times)
        if context is None:
            diagnostics["insufficient_context"] += 1
            continue
        efficiency_5d = context[3]

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

        diagnostics["trade_classified"] += 1
        for candidate in FAMILY:
            if _accept(candidate, efficiency_5d):
                rows[candidate].append(_retag(trade, candidate))

    frozen = {
        candidate: tuple(sorted(trades, key=lambda item: item.entry_opened_at))
        for candidate, trades in rows.items()
    }

    arms: dict[str, Any] = {}
    survivors: list[str] = []
    for candidate in FAMILY:
        trades = frozen[candidate]
        full = _summary(trades)
        year_1 = _summary(_window(trades, START, FOLD))
        year_2 = _summary(_window(trades, FOLD, END))
        survived, failures = _gate(full, year_1, year_2)
        if survived:
            survivors.append(candidate.value)
        arms[candidate.value] = {
            "bounds": _bounds_payload(candidate),
            "full_2y": full,
            "year_1": year_1,
            "year_2": year_2,
            "survived_research_gate": survived,
            "gate_failures": list(failures),
        }

    primary = arms[Candidate.EFF5D_010_020_PRIMARY.value]
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "validation_start": START.isoformat(),
        "validation_fold": FOLD.isoformat(),
        "validation_end_exclusive": END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "family": [candidate.value for candidate in FAMILY],
        "family_manifest": FAMILY_MANIFEST,
        "family_digest": FAMILY_DIGEST,
        "family_frozen_before_validation_results": True,
        "primary_candidate": Candidate.EFF5D_010_020_PRIMARY.value,
        "primary_survived": bool(primary["survived_research_gate"]),
        "neighbor_survival_cannot_replace_primary_failure": True,
        "research_gate": {
            "min_trades": MIN_TRADES,
            "min_profit_factor": MIN_PF,
            "max_drawdown_r": MAX_DD_R,
            "total_r_must_be_positive": True,
            "each_half_total_r_must_be_positive": True,
        },
        "diagnostics": diagnostics,
        "arms": arms,
        "survivors": survivors,
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

    family, report = run_validation()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for candidate in FAMILY:
            for trade in family[candidate]:
                row = asdict(trade)
                row["candidate_id"] = candidate.value
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2W_USDJPY_VALIDATION_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
