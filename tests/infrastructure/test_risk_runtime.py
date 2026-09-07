from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import qore.infrastructure.account_policy as account_policy
import qore.infrastructure.client_accounts as client_accounts
import qore.infrastructure.order_intent as order_intent
import qore.infrastructure.proprietary_accounts as proprietary_accounts
import qore.infrastructure.risk_authority as risk_authority
import qore.infrastructure.risk_budgets as risk_budgets
import qore.infrastructure.risk_runtime as risk_runtime
import qore.kernel.result as result

_USD = proprietary_accounts.CurrencyCode("USD")
_ACCOUNT = client_accounts.TradingAccountId(UUID("52000000-0000-0000-0000-000000000001"))
_T0 = datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)

_DECISION_ID = risk_authority.RiskDecisionId(UUID("52000000-0000-0000-0000-000000000070"))
_AUTH_ID = risk_authority.RiskAuthorizationId(UUID("52000000-0000-0000-0000-000000000080"))
_RESERVATION_ID = risk_authority.RiskReservationId(
    UUID("52000000-0000-0000-0000-000000000090")
)

_SNAPSHOT_ID = account_policy.AccountPolicySnapshotId(
    UUID("52000000-0000-0000-0000-000000000040")
)
_POLICY_REF = client_accounts.AccountPolicyReference(
    UUID("52000000-0000-0000-0000-000000000050")
)
_INTERNAL_POLICY_ID = risk_authority.RiskPolicyId(
    UUID("52000000-0000-0000-0000-000000000060")
)
_BUDGET_FINGERPRINT = risk_authority.compute_fingerprint("demo-budget-config")

_DEFAULT_NOTIONAL = proprietary_accounts.MoneyAmount(_USD, Decimal("1000"))


def _fp(seed: str) -> risk_authority.RiskFingerprint:
    return risk_authority.compute_fingerprint(seed)


def _money(
    amount: str, currency: proprietary_accounts.CurrencyCode = _USD
) -> proprietary_accounts.MoneyAmount:
    return proprietary_accounts.MoneyAmount(currency, Decimal(amount))


def _quantity(value: str) -> order_intent.OrderQuantity:
    return order_intent.OrderQuantity(Decimal(value))


def _price(value: str) -> order_intent.OrderPrice:
    return order_intent.OrderPrice(Decimal(value))


def _trader() -> risk_authority.RiskTraderIdentity:
    return risk_authority.RiskTraderIdentity(
        trader_id=UUID("52000000-0000-0000-0000-000000000010"),
        trader_version=1,
        config_fingerprint=_fp("trader-config"),
    )


def _scope(
    *,
    state: risk_authority.RiskScopeState = risk_authority.RiskScopeState.NORMAL,
    generation: int = 0,
) -> risk_authority.RiskScopeSnapshot:
    return risk_authority.RiskScopeSnapshot(
        state=state,
        kind=risk_authority.RiskScopeKind.ACCOUNT,
        scope_id=_ACCOUNT.value,
        since=_T0,
        reason=risk_authority.RiskReasonCode.reduced_capacity,
        generation=generation,
    )


def _account_state() -> risk_authority.RiskAccountObservedState:
    return risk_authority.RiskAccountObservedState(
        observation_id=UUID("52000000-0000-0000-0000-000000000020"),
        account_id=_ACCOUNT,
        observed_at=_T0,
        balance=_money("100000"),
        equity=_money("100000"),
        margin_used=_money("0"),
        drawdown=proprietary_accounts.DrawdownBps(0),
        daily_loss=proprietary_accounts.DrawdownBps(0),
    )


def _evidence(
    *,
    requested_notional: proprietary_accounts.MoneyAmount = _DEFAULT_NOTIONAL,
    account_policy_version: int = 3,
    snapshot_id: account_policy.AccountPolicySnapshotId = _SNAPSHOT_ID,
    evaluated_at: datetime = _T0,
) -> risk_authority.RiskEvidence:
    return risk_authority.RiskEvidence(
        environment=risk_authority.RiskEnvironment.DEMO,
        account_id=_ACCOUNT,
        trader=_trader(),
        intent_id=order_intent.OrderIntentId(UUID("52000000-0000-0000-0000-000000000030")),
        intent_digest=_fp("intent"),
        instrument=order_intent.ExecutionInstrument("EURUSD"),
        side=order_intent.OrderSide.BUY,
        requested_quantity=_quantity("1.0"),
        requested_notional=requested_notional,
        stop_loss=_price("1.05"),
        bounded_loss_at_stop=_money("50"),
        open_positions=(),
        per_trader_exposure=_money("5000"),
        per_instrument_exposure=_money("2000"),
        group_exposure=_money("1000"),
        portfolio_heat=_money("3000"),
        account_state=_account_state(),
        account_policy_snapshot_id=snapshot_id,
        account_policy_ref=_POLICY_REF,
        account_policy_version=account_policy.AccountPolicyVersion(account_policy_version),
        internal_risk_policy_id=_INTERNAL_POLICY_ID,
        internal_risk_policy_version=risk_authority.RiskPolicyVersion(1),
        market_evidence=risk_authority.RiskMarketEvidence(
            observed_at=_T0, fingerprint=_fp("market")
        ),
        committed_capacity=_money("100"),
        scope=_scope(),
        evaluated_at=evaluated_at,
        arm=risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
    )


def _account_policy(
    *,
    version: int = 3,
    effective_at: datetime = _T0 - timedelta(days=1),
    expires_at: datetime | None = None,
    snapshot_id: account_policy.AccountPolicySnapshotId = _SNAPSHOT_ID,
) -> account_policy.AccountPropPolicySnapshot:
    return account_policy.AccountPropPolicySnapshot(
        snapshot_id=snapshot_id,
        policy_ref=_POLICY_REF,
        account_id=_ACCOUNT,
        account_kind=client_accounts.TradingAccountKind.BROKERAGE,
        version=account_policy.AccountPolicyVersion(version),
        effective_at=effective_at,
        expires_at=expires_at,
        account_size=_money("100000"),
        max_drawdown=proprietary_accounts.DrawdownBps(1000),
        daily_loss_limit=proprietary_accounts.DrawdownBps(500),
        drawdown_mode=account_policy.DrawdownMode.STATIC,
        phase=account_policy.AccountPhase.NOT_APPLICABLE,
        client_profit_split=account_policy.ProfitSplitBps(8000),
        firm_ref=None,
        program_ref=None,
        rules=(),
    )


def _registry(
    policy: account_policy.AccountPropPolicySnapshot | None = None,
) -> account_policy.AccountPolicyRegistrySnapshot:
    return account_policy.AccountPolicyRegistrySnapshot(
        (_account_policy() if policy is None else policy,)
    )


def _budget_policy(
    per_trade_limit_bps: int = 2000, all_limit_bps: int | None = None
) -> risk_budgets.RiskBudgetPolicy:
    if all_limit_bps is not None:
        limits = (
            all_limit_bps,
            all_limit_bps,
            all_limit_bps,
            all_limit_bps,
            all_limit_bps,
            all_limit_bps,
        )
    else:
        limits = (per_trade_limit_bps, 5000, 5000, 5000, 8000, 10000)
    (
        per_trade,
        per_trader,
        per_instrument,
        group,
        heat,
        account_cap,
    ) = limits
    return risk_budgets.RiskBudgetPolicy(
        policy_id=risk_authority.RiskPolicyId(
            UUID("52000000-0000-0000-0000-0000000000b0")
        ),
        version=risk_authority.RiskPolicyVersion(1),
        fingerprint=_BUDGET_FINGERPRINT,
        per_trade_limit_bps=per_trade,
        per_trader_limit_bps=per_trader,
        per_instrument_limit_bps=per_instrument,
        group_limit_bps=group,
        portfolio_heat_limit_bps=heat,
        account_risk_capacity_bps=account_cap,
        safety_buffer_bps=0,
        require_stop_loss=True,
        stress_enabled=True,
    )


def _external() -> risk_budgets.ExternalAccountRiskLimits:
    return risk_budgets.ExternalAccountRiskLimits(
        max_drawdown_bps=1000,
        daily_loss_limit_bps=500,
        require_stop_loss=True,
    )


def _internal_policy(
    arm: risk_authority.RiskArm = risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
) -> risk_authority.RiskPolicySnapshot:
    return risk_authority.RiskPolicySnapshot(
        policy_id=_INTERNAL_POLICY_ID,
        version=risk_authority.RiskPolicyVersion(1),
        fingerprint=_fp("internal-policy"),
        budget_config_fingerprint=_BUDGET_FINGERPRINT,
        arm=arm,
    )


def _runtime(
    per_trade_limit_bps: int = 2000, all_limit_bps: int | None = None
) -> risk_runtime.DemoRiskRuntime:
    composed = risk_runtime.compose_demo_risk_runtime(
        _budget_policy(per_trade_limit_bps, all_limit_bps=all_limit_bps),
        _internal_policy(),
        external=_external(),
        capacity=_money("100000"),
        arm=risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
    )
    assert isinstance(composed, result.Success)
    return composed.value


def _admit(
    runtime: risk_runtime.DemoRiskRuntime,
    *,
    evidence: risk_authority.RiskEvidence | None = None,
    registry: account_policy.AccountPolicyRegistrySnapshot | None = None,
    reservation_generation: int = 1,
    reservation_id: risk_authority.RiskReservationId = _RESERVATION_ID,
) -> result.Result[risk_authority.RiskDecision, risk_authority.RiskError]:
    return runtime.admit(
        _evidence() if evidence is None else evidence,
        _internal_policy(),
        decision_id=_DECISION_ID,
        authorization_id=_AUTH_ID,
        reservation_id=reservation_id,
        reservation_generation=reservation_generation,
        account_policy_registry=registry,
    )


def _allow(runtime: risk_runtime.DemoRiskRuntime | None = None) -> risk_authority.RiskDecision:
    outcome = _admit(_runtime() if runtime is None else runtime, registry=_registry())
    assert isinstance(outcome, result.Success)
    decision = outcome.value
    assert decision.outcome is risk_authority.RiskOutcome.ALLOW
    return decision


def test_compose_demo_risk_runtime_requires_fingerprint_coherence() -> None:
    mismatched = risk_authority.RiskPolicySnapshot(
        policy_id=_INTERNAL_POLICY_ID,
        version=risk_authority.RiskPolicyVersion(1),
        fingerprint=_fp("internal-policy"),
        budget_config_fingerprint=_fp("other-budget-config"),
        arm=risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
    )
    outcome = risk_runtime.compose_demo_risk_runtime(
        _budget_policy(),
        mismatched,
        capacity=_money("100000"),
        arm=risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
    )
    assert isinstance(outcome, result.Failure)


def test_compose_demo_risk_runtime_requires_arm_coherence() -> None:
    outcome = risk_runtime.compose_demo_risk_runtime(
        _budget_policy(),
        _internal_policy(arm=risk_authority.RiskArm.TRADERS_RISK_ONLY),
        capacity=_money("100000"),
        arm=risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
    )
    assert isinstance(outcome, result.Failure)


def test_e2e_allow_then_validate_authorization() -> None:
    decision = _allow()
    auth = decision.authorization
    assert auth is not None
    assert auth.authorized_notional == _money("1000")
    expected = risk_authority.compute_authorization_fingerprint(auth)
    outcome = risk_runtime.validate_risk_authorization(
        auth,
        scope=_scope(generation=0),
        account_policy_version=account_policy.AccountPolicyVersion(3),
        expected_fingerprint=expected,
        evaluated_at=_T0,
    )
    assert isinstance(outcome, result.Success)


def test_e2e_reduce_when_over_per_trade_limit() -> None:
    runtime = _runtime()
    outcome = _admit(
        runtime,
        evidence=_evidence(requested_notional=_money("30000")),
        registry=_registry(),
    )
    assert isinstance(outcome, result.Success)
    decision = outcome.value
    assert decision.outcome is risk_authority.RiskOutcome.REDUCE
    auth = decision.authorization
    assert auth is not None
    assert auth.authorized_notional.amount < Decimal("30000")


def test_admit_rejects_snapshot_substitution() -> None:
    outcome = _admit(
        _runtime(),
        evidence=_evidence(
            snapshot_id=account_policy.AccountPolicySnapshotId(
                UUID("52000000-0000-0000-0000-0000000000ff")
            )
        ),
        registry=_registry(),
    )
    assert isinstance(outcome, result.Success)
    assert outcome.value.outcome is risk_authority.RiskOutcome.REJECT
    assert outcome.value.reasons[0].code is risk_authority.RiskReasonCode.account_mismatch


def test_admit_rejects_expired_policy() -> None:
    policy = _account_policy(
        effective_at=_T0 - timedelta(days=2), expires_at=_T0 - timedelta(days=1)
    )
    outcome = _admit(_runtime(), registry=_registry(policy))
    assert isinstance(outcome, result.Success)
    assert outcome.value.outcome is risk_authority.RiskOutcome.REJECT
    assert outcome.value.reasons[0].code is risk_authority.RiskReasonCode.policy_expired


def test_admit_rejects_not_yet_effective_policy() -> None:
    policy = _account_policy(effective_at=_T0 + timedelta(days=1))
    outcome = _admit(_runtime(), registry=_registry(policy))
    assert isinstance(outcome, result.Success)
    assert outcome.value.outcome is risk_authority.RiskOutcome.REJECT
    assert outcome.value.reasons[0].code is risk_authority.RiskReasonCode.policy_not_effective


def test_admit_rejects_policy_version_mismatch() -> None:
    policy = _account_policy(version=4)
    outcome = _admit(_runtime(), registry=_registry(policy))
    assert isinstance(outcome, result.Success)
    assert outcome.value.outcome is risk_authority.RiskOutcome.REJECT
    assert outcome.value.reasons[0].code is risk_authority.RiskReasonCode.policy_version_mismatch


def test_validate_authorization_rejects_trader_swap() -> None:
    decision = _allow()
    auth = decision.authorization
    assert auth is not None
    expected = risk_authority.compute_authorization_fingerprint(auth)
    swapped = replace(
        auth,
        trader=risk_authority.RiskTraderIdentity(
            trader_id=UUID("52000000-0000-0000-0000-0000000000ee"),
            trader_version=1,
            config_fingerprint=_fp("trader-config"),
        ),
    )
    outcome = risk_runtime.validate_risk_authorization(
        swapped,
        scope=_scope(generation=0),
        account_policy_version=account_policy.AccountPolicyVersion(3),
        expected_fingerprint=expected,
        evaluated_at=_T0,
    )
    assert isinstance(outcome, result.Failure)


def test_validate_authorization_rejects_scope_generation_change() -> None:
    decision = _allow()
    auth = decision.authorization
    assert auth is not None
    expected = risk_authority.compute_authorization_fingerprint(auth)
    outcome = risk_runtime.validate_risk_authorization(
        auth,
        scope=_scope(generation=1),
        account_policy_version=account_policy.AccountPolicyVersion(3),
        expected_fingerprint=expected,
        evaluated_at=_T0,
    )
    assert isinstance(outcome, result.Failure)


def test_validate_authorization_rejects_policy_version_change() -> None:
    decision = _allow()
    auth = decision.authorization
    assert auth is not None
    expected = risk_authority.compute_authorization_fingerprint(auth)
    outcome = risk_runtime.validate_risk_authorization(
        auth,
        scope=_scope(generation=0),
        account_policy_version=account_policy.AccountPolicyVersion(4),
        expected_fingerprint=expected,
        evaluated_at=_T0,
    )
    assert isinstance(outcome, result.Failure)


def test_validate_authorization_rejects_production_environment() -> None:
    decision = _allow()
    auth = decision.authorization
    assert auth is not None
    expected = risk_authority.compute_authorization_fingerprint(auth)
    production = replace(auth, environment=risk_authority.RiskEnvironment.PRODUCTION)
    outcome = risk_runtime.validate_risk_authorization(
        production,
        scope=_scope(generation=0),
        account_policy_version=account_policy.AccountPolicyVersion(3),
        expected_fingerprint=expected,
        evaluated_at=_T0,
    )
    assert isinstance(outcome, result.Failure)


def test_compose_execution_safety_from_scope_blocks_terminal_states() -> None:
    for state, expected in (
        (risk_authority.RiskScopeState.KILL, "blocked"),
        (risk_authority.RiskScopeState.CONTAIN_ACCOUNT, "blocked"),
        (risk_authority.RiskScopeState.FREEZE_TRADER, "blocked"),
        (risk_authority.RiskScopeState.REDUCED_CAPACITY, "enabled"),
        (risk_authority.RiskScopeState.NORMAL, "enabled"),
    ):
        outcome = risk_runtime.compose_execution_safety_from_scope(
            _scope(state=state),
            observed_at=_T0,
        )
        assert isinstance(outcome, result.Success)
        assert outcome.value.state.value == expected


def test_capacity_double_spend_is_blocked_across_admissions() -> None:
    runtime = _runtime(all_limit_bps=10000)
    # capacity 100000; notional 60000 twice would exceed it
    first = _admit(
        runtime,
        evidence=_evidence(requested_notional=_money("60000")),
        reservation_generation=1,
        reservation_id=risk_authority.RiskReservationId(
            UUID("52000000-0000-0000-0000-000000000091")
        ),
    )
    assert isinstance(first, result.Success)
    assert first.value.outcome is risk_authority.RiskOutcome.ALLOW
    second = _admit(
        runtime,
        evidence=_evidence(requested_notional=_money("60000")),
        reservation_generation=2,
        reservation_id=risk_authority.RiskReservationId(
            UUID("52000000-0000-0000-0000-000000000092")
        ),
    )
    assert isinstance(second, result.Success)
    assert second.value.outcome is risk_authority.RiskOutcome.REJECT
    assert second.value.reasons[0].code is risk_authority.RiskReasonCode.capacity_exhausted


def test_no_secret_material_in_runtime_representations() -> None:
    decision = _allow()
    for forbidden in ("token", "password", "secret", "bearer"):
        assert forbidden not in repr(decision)
        assert forbidden not in repr(_runtime())


def test_runtime_rejects_reservation_generation_non_monotonic() -> None:
    runtime = _runtime()
    _admit(
        runtime,
        reservation_generation=5,
        reservation_id=risk_authority.RiskReservationId(
            UUID("52000000-0000-0000-0000-000000000093")
        ),
    )
    stale = _admit(
        runtime,
        reservation_generation=5,
        reservation_id=risk_authority.RiskReservationId(
            UUID("52000000-0000-0000-0000-000000000094")
        ),
    )
    assert isinstance(stale, result.Success)
    assert stale.value.outcome is risk_authority.RiskOutcome.REJECT
