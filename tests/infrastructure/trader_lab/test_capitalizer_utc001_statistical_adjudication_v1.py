from __future__ import annotations

from fractions import Fraction

from qore.infrastructure.trader_lab import (
    capitalizer_utc001_statistical_adjudication_v1 as adjudication,
)


def test_exact_tail_all_losses_is_one_for_observed_full_run() -> None:
    assert adjudication.exact_longest_loss_run_tail(
        trades=5,
        losses=5,
        observed_longest_run=5,
    ) == Fraction(1, 1)


def test_exact_tail_single_loss_is_one() -> None:
    assert adjudication.exact_longest_loss_run_tail(
        trades=10,
        losses=1,
        observed_longest_run=1,
    ) == Fraction(1, 1)


def test_exact_tail_two_losses_adjacent_matches_combinatorics() -> None:
    # C(5,2)=10 fixed-loss orderings. Four place the two losses adjacent.
    assert adjudication.exact_longest_loss_run_tail(
        trades=5,
        losses=2,
        observed_longest_run=2,
    ) == Fraction(4, 10)


def test_frozen_sample_and_cluster_contract() -> None:
    assert adjudication.MIN_TRADES == 200
    assert adjudication.MIN_WINS == 50
    assert adjudication.MIN_LOSSES == 50
    assert adjudication.MIN_ACTIVE_MONTHS == 10
    assert adjudication.LOSS_CLUSTER_ALPHA == Fraction(1, 100)
    assert str(adjudication.MAX_PURE_LOSS_CLUSTER_R) == "6"
