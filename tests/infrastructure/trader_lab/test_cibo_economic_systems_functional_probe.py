from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_compound_adversarial_stress import (
    CompoundStressKind,
    CompoundStressScenario,
    audit_compound_stress_family_coverage,
    run_compound_adversarial_stress,
)
from qore.infrastructure.cibo_compound_path_monte_carlo import (
    CompoundMonteCarloEpisode,
    CompoundMonteCarloInitialState,
    run_compound_path_monte_carlo,
)
from qore.infrastructure.cibo_compound_temporal_replication import (
    CompoundTemporalFold,
    run_compound_temporal_replication,
)
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def _initial() -> CompoundMonteCarloInitialState:
    return CompoundMonteCarloInitialState(
        original_base_usd=Decimal("100"),
        generation_capacity_usd=((1, Decimal("20")),),
        protected_floor_usd=Decimal("0"),
        total_stop_risk_capacity_usd=Decimal("4"),
        total_margin_capacity_usd=Decimal("12"),
    )


def _episode(
    candidate: TraderLabCandidateBinding,
    suffix: str,
    *,
    start: datetime,
    generation: int,
    pnl: str,
    floor: str = "0",
) -> CompoundMonteCarloEpisode:
    floor_amount = Decimal(floor)
    return CompoundMonteCarloEpisode(
        episode_id=_tag(candidate, suffix),
        deployment_id=_tag(candidate, f"{suffix}:deployment"),
        market_event_id=_tag(candidate, f"{suffix}:market"),
        decision_id=_tag(candidate, f"{suffix}:decision"),
        candidate_id=_tag(candidate, f"{suffix}:candidate"),
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint=_tag(candidate, f"{suffix}:signal"),
        deployed_at=start,
        settled_at=start + timedelta(minutes=5),
        source_generation=generation,
        deployed_capital_usd=Decimal("5"),
        stop_risk_usd=Decimal("1"),
        margin_usd=Decimal("2"),
        realized_pnl_usd=Decimal(pnl),
        protected_floor_graduation_usd=floor_amount,
        floor_evidence_sha256=(
            "sha256:" + "a" * 64 if floor_amount > 0 else None
        ),
        market_record_present=True,
        terminal_release_present=True,
    )


def test_trader_lab_capital_generations_and_path_monte_carlo(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=960)
    episodes = (
        _episode(
            candidate,
            "gen1-win",
            start=T0,
            generation=1,
            pnl="8",
            floor="3",
        ),
        _episode(
            candidate,
            "gen2-use",
            start=T0 + timedelta(minutes=10),
            generation=2,
            pnl="2",
        ),
    )

    summary = run_compound_path_monte_carlo(
        initial=_initial(),
        episodes=episodes,
        simulations=2,
        draws_per_path=1,
        components_per_block=2,
        base_seed=11,
    )

    assert summary.simulation_count == 2
    assert summary.market_probability_claimed is False
    assert summary.certification_ready is False
    assert all(result.future_leakage_used is False for result in summary.results)
    assert all(result.productive_authority is False for result in summary.results)
    assert all(result.ending_realized_capital_usd >= 0 for result in summary.results)
    assert any(
        any(generation >= 2 for generation, _amount in result.ending_generation_capacity_usd)
        for result in summary.results
    )


def test_trader_lab_all_adversarial_stress_families_execute(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=961)
    episodes = (
        _episode(candidate, "winner", start=T0, generation=1, pnl="4"),
        _episode(
            candidate,
            "loss",
            start=T0 + timedelta(minutes=10),
            generation=1,
            pnl="-1",
        ),
        _episode(
            candidate,
            "gen2-loss",
            start=T0 + timedelta(minutes=20),
            generation=2,
            pnl="-1",
        ),
    )
    scenarios = tuple(
        CompoundStressScenario(
            scenario_id=_tag(candidate, f"stress:{kind.value}"),
            kind=kind,
            severity=Decimal("0.5"),
            evidence_sha256="sha256:" + "b" * 64,
        )
        for kind in CompoundStressKind
    )

    coverage = audit_compound_stress_family_coverage(scenarios)
    results = run_compound_adversarial_stress(
        initial=_initial(),
        episodes=episodes,
        scenarios=scenarios,
        simulations=1,
        draws_per_path=1,
        components_per_block=3,
        base_seed=17,
    )

    assert coverage.all_frozen_stress_families_represented is True
    assert coverage.scenario_count == len(tuple(CompoundStressKind))
    assert len(results) == len(tuple(CompoundStressKind))
    assert all(item.market_probability_claimed is False for item in results)
    assert all(item.certification_ready is False for item in results)


def test_trader_lab_temporal_replication_keeps_folds_separate(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=962)
    fold_a_start = T0
    fold_b_start = T0 + timedelta(days=7)
    folds = (
        CompoundTemporalFold(
            fold_id=_tag(candidate, "fold-a"),
            start_at=fold_a_start,
            end_at=fold_a_start + timedelta(days=7),
            initial_state=_initial(),
            episodes=(
                _episode(
                    candidate,
                    "fold-a-episode",
                    start=fold_a_start,
                    generation=1,
                    pnl="1",
                ),
            ),
            provider_economics_sha256="sha256:" + "c" * 64,
        ),
        CompoundTemporalFold(
            fold_id=_tag(candidate, "fold-b"),
            start_at=fold_b_start,
            end_at=fold_b_start + timedelta(days=7),
            initial_state=_initial(),
            episodes=(
                _episode(
                    candidate,
                    "fold-b-episode",
                    start=fold_b_start,
                    generation=1,
                    pnl="1",
                ),
            ),
            provider_economics_sha256="sha256:" + "d" * 64,
        ),
    )

    report = run_compound_temporal_replication(
        research_id=_tag(candidate, "temporal-replication"),
        folds=folds,
        simulations_per_fold=2,
        draws_per_path=1,
        components_per_block=1,
        base_seed=23,
    )

    assert report.fold_count == 2
    assert report.same_policy_mechanics_all_folds is True
    assert report.outcomes_pooled_across_folds is False
    assert report.economic_replication_claimed is False
    assert report.certification_ready is False
