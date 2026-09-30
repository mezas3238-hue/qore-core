"""V47-S2F fail-closed UTC-001 pre-Fresh qualification bridge.

Consumes a frozen S2E realized-R ledger and reuses QORE's existing certification
metrics + deterministic Monte Carlo engines. It does not certify a Trader and
does not open Fresh Holdout.

The bridge exists to answer one question mechanically:
"Is the frozen consumed population strong enough, with bound costs, to justify
freezing the candidate and opening Fresh Holdout exactly once?"

Development has zero certification authority. Reserved/Validation evidence is
consumed prequalification evidence only.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalper_certification_metrics_v2 as cert_metrics,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalper_monte_carlo_v2 as monte_carlo,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_two_route_gross_economics_v47_s2e as s2e,
)
from qore.infrastructure.trader_lab import (
    universal_trader_certification_standard_001 as utc,
)

IDENTITY = "QORE_CAPITALIZER_V47_S2F_UTC001_PREFRESH_QUALIFICATION"
MC_SEED = 240917
MC_REPLICATES = 5000
MC_BLOCK_LENGTHS = (5, 20)


@dataclass(frozen=True, slots=True)
class S2FPeriodQualification:
    period: str
    population_role: str
    trades: int
    profit_factor: str | None
    expectancy_r_per_trade: str
    sharpe_annualized: str | None
    sortino_annualized: str | None
    payoff_ratio: str | None
    observed_max_drawdown_r: str
    monte_carlo_positive_probability: str | None
    monte_carlo_p95_drawdown_r: str | None
    gross_gate_passed: bool
    mc_gate_passed: bool
    post_cost_profit_factor: str | None
    post_cost_expectancy_r_per_trade: str | None
    post_cost_gate_passed: bool
    cost_evidence_bound: bool
    sample_sufficiency_for_frozen_mc: bool
    certification_authority: bool = False


@dataclass(frozen=True, slots=True)
class S2FReport:
    identity: str
    source_population_rows: int
    provider_cost_evidence_bound: bool
    additional_cost_r_per_trade: str | None
    periods: tuple[S2FPeriodQualification, ...]
    all_consumed_oos_prefresh_gates_passed: bool
    candidate_head_can_be_frozen_for_fresh_holdout: bool
    fresh_holdout_opened: bool = False
    fresh_holdout_authority_claimed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("S2F identity drift")
        if (
            self.fresh_holdout_opened
            or self.fresh_holdout_authority_claimed
            or self.trader_certified
        ):
            raise ValueError("S2F cannot open/certify Fresh Holdout")


def _adapt(row: s2e.S2EGrossTrade) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol=row.symbol,
        session=row.session,
        operating_date=row.operating_date,
        side=row.side,
        entry_at=row.entry_at,
        exit_at=row.exit_at,
        entry_price=row.entry_price,
        original_stop_price=row.stop_price,
        final_stop_price=row.stop_price,
        target_price=row.target_price,
        realized_gross_r=row.realized_gross_r,
        exit_reason=row.exit_reason,
        mode=row.route,
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="0",
        same_minute_stop_target_ambiguity=row.stop_first_fallback_used,
    )


def _load(root: Path) -> tuple[s2e.S2EGrossTrade, ...]:
    rows: list[s2e.S2EGrossTrade] = []
    for path in sorted(root.rglob("capitalizer-s2e-*-trades.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(s2e.S2EGrossTrade(**json.loads(line)))
    if not rows:
        raise ValueError("S2F requires non-empty frozen S2E ledger")
    keys = {(row.symbol, row.entry_at) for row in rows}
    if len(keys) != len(rows):
        raise ValueError("S2F requires unique frozen entrant identities")
    return tuple(rows)


def _cost_adjusted(
    rows: tuple[milestone.SimulatedTrade, ...],
    cost: Decimal,
) -> tuple[milestone.SimulatedTrade, ...]:
    if not cost.is_finite() or cost < 0:
        raise ValueError("S2F provider-bound cost must be finite non-negative")
    return tuple(
        replace(
            row,
            realized_gross_r=str(Decimal(row.realized_gross_r) - cost),
        )
        for row in rows
    )


def _gross_gate(report: cert_metrics.CertificationMetricsReport) -> bool:
    econ = report.economics
    daily = report.daily_risk_adjusted
    return (
        econ.profit_factor is not None
        and Decimal(econ.profit_factor) >= utc.PF_MIN
        and Decimal(econ.expectancy_r_per_trade) >= utc.EXPECTANCY_MIN
        and daily.sharpe_annualized is not None
        and Decimal(daily.sharpe_annualized) >= utc.SHARPE_MIN
        and daily.sortino_annualized is not None
        and Decimal(daily.sortino_annualized) >= utc.SORTINO_MIN
        and econ.payoff_ratio is not None
        and Decimal(econ.payoff_ratio) >= utc.PAYOFF_MIN
        and Decimal(econ.max_drawdown_r) <= utc.OBSERVED_DD_MAX_R
    )


def _post_cost_gate(report: cert_metrics.CertificationMetricsReport) -> bool:
    econ = report.economics
    return (
        econ.profit_factor is not None
        and Decimal(econ.profit_factor) > utc.POST_COST_PF_MIN_EXCLUSIVE
        and Decimal(econ.expectancy_r_per_trade)
        > utc.POST_COST_EXPECTANCY_MIN_EXCLUSIVE
    )


def _qualification(
    *,
    period: str,
    rows: tuple[s2e.S2EGrossTrade, ...],
    provider_cost_evidence_bound: bool,
    additional_cost_r_per_trade: Decimal | None,
) -> S2FPeriodQualification:
    start_dt, end_dt = s1.PERIODS[period]
    adapted = tuple(_adapt(row) for row in rows)
    report = cert_metrics.build_certification_metrics_report(
        adapted,
        population_role=f"S2E_{period.upper()}_CONSUMED_PREFRESH",
        window_start=start_dt.date(),
        window_end_exclusive=end_dt.date(),
    )
    sample_ok = len(adapted) >= max(MC_BLOCK_LENGTHS)
    mc_positive: str | None = None
    mc_p95: str | None = None
    mc_pass = False
    if sample_ok:
        mc = monte_carlo.build_monte_carlo_report(
            adapted,
            population_role=f"S2E_{period.upper()}_CONSUMED_PREFRESH",
            seed=MC_SEED,
            replicates=MC_REPLICATES,
            block_lengths=MC_BLOCK_LENGTHS,
            provider_cost_evidence_bound=provider_cost_evidence_bound,
            additional_cost_r_per_trade=additional_cost_r_per_trade,
        )
        mc_positive = mc.conservative_positive_probability
        mc_p95 = mc.conservative_p95_drawdown_r
        mc_pass = mc.mc_gate_passed

    post_cost_pf: str | None = None
    post_cost_exp: str | None = None
    post_cost_pass = False
    if provider_cost_evidence_bound:
        if additional_cost_r_per_trade is None:
            raise ValueError("S2F bound cost requires explicit cost value")
        cost_rows = _cost_adjusted(adapted, additional_cost_r_per_trade)
        cost_report = cert_metrics.build_certification_metrics_report(
            cost_rows,
            population_role=f"S2E_{period.upper()}_BOUND_COST",
            window_start=start_dt.date(),
            window_end_exclusive=end_dt.date(),
        )
        post_cost_pf = cost_report.economics.profit_factor
        post_cost_exp = cost_report.economics.expectancy_r_per_trade
        post_cost_pass = _post_cost_gate(cost_report)
    elif additional_cost_r_per_trade is not None:
        raise ValueError("S2F cannot consume unbound cost value")

    return S2FPeriodQualification(
        period=period,
        population_role=report.population_role,
        trades=report.economics.trades,
        profit_factor=report.economics.profit_factor,
        expectancy_r_per_trade=report.economics.expectancy_r_per_trade,
        sharpe_annualized=report.daily_risk_adjusted.sharpe_annualized,
        sortino_annualized=report.daily_risk_adjusted.sortino_annualized,
        payoff_ratio=report.economics.payoff_ratio,
        observed_max_drawdown_r=report.economics.max_drawdown_r,
        monte_carlo_positive_probability=mc_positive,
        monte_carlo_p95_drawdown_r=mc_p95,
        gross_gate_passed=_gross_gate(report),
        mc_gate_passed=mc_pass,
        post_cost_profit_factor=post_cost_pf,
        post_cost_expectancy_r_per_trade=post_cost_exp,
        post_cost_gate_passed=post_cost_pass,
        cost_evidence_bound=provider_cost_evidence_bound,
        sample_sufficiency_for_frozen_mc=sample_ok,
    )


def build_report(
    rows: tuple[s2e.S2EGrossTrade, ...],
    *,
    provider_cost_evidence_bound: bool,
    additional_cost_r_per_trade: Decimal | None,
) -> S2FReport:
    if provider_cost_evidence_bound != (additional_cost_r_per_trade is not None):
        raise ValueError("S2F cost evidence/value binding mismatch")
    periods: list[S2FPeriodQualification] = []
    for period in ("reserved", "validation", "development"):
        subset = tuple(row for row in rows if row.period == period)
        if not subset:
            raise ValueError(f"S2F missing frozen period {period}")
        periods.append(
            _qualification(
                period=period,
                rows=subset,
                provider_cost_evidence_bound=provider_cost_evidence_bound,
                additional_cost_r_per_trade=additional_cost_r_per_trade,
            )
        )

    oos = tuple(row for row in periods if row.period in {"reserved", "validation"})
    all_oos = bool(oos) and all(
        row.gross_gate_passed
        and row.mc_gate_passed
        and row.post_cost_gate_passed
        and row.cost_evidence_bound
        and row.sample_sufficiency_for_frozen_mc
        for row in oos
    )
    return S2FReport(
        identity=IDENTITY,
        source_population_rows=len(rows),
        provider_cost_evidence_bound=provider_cost_evidence_bound,
        additional_cost_r_per_trade=(
            None
            if additional_cost_r_per_trade is None
            else str(additional_cost_r_per_trade)
        ),
        periods=tuple(periods),
        all_consumed_oos_prefresh_gates_passed=all_oos,
        candidate_head_can_be_frozen_for_fresh_holdout=all_oos,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("s2e_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider-cost-evidence-bound", action="store_true")
    parser.add_argument("--additional-cost-r-per-trade")
    args = parser.parse_args()
    rows = _load(args.s2e_root)
    cost = (
        None
        if args.additional_cost_r_per_trade is None
        else Decimal(args.additional_cost_r_per_trade)
    )
    report = build_report(
        rows,
        provider_cost_evidence_bound=args.provider_cost_evidence_bound,
        additional_cost_r_per_trade=cost,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "capitalizer-s2f-utc001-prefresh.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
