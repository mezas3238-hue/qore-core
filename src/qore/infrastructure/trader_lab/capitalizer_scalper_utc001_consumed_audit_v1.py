"""UTC-001 consumed-evidence audit for Capitalizer Scalper.

This audit is diagnostic/regression evidence only. It never turns consumed
Validation/Reserved into fresh OOS. Each 24-month source window is split into
two exact anniversary-aligned 12-month exam years and each year is evaluated
independently under UTC-001.

Costs remain BLOCKED unless explicit bound provider economics are supplied.
Loss-cluster and sample-sufficiency certification remain MISSING until their
predeclared adjudication contracts exist; descriptive cluster metrics are still
emitted.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalper_certification_metrics_v2 as metrics,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalper_monte_carlo_v2 as mc,
)
from qore.infrastructure.trader_lab import (
    universal_trader_certification_standard_001 as utc,
)

IDENTITY = "QORE_CAPITALIZER_SCALPER_UTC001_CONSUMED_AUDIT_V1"
MC_REPLICATES = 5000
MC_SEED = 240917
MC_BLOCK_LENGTHS = (5, 20)


@dataclass(frozen=True, slots=True)
class ExamYearReport:
    period_id: str
    year_index: int
    window_start: str
    window_end_exclusive: str
    economics: metrics.TradeEconomics
    risk_adjusted: metrics.DailyRiskAdjustedMetrics
    loss_clustering: metrics.LossClusterMetrics
    monte_carlo: mc.MonteCarloReport
    utc_evidence: utc.TemporalPeriodEvidence
    utc_gate_statuses: tuple[utc.GateResult, ...]


@dataclass(frozen=True, slots=True)
class ConsumedUtcAuditReport:
    identity: str
    utc_identity: str
    population_role: str
    source_window_start: str
    source_window_end_exclusive: str
    development_only: bool
    consumed_for_engineering: bool
    fresh_certification_authority: bool
    cost_certification_blocked: bool
    loss_cluster_certification_adjudication_available: bool
    sample_sufficiency_rule_predeclared: bool
    exam_years: tuple[ExamYearReport, ...]
    failed_economic_gates: tuple[str, ...]
    missing_mandatory_gates: tuple[str, ...]
    global_metrics_have_certification_authority: bool
    temporal_compensation_allowed: bool
    fresh_holdout_opened: bool
    trader_certified: bool


def _next_anniversary(value: date) -> date:
    return value.replace(year=value.year + 1)


def _split_exam_years(
    rows: tuple[milestone.SimulatedTrade, ...],
    *,
    window_start: date,
    window_end_exclusive: date,
) -> tuple[
    tuple[date, date, tuple[milestone.SimulatedTrade, ...]],
    ...,
]:
    if window_end_exclusive <= window_start:
        raise ValueError("UTC audit source window must be positive")

    boundaries: list[tuple[date, date]] = []
    current = window_start
    while current < window_end_exclusive:
        nxt = min(_next_anniversary(current), window_end_exclusive)
        boundaries.append((current, nxt))
        current = nxt

    if len(boundaries) != 2:
        raise ValueError("UTC consumed audit requires exact two-year source window")

    assigned: set[tuple[str, str]] = set()
    result: list[
        tuple[date, date, tuple[milestone.SimulatedTrade, ...]]
    ] = []
    ordered = metrics._canonical(rows)
    for start, end in boundaries:
        selected = tuple(
            row
            for row in ordered
            if start <= date.fromisoformat(row.operating_date) < end
        )
        keys = {(row.symbol, row.entry_at) for row in selected}
        if assigned.intersection(keys):
            raise ValueError("UTC exam-year assignment overlap")
        assigned.update(keys)
        result.append((start, end, selected))

    all_keys = {(row.symbol, row.entry_at) for row in ordered}
    if assigned != all_keys:
        missing = all_keys - assigned
        raise ValueError(
            f"UTC exam-year assignment lost entrants: {len(missing)}"
        )
    return tuple(result)


def _period_evidence(
    *,
    period_id: str,
    window_start: date,
    window_end_exclusive: date,
    rows: tuple[milestone.SimulatedTrade, ...],
    development_only: bool,
    consumed_for_engineering: bool,
) -> tuple[
    metrics.TradeEconomics,
    metrics.DailyRiskAdjustedMetrics,
    metrics.LossClusterMetrics,
    mc.MonteCarloReport,
    utc.TemporalPeriodEvidence,
]:
    economics = metrics._economics(rows)
    risk = metrics._daily_metrics(
        rows,
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
    )
    clusters = metrics._loss_clusters(rows)
    monte_carlo = mc.build_monte_carlo_report(
        rows,
        population_role=period_id,
        seed=MC_SEED,
        replicates=MC_REPLICATES,
        block_lengths=MC_BLOCK_LENGTHS,
        provider_cost_evidence_bound=False,
        additional_cost_r_per_trade=None,
    )

    evidence = utc.TemporalPeriodEvidence(
        period_id=period_id,
        kind=utc.PeriodKind.YEAR,
        window_start=window_start.isoformat(),
        window_end_exclusive=window_end_exclusive.isoformat(),
        certification_required=not development_only,
        trades=economics.trades,
        wins=economics.wins,
        losses=economics.losses,
        breakeven=economics.flats,
        win_rate=Decimal(economics.win_rate),
        profit_factor=(
            None
            if economics.profit_factor is None
            else Decimal(economics.profit_factor)
        ),
        expectancy_r_per_trade=Decimal(
            economics.expectancy_r_per_trade
        ),
        sharpe_annualized=(
            None
            if risk.sharpe_annualized is None
            else Decimal(risk.sharpe_annualized)
        ),
        sortino_annualized=(
            None
            if risk.sortino_annualized is None
            else Decimal(risk.sortino_annualized)
        ),
        observed_max_drawdown_r=Decimal(economics.max_drawdown_r),
        average_winner_r=(
            None
            if economics.average_winner_r is None
            else Decimal(economics.average_winner_r)
        ),
        average_loser_r_abs=(
            None
            if economics.average_loser_r_abs is None
            else Decimal(economics.average_loser_r_abs)
        ),
        payoff_ratio=(
            None
            if economics.payoff_ratio is None
            else Decimal(economics.payoff_ratio)
        ),
        longest_losing_streak=economics.max_losing_streak,
        monte_carlo_positive_probability=Decimal(
            monte_carlo.conservative_positive_probability
        ),
        monte_carlo_p95_drawdown_r=Decimal(
            monte_carlo.conservative_p95_drawdown_r
        ),
        post_cost_profit_factor=None,
        post_cost_expectancy_r_per_trade=None,
        loss_cluster_gate_passed=None,
        sample_sufficiency_passed=None,
        cost_evidence_bound=False,
        cost_certification_blocked=True,
        development_only=development_only,
        consumed_for_engineering=consumed_for_engineering,
        fresh_holdout=False,
    )
    return economics, risk, clusters, monte_carlo, evidence


def build_report(
    rows: tuple[milestone.SimulatedTrade, ...],
    *,
    population_role: str,
    window_start: date,
    window_end_exclusive: date,
    development_only: bool,
    consumed_for_engineering: bool,
) -> ConsumedUtcAuditReport:
    if not population_role:
        raise ValueError("population_role must be non-empty")
    split = _split_exam_years(
        rows,
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
    )

    year_reports: list[ExamYearReport] = []
    failed: list[str] = []
    missing: list[str] = []

    for index, (start, end, year_rows) in enumerate(split, start=1):
        period_id = f"{population_role}:YEAR_{index}"
        economics, risk, clusters, monte_carlo, evidence = _period_evidence(
            period_id=period_id,
            window_start=start,
            window_end_exclusive=end,
            rows=year_rows,
            development_only=development_only,
            consumed_for_engineering=consumed_for_engineering,
        )
        gates = utc._period_gates(evidence)
        for gate in gates:
            if gate.status is utc.GateStatus.FAIL:
                failed.append(f"{period_id}.{gate.gate}")
            elif gate.status is utc.GateStatus.MISSING:
                missing.append(f"{period_id}.{gate.gate}")
        year_reports.append(
            ExamYearReport(
                period_id=period_id,
                year_index=index,
                window_start=start.isoformat(),
                window_end_exclusive=end.isoformat(),
                economics=economics,
                risk_adjusted=risk,
                loss_clustering=clusters,
                monte_carlo=monte_carlo,
                utc_evidence=evidence,
                utc_gate_statuses=gates,
            )
        )

    return ConsumedUtcAuditReport(
        identity=IDENTITY,
        utc_identity=utc.IDENTITY,
        population_role=population_role,
        source_window_start=window_start.isoformat(),
        source_window_end_exclusive=window_end_exclusive.isoformat(),
        development_only=development_only,
        consumed_for_engineering=consumed_for_engineering,
        fresh_certification_authority=False,
        cost_certification_blocked=True,
        loss_cluster_certification_adjudication_available=False,
        sample_sufficiency_rule_predeclared=False,
        exam_years=tuple(year_reports),
        failed_economic_gates=tuple(sorted(failed)),
        missing_mandatory_gates=tuple(sorted(missing)),
        global_metrics_have_certification_authority=False,
        temporal_compensation_allowed=False,
        fresh_holdout_opened=False,
        trader_certified=False,
    )


def _load_rows(path: Path) -> tuple[milestone.SimulatedTrade, ...]:
    rows: list[milestone.SimulatedTrade] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            if raw.strip():
                item: Any = json.loads(raw)
                if not isinstance(item, dict):
                    raise ValueError("UTC audit ledger row must be object")
                rows.append(milestone.SimulatedTrade(**item))
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--population-role", required=True)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--window-end-exclusive", required=True)
    parser.add_argument("--development-only", action="store_true")
    parser.add_argument("--consumed-for-engineering", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        _load_rows(args.ledger),
        population_role=args.population_role,
        window_start=date.fromisoformat(args.window_start),
        window_end_exclusive=date.fromisoformat(
            args.window_end_exclusive
        ),
        development_only=args.development_only,
        consumed_for_engineering=args.consumed_for_engineering,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output / "capitalizer-scalper-utc001-consumed-audit-v1.json"
    out.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
