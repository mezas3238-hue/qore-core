from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_compound_adversarial_stress import (
    COMPOUND_STRESS_POLICY_SHA256,
    CompoundStressKind,
    CompoundStressScenario,
    apply_compound_stress,
    run_compound_adversarial_stress,
)
from qore.infrastructure.cibo_compound_path_monte_carlo import (
    CompoundMonteCarloEpisode,
    CompoundMonteCarloInitialState,
)

T0 = datetime(2026, 9, 30, 9, 30, tzinfo=UTC)


def _episode(
    episode_id: str,
    *,
    minute: int,
    generation: int,
    pnl: str,
) -> CompoundMonteCarloEpisode:
    return CompoundMonteCarloEpisode(
        episode_id=episode_id,
        deployment_id=f"{episode_id}:deployment",
        market_event_id=f"{episode_id}:market",
        decision_id=f"{episode_id}:decision",
        candidate_id=f"{episode_id}:candidate",
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint=f"{episode_id}:signal",
        deployed_at=T0 + timedelta(minutes=minute),
        settled_at=T0 + timedelta(minutes=minute + 5),
        source_generation=generation,
        deployed_capital_usd=Decimal("5"),
        stop_risk_usd=Decimal("1"),
        margin_usd=Decimal("2"),
        realized_pnl_usd=Decimal(pnl),
        protected_floor_graduation_usd=Decimal(0),
        floor_evidence_sha256=None,
        market_record_present=True,
        terminal_release_present=True,
    )


def _episodes() -> tuple[CompoundMonteCarloEpisode, ...]:
    return (
        _episode("winner", minute=0, generation=1, pnl="4"),
        _episode("loss", minute=10, generation=1, pnl="-1"),
        _episode("gen2-loss", minute=20, generation=2, pnl="-1"),
    )


def _initial() -> CompoundMonteCarloInitialState:
    return CompoundMonteCarloInitialState(
        original_base_usd=Decimal("100"),
        generation_capacity_usd=((1, Decimal("20")),),
        protected_floor_usd=Decimal(0),
        total_stop_risk_capacity_usd=Decimal("3"),
        total_margin_capacity_usd=Decimal("10"),
    )


def _scenario(
    kind: CompoundStressKind,
    *,
    severity: str = "1",
) -> CompoundStressScenario:
    return CompoundStressScenario(
        scenario_id=kind.value.lower(),
        kind=kind,
        severity=Decimal(severity),
        evidence_sha256="sha256:" + "a" * 64,
    )


def test_compound_stress_policy_digest_is_frozen() -> None:
    assert COMPOUND_STRESS_POLICY_SHA256 == (
        "sha256:99ef9dbf2f6c98b161ee5d04568ba0b89bd6dc5d5f8b11cda2f10ef2f64ac46d"
    )


def test_losses_first_places_loser_before_winner() -> None:
    stressed = apply_compound_stress(
        episodes=_episodes(),
        scenario=_scenario(CompoundStressKind.LOSSES_FIRST),
    )
    assert stressed[0].realized_pnl_usd < 0
    assert stressed[-1].realized_pnl_usd > 0


def test_margin_hike_increases_margin_without_changing_stop_risk() -> None:
    stressed = apply_compound_stress(
        episodes=_episodes(),
        scenario=_scenario(
            CompoundStressKind.MARGIN_HIKE,
            severity="0.5",
        ),
    )
    assert stressed[0].margin_usd == Decimal("3")
    assert stressed[0].stop_risk_usd == Decimal("1")


def test_correlation_convergence_forces_overlap() -> None:
    stressed = apply_compound_stress(
        episodes=_episodes(),
        scenario=_scenario(CompoundStressKind.CORRELATION_CONVERGENCE),
    )
    assert stressed[1].deployed_at < stressed[0].settled_at
    assert stressed[2].deployed_at < stressed[0].settled_at


def test_gen_n_losses_early_exposes_generation_dependency_fragility() -> None:
    results = run_compound_adversarial_stress(
        initial=_initial(),
        episodes=_episodes(),
        scenarios=(
            _scenario(CompoundStressKind.GEN_N_LOSSES_EARLY),
        ),
        simulations=1,
        draws_per_path=1,
        components_per_block=3,
        base_seed=1,
    )
    result = results[0].monte_carlo.results[0]
    assert result.dependency_breach_count >= 1
    assert result.market_probability_claimed is False


def test_gap_slippage_never_increases_positive_pnl() -> None:
    stressed = apply_compound_stress(
        episodes=_episodes(),
        scenario=_scenario(
            CompoundStressKind.GAP_AND_SLIPPAGE,
            severity="1",
        ),
    )
    original = {item.episode_id: item for item in _episodes()}
    for item in stressed:
        assert item.realized_pnl_usd <= original[item.episode_id].realized_pnl_usd

def test_stress_result_rejects_manual_episode_count_drift() -> None:
    result = run_compound_adversarial_stress(
        initial=_initial(),
        episodes=_episodes(),
        scenarios=(_scenario(CompoundStressKind.MARGIN_HIKE),),
        simulations=1,
        draws_per_path=1,
        components_per_block=3,
        base_seed=1,
    )[0]

    with pytest.raises(
        CiboCompoundCapitalError,
        match="episode-count drift",
    ):
        replace(result, stressed_episode_count=2)

