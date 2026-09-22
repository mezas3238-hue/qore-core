from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.fundednext_stellar_instant import (
    MAXIMUM_LOSS_FRACTION,
    SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION,
    AutomationVerificationState,
    RuleVerificationState,
    StellarInstantAccountSnapshot,
    StellarInstantContractError,
    StellarInstantRuleVerification,
    evaluate_stellar_instant_budget,
    opening_commission_per_lot,
    resolve_pilot_symbol,
)


def _snapshot(
    *,
    balance: str = "2000",
    equity: str = "2000",
    high: str = "2000",
    previous_mll: str = "1880",
    reported: str | None = None,
) -> StellarInstantAccountSnapshot:
    return StellarInstantAccountSnapshot(
        initial_balance=Decimal("2000"),
        balance=Decimal(balance),
        equity=Decimal(equity),
        highest_closed_balance=Decimal(high),
        previous_active_mll=Decimal(previous_mll),
        provider_reported_mll=Decimal(reported) if reported is not None else None,
    )


def test_2k_exact_account_contract_is_6pct_trailing_with_3pct_cumulative_open_risk_gate() -> None:
    budget = evaluate_stellar_instant_budget(_snapshot())
    assert MAXIMUM_LOSS_FRACTION == Decimal("0.06")
    assert SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION == Decimal("0.03")
    assert budget.loss_allowance == Decimal("120.00")
    assert budget.active_mll == Decimal("1880")
    assert budget.provider_headroom == Decimal("120")
    assert budget.max_risk_at_any_time == Decimal("60.00")
    assert budget.daily_loss_limit_present is False
    assert budget.separate_max_risk_at_any_time_fraction == Decimal("0.03")
    assert budget.payout_can_lower_mll is False


def test_trailing_floor_rises_never_falls_and_caps_at_starting_balance() -> None:
    risen = evaluate_stellar_instant_budget(
        _snapshot(balance="2050", equity="2050", high="2050")
    )
    assert risen.active_mll == Decimal("1930.00")

    after_loss = evaluate_stellar_instant_budget(
        _snapshot(balance="2010", equity="2010", high="2050", previous_mll="1930")
    )
    assert after_loss.active_mll == Decimal("1930")

    capped = evaluate_stellar_instant_budget(
        _snapshot(balance="2200", equity="2200", high="2200", previous_mll="1930")
    )
    assert capped.active_mll == Decimal("2000")


def test_payout_does_not_lower_previous_mll() -> None:
    budget = evaluate_stellar_instant_budget(
        _snapshot(balance="2010", equity="2010", high="2200", previous_mll="2000")
    )
    assert budget.active_mll == Decimal("2000")
    assert budget.provider_headroom == Decimal("10")
    assert budget.max_risk_at_any_time == Decimal("10")


def test_provider_report_cannot_loosen_reconstructed_floor() -> None:
    with pytest.raises(StellarInstantContractError):
        evaluate_stellar_instant_budget(
            _snapshot(high="2050", previous_mll="1880", reported="1900")
        )


def test_provider_breach_uses_equity_below_active_mll() -> None:
    budget = evaluate_stellar_instant_budget(
        _snapshot(balance="1900", equity="1879.99", high="2000")
    )
    assert budget.hard_breach is True
    assert budget.provider_headroom == 0


def test_exact_six_symbol_mapping_and_commissions() -> None:
    assert resolve_pilot_symbol("NAS100") == "NDX100"
    assert resolve_pilot_symbol("SP500") == "SPX500"
    assert resolve_pilot_symbol("US30") == "US30"
    assert opening_commission_per_lot("GBPUSD") == Decimal("7")
    assert opening_commission_per_lot("NAS100") == 0
    assert opening_commission_per_lot(
        "XAUUSD",
        executable_entry=Decimal("4342.90"),
        contract_size=Decimal("100"),
    ) == Decimal("6.9486400")
    with pytest.raises(StellarInstantContractError):
        resolve_pilot_symbol("EURUSD")


def test_automation_has_no_owner_expiry_and_fails_closed_when_unverified() -> None:
    now = datetime(2026, 9, 13, 18, 0, tzinfo=UTC)
    current = StellarInstantRuleVerification(
        verification_state=RuleVerificationState.CURRENT,
        automation_state=AutomationVerificationState.VERIFIED,
        ea_addon_verified=True,
        platform_verified=True,
        exact_product_verified=True,
    )
    assert current.automated_mt5_allowed(now) is True
    assert current.automated_mt5_allowed(now + timedelta(days=365)) is True

    unresolved = StellarInstantRuleVerification(
        verification_state=RuleVerificationState.CONFLICTED,
        automation_state=AutomationVerificationState.VERIFIED,
        ea_addon_verified=True,
        platform_verified=True,
        exact_product_verified=True,
    )
    assert unresolved.automated_mt5_allowed(now) is False
