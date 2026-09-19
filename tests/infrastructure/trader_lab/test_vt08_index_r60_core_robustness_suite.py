from __future__ import annotations

from decimal import Decimal

from qore.infrastructure import research_block_bootstrap as core_bootstrap
from qore.infrastructure.trader_lab import (
    vt08_index_r60_core_robustness_suite as r60,
)


def test_r60_is_bound_to_frozen_r58() -> None:
    assert r60.CANDIDATE_ID == (
        "VT08_INDEX_R58_EXACT_R47_DISTRIBUTED_CAUSAL_RISK_001"
    )
    assert r60.CANDIDATE_RULE_FINGERPRINT == (
        "e959c8578a7ac71658cd19daf6d61815dfe277ecd06d8100c2655b30a62f48fa"
    )
    assert r60.dependency_contract_matches() is True


def test_r60_preregistration_is_fixed() -> None:
    assert r60.BOOTSTRAP_POLICY.block_length == 5
    assert r60.BOOTSTRAP_POLICY.resample_count == 10_000
    assert r60.BOOTSTRAP_POLICY.seed == 20260919
    assert r60.HARD_STRESSES == (Decimal("0.15"), Decimal("0.20"))
    assert r60.HARD_STRESS_PF_MIN == Decimal("1.30")
    assert r60.PORTFOLIO_DD_MAX_R == Decimal("6")


def test_r60_uses_core_circular_draw_deterministically() -> None:
    first = core_bootstrap._draw_start(
        seed=r60.BOOTSTRAP_SEED,
        replicate=7,
        draw=3,
        sample_size=1017,
    )
    second = core_bootstrap._draw_start(
        seed=r60.BOOTSTRAP_SEED,
        replicate=7,
        draw=3,
        sample_size=1017,
    )
    assert first == second
    assert 0 <= first < 1017


def test_r60_wfo_contract_is_chronological() -> None:
    five = r60._five_year_folds()
    two = r60._two_year_folds()
    assert len(five) == 3
    assert len(two) == 3
    for fold in (*five, *two):
        assert fold.in_sample.closed_at <= fold.out_of_sample.opened_at
