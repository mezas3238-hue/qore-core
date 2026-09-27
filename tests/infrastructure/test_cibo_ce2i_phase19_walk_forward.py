from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedCapitalAllocation,
    Phase19NormalizedReplayTrade,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase19_simple_policy import (
    Phase19SimpleCapitalPolicy,
    replay_phase19_simple_policy,
)
from qore.infrastructure.cibo_ce2i_phase19_walk_forward import (
    build_phase19j_walk_forward_folds,
    phase19j_survival_failures,
)

START = datetime(2022, 3, 9, 17, tzinfo=UTC)
END = datetime(2022, 6, 29, 9, tzinfo=UTC)


def _trade(
    *,
    signal: str,
    entry_at: datetime,
    outcome: str,
) -> Phase19NormalizedReplayTrade:
    opportunity = Phase19ChronologicalOpportunity(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint=signal,
        qore_symbol="EURUSD",
        entry_at=entry_at,
        exit_at=entry_at + timedelta(hours=1),
    )
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=signal,
        trader_id=TraderLineage.R38_EURUSD,
        decision_at=entry_at - timedelta(seconds=1),
        risk_budget_ncu=Decimal("1"),
        allocation_priority=0,
        policy_id="source",
        evidence_id=f"source:{signal}",
        train_cutoff_at=START - timedelta(days=1),
    )
    return Phase19NormalizedReplayTrade(
        opportunity=opportunity,
        allocation=allocation,
        normalized_outcome_r=Decimal(outcome),
        outcome_evidence_id=f"outcome:{signal}",
    )


def _policy() -> Phase19SimpleCapitalPolicy:
    return Phase19SimpleCapitalPolicy(
        policy_id="wf-test",
        gross_initial_capital_ncu=Decimal("10"),
        fixed_reserve_ncu=Decimal("0"),
        risk_budget_ncu=Decimal("0.25"),
    )


def test_walk_forward_folds_are_two_equal_time_halves_without_refit() -> None:
    folds = build_phase19j_walk_forward_folds(
        frozen_at=START,
        common_end=END,
    )

    assert len(folds) == 2
    assert folds[0].validation_start_at == START
    assert folds[0].validation_end_at == folds[1].validation_start_at
    assert folds[1].validation_end_at == END
    assert all(item.policy_refit_authorized is False for item in folds)
    assert (
        folds[0].validation_end_at - START
        <= END - folds[0].validation_end_at
    )


def test_walk_forward_rejects_invalid_time_window() -> None:
    with pytest.raises(CiboCapitalManagementError, match="must follow"):
        build_phase19j_walk_forward_folds(
            frozen_at=START,
            common_end=START,
        )


def test_survival_gate_requires_positive_combined_and_each_fold() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="wf-test")
    policy = _policy()
    first = _trade(
        signal="first",
        entry_at=START + timedelta(days=1),
        outcome="1",
    )
    second = _trade(
        signal="second",
        entry_at=START + timedelta(days=70),
        outcome="1",
    )
    combined = replay_phase19_simple_policy(
        policy=policy,
        contract=contract,
        trades=(first, second),
    )
    fold1 = replay_phase19_simple_policy(
        policy=policy,
        contract=contract,
        trades=(first,),
    )
    fold2 = replay_phase19_simple_policy(
        policy=policy,
        contract=contract,
        trades=(second,),
    )

    assert (
        phase19j_survival_failures(
            combined=combined,
            folds=(fold1, fold2),
        )
        == ()
    )


def test_survival_gate_exposes_negative_forward_fold() -> None:
    contract = Phase19CapitalNumeraireContract(contract_id="wf-test")
    policy = _policy()
    first = _trade(
        signal="first",
        entry_at=START + timedelta(days=1),
        outcome="1",
    )
    second = _trade(
        signal="second",
        entry_at=START + timedelta(days=70),
        outcome="-2",
    )
    combined = replay_phase19_simple_policy(
        policy=policy,
        contract=contract,
        trades=(first, second),
    )
    fold1 = replay_phase19_simple_policy(
        policy=policy,
        contract=contract,
        trades=(first,),
    )
    fold2 = replay_phase19_simple_policy(
        policy=policy,
        contract=contract,
        trades=(second,),
    )

    failures = phase19j_survival_failures(
        combined=combined,
        folds=(fold1, fold2),
    )

    assert "COMBINED_REALIZED_DELTA_NOT_POSITIVE" in failures
    assert "FOLD_2_REALIZED_DELTA_NOT_POSITIVE" in failures
