from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19NormalizedCapitalAllocation,
    Phase19NormalizedReplayTrade,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase21_historical_shadow import (
    EXPECTED_ROWS_BY_TRADER,
    VALIDATION_START,
    evaluate_phase21_historical_shadow,
    frozen_v3_structural_selection,
)


def _population() -> tuple[Phase19NormalizedReplayTrade, ...]:
    rows = []
    index = 0
    positive = {
        trader
        for trader in EXPECTED_ROWS_BY_TRADER
        if frozen_v3_structural_selection(trader)
    }
    for trader, count in EXPECTED_ROWS_BY_TRADER.items():
        for _ in range(count):
            decision_at = VALIDATION_START + timedelta(
                hours=index * 3,
            )
            entry_at = decision_at + timedelta(minutes=1)
            exit_at = entry_at + timedelta(minutes=30)
            fingerprint = f"phase21-test-{index}"
            opportunity = Phase19ChronologicalOpportunity(
                trader_id=trader,
                signal_fingerprint=fingerprint,
                qore_symbol="TEST",
                entry_at=entry_at,
                exit_at=exit_at,
            )
            allocation = Phase19NormalizedCapitalAllocation(
                signal_fingerprint=fingerprint,
                trader_id=trader,
                decision_at=decision_at,
                risk_budget_ncu=Decimal("1"),
                allocation_priority=0,
                policy_id="PHASE21_TEST",
                evidence_id=f"evidence-{index}",
                train_cutoff_at=VALIDATION_START,
                outcome_aware=False,
            )
            rows.append(
                Phase19NormalizedReplayTrade(
                    opportunity=opportunity,
                    allocation=allocation,
                    normalized_outcome_r=(
                        Decimal("1") if trader in positive
                        else Decimal("-1")
                    ),
                    outcome_evidence_id=f"outcome-{index}",
                )
            )
            index += 1
    return tuple(rows)


def test_frozen_prior_selection_is_fixed_before_shadow() -> None:
    assert frozen_v3_structural_selection(TraderLineage.R38_GBPJPY)
    assert frozen_v3_structural_selection(TraderLineage.R43_GBPUSD)
    assert frozen_v3_structural_selection(TraderLineage.R42_AUDJPY)
    assert frozen_v3_structural_selection(TraderLineage.R34_XAUUSD)
    assert frozen_v3_structural_selection(TraderLineage.VT31_NAS100)
    assert not frozen_v3_structural_selection(TraderLineage.R38_EURUSD)
    assert not frozen_v3_structural_selection(TraderLineage.VT08_FOREX)


def test_phase21_shadow_screen_uses_post_train_population_only() -> None:
    report = evaluate_phase21_historical_shadow(_population())

    assert report.passed is True
    assert report.validation_rows == 332
    assert report.selected_outcomes == 256
    assert report.represented_lineages == 7
    assert report.monte_carlo.simulation_count == 1000
    assert report.policy.realized_delta_ncu > report.baseline.realized_delta_ncu
    assert (
        report.policy.capital_productivity_ncu_per_risk_minute
        > report.baseline.capital_productivity_ncu_per_risk_minute
    )
    assert report.final_holdout_2017h1_read is False
    assert report.policy_retuned_from_shadow_outcomes is False
