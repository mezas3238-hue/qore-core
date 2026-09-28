from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19NormalizedCapitalAllocation,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase19_temporal_concordance import (
    PHASE19K_FREEZE_AT,
    PHASE19K_POLICY,
    build_phase19k_candidate_allocation,
    phase19k_eligible_traders,
    phase19k_priority_order,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    prior_digest_sha256,
)


def _source(
    trader: TraderLineage,
    *,
    decision_at: datetime | None = None,
) -> tuple[Phase19ChronologicalOpportunity, Phase19NormalizedCapitalAllocation]:
    signal = f"phase19k:{trader.value}"
    decision = decision_at or PHASE19K_FREEZE_AT
    opportunity = Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol=trader.value,
        entry_at=decision + timedelta(minutes=1),
        exit_at=decision + timedelta(hours=1),
    )
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=signal,
        trader_id=trader,
        decision_at=decision,
        risk_budget_ncu=Decimal("1"),
        allocation_priority=0,
        policy_id="source",
        evidence_id=f"source:{trader.value}",
    )
    return opportunity, allocation


def test_temporal_concordance_uses_train_center_and_recent_block() -> None:
    assert phase19k_eligible_traders() == (
        TraderLineage.R38_GBPJPY,
        TraderLineage.R43_GBPUSD,
        TraderLineage.R34_XAUUSD,
        TraderLineage.VT31_NAS100,
    )
    assert TraderLineage.R42_AUDJPY not in phase19k_eligible_traders()
    assert TraderLineage.R38_EURUSD not in phase19k_eligible_traders()
    assert TraderLineage.VT08_FOREX not in phase19k_eligible_traders()


def test_priority_is_frozen_train_capital_velocity_not_trader_identity() -> None:
    assert phase19k_priority_order() == (
        TraderLineage.VT31_NAS100,
        TraderLineage.R38_GBPJPY,
        TraderLineage.R43_GBPUSD,
        TraderLineage.R34_XAUUSD,
    )


def test_candidate_allocation_retains_predeclared_quarter_ncu() -> None:
    opportunity, source = _source(TraderLineage.VT31_NAS100)
    allocation = build_phase19k_candidate_allocation(
        opportunity=opportunity,
        source_allocation=source,
    )

    assert allocation is not None
    assert allocation.risk_budget_ncu == Decimal("0.25")
    assert allocation.allocation_priority == 0
    assert allocation.train_cutoff_at == PHASE19K_FREEZE_AT
    assert allocation.outcome_aware is False
    assert prior_digest_sha256() in allocation.evidence_id


def test_candidate_blocks_non_concordant_trader_without_outcome_input() -> None:
    opportunity, source = _source(TraderLineage.R42_AUDJPY)

    assert (
        build_phase19k_candidate_allocation(
            opportunity=opportunity,
            source_allocation=source,
        )
        is None
    )


def test_candidate_rejects_pre_freeze_decision() -> None:
    opportunity, source = _source(
        TraderLineage.VT31_NAS100,
        decision_at=PHASE19K_FREEZE_AT - timedelta(seconds=1),
    )

    with pytest.raises(CiboCapitalManagementError, match="pre-freeze"):
        build_phase19k_candidate_allocation(
            opportunity=opportunity,
            source_allocation=source,
        )


def test_policy_discloses_post_validation_research_status() -> None:
    assert PHASE19K_POLICY.post_validation_hypothesis is True
    assert PHASE19K_POLICY.independent_validation_available is False
    assert PHASE19K_POLICY.outcome_aware_at_decision is False
    assert PHASE19K_POLICY.historical_provider_usd_claimed is False
    assert PHASE19K_POLICY.holdout_2017h1_used is False
    assert PHASE19K_POLICY.allocation_authority is False
    assert PHASE19K_POLICY.risk_authority is False
    assert PHASE19K_POLICY.execution_authority is False
