from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19NormalizedCapitalAllocation,
    Phase19NormalizedReplayTrade,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase19l_competition import (
    exact_competition_epochs,
    one_slot_delta_ncu,
    select_train_priority_candidate,
)


def _trade(
    trader: TraderLineage,
    *,
    entry_at: datetime,
    outcome: str,
    suffix: str,
    decision_at: datetime | None = None,
) -> Phase19NormalizedReplayTrade:
    signal = f"{trader.value}:{suffix}"
    opportunity = Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol=trader.value,
        entry_at=entry_at,
        exit_at=entry_at + timedelta(hours=1),
    )
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=signal,
        trader_id=trader,
        decision_at=decision_at or entry_at - timedelta(seconds=1),
        risk_budget_ncu=Decimal("1"),
        allocation_priority=0,
        policy_id="source",
        evidence_id=f"source:{signal}",
    )
    return Phase19NormalizedReplayTrade(
        opportunity=opportunity,
        allocation=allocation,
        normalized_outcome_r=Decimal(outcome),
        outcome_evidence_id=f"outcome:{signal}",
    )


def test_shared_entry_time_without_shared_decision_is_not_competition() -> None:
    now = datetime(2022, 4, 1, 12, tzinfo=UTC)
    trades = (
        _trade(
            TraderLineage.R38_GBPJPY,
            entry_at=now,
            decision_at=now - timedelta(minutes=10),
            outcome="1",
            suffix="a",
        ),
        _trade(
            TraderLineage.R43_GBPUSD,
            entry_at=now,
            decision_at=now - timedelta(minutes=5),
            outcome="-1",
            suffix="b",
        ),
    )

    assert exact_competition_epochs(trades) == ()


def test_shared_decision_time_forms_competition_epoch() -> None:
    now = datetime(2022, 4, 1, 12, tzinfo=UTC)
    decision = now - timedelta(minutes=5)
    trades = (
        _trade(
            TraderLineage.R38_GBPJPY,
            entry_at=now,
            decision_at=decision,
            outcome="1",
            suffix="a",
        ),
        _trade(
            TraderLineage.R43_GBPUSD,
            entry_at=now + timedelta(minutes=1),
            decision_at=decision,
            outcome="-1",
            suffix="b",
        ),
    )

    epochs = exact_competition_epochs(trades)

    assert len(epochs) == 1
    assert epochs[0].decision_at == decision
    assert len(epochs[0].candidates) == 2


def test_train_priority_selects_frozen_capital_velocity_winner() -> None:
    now = datetime(2022, 4, 1, 12, tzinfo=UTC)
    decision = now - timedelta(minutes=1)
    epoch = exact_competition_epochs(
        (
            _trade(
                TraderLineage.R38_GBPJPY,
                entry_at=now,
                decision_at=decision,
                outcome="-1",
                suffix="a",
            ),
            _trade(
                TraderLineage.VT31_NAS100,
                entry_at=now + timedelta(seconds=30),
                decision_at=decision,
                outcome="1",
                suffix="b",
            ),
        )
    )[0]

    selected = select_train_priority_candidate(epoch)

    assert selected.opportunity.trader_id is TraderLineage.VT31_NAS100


def test_one_slot_diagnostic_uses_outcomes_only_after_selection() -> None:
    now = datetime(2022, 4, 1, 12, tzinfo=UTC)
    decision = now - timedelta(minutes=1)
    epoch = exact_competition_epochs(
        (
            _trade(
                TraderLineage.R38_GBPJPY,
                entry_at=now,
                decision_at=decision,
                outcome="-1",
                suffix="a",
            ),
            _trade(
                TraderLineage.VT31_NAS100,
                entry_at=now + timedelta(seconds=30),
                decision_at=decision,
                outcome="2",
                suffix="b",
            ),
        )
    )[0]
    selected = select_train_priority_candidate(epoch)

    assert one_slot_delta_ncu((selected,)) == Decimal("0.50")
