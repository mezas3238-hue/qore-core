from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_counterfactual_portfolio_episode_simulator_v1 as simulator,
)


def test_effect_sign() -> None:
    assert simulator._sign(Decimal("1")) == 1
    assert simulator._sign(Decimal("-0.01")) == -1
    assert simulator._sign(Decimal("0")) == 0


def test_pf_gate_handles_none() -> None:
    assert simulator._pf_at_least("2", "1") is True
    assert simulator._pf_at_least("0.9", "1") is False
    assert simulator._pf_at_least(None, "1") is False
    assert simulator._pf_at_least(None, None) is True


def test_action_summary_empty_contract() -> None:
    assert simulator._action_summary(()) == {
        "transitions": 0,
        "improves_total_r_and_legacy_dd": 0,
        "feedback_sign_changes": 0,
        "single_intervention_full_gate": 0,
    }


def test_simulator_identity_and_non_candidate_contract() -> None:
    assert simulator.IDENTITY == (
        "QORE_CAPITALIZER_COUNTERFACTUAL_PORTFOLIO_EPISODE_SIMULATOR_V1"
    )
