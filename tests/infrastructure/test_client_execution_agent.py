from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

import qore.domain.events as domain_events
import qore.functional.decisions as decisions
import qore.infrastructure.account_policy as account_policy
import qore.infrastructure.client_accounts as client_accounts
import qore.infrastructure.client_execution_agent as client_agent
import qore.infrastructure.order_intent as order_intent
import qore.infrastructure.proprietary_accounts as proprietary_accounts
import qore.kernel.result as result

_EVALUATED_AT = datetime(2026, 8, 9, 6, 0, tzinfo=UTC)
_DECISION_AT = _EVALUATED_AT - timedelta(seconds=50)
_SECURITY_AT = _EVALUATED_AT - timedelta(seconds=30)
_OBSERVED_AT = _EVALUATED_AT - timedelta(seconds=20)
_CALCULATED_AT = _EVALUATED_AT - timedelta(seconds=10)
_USD = proprietary_accounts.CurrencyCode("USD")


def _uuid(suffix: int) -> UUID:
    return UUID(f"33000000-0000-0000-0000-{suffix:012d}")


def _decision(
    *,
    decision_id: decisions.DecisionId | None = None,
    outcome: decisions.DecisionOutcome | None = decisions.DecisionOutcome.APPROVED,
    status: decisions.DecisionStatus = decisions.DecisionStatus.RESOLVED,
    decision_type: str = "core.trade",
    side: order_intent.OrderSide = order_intent.OrderSide.BUY,
    order_type: order_intent.OrderType = order_intent.OrderType.MARKET,
    limit_price: order_intent.OrderPrice | None = None,
    expires_at: datetime | None = None,
) -> client_agent.CoreTradeDecision:
    reason_values: tuple[decisions.DecisionReason, ...]
    if status is decisions.DecisionStatus.RESOLVED:
        reason_values = (
            decisions.DecisionReason(
                code=decisions.DecisionReasonCode("strategy.approved"),
                summary="Canonical strategic decision fixture",
            ),
        )
    else:
        reason_values = ()
    functional = decisions.FunctionalDecision(
        decision_id=decision_id or decisions.DecisionId(_uuid(1)),
        timestamp=_DECISION_AT,
        decision_type=decisions.DecisionType(decision_type),
        status=status,
        priority=decisions.DecisionPriority.NORMAL,
        metadata=decisions.DecisionMetadata(
            correlation_id=domain_events.CorrelationId(_uuid(2)),
        ),
        reasons=reason_values,
        outcome=outcome,
    )
    return client_agent.CoreTradeDecision(
        decision=functional,
        instrument=order_intent.ExecutionInstrument("EUR_USD"),
        side=side,
        order_type=order_type,
        expires_at=expires_at or (_EVALUATED_AT + timedelta(minutes=4)),
        limit_price=limit_price,
    )


def _binding(
    *,
    client_suffix: int = 10,
    account_suffix: int = 11,
    policy_suffix: int = 12,
    entitlement_suffix: int = 13,
    runtime_suffix: int = 14,
    lifecycle: client_accounts.TradingAccountLifecycleState = (
        client_accounts.TradingAccountLifecycleState.ACTIVE
    ),
) -> client_accounts.ClientTradingAccountBinding:
    return client_accounts.ClientTradingAccountBinding(
        client_id=client_accounts.ClientId(_uuid(client_suffix)),
        account_id=client_accounts.TradingAccountId(_uuid(account_suffix)),
        account_kind=client_accounts.TradingAccountKind.PROP_FIRM,
        lifecycle_state=lifecycle,
        policy_ref=client_accounts.AccountPolicyReference(_uuid(policy_suffix)),
        product_entitlement_ref=client_accounts.ProductEntitlementReference(
            _uuid(entitlement_suffix)
        ),
        runtime_ref=client_accounts.ExecutionRuntimeReference(_uuid(runtime_suffix)),
    )


def _account_policy(
    binding: client_accounts.ClientTradingAccountBinding,
    *,
    snapshot_suffix: int = 20,
    max_drawdown: int = 1000,
    daily_loss: int = 500,
    drawdown_mode: account_policy.DrawdownMode = account_policy.DrawdownMode.STATIC,
    expires_at: datetime | None = None,
) -> account_policy.AccountPropPolicySnapshot:
    return account_policy.AccountPropPolicySnapshot(
        snapshot_id=account_policy.AccountPolicySnapshotId(_uuid(snapshot_suffix)),
        policy_ref=binding.policy_ref,
        account_id=binding.account_id,
        account_kind=binding.account_kind,
        version=account_policy.AccountPolicyVersion(1),
        effective_at=_EVALUATED_AT - timedelta(days=1),
        expires_at=expires_at,
        account_size=proprietary_accounts.MoneyAmount(_USD, Decimal("100000")),
        max_drawdown=proprietary_accounts.DrawdownBps(max_drawdown),
        daily_loss_limit=proprietary_accounts.DrawdownBps(daily_loss),
        drawdown_mode=drawdown_mode,
        phase=account_policy.AccountPhase.FUNDED,
        client_profit_split=account_policy.ProfitSplitBps(8000),
        firm_ref=account_policy.PropFirmReference(_uuid(21)),
        program_ref=account_policy.PropProgramReference(_uuid(22)),
        rules=(),
    )


def _observed_state(
    binding: client_accounts.ClientTradingAccountBinding,
    *,
    observation_suffix: int = 30,
    observed_at: datetime = _OBSERVED_AT,
    equity: Decimal = Decimal("100000"),
    currency: proprietary_accounts.CurrencyCode = _USD,
    current_drawdown: int = 100,
    daily_loss: int = 50,
) -> client_agent.ClientAccountObservedState:
    return client_agent.ClientAccountObservedState(
        observation_id=client_agent.ClientAccountObservationId(
            _uuid(observation_suffix)
        ),
        account_id=binding.account_id,
        observed_at=observed_at,
        balance=proprietary_accounts.MoneyAmount(currency, Decimal("100000")),
        equity=proprietary_accounts.MoneyAmount(currency, equity),
        current_drawdown=proprietary_accounts.DrawdownBps(current_drawdown),
        daily_loss=proprietary_accounts.DrawdownBps(daily_loss),
        open_positions=0,
    )


def _entitlement(
    binding: client_accounts.ClientTradingAccountBinding,
    *,
    state: client_agent.ClientAgentEntitlementState = (
        client_agent.ClientAgentEntitlementState.ENABLED
    ),
    evaluated_at: datetime = _OBSERVED_AT,
) -> client_agent.ClientAgentEntitlementSnapshot:
    return client_agent.ClientAgentEntitlementSnapshot(
        entitlement_ref=binding.product_entitlement_ref,
        account_id=binding.account_id,
        state=state,
        evaluated_at=evaluated_at,
    )


def _execution_policy(
    *,
    policy_suffix: int = 40,
    sizing_suffix: int = 41,
    protection_suffix: int = 42,
    trailing_suffix: int | None = 43,
    max_risk: int = 100,
    max_age: int = 120,
) -> client_agent.ClientExecutionPolicy:
    trailing = (
        client_agent.TrailingPolicyReference(_uuid(trailing_suffix))
        if trailing_suffix is not None
        else None
    )
    return client_agent.ClientExecutionPolicy(
        policy_id=client_agent.ClientExecutionPolicyId(_uuid(policy_suffix)),
        sizing_policy_ref=client_agent.SizingPolicyReference(_uuid(sizing_suffix)),
        protection_policy_ref=client_agent.ProtectionPolicyReference(
            _uuid(protection_suffix)
        ),
        trailing_policy_ref=trailing,
        max_risk_per_trade=proprietary_accounts.DrawdownBps(max_risk),
        max_account_state_age_seconds=max_age,
        max_entitlement_age_seconds=max_age,
        max_security_attestation_age_seconds=max_age,
    )


def _security(
    decision: client_agent.CoreTradeDecision,
    binding: client_accounts.ClientTradingAccountBinding,
    *,
    status: client_agent.DecisionSecurityStatus = (
        client_agent.DecisionSecurityStatus.VERIFIED
    ),
    account_id: client_accounts.TradingAccountId | None = None,
    runtime_ref: client_accounts.ExecutionRuntimeReference | None = None,
    verified_at: datetime = _SECURITY_AT,
    evidence_suffix: int = 50,
) -> client_agent.DecisionSecurityAttestation:
    return client_agent.DecisionSecurityAttestation(
        decision_id=decision.decision.decision_id,
        account_id=account_id or binding.account_id,
        runtime_ref=runtime_ref or binding.runtime_ref,
        status=status,
        evidence_ref=client_agent.DecisionSecurityEvidenceReference(
            _uuid(evidence_suffix)
        ),
        verified_at=verified_at,
    )


def _calculation(
    decision: client_agent.CoreTradeDecision,
    binding: client_accounts.ClientTradingAccountBinding,
    execution_policy: client_agent.ClientExecutionPolicy,
    *,
    account_id: client_accounts.TradingAccountId | None = None,
    decision_id: decisions.DecisionId | None = None,
    calculated_at: datetime = _CALCULATED_AT,
    entry: str = "1.1000",
    stop: str = "1.0950",
    take_profit: str = "1.1100",
    estimated_risk: int = 50,
    protection_ref: client_agent.ProtectionPolicyReference | None = None,
) -> client_agent.ClientExecutionCalculation:
    return client_agent.ClientExecutionCalculation(
        decision_id=decision_id or decision.decision.decision_id,
        account_id=account_id or binding.account_id,
        calculated_at=calculated_at,
        quantity=order_intent.OrderQuantity(Decimal("1.25")),
        entry_reference_price=order_intent.OrderPrice(Decimal(entry)),
        stop_loss=order_intent.OrderPrice(Decimal(stop)),
        take_profit=order_intent.OrderPrice(Decimal(take_profit)),
        estimated_risk=proprietary_accounts.DrawdownBps(estimated_risk),
        sizing_policy_ref=execution_policy.sizing_policy_ref,
        protection_policy_ref=protection_ref or execution_policy.protection_policy_ref,
        trailing_policy_ref=execution_policy.trailing_policy_ref,
    )


def _evaluate(
    *,
    decision: client_agent.CoreTradeDecision | None = None,
    binding: client_accounts.ClientTradingAccountBinding | None = None,
    policy: account_policy.AccountPropPolicySnapshot | None = None,
    observed: client_agent.ClientAccountObservedState | None = None,
    entitlement: client_agent.ClientAgentEntitlementSnapshot | None = None,
    execution_policy: client_agent.ClientExecutionPolicy | None = None,
    security: client_agent.DecisionSecurityAttestation | None = None,
    calculation: client_agent.ClientExecutionCalculation | None = None,
) -> result.Result[
    client_agent.ClientExecutionEvaluation,
    client_agent.ClientExecutionAgentError,
]:
    selected_decision = decision or _decision()
    selected_binding = binding or _binding()
    selected_policy = policy or _account_policy(selected_binding)
    selected_observed = observed or _observed_state(selected_binding)
    selected_entitlement = entitlement or _entitlement(selected_binding)
    selected_execution_policy = execution_policy or _execution_policy()
    selected_security = security or _security(selected_decision, selected_binding)
    selected_calculation = calculation or _calculation(
        selected_decision,
        selected_binding,
        selected_execution_policy,
    )
    return client_agent.evaluate_client_execution(
        selected_decision,
        selected_security,
        selected_binding,
        selected_policy,
        selected_observed,
        selected_entitlement,
        selected_execution_policy,
        selected_calculation,
        evaluated_at=_EVALUATED_AT,
    )


def _assert_blocked(
    evaluated: result.Result[
        client_agent.ClientExecutionEvaluation,
        client_agent.ClientExecutionAgentError,
    ],
    *,
    verdict: client_agent.ClientExecutionVerdict,
    reason: client_agent.ClientExecutionReason,
) -> None:
    assert isinstance(evaluated, result.Success)
    assert evaluated.value.verdict is verdict
    assert evaluated.value.reason is reason
    assert evaluated.value.plan is None


def test_core_trade_decision_reuses_functional_decision_and_order_semantics() -> None:
    decision = _decision()

    assert decision.decision.decision_type.value == "core.trade"
    assert decision.instrument == order_intent.ExecutionInstrument("EUR_USD")
    assert decision.side is order_intent.OrderSide.BUY
    assert decision.order_type is order_intent.OrderType.MARKET
    assert not hasattr(decision, "quantity")
    assert decision.logical_values() == decision.logical_values()

    with pytest.raises(client_agent.ClientExecutionAgentValidationError):
        _decision(decision_type="portfolio.rebalance")


def test_limit_core_decision_requires_canonical_limit_price() -> None:
    price = order_intent.OrderPrice(Decimal("1.0990"))
    decision = _decision(
        order_type=order_intent.OrderType.LIMIT,
        limit_price=price,
    )

    assert decision.limit_price == price

    with pytest.raises(client_agent.ClientExecutionAgentValidationError):
        _decision(order_type=order_intent.OrderType.LIMIT)


def test_account_observation_and_execution_policy_are_strict_contracts() -> None:
    binding = _binding()
    observed = _observed_state(binding)
    policy = _execution_policy()

    assert observed.account_id == binding.account_id
    assert observed.equity.logical_values() == ("USD", "100000")
    assert policy.max_risk_per_trade.logical_values() == (100,)
    assert policy.logical_values() == policy.logical_values()

    with pytest.raises(client_agent.ClientExecutionAgentValidationError):
        client_agent.ClientExecutionPolicy(
            policy_id=policy.policy_id,
            sizing_policy_ref=policy.sizing_policy_ref,
            protection_policy_ref=policy.protection_policy_ref,
            trailing_policy_ref=policy.trailing_policy_ref,
            max_risk_per_trade=policy.max_risk_per_trade,
            max_account_state_age_seconds=0,
            max_entitlement_age_seconds=120,
            max_security_attestation_age_seconds=120,
        )


def test_valid_account_evaluation_creates_auditable_plan_but_does_not_submit() -> None:
    evaluated = _evaluate()

    assert isinstance(evaluated, result.Success)
    assert evaluated.value.verdict is client_agent.ClientExecutionVerdict.EXECUTE
    assert evaluated.value.reason is client_agent.ClientExecutionReason.READY
    assert evaluated.value.plan is not None
    plan = evaluated.value.plan
    assert plan.decision_id == decisions.DecisionId(_uuid(1))
    assert plan.account_id == client_accounts.TradingAccountId(_uuid(11))
    assert plan.stop_loss == order_intent.OrderPrice(Decimal("1.0950"))
    assert plan.take_profit == order_intent.OrderPrice(Decimal("1.1100"))
    assert plan.account_policy_snapshot_id == account_policy.AccountPolicySnapshotId(
        _uuid(20)
    )
    assert plan.logical_values() == plan.logical_values()
    assert not hasattr(plan, "submit")
    assert not hasattr(plan, "broker")
    assert not hasattr(plan, "credentials")


def test_unapproved_or_expired_core_decision_blocks_new_trade() -> None:
    rejected = _decision(outcome=decisions.DecisionOutcome.REJECTED)
    expired = _decision(expires_at=_EVALUATED_AT)

    _assert_blocked(
        _evaluate(decision=rejected),
        verdict=client_agent.ClientExecutionVerdict.DECISION_BLOCKED,
        reason=client_agent.ClientExecutionReason.CORE_DECISION_NOT_APPROVED,
    )
    _assert_blocked(
        _evaluate(decision=expired),
        verdict=client_agent.ClientExecutionVerdict.DECISION_BLOCKED,
        reason=client_agent.ClientExecutionReason.CORE_DECISION_EXPIRED,
    )


def test_security_must_be_verified_and_bound_to_account_runtime() -> None:
    decision = _decision()
    binding = _binding()
    rejected = _security(
        decision,
        binding,
        status=client_agent.DecisionSecurityStatus.REJECTED,
    )
    wrong_account = _security(
        decision,
        binding,
        account_id=client_accounts.TradingAccountId(_uuid(999)),
    )

    _assert_blocked(
        _evaluate(decision=decision, binding=binding, security=rejected),
        verdict=client_agent.ClientExecutionVerdict.SECURITY_BLOCKED,
        reason=client_agent.ClientExecutionReason.SECURITY_NOT_VERIFIED,
    )
    _assert_blocked(
        _evaluate(decision=decision, binding=binding, security=wrong_account),
        verdict=client_agent.ClientExecutionVerdict.SECURITY_BLOCKED,
        reason=client_agent.ClientExecutionReason.SECURITY_BINDING_MISMATCH,
    )


def test_security_attestation_must_be_temporally_valid_and_fresh() -> None:
    decision = _decision()
    binding = _binding()
    future = _security(
        decision,
        binding,
        verified_at=_EVALUATED_AT + timedelta(seconds=1),
    )
    stale = _security(
        decision,
        binding,
        verified_at=_DECISION_AT,
    )
    short_policy = _execution_policy(max_age=20)

    _assert_blocked(
        _evaluate(decision=decision, binding=binding, security=future),
        verdict=client_agent.ClientExecutionVerdict.SECURITY_BLOCKED,
        reason=client_agent.ClientExecutionReason.SECURITY_ATTESTATION_INVALID_TIME,
    )
    _assert_blocked(
        _evaluate(
            decision=decision,
            binding=binding,
            security=stale,
            execution_policy=short_policy,
        ),
        verdict=client_agent.ClientExecutionVerdict.SECURITY_BLOCKED,
        reason=client_agent.ClientExecutionReason.SECURITY_ATTESTATION_STALE,
    )


def test_non_active_account_or_mismatched_policy_fails_closed() -> None:
    restricted = _binding(
        lifecycle=client_accounts.TradingAccountLifecycleState.RESTRICTED,
    )
    active = _binding()
    other_binding = _binding(account_suffix=111, policy_suffix=112)
    wrong_policy = _account_policy(other_binding)

    _assert_blocked(
        _evaluate(binding=restricted),
        verdict=client_agent.ClientExecutionVerdict.ACCOUNT_BLOCKED,
        reason=client_agent.ClientExecutionReason.ACCOUNT_NOT_ACTIVE,
    )
    _assert_blocked(
        _evaluate(binding=active, policy=wrong_policy),
        verdict=client_agent.ClientExecutionVerdict.PROP_POLICY_BLOCKED,
        reason=client_agent.ClientExecutionReason.ACCOUNT_POLICY_BINDING_MISMATCH,
    )


def test_unresolved_or_expired_account_policy_fails_closed() -> None:
    binding = _binding()
    unresolved = _account_policy(
        binding,
        drawdown_mode=account_policy.DrawdownMode.UNKNOWN,
    )
    expired = _account_policy(binding, expires_at=_EVALUATED_AT)

    _assert_blocked(
        _evaluate(binding=binding, policy=unresolved),
        verdict=client_agent.ClientExecutionVerdict.PROP_POLICY_BLOCKED,
        reason=client_agent.ClientExecutionReason.ACCOUNT_POLICY_UNRESOLVED,
    )
    _assert_blocked(
        _evaluate(binding=binding, policy=expired),
        verdict=client_agent.ClientExecutionVerdict.PROP_POLICY_BLOCKED,
        reason=client_agent.ClientExecutionReason.ACCOUNT_POLICY_EXPIRED,
    )


def test_stale_or_mismatched_account_state_fails_closed() -> None:
    binding = _binding()
    stale = _observed_state(
        binding,
        observed_at=_EVALUATED_AT - timedelta(minutes=5),
    )
    other_binding = _binding(account_suffix=211)
    wrong_account = _observed_state(other_binding, observation_suffix=230)

    _assert_blocked(
        _evaluate(binding=binding, observed=stale),
        verdict=client_agent.ClientExecutionVerdict.UNRESOLVED,
        reason=client_agent.ClientExecutionReason.ACCOUNT_STATE_STALE,
    )
    _assert_blocked(
        _evaluate(binding=binding, observed=wrong_account),
        verdict=client_agent.ClientExecutionVerdict.UNRESOLVED,
        reason=client_agent.ClientExecutionReason.ACCOUNT_STATE_BINDING_MISMATCH,
    )


def test_drawdown_daily_loss_and_non_positive_equity_block_execution() -> None:
    binding = _binding()
    max_dd = _observed_state(binding, current_drawdown=1000)
    daily = _observed_state(binding, daily_loss=500)
    no_equity = _observed_state(binding, equity=Decimal("0"))

    _assert_blocked(
        _evaluate(binding=binding, observed=max_dd),
        verdict=client_agent.ClientExecutionVerdict.RISK_BLOCKED,
        reason=client_agent.ClientExecutionReason.MAX_DRAWDOWN_REACHED,
    )
    _assert_blocked(
        _evaluate(binding=binding, observed=daily),
        verdict=client_agent.ClientExecutionVerdict.RISK_BLOCKED,
        reason=client_agent.ClientExecutionReason.DAILY_LOSS_REACHED,
    )
    _assert_blocked(
        _evaluate(binding=binding, observed=no_equity),
        verdict=client_agent.ClientExecutionVerdict.RISK_BLOCKED,
        reason=client_agent.ClientExecutionReason.ACCOUNT_EQUITY_NON_POSITIVE,
    )


def test_entitlement_is_account_bound_enabled_and_fresh() -> None:
    binding = _binding()
    blocked = _entitlement(
        binding,
        state=client_agent.ClientAgentEntitlementState.BLOCKED,
    )
    stale = _entitlement(
        binding,
        evaluated_at=_EVALUATED_AT - timedelta(minutes=5),
    )

    _assert_blocked(
        _evaluate(binding=binding, entitlement=blocked),
        verdict=client_agent.ClientExecutionVerdict.ENTITLEMENT_BLOCKED,
        reason=client_agent.ClientExecutionReason.ENTITLEMENT_NOT_ENABLED,
    )
    _assert_blocked(
        _evaluate(binding=binding, entitlement=stale),
        verdict=client_agent.ClientExecutionVerdict.ENTITLEMENT_BLOCKED,
        reason=client_agent.ClientExecutionReason.ENTITLEMENT_STALE,
    )


def test_calculation_must_bind_decision_account_and_authorized_policies() -> None:
    decision = _decision()
    binding = _binding()
    execution_policy = _execution_policy()
    wrong_account = _calculation(
        decision,
        binding,
        execution_policy,
        account_id=client_accounts.TradingAccountId(_uuid(777)),
    )
    wrong_protection = _calculation(
        decision,
        binding,
        execution_policy,
        protection_ref=client_agent.ProtectionPolicyReference(_uuid(778)),
    )

    _assert_blocked(
        _evaluate(
            decision=decision,
            binding=binding,
            execution_policy=execution_policy,
            calculation=wrong_account,
        ),
        verdict=client_agent.ClientExecutionVerdict.UNRESOLVED,
        reason=client_agent.ClientExecutionReason.CALCULATION_BINDING_MISMATCH,
    )
    _assert_blocked(
        _evaluate(
            decision=decision,
            binding=binding,
            execution_policy=execution_policy,
            calculation=wrong_protection,
        ),
        verdict=client_agent.ClientExecutionVerdict.UNRESOLVED,
        reason=client_agent.ClientExecutionReason.CALCULATION_POLICY_MISMATCH,
    )


def test_calculated_risk_and_protection_geometry_fail_closed() -> None:
    decision = _decision()
    binding = _binding()
    execution_policy = _execution_policy(max_risk=100)
    too_risky = _calculation(
        decision,
        binding,
        execution_policy,
        estimated_risk=101,
    )
    invalid_stop = _calculation(
        decision,
        binding,
        execution_policy,
        stop="1.1050",
    )

    _assert_blocked(
        _evaluate(
            decision=decision,
            binding=binding,
            execution_policy=execution_policy,
            calculation=too_risky,
        ),
        verdict=client_agent.ClientExecutionVerdict.RISK_BLOCKED,
        reason=client_agent.ClientExecutionReason.CALCULATED_RISK_EXCEEDS_POLICY,
    )
    _assert_blocked(
        _evaluate(
            decision=decision,
            binding=binding,
            execution_policy=execution_policy,
            calculation=invalid_stop,
        ),
        verdict=client_agent.ClientExecutionVerdict.RISK_BLOCKED,
        reason=client_agent.ClientExecutionReason.INVALID_PROTECTION_GEOMETRY,
    )


def test_sell_protection_geometry_is_directionally_inverted() -> None:
    decision = _decision(side=order_intent.OrderSide.SELL)
    binding = _binding()
    execution_policy = _execution_policy()
    calculation = _calculation(
        decision,
        binding,
        execution_policy,
        stop="1.1050",
        take_profit="1.0900",
    )

    evaluated = _evaluate(
        decision=decision,
        binding=binding,
        execution_policy=execution_policy,
        calculation=calculation,
    )

    assert isinstance(evaluated, result.Success)
    assert evaluated.value.verdict is client_agent.ClientExecutionVerdict.EXECUTE


def test_limit_decision_requires_calculation_at_authorized_limit_price() -> None:
    decision = _decision(
        order_type=order_intent.OrderType.LIMIT,
        limit_price=order_intent.OrderPrice(Decimal("1.0990")),
    )
    binding = _binding()
    execution_policy = _execution_policy()
    mismatched = _calculation(
        decision,
        binding,
        execution_policy,
        entry="1.1000",
    )

    _assert_blocked(
        _evaluate(
            decision=decision,
            binding=binding,
            execution_policy=execution_policy,
            calculation=mismatched,
        ),
        verdict=client_agent.ClientExecutionVerdict.UNRESOLVED,
        reason=client_agent.ClientExecutionReason.LIMIT_PRICE_MISMATCH,
    )


def test_one_core_decision_is_evaluated_independently_for_multiple_accounts() -> None:
    decision = _decision()
    first_binding = _binding()
    second_binding = _binding(
        client_suffix=10,
        account_suffix=311,
        policy_suffix=312,
        entitlement_suffix=313,
        runtime_suffix=314,
    )
    first = _evaluate(decision=decision, binding=first_binding)
    second_policy = _account_policy(second_binding, snapshot_suffix=320)
    second_state = _observed_state(
        second_binding,
        observation_suffix=330,
        daily_loss=500,
    )
    second_execution_policy = _execution_policy(
        policy_suffix=340,
        sizing_suffix=341,
        protection_suffix=342,
        trailing_suffix=343,
    )
    second = _evaluate(
        decision=decision,
        binding=second_binding,
        policy=second_policy,
        observed=second_state,
        entitlement=_entitlement(second_binding),
        execution_policy=second_execution_policy,
        security=_security(decision, second_binding, evidence_suffix=350),
        calculation=_calculation(
            decision,
            second_binding,
            second_execution_policy,
        ),
    )

    assert isinstance(first, result.Success)
    assert first.value.verdict is client_agent.ClientExecutionVerdict.EXECUTE
    _assert_blocked(
        second,
        verdict=client_agent.ClientExecutionVerdict.RISK_BLOCKED,
        reason=client_agent.ClientExecutionReason.DAILY_LOSS_REACHED,
    )
    assert isinstance(second, result.Success)
    assert first.value.account_id != second.value.account_id


def test_agent_contract_exposes_calculation_boundary_not_broker_execution() -> None:
    assert hasattr(client_agent.ClientExecutionCalculator, "calculate")
    assert not hasattr(client_agent.ClientExecutionCalculator, "submit")
    assert not hasattr(client_agent.ClientExecutionCalculator, "send_order")
