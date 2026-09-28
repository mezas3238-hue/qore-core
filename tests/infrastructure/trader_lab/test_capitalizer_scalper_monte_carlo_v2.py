from __future__ import annotations

from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalper_monte_carlo_v2 as mc,
)


def _trade(index: int, realized_r: str) -> milestone.SimulatedTrade:
    day = index + 1
    stamp = f"2026-01-{day:02d}T10:00:00+00:00"
    return milestone.SimulatedTrade(
        symbol=f"S{index:02d}",
        session="NEW_YORK",
        operating_date=f"2026-01-{day:02d}",
        side="LONG",
        entry_at=stamp,
        exit_at=f"2026-01-{day:02d}T11:00:00+00:00",
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r=realized_r,
        exit_reason="TARGET" if Decimal(realized_r) > 0 else "STOP",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="0",
        same_minute_stop_target_ambiguity=False,
    )


def _rows() -> tuple[milestone.SimulatedTrade, ...]:
    values = ("2", "-1", "2", "-1", "2", "-1", "2", "-1", "2", "-1")
    return tuple(_trade(index, value) for index, value in enumerate(values))


def test_monte_carlo_is_deterministic_for_same_seed() -> None:
    first = mc.build_monte_carlo_report(
        _rows(),
        population_role="TEST",
        seed=42,
        replicates=100,
        block_lengths=(2, 4),
    )
    second = mc.build_monte_carlo_report(
        _rows(),
        population_role="TEST",
        seed=42,
        replicates=100,
        block_lengths=(2, 4),
    )

    assert first == second
    assert first.trades == 10
    assert first.source_total_r == "5"
    assert first.source_max_drawdown_r == "1"
    assert first.provider_cost_evidence_bound is False
    assert first.cost_stress_status == (
        "NOT_RUN_NO_BOUND_PROVIDER_COST_EVIDENCE"
    )
    assert {row.scenario for row in first.scenarios} == {
        "RESHUFFLE",
        "CIRCULAR_BLOCK_2",
        "CIRCULAR_BLOCK_4",
        "LOSS_CLUSTER_STRESS_BLOCK_4",
    }


def test_reshuffle_preserves_positive_total() -> None:
    report = mc.build_monte_carlo_report(
        _rows(),
        population_role="TEST",
        seed=7,
        replicates=100,
        block_lengths=(2,),
    )
    reshuffle = next(
        row for row in report.scenarios if row.scenario == "RESHUFFLE"
    )

    assert reshuffle.positive_probability == "1"
    assert reshuffle.p05_total_r == "5"
    assert reshuffle.median_total_r == "5"


def test_cost_stress_requires_bound_provider_evidence() -> None:
    with pytest.raises(ValueError, match="bound provider evidence"):
        mc.build_monte_carlo_report(
            _rows(),
            population_role="TEST",
            seed=1,
            replicates=10,
            block_lengths=(2,),
            provider_cost_evidence_bound=False,
            additional_cost_r_per_trade=Decimal("0.01"),
        )


def test_cost_stress_runs_when_explicitly_bound() -> None:
    report = mc.build_monte_carlo_report(
        _rows(),
        population_role="TEST",
        seed=1,
        replicates=25,
        block_lengths=(2,),
        provider_cost_evidence_bound=True,
        additional_cost_r_per_trade=Decimal("0.05"),
    )

    assert report.provider_cost_evidence_bound is True
    assert report.cost_stress_status == (
        "RUN_WITH_BOUND_PROVIDER_COST_EVIDENCE"
    )
    assert any(row.scenario.endswith("_COST") for row in report.scenarios)


def test_loss_cluster_stress_records_historical_worst_cluster() -> None:
    rows = (
        _trade(0, "2"),
        _trade(1, "-1"),
        _trade(2, "-1"),
        _trade(3, "-1"),
        _trade(4, "2"),
        _trade(5, "-0.5"),
    )
    report = mc.build_monte_carlo_report(
        rows,
        population_role="TEST",
        seed=3,
        replicates=50,
        block_lengths=(2,),
    )
    stressed = next(
        row
        for row in report.scenarios
        if row.scenario == "LOSS_CLUSTER_STRESS_BLOCK_2"
    )

    assert stressed.worst_loss_cluster_length == 3
    assert stressed.worst_loss_cluster_r == "-3"


def test_duplicate_entrant_identity_fails_closed() -> None:
    row = _trade(0, "1")
    with pytest.raises(ValueError, match="unique entrant identities"):
        mc.build_monte_carlo_report(
            (row, row),
            population_role="TEST",
            replicates=10,
            block_lengths=(2,),
        )
