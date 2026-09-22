from decimal import Decimal

import pytest

from qore.infrastructure.provider_contracts import (
    FTMO_1_STEP_CHALLENGE,
    FTMO_2_STEP_PHASE_1,
    FUNDEDNEXT_STELLAR_1_STEP,
    FUNDEDNEXT_STELLAR_2_STEP_PHASE_1,
    ChallengeProgram,
    ChallengeStage,
    Provider,
    ProviderAccountSnapshot,
    ProviderContractError,
    RuleAuthority,
    TradingPlatform,
    evaluate_provider_budget,
)
from qore.infrastructure.provider_operating import (
    BudgetRequestStatus,
    ExecutionRoute,
    ProviderAccountBinding,
    QoreRiskOverlayPolicy,
    apply_qore_risk_overlay,
    evaluate_bound_provider_budget,
    evaluate_requested_loss_budget,
    resolve_execution_route,
)


def _snapshot(
    *,
    initial: str = "100000",
    balance: str = "100000",
    equity: str = "100000",
    daily_reset_balance: str = "100000",
    highest_eod_balance: str = "100000",
) -> ProviderAccountSnapshot:
    return ProviderAccountSnapshot(
        initial_balance=Decimal(initial),
        balance=Decimal(balance),
        equity=Decimal(equity),
        daily_reset_balance=Decimal(daily_reset_balance),
        highest_eod_balance=Decimal(highest_eod_balance),
        trading_days_completed=0,
    )


def _binding(
    *,
    contract_id: str = FTMO_2_STEP_PHASE_1.contract_id,
    provider: Provider = Provider.FTMO,
    program: ChallengeProgram = ChallengeProgram.FTMO_2_STEP,
    stage: ChallengeStage = ChallengeStage.PHASE_1,
    platform: TradingPlatform = TradingPlatform.CTRADER,
    initial: str = "100000",
    addon: bool = False,
    enabled: bool = True,
) -> ProviderAccountBinding:
    return ProviderAccountBinding(
        binding_id="test-binding",
        contract_id=contract_id,
        provider=provider,
        program=program,
        stage=stage,
        platform=platform,
        initial_balance=Decimal(initial),
        rules_verified_on="2026-09-13",
        fundednext_ea_addon_enabled=addon,
        enabled=enabled,
    )


def test_qore_overlay_can_only_reduce_provider_headroom() -> None:
    snapshot = _snapshot(
        balance="104000",
        equity="104000",
        daily_reset_balance="103000",
        highest_eod_balance="104000",
    )
    provider_budget = evaluate_provider_budget(FTMO_2_STEP_PHASE_1, snapshot)
    effective = apply_qore_risk_overlay(
        provider_budget,
        snapshot,
        QoreRiskOverlayPolicy(
            policy_id="internal-buffer",
            daily_reserve_fraction=Decimal("0.005"),
            overall_reserve_fraction=Decimal("0.01"),
        ),
    )

    assert provider_budget.daily_headroom == Decimal("6000.000")
    assert provider_budget.overall_headroom == Decimal("14000.00")
    assert effective.qore_daily_headroom == Decimal("5500.000")
    assert effective.qore_overall_headroom == Decimal("13000.00")
    assert effective.authorizable_headroom == Decimal("5500.000")
    assert effective.authorizable_headroom <= provider_budget.provider_headroom
    assert effective.provider_authority is RuleAuthority.PROVIDER_RULE
    assert effective.qore_authority is RuleAuthority.QORE_POLICY


def test_zero_qore_overlay_preserves_provider_headroom_exactly() -> None:
    snapshot = _snapshot()
    provider_budget = evaluate_provider_budget(FUNDEDNEXT_STELLAR_1_STEP, snapshot)
    effective = apply_qore_risk_overlay(
        provider_budget,
        snapshot,
        QoreRiskOverlayPolicy(policy_id="zero-overlay"),
    )

    assert effective.authorizable_headroom == provider_budget.provider_headroom


def test_provider_hard_breach_forces_zero_effective_budget() -> None:
    snapshot = _snapshot(equity="93000")
    provider_budget = evaluate_provider_budget(FUNDEDNEXT_STELLAR_1_STEP, snapshot)
    effective = apply_qore_risk_overlay(
        provider_budget,
        snapshot,
        QoreRiskOverlayPolicy(policy_id="zero-overlay"),
    )

    assert provider_budget.hard_breach
    assert effective.authorizable_headroom == Decimal(0)
    assert effective.qore_suspended


def test_budget_request_is_not_risk_authorization_and_cannot_exceed_overlay() -> None:
    snapshot = _snapshot()
    provider_budget = evaluate_provider_budget(FTMO_2_STEP_PHASE_1, snapshot)
    effective = apply_qore_risk_overlay(
        provider_budget,
        snapshot,
        QoreRiskOverlayPolicy(
            policy_id="one-percent-daily-reserve",
            daily_reserve_fraction=Decimal("0.01"),
        ),
    )

    allowed = evaluate_requested_loss_budget(
        provider_budget,
        effective,
        Decimal("3000"),
    )
    rejected = evaluate_requested_loss_budget(
        provider_budget,
        effective,
        Decimal("4500"),
    )

    assert allowed.status is BudgetRequestStatus.WITHIN_BUDGET
    assert allowed.within_provider_headroom
    assert allowed.within_qore_headroom
    assert rejected.status is BudgetRequestStatus.EXCEEDS_QORE_BUDGET
    assert rejected.within_provider_headroom
    assert not rejected.within_qore_headroom


def test_static_provider_profit_cushion_is_not_retrailed_by_qore() -> None:
    snapshot = _snapshot(
        balance="108000",
        equity="108000",
        daily_reset_balance="108000",
        highest_eod_balance="108000",
    )
    provider_budget = evaluate_provider_budget(
        FUNDEDNEXT_STELLAR_2_STEP_PHASE_1,
        snapshot,
    )
    effective = apply_qore_risk_overlay(
        provider_budget,
        snapshot,
        QoreRiskOverlayPolicy(policy_id="zero-overlay"),
    )

    assert provider_budget.overall_headroom == Decimal("18000.00")
    assert effective.qore_overall_headroom == Decimal("18000.00")


def test_ftmo_one_step_trails_only_from_bound_eod_reference() -> None:
    snapshot = _snapshot(
        balance="109000",
        equity="109000",
        daily_reset_balance="104000",
        highest_eod_balance="104000",
    )
    provider_budget = evaluate_provider_budget(FTMO_1_STEP_CHALLENGE, snapshot)

    assert provider_budget.overall_floor == Decimal("94000.00")
    assert provider_budget.overall_headroom == Decimal("15000.00")


def test_bound_budget_requires_exact_initial_balance() -> None:
    binding = _binding(initial="200000")
    with pytest.raises(ProviderContractError):
        evaluate_bound_provider_budget(binding, _snapshot(initial="100000"))


def test_ftmo_ctrader_routes_to_automated_execution() -> None:
    decision = resolve_execution_route(_binding(platform=TradingPlatform.CTRADER))

    assert decision.route is ExecutionRoute.AUTOMATED
    assert decision.capability.automated_order_submission_allowed
    assert decision.activation_reverification_required


def test_ftmo_match_trader_fails_closed_even_if_low_level_capability_changes() -> None:
    decision = resolve_execution_route(_binding(platform=TradingPlatform.MATCH_TRADER))

    assert decision.route is ExecutionRoute.REJECT
    assert not decision.capability.automated_order_submission_allowed


def test_fundednext_ctrader_is_manual_handoff_below_100k() -> None:
    decision = resolve_execution_route(
        _binding(
            contract_id=FUNDEDNEXT_STELLAR_1_STEP.contract_id,
            provider=Provider.FUNDEDNEXT,
            program=ChallengeProgram.FUNDEDNEXT_STELLAR_1_STEP,
            stage=ChallengeStage.SINGLE_STEP,
            platform=TradingPlatform.CTRADER,
            initial="25000",
        )
    )

    assert decision.route is ExecutionRoute.MANUAL_HANDOFF
    assert not decision.capability.automated_order_submission_allowed


def test_fundednext_100k_ctrader_is_rejected_as_unavailable() -> None:
    decision = resolve_execution_route(
        _binding(
            contract_id=FUNDEDNEXT_STELLAR_2_STEP_PHASE_1.contract_id,
            provider=Provider.FUNDEDNEXT,
            program=ChallengeProgram.FUNDEDNEXT_STELLAR_2_STEP,
            stage=ChallengeStage.PHASE_1,
            platform=TradingPlatform.CTRADER,
            initial="100000",
        )
    )

    assert decision.route is ExecutionRoute.REJECT


@pytest.mark.parametrize("addon", (False, True))
def test_fundednext_25k_mt5_stays_manual_until_exact_product_reverified(
    addon: bool,
) -> None:
    decision = resolve_execution_route(
        _binding(
            contract_id=FUNDEDNEXT_STELLAR_2_STEP_PHASE_1.contract_id,
            provider=Provider.FUNDEDNEXT,
            program=ChallengeProgram.FUNDEDNEXT_STELLAR_2_STEP,
            stage=ChallengeStage.PHASE_1,
            platform=TradingPlatform.MT5,
            initial="25000",
            addon=addon,
        )
    )

    assert decision.route is ExecutionRoute.MANUAL_HANDOFF
    assert not decision.capability.automated_order_submission_allowed
    assert decision.capability.reason == (
        "fundednext-product-specific-automation-authority-unresolved"
    )


def test_fundednext_50k_mt5_is_manual_even_with_ea_option() -> None:
    decision = resolve_execution_route(
        _binding(
            contract_id=FUNDEDNEXT_STELLAR_2_STEP_PHASE_1.contract_id,
            provider=Provider.FUNDEDNEXT,
            program=ChallengeProgram.FUNDEDNEXT_STELLAR_2_STEP,
            stage=ChallengeStage.PHASE_1,
            platform=TradingPlatform.MT5,
            initial="50000",
            addon=True,
        )
    )

    assert decision.route is ExecutionRoute.MANUAL_HANDOFF
    assert not decision.capability.automated_order_submission_allowed


def test_disabled_binding_is_rejected() -> None:
    decision = resolve_execution_route(_binding(enabled=False))

    assert decision.route is ExecutionRoute.REJECT


def test_binding_mismatch_fails_closed() -> None:
    with pytest.raises(ProviderContractError):
        _binding(
            contract_id=FTMO_2_STEP_PHASE_1.contract_id,
            provider=Provider.FUNDEDNEXT,
        )
