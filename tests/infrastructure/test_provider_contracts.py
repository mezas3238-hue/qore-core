from decimal import Decimal

import pytest

from qore.infrastructure.provider_contracts import (
    FTMO_1_STEP_CHALLENGE,
    FTMO_2_STEP_PHASE_1,
    FTMO_2_STEP_PHASE_2,
    FUNDEDNEXT_STELLAR_1_STEP,
    FUNDEDNEXT_STELLAR_2_STEP_PHASE_1,
    FUNDEDNEXT_STELLAR_2_STEP_PHASE_2,
    AutomationMode,
    ProviderAccountSnapshot,
    ProviderContract,
    ProviderContractError,
    RuleAuthority,
    TradingPlatform,
    evaluate_provider_budget,
    execution_capability,
)


def _snapshot(
    *,
    balance: str = "100000",
    equity: str = "100000",
    daily_reset_balance: str = "100000",
    highest_eod_balance: str = "100000",
    trading_days: int = 0,
    open_positions: int = 0,
    best_day_profit: str = "0",
    positive_days_profit: str = "0",
) -> ProviderAccountSnapshot:
    return ProviderAccountSnapshot(
        initial_balance=Decimal("100000"),
        balance=Decimal(balance),
        equity=Decimal(equity),
        daily_reset_balance=Decimal(daily_reset_balance),
        highest_eod_balance=Decimal(highest_eod_balance),
        trading_days_completed=trading_days,
        open_positions=open_positions,
        best_day_profit=Decimal(best_day_profit),
        positive_days_profit=Decimal(positive_days_profit),
    )


def test_ftmo_one_step_uses_eod_trailing_not_intraday_peak() -> None:
    budget = evaluate_provider_budget(
        FTMO_1_STEP_CHALLENGE,
        _snapshot(
            balance="108000",
            equity="108000",
            daily_reset_balance="104000",
            highest_eod_balance="104000",
        ),
    )

    assert budget.daily_floor == Decimal("101000.00")
    assert budget.overall_floor == Decimal("94000.00")
    assert budget.overall_headroom == Decimal("14000.00")


def test_ftmo_one_step_eod_floor_can_only_follow_eod_reference() -> None:
    previous = evaluate_provider_budget(
        FTMO_1_STEP_CHALLENGE,
        _snapshot(highest_eod_balance="104000"),
    )
    advanced = evaluate_provider_budget(
        FTMO_1_STEP_CHALLENGE,
        _snapshot(highest_eod_balance="107000"),
    )

    assert previous.overall_floor == Decimal("94000.00")
    assert advanced.overall_floor == Decimal("97000.00")


def test_ftmo_two_step_overall_floor_remains_static_after_profit() -> None:
    budget = evaluate_provider_budget(
        FTMO_2_STEP_PHASE_1,
        _snapshot(
            balance="112000",
            equity="112000",
            daily_reset_balance="110000",
            highest_eod_balance="112000",
            trading_days=4,
        ),
    )

    assert budget.overall_floor == Decimal("90000.00")
    assert budget.overall_headroom == Decimal("22000.00")
    assert budget.daily_floor == Decimal("105000.00")
    assert budget.profit_target_met
    assert budget.minimum_trading_days_met
    assert budget.challenge_completion_eligible


def test_ftmo_two_step_phase_two_target_is_five_percent() -> None:
    budget = evaluate_provider_budget(
        FTMO_2_STEP_PHASE_2,
        _snapshot(balance="105000", equity="105000", trading_days=4),
    )

    assert budget.profit_target_balance == Decimal("105000.00")
    assert budget.challenge_completion_eligible


def test_ftmo_one_step_best_day_rule_is_completion_not_loss_budget() -> None:
    budget = evaluate_provider_budget(
        FTMO_1_STEP_CHALLENGE,
        _snapshot(
            balance="110000",
            equity="110000",
            daily_reset_balance="108000",
            highest_eod_balance="108000",
            best_day_profit="7000",
            positive_days_profit="10000",
        ),
    )

    assert not budget.hard_breach
    assert budget.profit_target_met
    assert not budget.best_day_rule_met
    assert not budget.challenge_completion_eligible


def test_fundednext_stellar_one_step_uses_static_six_percent_floor() -> None:
    budget = evaluate_provider_budget(
        FUNDEDNEXT_STELLAR_1_STEP,
        _snapshot(
            balance="110000",
            equity="110000",
            daily_reset_balance="108000",
            highest_eod_balance="110000",
            trading_days=2,
        ),
    )

    assert budget.daily_floor == Decimal("105000.00")
    assert budget.overall_floor == Decimal("94000.00")
    assert budget.overall_headroom == Decimal("16000.00")
    assert budget.challenge_completion_eligible


@pytest.mark.parametrize(
    "contract,target",
    (
        (FUNDEDNEXT_STELLAR_2_STEP_PHASE_1, Decimal("108000.00")),
        (FUNDEDNEXT_STELLAR_2_STEP_PHASE_2, Decimal("105000.00")),
    ),
)
def test_fundednext_stellar_two_step_static_floor_and_targets(
    contract: ProviderContract,
    target: Decimal,
) -> None:
    budget = evaluate_provider_budget(
        contract,
        _snapshot(
            balance=str(target),
            equity=str(target),
            highest_eod_balance=str(target),
            trading_days=5,
        ),
    )

    assert budget.overall_floor == Decimal("90000.00")
    assert budget.profit_target_balance == target
    assert budget.challenge_completion_eligible


def test_provider_headroom_is_minimum_of_daily_and_overall() -> None:
    budget = evaluate_provider_budget(
        FUNDEDNEXT_STELLAR_2_STEP_PHASE_1,
        _snapshot(
            balance="104000",
            equity="104000",
            daily_reset_balance="103000",
            highest_eod_balance="104000",
        ),
    )

    assert budget.daily_floor == Decimal("98000.00")
    assert budget.overall_floor == Decimal("90000.00")
    assert budget.provider_headroom == Decimal("6000.00")
    assert budget.authority is RuleAuthority.PROVIDER_RULE


def test_equity_below_either_provider_floor_is_hard_breach() -> None:
    budget = evaluate_provider_budget(
        FUNDEDNEXT_STELLAR_1_STEP,
        _snapshot(equity="93999", daily_reset_balance="100000"),
    )

    assert budget.hard_breach
    assert budget.provider_headroom == Decimal("0")


def test_open_position_prevents_profit_target_completion() -> None:
    budget = evaluate_provider_budget(
        FTMO_2_STEP_PHASE_1,
        _snapshot(
            balance="111000",
            equity="111000",
            trading_days=4,
            open_positions=1,
        ),
    )

    assert not budget.profit_target_met
    assert not budget.challenge_completion_eligible


def test_ftmo_ctrader_automation_is_provider_supported() -> None:
    capability = execution_capability(
        FTMO_2_STEP_PHASE_1,
        platform=TradingPlatform.CTRADER,
        initial_balance=Decimal("200000"),
    )

    assert capability.mode is AutomationMode.AUTOMATED_ALLOWED
    assert capability.automated_order_submission_allowed


def test_fundednext_ctrader_is_manual_only() -> None:
    capability = execution_capability(
        FUNDEDNEXT_STELLAR_2_STEP_PHASE_1,
        platform=TradingPlatform.CTRADER,
        initial_balance=Decimal("25000"),
        fundednext_ea_addon_enabled=True,
    )

    assert capability.mode is AutomationMode.MANUAL_ONLY
    assert not capability.automated_order_submission_allowed


def test_fundednext_50k_or_larger_meta_account_is_manual_only() -> None:
    capability = execution_capability(
        FUNDEDNEXT_STELLAR_1_STEP,
        platform=TradingPlatform.MT5,
        initial_balance=Decimal("50000"),
        fundednext_ea_addon_enabled=True,
    )

    assert capability.mode is AutomationMode.MANUAL_ONLY
    assert not capability.automated_order_submission_allowed


def test_fundednext_sub_50k_meta_requires_confirmed_ea_option() -> None:
    without_addon = execution_capability(
        FUNDEDNEXT_STELLAR_1_STEP,
        platform=TradingPlatform.MT5,
        initial_balance=Decimal("25000"),
    )
    with_addon = execution_capability(
        FUNDEDNEXT_STELLAR_1_STEP,
        platform=TradingPlatform.MT5,
        initial_balance=Decimal("25000"),
        fundednext_ea_addon_enabled=True,
    )

    assert without_addon.mode is AutomationMode.CONDITIONAL
    assert not without_addon.automated_order_submission_allowed
    assert with_addon.mode is AutomationMode.CONDITIONAL
    assert with_addon.automated_order_submission_allowed


def test_unknown_platform_fails_closed() -> None:
    capability = execution_capability(
        FTMO_1_STEP_CHALLENGE,
        platform=TradingPlatform.UNKNOWN,
        initial_balance=Decimal("100000"),
    )

    assert capability.mode is AutomationMode.FAIL_CLOSED
    assert not capability.automated_order_submission_allowed


def test_invalid_snapshot_fails_closed() -> None:
    with pytest.raises(ProviderContractError):
        ProviderAccountSnapshot(
            initial_balance=Decimal("100000"),
            balance=Decimal("100000"),
            equity=Decimal("100000"),
            daily_reset_balance=Decimal("100000"),
            highest_eod_balance=Decimal("99999"),
            trading_days_completed=0,
        )
