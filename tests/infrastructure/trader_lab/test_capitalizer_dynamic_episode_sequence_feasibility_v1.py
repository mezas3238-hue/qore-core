from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_dynamic_episode_sequence_feasibility_v1 as seq,
)


def test_full_gate_requires_nonzero_intervention_and_six_r() -> None:
    baseline = {
        "profit_factor": "1.5",
        "total_r": "100",
        "max_drawdown_r": "7",
        "max_losing_streak": 6,
        "trades": 1000,
    }
    candidate = {
        "profit_factor": "1.6",
        "total_r": "101",
        "max_drawdown_r": "5.9",
        "max_losing_streak": 5,
        "trades": 1000,
    }

    assert seq._full_gate(
        candidate,
        baseline=baseline,
        intervention_count=1,
    )
    assert not seq._full_gate(
        candidate,
        baseline=baseline,
        intervention_count=0,
    )


def test_admissible_extension_is_monotone_on_dd_and_edge() -> None:
    baseline = {
        "profit_factor": "1.5",
        "total_r": "100",
        "max_drawdown_r": "7",
        "max_losing_streak": 6,
        "trades": 1000,
    }
    candidate = {
        "profit_factor": "1.5",
        "total_r": "100",
        "max_drawdown_r": "6.5",
        "max_losing_streak": 6,
        "trades": 1000,
    }

    assert seq._admissible_extension(
        candidate,
        baseline=baseline,
        current_dd=Decimal("6.8"),
    )
    candidate["total_r"] = "99.999"
    assert not seq._admissible_extension(
        candidate,
        baseline=baseline,
        current_dd=Decimal("6.8"),
    )


def test_identity_contract() -> None:
    assert seq.IDENTITY == (
        "QORE_CAPITALIZER_DYNAMIC_EPISODE_SEQUENCE_FEASIBILITY_V1"
    )
