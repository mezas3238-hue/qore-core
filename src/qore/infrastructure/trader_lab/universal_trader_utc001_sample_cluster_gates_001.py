"""UTC-001 sample sufficiency and loss-cluster adjudication.

Frozen Owner-governance helper. These gates operate on one mandatory year/fold
at a time. No global population may rescue a failed temporal period.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_certification_metrics_v2 as metrics,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalper_monte_carlo_v2 as mc,
)

IDENTITY = "QORE_UNIVERSAL_TRADER_UTC001_SAMPLE_CLUSTER_GATES_001"

SAMPLE_MIN_TRADES = 385
SAMPLE_MIN_WINNERS = 30
SAMPLE_MIN_LOSERS = 30
OBSERVED_CLUSTER_LOSS_MAX_R = Decimal("6")
CLUSTER_STRESS_POSITIVE_MIN = Decimal("0.90")
CLUSTER_STRESS_P95_DD_MAX_R = Decimal("15")
CLUSTER_STRESS_SCENARIO = "LOSS_CLUSTER_STRESS_BLOCK_20"


@dataclass(frozen=True, slots=True)
class SampleSufficiencyGate:
    trades: int
    winners: int
    losers: int
    min_trades: int
    min_winners: int
    min_losers: int
    passed: bool


@dataclass(frozen=True, slots=True)
class LossClusterGate:
    worst_historical_cluster_r: str
    worst_historical_cluster_magnitude_r: str
    observed_cluster_ceiling_r: str
    stress_scenario: str
    stress_positive_probability: str
    stress_positive_gate: str
    stress_p95_drawdown_r: str
    stress_p95_drawdown_gate_r: str
    historical_cluster_passed: bool
    stress_positive_passed: bool
    stress_p95_drawdown_passed: bool
    passed: bool


def sample_sufficiency_gate(
    economics: metrics.TradeEconomics,
) -> SampleSufficiencyGate:
    passed = (
        economics.trades >= SAMPLE_MIN_TRADES
        and economics.wins >= SAMPLE_MIN_WINNERS
        and economics.losses >= SAMPLE_MIN_LOSERS
    )
    return SampleSufficiencyGate(
        trades=economics.trades,
        winners=economics.wins,
        losers=economics.losses,
        min_trades=SAMPLE_MIN_TRADES,
        min_winners=SAMPLE_MIN_WINNERS,
        min_losers=SAMPLE_MIN_LOSERS,
        passed=passed,
    )


def loss_cluster_gate(
    cluster_metrics: metrics.LossClusterMetrics,
    monte_carlo: mc.MonteCarloReport,
) -> LossClusterGate:
    matching = tuple(
        row
        for row in monte_carlo.scenarios
        if row.scenario == CLUSTER_STRESS_SCENARIO
    )
    if len(matching) != 1:
        raise ValueError(
            "UTC-001 requires exactly one LOSS_CLUSTER_STRESS_BLOCK_20 scenario"
        )
    scenario = matching[0]

    worst_cluster = Decimal(cluster_metrics.worst_cluster_total_r)
    worst_magnitude = abs(min(worst_cluster, Decimal("0")))
    positive = Decimal(scenario.positive_probability)
    p95_dd = Decimal(scenario.p95_drawdown_r)

    historical_passed = worst_magnitude <= OBSERVED_CLUSTER_LOSS_MAX_R
    positive_passed = positive >= CLUSTER_STRESS_POSITIVE_MIN
    p95_passed = p95_dd <= CLUSTER_STRESS_P95_DD_MAX_R

    return LossClusterGate(
        worst_historical_cluster_r=str(worst_cluster),
        worst_historical_cluster_magnitude_r=str(worst_magnitude),
        observed_cluster_ceiling_r=str(OBSERVED_CLUSTER_LOSS_MAX_R),
        stress_scenario=scenario.scenario,
        stress_positive_probability=str(positive),
        stress_positive_gate=str(CLUSTER_STRESS_POSITIVE_MIN),
        stress_p95_drawdown_r=str(p95_dd),
        stress_p95_drawdown_gate_r=str(CLUSTER_STRESS_P95_DD_MAX_R),
        historical_cluster_passed=historical_passed,
        stress_positive_passed=positive_passed,
        stress_p95_drawdown_passed=p95_passed,
        passed=historical_passed and positive_passed and p95_passed,
    )
