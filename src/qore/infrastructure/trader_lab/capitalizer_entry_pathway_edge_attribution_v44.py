"""Entry-pathway edge attribution audit for Capitalizer V44.

Diagnostic architecture audit only.

V44 joins the already-frozen causal entry provenance retained by V38 selected
geometry to the exact reconstructed selected portfolio ledgers.  It measures
where edge is created or destroyed without changing admission, sizing,
protection, stop, target, density, or any runtime decision.

The scientific contract was frozen in PR #623 comment 5882972050 before V44
code/economics.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_separability_v38 as v38,
)

IDENTITY = "QORE_CAPITALIZER_ENTRY_PATHWAY_EDGE_ATTRIBUTION_V44"
PREDECLARATION_COMMENT_ID = 5882972050

PERIOD_SPECS = (
    (
        "DEVELOPMENT_2024_2026",
        "development",
        date(2024, 9, 17),
        date(2026, 9, 17),
        948,
    ),
    (
        "CONSUMED_VALIDATION_2022_2024",
        "validation",
        date(2022, 9, 17),
        date(2024, 9, 17),
        1034,
    ),
    (
        "CONSUMED_RESERVED_2020_2022",
        "reserved",
        date(2020, 9, 17),
        date(2022, 9, 17),
        1088,
    ),
)

MIN_TRADES = 30
MIN_WINS = 10
MIN_LOSSES = 10


@dataclass(frozen=True, slots=True)
class PathwayMetrics:
    period: str
    window_start: str
    window_end_exclusive: str
    provenance: str
    trades: int
    wins: int
    losses: int
    flats: int
    gross_positive_r: str
    gross_negative_r_abs: str
    total_r: str
    expectancy_r_per_trade: str
    profit_factor: str | None
    average_winner_r: str | None
    average_loser_r_abs: str | None
    payoff_ratio: str | None
    stops: int
    stop_rate: str
    targets: int
    target_rate: str
    other_exits: int
    entrant_share: str
    portfolio_gross_positive_share: str | None
    portfolio_gross_negative_share: str | None
    portfolio_total_r_share: str | None
    diagnostic_sample_sufficient: bool


@dataclass(frozen=True, slots=True)
class PathwayClassification:
    provenance: str
    classification: str
    era_rows: int
    all_eras_sample_sufficient: bool
    all_eras_pf_above_one: bool
    all_eras_expectancy_positive: bool
    all_eras_pf_below_one: bool
    all_eras_expectancy_negative: bool


def _original_ledger(root: Path, *, expected: int) -> tuple[milestone.SimulatedTrade, ...]:
    ledgers = router._load_selected(root, expected=expected)
    rows = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    if len(rows) != expected:
        raise ValueError("V44 selected population count drift")
    keys = {(row.symbol, row.entry_at) for row in rows}
    if len(keys) != expected:
        raise ValueError("V44 selected population identity collision")
    return tuple(
        sorted(rows, key=lambda row: (milestone._aware(row.entry_at), row.symbol))
    )


def _anniversary_windows(
    start: date,
    end: date,
) -> tuple[tuple[date, date], ...]:
    first = start.replace(year=start.year + 1)
    if first >= end:
        raise ValueError("V44 period must contain two anniversary years")
    second = first.replace(year=first.year + 1)
    if second != end:
        raise ValueError("V44 requires exact two-year anniversary window")
    return ((start, first), (first, end))


def _portfolio_totals(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[Decimal, Decimal, Decimal]:
    values = tuple(Decimal(row.realized_gross_r) for row in rows)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gn = -sum((value for value in values if value < 0), Decimal("0"))
    total = sum(values, Decimal("0"))
    return gp, gn, total


def _ratio(numerator: Decimal, denominator: Decimal) -> str | None:
    if denominator == 0:
        return None
    return str(numerator / denominator)


def _metrics(
    *,
    period: str,
    start: date,
    end: date,
    provenance: str,
    rows: tuple[milestone.SimulatedTrade, ...],
    portfolio_rows: tuple[milestone.SimulatedTrade, ...],
) -> PathwayMetrics:
    ordered = tuple(
        sorted(rows, key=lambda row: (milestone._aware(row.entry_at), row.symbol))
    )
    if not ordered:
        raise ValueError("V44 pathway metrics cannot be empty")

    values = tuple(Decimal(row.realized_gross_r) for row in ordered)
    wins = tuple(value for value in values if value > 0)
    losses = tuple(value for value in values if value < 0)
    flats = len(values) - len(wins) - len(losses)
    gp = sum(wins, Decimal("0"))
    gn = -sum(losses, Decimal("0"))
    total = sum(values, Decimal("0"))
    trades = len(values)
    pf = None if gn == 0 else gp / gn
    avg_win = None if not wins else gp / Decimal(len(wins))
    avg_loss = None if not losses else gn / Decimal(len(losses))
    payoff = (
        None
        if avg_win is None or avg_loss is None or avg_loss == 0
        else avg_win / avg_loss
    )

    portfolio_gp, portfolio_gn, portfolio_total = _portfolio_totals(portfolio_rows)

    stops = sum(row.exit_reason == "STOP" for row in ordered)
    targets = sum(row.exit_reason == "TARGET" for row in ordered)
    other = trades - stops - targets

    sample_ok = (
        trades >= MIN_TRADES
        and len(wins) >= MIN_WINS
        and len(losses) >= MIN_LOSSES
    )

    return PathwayMetrics(
        period=period,
        window_start=start.isoformat(),
        window_end_exclusive=end.isoformat(),
        provenance=provenance,
        trades=trades,
        wins=len(wins),
        losses=len(losses),
        flats=flats,
        gross_positive_r=str(gp),
        gross_negative_r_abs=str(gn),
        total_r=str(total),
        expectancy_r_per_trade=str(total / Decimal(trades)),
        profit_factor=None if pf is None else str(pf),
        average_winner_r=None if avg_win is None else str(avg_win),
        average_loser_r_abs=None if avg_loss is None else str(avg_loss),
        payoff_ratio=None if payoff is None else str(payoff),
        stops=stops,
        stop_rate=str(Decimal(stops) / Decimal(trades)),
        targets=targets,
        target_rate=str(Decimal(targets) / Decimal(trades)),
        other_exits=other,
        entrant_share=str(Decimal(trades) / Decimal(len(portfolio_rows))),
        portfolio_gross_positive_share=_ratio(gp, portfolio_gp),
        portfolio_gross_negative_share=_ratio(gn, portfolio_gn),
        portfolio_total_r_share=_ratio(total, portfolio_total),
        diagnostic_sample_sufficient=sample_ok,
    )


def _classify(
    provenance: str,
    era_rows: tuple[PathwayMetrics, ...],
) -> PathwayClassification:
    if len(era_rows) != 3:
        raise ValueError("V44 classification requires exactly three era rows")

    sufficient = all(row.diagnostic_sample_sufficient for row in era_rows)

    def pf(row: PathwayMetrics) -> Decimal | None:
        return None if row.profit_factor is None else Decimal(row.profit_factor)

    pfs = tuple(pf(row) for row in era_rows)
    exps = tuple(Decimal(row.expectancy_r_per_trade) for row in era_rows)

    all_pf_above = sufficient and all(value is not None and value > 1 for value in pfs)
    all_exp_positive = sufficient and all(value > 0 for value in exps)
    all_pf_below = sufficient and all(value is not None and value < 1 for value in pfs)
    all_exp_negative = sufficient and all(value < 0 for value in exps)

    if not sufficient:
        classification = "INSUFFICIENT_STRUCTURAL_SAMPLE"
    elif all_pf_above and all_exp_positive:
        classification = "CONSISTENT_EDGE_POSITIVE"
    elif all_pf_below and all_exp_negative:
        classification = "CONSISTENT_EDGE_NEGATIVE"
    else:
        classification = "MIXED_OR_NONSTATIONARY"

    return PathwayClassification(
        provenance=provenance,
        classification=classification,
        era_rows=len(era_rows),
        all_eras_sample_sufficient=sufficient,
        all_eras_pf_above_one=all_pf_above,
        all_eras_expectancy_positive=all_exp_positive,
        all_eras_pf_below_one=all_pf_below,
        all_eras_expectancy_negative=all_exp_negative,
    )


def _next_phase(classifications: tuple[PathwayClassification, ...]) -> str:
    if any(
        row.classification == "INSUFFICIENT_STRUCTURAL_SAMPLE"
        for row in classifications
    ):
        return "PATHWAY_ATTRIBUTION_INCONCLUSIVE"

    negative = tuple(
        row
        for row in classifications
        if row.classification == "CONSISTENT_EDGE_NEGATIVE"
    )
    positive = tuple(
        row
        for row in classifications
        if row.classification == "CONSISTENT_EDGE_POSITIVE"
    )
    if len(negative) == 1 and positive:
        return "REDESIGN_NEGATIVE_ENTRY_PATHWAY_WITH_COMMON_GRAMMAR_CONTROL"
    if len(negative) >= 2:
        return "REDESIGN_SHARED_PREENTRY_GRAMMAR_BEFORE_PATHWAY_BRANCHING"
    return "EDGE_DEGRADATION_NOT_PATHWAY_LOCAL_REQUIRE_SHARED_STATE_OR_SETUP_REDESIGN"


def build_report(
    *,
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    selected_geometry_root: Path,
) -> dict[str, Any]:
    roots = {
        "development": development_root,
        "validation": validation_root,
        "reserved": reserved_root,
    }

    era_metrics: list[PathwayMetrics] = []
    annual_metrics: list[PathwayMetrics] = []
    provenance_sets: list[set[str]] = []
    period_counts: dict[str, Any] = {}

    for period, slug, start, end, expected in PERIOD_SPECS:
        ledger = _original_ledger(roots[slug], expected=expected)
        geometry = v38._load_period_geometry(selected_geometry_root, slug=slug)

        ledger_keys = {(row.symbol, row.entry_at) for row in ledger}
        geometry_keys = set(geometry)
        if ledger_keys != geometry_keys:
            raise ValueError(
                "V44 exact provenance coverage mismatch: "
                f"period={period} missing={len(ledger_keys-geometry_keys)} "
                f"extra={len(geometry_keys-ledger_keys)}"
            )

        provenance_by_key = {
            key: row.provenance
            for key, row in geometry.items()
        }
        provenances = set(provenance_by_key.values())
        if not provenances:
            raise ValueError("V44 period has no provenance")
        provenance_sets.append(provenances)

        grouped: dict[str, list[milestone.SimulatedTrade]] = defaultdict(list)
        for row in ledger:
            grouped[provenance_by_key[(row.symbol, row.entry_at)]].append(row)

        period_counts[period] = {
            "entrants": len(ledger),
            "provenance_counts": dict(
                sorted(Counter(provenance_by_key.values()).items())
            ),
            "coverage": "1",
            "missing": 0,
            "extra": 0,
        }

        for provenance in sorted(grouped):
            selected_pathway_trades = tuple(grouped[provenance])
            era_metrics.append(
                _metrics(
                    period=period,
                    start=start,
                    end=end,
                    provenance=provenance,
                    rows=selected_pathway_trades,
                    portfolio_rows=ledger,
                )
            )

        for index, (year_start, year_end) in enumerate(
            _anniversary_windows(start, end),
            start=1,
        ):
            portfolio_year = tuple(
                row
                for row in ledger
                if year_start <= date.fromisoformat(row.operating_date) < year_end
            )
            if not portfolio_year:
                raise ValueError("V44 annual portfolio slice empty")
            grouped_year: dict[str, list[milestone.SimulatedTrade]] = defaultdict(list)
            for row in portfolio_year:
                grouped_year[
                    provenance_by_key[(row.symbol, row.entry_at)]
                ].append(row)
            for provenance in sorted(grouped_year):
                annual_metrics.append(
                    _metrics(
                        period=f"{period}:YEAR_{index}",
                        start=year_start,
                        end=year_end,
                        provenance=provenance,
                        rows=tuple(grouped_year[provenance]),
                        portfolio_rows=portfolio_year,
                    )
                )

    all_provenances = set().union(*provenance_sets)
    if any(values != all_provenances for values in provenance_sets):
        # This is allowed as data, but such a pathway necessarily lacks a three-era
        # structural row and must fail closed as insufficient.
        pass

    by_provenance: dict[str, list[PathwayMetrics]] = defaultdict(list)
    for metric_row in era_metrics:
        by_provenance[metric_row.provenance].append(metric_row)

    classifications: list[PathwayClassification] = []
    period_order = {
        period: index
        for index, (period, *_rest) in enumerate(PERIOD_SPECS)
    }
    for provenance in sorted(all_provenances):
        classification_rows: tuple[PathwayMetrics, ...] = tuple(
            sorted(
                by_provenance.get(provenance, ()),
                key=lambda metric_row: period_order.get(metric_row.period, 999),
            )
        )
        if len(classification_rows) != 3:
            classifications.append(
                PathwayClassification(
                    provenance=provenance,
                    classification="INSUFFICIENT_STRUCTURAL_SAMPLE",
                    era_rows=len(classification_rows),
                    all_eras_sample_sufficient=False,
                    all_eras_pf_above_one=False,
                    all_eras_expectancy_positive=False,
                    all_eras_pf_below_one=False,
                    all_eras_expectancy_negative=False,
                )
            )
        else:
            classifications.append(_classify(provenance, classification_rows))

    frozen_classifications = tuple(classifications)
    return {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "evaluation": "ENTRY_PATHWAY_EDGE_ATTRIBUTION_ONLY",
        "population_counts": {
            "development": 948,
            "validation": 1034,
            "reserved": 1088,
        },
        "period_coverage": period_counts,
        "pathways": sorted(all_provenances),
        "sample_law": {
            "min_trades": MIN_TRADES,
            "min_wins": MIN_WINS,
            "min_losses": MIN_LOSSES,
        },
        "era_metrics": [asdict(row) for row in era_metrics],
        "annual_metrics": [asdict(row) for row in annual_metrics],
        "classifications": [asdict(row) for row in frozen_classifications],
        "pathway_filtering_authorized": False,
        "classifier_used": False,
        "threshold_grid_searched": False,
        "symbol_conditioned_policy": False,
        "session_conditioned_policy": False,
        "date_conditioned_policy": False,
        "admission_changed": False,
        "density_changed": False,
        "sizing_changed": False,
        "protection_changed": False,
        "stop_target_changed": False,
        "fresh_holdout_opened": False,
        "runtime_policy_candidate": False,
        "candidate_count": 0,
        "trader_certified": False,
        "next_phase": _next_phase(frozen_classifications),
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-entry-pathway-edge-attribution-v44.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development-root", type=Path, required=True)
    parser.add_argument("--validation-root", type=Path, required=True)
    parser.add_argument("--reserved-root", type=Path, required=True)
    parser.add_argument("--selected-geometry-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        development_root=args.development_root,
        validation_root=args.validation_root,
        reserved_root=args.reserved_root,
        selected_geometry_root=args.selected_geometry_root,
    )
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
