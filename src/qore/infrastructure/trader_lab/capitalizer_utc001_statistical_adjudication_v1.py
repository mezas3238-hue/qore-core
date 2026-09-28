"""Frozen statistical adjudication for UTC-001 sample and loss-cluster gates.

The contract is deliberately independent of economic acceptance. It evaluates
only whether one 12-month ledger has enough observations/temporal coverage and
whether its loss streak is statistically anomalous relative to an exact
permutation null with the same numbers of losses and non-losses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from fractions import Fraction
from math import comb

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalper_certification_metrics_v2 as metrics,
)

IDENTITY = "QORE_CAPITALIZER_UTC001_STATISTICAL_ADJUDICATION_V1"
MIN_TRADES = 200
MIN_WINS = 50
MIN_LOSSES = 50
MIN_ACTIVE_MONTHS = 10
LOSS_CLUSTER_ALPHA = Fraction(1, 100)
MAX_PURE_LOSS_CLUSTER_R = Decimal("6")


@dataclass(frozen=True, slots=True)
class StatisticalAdjudication:
    identity: str
    trades: int
    wins: int
    losses: int
    active_months: int
    sample_sufficiency_passed: bool
    observed_longest_losing_streak: int
    exact_permutation_tail_probability: str
    exact_permutation_tail_probability_numerator: int
    exact_permutation_tail_probability_denominator: int
    clustering_anomaly_detected: bool
    worst_pure_loss_cluster_r: str
    pure_loss_cluster_within_6r: bool
    loss_cluster_gate_passed: bool
    threshold_fit_to_current_outcomes: bool = False
    fresh_holdout_used: bool = False


def _bounded_compositions(
    *,
    losses: int,
    nonlosses: int,
    max_run: int,
) -> int:
    """Count binary sequences with fixed counts and loss runs <= max_run.

    Each sequence is uniquely represented by distributing losses into the
    nonlosses + 1 gaps around the fixed-order non-loss markers.
    """

    if losses < 0 or nonlosses < 0 or max_run < 0:
        raise ValueError("bounded-composition arguments must be non-negative")
    if losses == 0:
        return 1
    if max_run == 0:
        return 0

    ways = [0] * (losses + 1)
    ways[0] = 1
    for _gap in range(nonlosses + 1):
        prefix = [0] * (losses + 2)
        for index, value in enumerate(ways):
            prefix[index + 1] = prefix[index] + value
        updated = [0] * (losses + 1)
        for used in range(losses + 1):
            low = max(0, used - max_run)
            updated[used] = prefix[used + 1] - prefix[low]
        ways = updated
    return ways[losses]


def exact_longest_loss_run_tail(
    *,
    trades: int,
    losses: int,
    observed_longest_run: int,
) -> Fraction:
    """P(max loss run >= observed | fixed n, fixed number of losses)."""

    if trades < 0 or losses < 0 or losses > trades:
        raise ValueError("invalid fixed-count loss-run population")
    if observed_longest_run < 0:
        raise ValueError("observed longest run cannot be negative")
    if losses == 0:
        return Fraction(0, 1) if observed_longest_run > 0 else Fraction(1, 1)
    if observed_longest_run == 0:
        return Fraction(1, 1)

    total = comb(trades, losses)
    with_shorter_runs = _bounded_compositions(
        losses=losses,
        nonlosses=trades - losses,
        max_run=observed_longest_run - 1,
    )
    return Fraction(total - with_shorter_runs, total)


def _fraction_decimal(value: Fraction) -> str:
    with localcontext() as ctx:
        ctx.prec = 28
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def adjudicate(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> StatisticalAdjudication:
    ordered = metrics._canonical(rows)
    economics = metrics._economics(ordered)
    clusters = metrics._loss_clusters(ordered)

    active_months = len(
        {
            (
                date.fromisoformat(row.operating_date).year,
                date.fromisoformat(row.operating_date).month,
            )
            for row in ordered
        }
    )
    sample_pass = (
        economics.trades >= MIN_TRADES
        and economics.wins >= MIN_WINS
        and economics.losses >= MIN_LOSSES
        and active_months >= MIN_ACTIVE_MONTHS
    )

    tail = exact_longest_loss_run_tail(
        trades=economics.trades,
        losses=economics.losses,
        observed_longest_run=clusters.max_cluster_length,
    )
    anomaly = tail < LOSS_CLUSTER_ALPHA
    worst_cluster = Decimal(clusters.worst_cluster_total_r)
    cluster_within = worst_cluster >= -MAX_PURE_LOSS_CLUSTER_R
    cluster_pass = (not anomaly) and cluster_within

    return StatisticalAdjudication(
        identity=IDENTITY,
        trades=economics.trades,
        wins=economics.wins,
        losses=economics.losses,
        active_months=active_months,
        sample_sufficiency_passed=sample_pass,
        observed_longest_losing_streak=clusters.max_cluster_length,
        exact_permutation_tail_probability=_fraction_decimal(tail),
        exact_permutation_tail_probability_numerator=tail.numerator,
        exact_permutation_tail_probability_denominator=tail.denominator,
        clustering_anomaly_detected=anomaly,
        worst_pure_loss_cluster_r=str(worst_cluster),
        pure_loss_cluster_within_6r=cluster_within,
        loss_cluster_gate_passed=cluster_pass,
    )
