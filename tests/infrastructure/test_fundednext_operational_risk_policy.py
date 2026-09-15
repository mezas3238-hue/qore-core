from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.fundednext_operational_risk_policy import (
    QORE_INTERNAL_ATTACK_HEAT_FRACTION,
    QORE_INTERNAL_BANK_HEAT_FRACTION,
    QORE_INTERNAL_NORMAL_HEAT_FRACTION,
    QORE_INTERNAL_TRAILING_LOSS_FRACTION,
    CapitalBudgetDecision,
    QoreOperationalCapitalBudget,
    evaluate_qore_operational_capital_budget,
)
from qore.infrastructure.fundednext_stellar_instant import (
    StellarInstantAccountSnapshot,
    StellarInstantRiskBudget,
    evaluate_stellar_instant_budget,
)
from qore.infrastructure.vt08_forex_cibo_operational import Vt08ForexCiboPosture


def _provider(
    *,
    balance: str = "2000",
    equity: str = "2000",
    high: str = "2000",
    previous_mll: str = "1880",
) -> StellarInstantRiskBudget:
    return evaluate_stellar_instant_budget(
        StellarInstantAccountSnapshot(
            initial_balance=Decimal("2000"),
            balance=Decimal(balance),
            equity=Decimal(equity),
            highest_closed_balance=Decimal(high),
            previous_active_mll=Decimal(previous_mll),
        )
    )


def _budget(
    posture: Vt08ForexCiboPosture,
    *,
    balance: str = "2000",
    equity: str = "2000",
    high: str = "2000",
    previous_mll: str = "1880",
    current_risk: str = "0",
) -> QoreOperationalCapitalBudget:
    provider = _provider(
        balance=balance,
        equity=equity,
        high=high,
        previous_mll=previous_mll,
    )
    return evaluate_qore_operational_capital_budget(
        provider_budget=provider,
        initial_balance=Decimal("2000"),
        balance=Decimal(balance),
        equity=Decimal(equity),
        highest_closed_balance=Decimal(high),
        current_aggregate_stop_risk=Decimal(current_risk),
        requested_posture=posture,
    )


def test_normal_policy_is_stricter_than_provider_6pct_wall() -> None:
    budget = _budget(Vt08ForexCiboPosture.NORMAL)
    assert budget.provider_maximum_loss_fraction == Decimal("0.06")
    assert budget.qore_internal_trailing_loss_fraction == Decimal("0.03")
    assert QORE_INTERNAL_TRAILING_LOSS_FRACTION < budget.provider_maximum_loss_fraction
    assert budget.provider_active_mll == Decimal("1880")
    assert budget.qore_internal_floor == Decimal("1940.00")
    assert budget.aggregate_heat_cap == Decimal("20.00")
    assert budget.qore_authorizable_headroom == Decimal("20.00")
    assert budget.available_risk_budget == Decimal("20.00")
    assert budget.decision is CapitalBudgetDecision.ALLOW


def test_attack_without_earned_cushion_is_reduced_to_normal() -> None:
    budget = _budget(Vt08ForexCiboPosture.ATTACK)
    assert budget.decision is CapitalBudgetDecision.REDUCE
    assert budget.authorized_posture is Vt08ForexCiboPosture.NORMAL
    assert budget.attack_authorized is False
    assert budget.aggregate_heat_cap == Decimal("20.00")
    assert QORE_INTERNAL_NORMAL_HEAT_FRACTION == Decimal("0.01")


def test_attack_requires_earned_closed_balance_cushion_and_never_uses_provider_wall() -> None:
    budget = _budget(
        Vt08ForexCiboPosture.ATTACK,
        balance="2025",
        equity="2025",
        high="2025",
    )
    assert budget.decision is CapitalBudgetDecision.ALLOW
    assert budget.authorized_posture is Vt08ForexCiboPosture.ATTACK
    assert budget.attack_authorized is True
    assert budget.earned_closed_balance_cushion == Decimal("25")
    assert budget.aggregate_heat_cap == Decimal("30.000")
    assert budget.qore_authorizable_headroom == Decimal("30.000")
    assert QORE_INTERNAL_ATTACK_HEAT_FRACTION == Decimal("0.015")


def test_bank_reduces_account_heat_without_changing_provider_contract() -> None:
    budget = _budget(Vt08ForexCiboPosture.BANK)
    assert budget.decision is CapitalBudgetDecision.ALLOW
    assert budget.aggregate_heat_cap == Decimal("10.000")
    assert QORE_INTERNAL_BANK_HEAT_FRACTION == Decimal("0.005")
    assert budget.provider_maximum_loss_fraction == Decimal("0.06")


def test_existing_account_heat_can_exhaust_new_risk_budget() -> None:
    budget = _budget(Vt08ForexCiboPosture.NORMAL, current_risk="20")
    assert budget.decision is CapitalBudgetDecision.REJECT
    assert budget.available_risk_budget == 0
    assert budget.reason == "qore-account-wide-heat-or-dd-budget-exhausted"


def test_provider_or_internal_dd_breach_rejects_new_risk() -> None:
    # This equity is above FundedNext's 1880 provider wall but below QORE's
    # internal 1940 floor plus its 10 USD safety buffer.
    budget = _budget(
        Vt08ForexCiboPosture.NORMAL,
        balance="1945",
        equity="1945",
        high="2000",
    )
    assert budget.decision is CapitalBudgetDecision.REJECT
    assert budget.qore_authorizable_headroom == 0
    assert budget.reason == "qore-internal-dd-buffer-exhausted"
