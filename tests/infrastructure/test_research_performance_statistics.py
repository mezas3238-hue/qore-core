from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_economic_evidence import (
    ResearchCashCostCategory,
    ResearchCashCostStatus,
    ResearchEconomicResultId,
    ResearchFillId,
    ResearchReturnObservation,
    ResearchReturnObservationId,
    build_research_cash_cost_coverage,
    build_research_net_economic_result,
    build_research_return_observation,
)
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceSnapshotId,
    ResearchPerformanceStatisticsValidationError,
    build_research_performance_statistics,
)
from qore.infrastructure.research_run import ResearchRunEvidence, ResearchRunId
from qore.kernel.result import Failure, Success
from tests.infrastructure import test_research_economic_evidence as economic


def _uuid(suffix: int) -> UUID:
    return UUID(f"67000000-0000-0000-0000-{suffix:012d}")


def _gross_return(
    run: ResearchRunEvidence,
    *,
    suffix: int,
    pnl: str,
    capital: str = "1000",
) -> ResearchReturnObservation:
    built_gross = economic._gross(run, pnl=pnl)
    assert isinstance(built_gross, Success)
    source = built_gross.value
    entry = replace(source.entry_fills[0], fill_id=ResearchFillId(_uuid(suffix * 10 + 1)))
    exit_fill = replace(
        source.exit_fills[0],
        fill_id=ResearchFillId(_uuid(suffix * 10 + 2)),
    )
    gross = replace(
        source,
        result_id=ResearchEconomicResultId(_uuid(suffix * 10 + 3)),
        entry_fills=(entry,),
        exit_fills=(exit_fill,),
        gross_pnl=economic._money(pnl),
        valued_at=economic._BASE + timedelta(minutes=2, seconds=suffix),
    )
    built_return = build_research_return_observation(
        observation_id=ResearchReturnObservationId(_uuid(suffix * 10 + 4)),
        source_result=gross,
        capital_basis=economic._money(capital),
        observed_at=gross.valued_at + timedelta(seconds=1),
    )
    assert isinstance(built_return, Success)
    return built_return.value


def _net_return(run: ResearchRunEvidence, *, suffix: int) -> ResearchReturnObservation:
    gross_return = _gross_return(run, suffix=suffix, pnl="100")
    gross = gross_return.source_result
    assert not hasattr(gross, "net_pnl")
    coverage = build_research_cash_cost_coverage(
        run=run,
        model_id=economic._COST_MODEL,
        required_categories=(ResearchCashCostCategory.FEE,),
        costs=(
            economic._cost(
                ResearchCashCostCategory.FEE,
                ResearchCashCostStatus.KNOWN,
                "10",
                suffix * 10 + 5,
            ),
        ),
    )
    assert isinstance(coverage, Success)
    net = build_research_net_economic_result(
        result_id=ResearchEconomicResultId(_uuid(suffix * 10 + 6)),
        gross_result=gross,
        cost_coverage=coverage.value,
        valued_at=gross.valued_at + timedelta(seconds=2),
    )
    assert isinstance(net, Success)
    built_return = build_research_return_observation(
        observation_id=ResearchReturnObservationId(_uuid(suffix * 10 + 7)),
        source_result=net.value,
        capital_basis=economic._money("1000"),
        observed_at=net.value.valued_at + timedelta(seconds=1),
    )
    assert isinstance(built_return, Success)
    return built_return.value


def test_statistics_are_derived_only_from_return_evidence() -> None:
    run = economic._run()
    observations = (
        _gross_return(run, suffix=1, pnl="100"),
        _gross_return(run, suffix=2, pnl="-50"),
        _gross_return(run, suffix=3, pnl="0"),
    )
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(100)),
        observations=tuple(reversed(observations)),
        observed_at=observations[-1].observed_at + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    snapshot = built.value
    assert snapshot.observations == observations
    assert snapshot.sample_size == 3
    assert snapshot.positive_count == 1
    assert snapshot.negative_count == 1
    assert snapshot.flat_count == 1
    assert snapshot.minimum_return == Decimal("-0.05")
    assert snapshot.maximum_return == Decimal("0.1")
    assert snapshot.mean_return == Decimal("0.01666666666666666666666666666666667")
    assert snapshot.win_rate == Decimal("0.3333333333333333333333333333333333")
    assert snapshot.population_variance > 0


def test_snapshot_rejects_mixed_research_runs() -> None:
    first_run = economic._run()
    second_run = replace(first_run, run_id=ResearchRunId(_uuid(200)))
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(201)),
        observations=(
            _gross_return(first_run, suffix=20, pnl="10"),
            _gross_return(second_run, suffix=21, pnl="20"),
        ),
        observed_at=economic._BASE + timedelta(minutes=4),
    )
    assert isinstance(built, Failure)
    assert "one research run" in str(built.error)


def test_snapshot_rejects_mixed_gross_and_net_basis() -> None:
    run = economic._run()
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(300)),
        observations=(
            _gross_return(run, suffix=30, pnl="100"),
            _net_return(run, suffix=31),
        ),
        observed_at=economic._BASE + timedelta(minutes=4),
    )
    assert isinstance(built, Failure)
    assert "gross-or-net return basis" in str(built.error)


def test_snapshot_rejects_reused_fill_evidence_under_new_result_identity() -> None:
    run = economic._run()
    original = _gross_return(run, suffix=40, pnl="25")
    duplicated_result = replace(
        original.source_result,
        result_id=ResearchEconomicResultId(_uuid(401)),
    )
    duplicated_return = replace(
        original,
        observation_id=ResearchReturnObservationId(_uuid(402)),
        source_result=duplicated_result,
    )
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(403)),
        observations=(original, duplicated_return),
        observed_at=duplicated_return.observed_at + timedelta(seconds=1),
    )
    assert isinstance(built, Failure)
    assert "reuse economic fill evidence" in str(built.error)


def test_snapshot_rejects_metric_tampering() -> None:
    run = economic._run()
    observations = (
        _gross_return(run, suffix=50, pnl="10"),
        _gross_return(run, suffix=51, pnl="20"),
    )
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(500)),
        observations=observations,
        observed_at=observations[-1].observed_at + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    with pytest.raises(ResearchPerformanceStatisticsValidationError):
        replace(built.value, mean_return=Decimal("999"))


def test_statistics_boundary_does_not_claim_advanced_metrics() -> None:
    run = economic._run()
    observation = _gross_return(run, suffix=60, pnl="10")
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(600)),
        observations=(observation,),
        observed_at=observation.observed_at,
    )
    assert isinstance(built, Success)
    snapshot = built.value
    assert not hasattr(snapshot, "sharpe_ratio")
    assert not hasattr(snapshot, "sortino_ratio")
    assert not hasattr(snapshot, "max_drawdown")
    assert not hasattr(snapshot, "annualized_return")
    assert not hasattr(snapshot, "equity_curve")
