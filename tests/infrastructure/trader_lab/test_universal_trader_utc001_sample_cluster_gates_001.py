from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_certification_metrics_v2 as metrics,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalper_monte_carlo_v2 as mc,
)
from qore.infrastructure.trader_lab import (
    universal_trader_utc001_sample_cluster_gates_001 as gates,
)


def _economics(*, trades: int, wins: int, losses: int) -> metrics.TradeEconomics:
    return metrics.TradeEconomics(
        trades=trades,
        wins=wins,
        losses=losses,
        flats=trades - wins - losses,
        win_rate="0.5",
        profit_factor="1.8",
        total_r="50",
        expectancy_r_per_trade="0.20",
        average_winner_r="1.0",
        average_loser_r_abs="0.5",
        payoff_ratio="2.0",
        max_drawdown_r="4",
        max_losing_streak=4,
    )


def _clusters(worst: str) -> metrics.LossClusterMetrics:
    return metrics.LossClusterMetrics(
        cluster_count=10,
        losing_trade_count=100,
        max_cluster_length=5,
        mean_cluster_length="2.5",
        worst_cluster_total_r=worst,
        clusters=(),
    )


def _mc(*, positive: str, p95: str) -> mc.MonteCarloReport:
    scenario = mc.MonteCarloScenario(
        scenario="LOSS_CLUSTER_STRESS_BLOCK_20",
        replicates=5000,
        block_length=20,
        worst_loss_cluster_length=5,
        worst_loss_cluster_r="-4",
        additional_cost_r_per_trade="0",
        positive_probability=positive,
        p05_total_r="10",
        median_total_r="50",
        p95_drawdown_r=p95,
        p99_drawdown_r="14",
        max_drawdown_r="16",
    )
    return mc.MonteCarloReport(
        identity=mc.IDENTITY,
        population_role="YEAR",
        trades=500,
        source_total_r="50",
        source_max_drawdown_r="4",
        seed=240917,
        replicates_per_scenario=5000,
        block_lengths=(5, 20),
        scenarios=(scenario,),
        conservative_positive_probability=positive,
        conservative_p95_drawdown_r=p95,
        mc_positive_gate="0.90",
        mc_p95_dd_gate_r="15",
        mc_gate_passed=True,
        provider_cost_evidence_bound=False,
        cost_stress_status="NOT_RUN_NO_BOUND_PROVIDER_COST_EVIDENCE",
    )


def test_sample_gate_passes_exact_boundary() -> None:
    result = gates.sample_sufficiency_gate(
        _economics(trades=385, wins=30, losses=30)
    )

    assert result.passed is True


def test_sample_gate_fails_one_below_trade_boundary() -> None:
    result = gates.sample_sufficiency_gate(
        _economics(trades=384, wins=100, losses=100)
    )

    assert result.passed is False


def test_sample_gate_fails_thin_outcome_class() -> None:
    result = gates.sample_sufficiency_gate(
        _economics(trades=500, wins=29, losses=100)
    )

    assert result.passed is False


def test_cluster_gate_passes_exact_utc_boundaries() -> None:
    result = gates.loss_cluster_gate(
        _clusters("-6"),
        _mc(positive="0.90", p95="15"),
    )

    assert result.historical_cluster_passed is True
    assert result.stress_positive_passed is True
    assert result.stress_p95_drawdown_passed is True
    assert result.passed is True


def test_cluster_gate_fails_historical_cluster_over_6r() -> None:
    result = gates.loss_cluster_gate(
        _clusters("-6.0001"),
        _mc(positive="0.95", p95="10"),
    )

    assert result.passed is False
    assert result.historical_cluster_passed is False


def test_cluster_gate_fails_stress_tail() -> None:
    result = gates.loss_cluster_gate(
        _clusters("-4"),
        _mc(positive="0.8999", p95="15.0001"),
    )

    assert result.passed is False
    assert result.stress_positive_passed is False
    assert result.stress_p95_drawdown_passed is False
