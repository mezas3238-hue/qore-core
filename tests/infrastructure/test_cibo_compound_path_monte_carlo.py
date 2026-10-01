from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_compound_path_monte_carlo import (
    CompoundMonteCarloEpisode,
    CompoundMonteCarloInitialState,
    build_compound_monte_carlo_blocks,
    genc9_path_from_compound_monte_carlo,
    run_compound_path_monte_carlo,
)
from qore.infrastructure.cibo_robust_growth_ruin_capacity import (
    Genc9Numeraire,
)

T0 = datetime(2026, 9, 30, 9, 0, tzinfo=UTC)


def _episode(
    *,
    episode_id: str,
    start_minute: int,
    duration_minutes: int,
    generation: int,
    deployed: str,
    pnl: str,
    floor: str = "0",
) -> CompoundMonteCarloEpisode:
    floor_amount = Decimal(floor)
    return CompoundMonteCarloEpisode(
        episode_id=episode_id,
        deployment_id=f"{episode_id}:deployment",
        market_event_id=f"{episode_id}:market",
        decision_id=f"{episode_id}:decision",
        candidate_id=f"{episode_id}:candidate",
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint=f"{episode_id}:signal",
        deployed_at=T0 + timedelta(minutes=start_minute),
        settled_at=T0 + timedelta(
            minutes=start_minute + duration_minutes
        ),
        source_generation=generation,
        deployed_capital_usd=Decimal(deployed),
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


def _initial() -> CompoundMonteCarloInitialState:
    return CompoundMonteCarloInitialState(
        original_base_usd=Decimal("100"),
        generation_capacity_usd=((1, Decimal("20")),),
        protected_floor_usd=Decimal("0"),
        total_stop_risk_capacity_usd=Decimal("3"),
        total_margin_capacity_usd=Decimal("10"),
    )


def test_compound_blocks_preserve_overlap_components() -> None:
    episodes = (
        _episode(
            episode_id="a",
            start_minute=0,
            duration_minutes=10,
            generation=1,
            deployed="5",
            pnl="3",
        ),
        _episode(
            episode_id="b",
            start_minute=5,
            duration_minutes=10,
            generation=1,
            deployed="5",
            pnl="-1",
        ),
        _episode(
            episode_id="c",
            start_minute=30,
            duration_minutes=5,
            generation=1,
            deployed="5",
            pnl="1",
        ),
    )
    blocks = build_compound_monte_carlo_blocks(
        episodes=episodes,
        components_per_block=1,
    )

    assert len(blocks) == 2
    assert tuple(item.episode_id for item in blocks[0].episodes) == ("a", "b")
    assert tuple(item.episode_id for item in blocks[1].episodes) == ("c",)


def test_compound_mc_does_not_remap_missing_generation_dependency() -> None:
    gen2_first = _episode(
        episode_id="gen2",
        start_minute=0,
        duration_minutes=5,
        generation=2,
        deployed="5",
        pnl="2",
    )
    summary = run_compound_path_monte_carlo(
        initial=_initial(),
        episodes=(gen2_first,),
        simulations=1,
        draws_per_path=1,
        components_per_block=1,
        base_seed=7,
    )
    result = summary.results[0]

    assert result.dependency_breach_count == 1
    assert result.capacity_breach_count == 1
    assert result.rejected_episode_count == 1
    assert result.ending_realized_capital_usd == Decimal("120")


def test_compound_mc_winner_creates_next_generation_and_floor() -> None:
    winner = _episode(
        episode_id="gen1-win",
        start_minute=0,
        duration_minutes=5,
        generation=1,
        deployed="10",
        pnl="8",
        floor="3",
    )
    gen2 = _episode(
        episode_id="gen2-use",
        start_minute=10,
        duration_minutes=5,
        generation=2,
        deployed="5",
        pnl="2",
    )
    summary = run_compound_path_monte_carlo(
        initial=_initial(),
        episodes=(winner, gen2),
        simulations=1,
        draws_per_path=2,
        components_per_block=1,
        base_seed=1,
    )
    result = summary.results[0]

    assert result.protected_floor_usd >= Decimal("0")
    assert result.ending_realized_capital_usd >= Decimal("120")
    assert result.market_probability_claimed is False


def test_compound_mc_overlap_preserves_risk_and_margin_capacity() -> None:
    episodes = (
        _episode(
            episode_id="a",
            start_minute=0,
            duration_minutes=10,
            generation=1,
            deployed="5",
            pnl="0",
        ),
        _episode(
            episode_id="b",
            start_minute=1,
            duration_minutes=10,
            generation=1,
            deployed="5",
            pnl="0",
        ),
        _episode(
            episode_id="c",
            start_minute=2,
            duration_minutes=10,
            generation=1,
            deployed="5",
            pnl="0",
        ),
        _episode(
            episode_id="d",
            start_minute=3,
            duration_minutes=10,
            generation=1,
            deployed="5",
            pnl="0",
        ),
    )
    summary = run_compound_path_monte_carlo(
        initial=_initial(),
        episodes=episodes,
        simulations=1,
        draws_per_path=1,
        components_per_block=1,
        base_seed=3,
    )
    result = summary.results[0]

    assert result.peak_stop_risk_usd == Decimal("3")
    assert result.capacity_breach_count == 1
    assert result.rejected_episode_count == 1


def test_compound_mc_converts_to_genc9_usd_path_evidence() -> None:
    episode = _episode(
        episode_id="single",
        start_minute=0,
        duration_minutes=5,
        generation=1,
        deployed="5",
        pnl="2",
    )
    summary = run_compound_path_monte_carlo(
        initial=_initial(),
        episodes=(episode,),
        simulations=1,
        draws_per_path=1,
        components_per_block=1,
        base_seed=11,
    )
    evidence = genc9_path_from_compound_monte_carlo(
        candidate_id="control",
        scenario_id="mc-0",
        evaluated_at=T0 + timedelta(hours=1),
        scenario_evidence_sha256="sha256:" + "b" * 64,
        provider_economics_sha256="sha256:" + "c" * 64,
        initial=_initial(),
        result=summary.results[0],
        ruin_boundary_usd=Decimal("20"),
        horizon_minutes=Decimal("60"),
    )

    assert evidence.numeraire is Genc9Numeraire.PROVIDER_VALID_USD
    assert evidence.capacity_breach is False
    assert evidence.future_leakage_used is False
    assert evidence.market_probability_claimed is False


def test_floor_graduation_cannot_exceed_realized_profit() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="floor graduation exceeds realized profit",
    ):
        _episode(
            episode_id="bad-floor",
            start_minute=0,
            duration_minutes=5,
            generation=1,
            deployed="5",
            pnl="1",
            floor="2",
        )

def test_compound_mc_summary_rejects_manual_aggregate_drift() -> None:
    episode = _episode(
        episode_id="single-aggregate",
        start_minute=0,
        duration_minutes=5,
        generation=1,
        deployed="5",
        pnl="2",
    )
    summary = run_compound_path_monte_carlo(
        initial=_initial(),
        episodes=(episode,),
        simulations=1,
        draws_per_path=1,
        components_per_block=1,
        base_seed=13,
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="dependency breach aggregate drift",
    ):
        replace(summary, dependency_breach_paths=1)

