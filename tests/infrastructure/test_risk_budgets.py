from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

import qore.infrastructure.account_policy as account_policy
import qore.infrastructure.client_accounts as client_accounts
import qore.infrastructure.order_intent as order_intent
import qore.infrastructure.proprietary_accounts as proprietary_accounts
import qore.infrastructure.risk_authority as risk_authority
import qore.infrastructure.risk_budgets as risk_budgets
import qore.kernel.result as result

_USD = proprietary_accounts.CurrencyCode("USD")
_EUR = proprietary_accounts.CurrencyCode("EUR")
_ACCOUNT = client_accounts.TradingAccountId(UUID("52000000-0000-0000-0000-000000000001"))
_T0 = datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)

_POLICY_ID = risk_authority.RiskPolicyId(UUID("52000000-0000-0000-0000-000000000010"))
_POLICY_VERSION = risk_authority.RiskPolicyVersion(1)

_DEFAULT_STOP = order_intent.OrderPrice(Decimal("1.05"))
_DEFAULT_BOUNDED_LOSS = proprietary_accounts.MoneyAmount(_USD, Decimal("50"))
_DEFAULT_NOTIONAL = proprietary_accounts.MoneyAmount(_USD, Decimal("1000"))
_DEFAULT_QUANTITY = order_intent.OrderQuantity(Decimal("1.0"))
_DEFAULT_TRADER_EXPOSURE = proprietary_accounts.MoneyAmount(_USD, Decimal("5000"))
_DEFAULT_INSTRUMENT_EXPOSURE = proprietary_accounts.MoneyAmount(_USD, Decimal("2000"))
_DEFAULT_GROUP_EXPOSURE = proprietary_accounts.MoneyAmount(_USD, Decimal("1000"))
_DEFAULT_HEAT = proprietary_accounts.MoneyAmount(_USD, Decimal("3000"))
_DEFAULT_COMMITTED = proprietary_accounts.MoneyAmount(_USD, Decimal("100"))


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


def _instrument(code: str = "EURUSD") -> order_intent.ExecutionInstrument:
    return order_intent.ExecutionInstrument(code)


def _trader() -> risk_authority.RiskTraderIdentity:
    return risk_authority.RiskTraderIdentity(
        trader_id=UUID("52000000-0000-0000-0000-000000000020"),
        trader_version=1,
        config_fingerprint=_fp("trader-config"),
    )


def _scope() -> risk_authority.RiskScopeSnapshot:
    return risk_authority.RiskScopeSnapshot(
        state=risk_authority.RiskScopeState.NORMAL,
        kind=risk_authority.RiskScopeKind.ACCOUNT,
        scope_id=_ACCOUNT.value,
        since=_T0,
        reason=risk_authority.RiskReasonCode.reduced_capacity,
        generation=0,
    )


def _account_state(
    *,
    equity: str = "100000",
    observed_at: datetime = _T0,
    drawdown: int = 0,
    daily_loss: int = 0,
) -> risk_authority.RiskAccountObservedState:
    return risk_authority.RiskAccountObservedState(
        observation_id=UUID("52000000-0000-0000-0000-000000000030"),
        account_id=_ACCOUNT,
        observed_at=observed_at,
        balance=_money(equity),
        equity=_money(equity),
        margin_used=_money("0"),
        drawdown=proprietary_accounts.DrawdownBps(drawdown),
        daily_loss=proprietary_accounts.DrawdownBps(daily_loss),
    )


def _market_evidence(observed_at: datetime = _T0) -> risk_authority.RiskMarketEvidence:
    return risk_authority.RiskMarketEvidence(
        observed_at=observed_at,
        fingerprint=_fp("market"),
    )


def _evidence(
    *,
    stop_loss: order_intent.OrderPrice | None = _DEFAULT_STOP,
    bounded_loss_at_stop: proprietary_accounts.MoneyAmount | None = _DEFAULT_BOUNDED_LOSS,
    requested_notional: proprietary_accounts.MoneyAmount = _DEFAULT_NOTIONAL,
    requested_quantity: order_intent.OrderQuantity = _DEFAULT_QUANTITY,
    instrument: order_intent.ExecutionInstrument | None = None,
    per_trader_exposure: proprietary_accounts.MoneyAmount = _DEFAULT_TRADER_EXPOSURE,
    per_instrument_exposure: proprietary_accounts.MoneyAmount = _DEFAULT_INSTRUMENT_EXPOSURE,
    group_exposure: proprietary_accounts.MoneyAmount = _DEFAULT_GROUP_EXPOSURE,
    portfolio_heat: proprietary_accounts.MoneyAmount = _DEFAULT_HEAT,
    committed_capacity: proprietary_accounts.MoneyAmount = _DEFAULT_COMMITTED,
    account_state: risk_authority.RiskAccountObservedState | None = None,
    evaluated_at: datetime = _T0,
) -> risk_authority.RiskEvidence:
    return risk_authority.RiskEvidence(
        environment=risk_authority.RiskEnvironment.DEMO,
        account_id=_ACCOUNT,
        trader=_trader(),
        intent_id=order_intent.OrderIntentId(UUID("52000000-0000-0000-0000-000000000040")),
        intent_digest=_fp("intent"),
        instrument=_instrument() if instrument is None else instrument,
        side=order_intent.OrderSide.BUY,
        requested_quantity=requested_quantity,
        requested_notional=requested_notional,
        stop_loss=stop_loss,
        bounded_loss_at_stop=bounded_loss_at_stop,
        open_positions=(),
        per_trader_exposure=per_trader_exposure,
        per_instrument_exposure=per_instrument_exposure,
        group_exposure=group_exposure,
        portfolio_heat=portfolio_heat,
        account_state=_account_state() if account_state is None else account_state,
        account_policy_snapshot_id=account_policy.AccountPolicySnapshotId(
            UUID("52000000-0000-0000-0000-000000000050")
        ),
        account_policy_ref=client_accounts.AccountPolicyReference(
            UUID("52000000-0000-0000-0000-000000000060")
        ),
        account_policy_version=account_policy.AccountPolicyVersion(3),
        internal_risk_policy_id=risk_authority.RiskPolicyId(
            UUID("52000000-0000-0000-0000-000000000070")
        ),
        internal_risk_policy_version=risk_authority.RiskPolicyVersion(1),
        market_evidence=_market_evidence(),
        committed_capacity=committed_capacity,
        scope=_scope(),
        evaluated_at=evaluated_at,
        arm=risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
    )


def _group(
    group_id: str,
    instruments: tuple[order_intent.ExecutionInstrument, ...],
    limit_bps: int,
) -> risk_budgets.CorrelationGroup:
    return risk_budgets.CorrelationGroup(
        group_id=UUID(group_id),
        instruments=instruments,
        limit_bps=limit_bps,
    )


def _policy(
    *,
    per_trade_limit_bps: int = 5000,
    per_trader_limit_bps: int = 5000,
    per_instrument_limit_bps: int = 5000,
    group_limit_bps: int = 5000,
    portfolio_heat_limit_bps: int = 5000,
    account_risk_capacity_bps: int = 5000,
    safety_buffer_bps: int = 0,
    require_stop_loss: bool = False,
    stress_enabled: bool = False,
    correlation_groups: tuple[risk_budgets.CorrelationGroup, ...] = (),
) -> risk_budgets.RiskBudgetPolicy:
    return risk_budgets.RiskBudgetPolicy(
        policy_id=_POLICY_ID,
        version=_POLICY_VERSION,
        fingerprint=_fp("budget-policy"),
        per_trade_limit_bps=per_trade_limit_bps,
        per_trader_limit_bps=per_trader_limit_bps,
        per_instrument_limit_bps=per_instrument_limit_bps,
        group_limit_bps=group_limit_bps,
        portfolio_heat_limit_bps=portfolio_heat_limit_bps,
        account_risk_capacity_bps=account_risk_capacity_bps,
        safety_buffer_bps=safety_buffer_bps,
        require_stop_loss=require_stop_loss,
        stress_enabled=stress_enabled,
        correlation_groups=correlation_groups,
    )


def _snapshot_for(policy: risk_budgets.RiskBudgetPolicy) -> risk_authority.RiskPolicySnapshot:
    return risk_authority.RiskPolicySnapshot(
        policy_id=policy.policy_id,
        version=policy.version,
        fingerprint=_fp("internal-policy"),
        budget_config_fingerprint=policy.fingerprint,
        arm=risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
    )


def _engine(
    policy: risk_budgets.RiskBudgetPolicy,
    external: risk_budgets.ExternalAccountRiskLimits | None = None,
) -> risk_budgets.RiskBudgetEngine:
    return risk_budgets.RiskBudgetEngine(policy, external)


def _run(
    engine: risk_budgets.RiskBudgetEngine,
    evidence: risk_authority.RiskEvidence,
) -> result.Result[risk_authority.RiskBudgetEvaluation, risk_authority.RiskError]:
    return engine.evaluate(
        evidence, _snapshot_for(engine.policy), evaluated_at=evidence.evaluated_at
    )


def _ok(
    outcome: result.Result[risk_authority.RiskBudgetEvaluation, risk_authority.RiskError],
) -> risk_authority.RiskBudgetEvaluation:
    assert isinstance(outcome, result.Success)
    return outcome.value


def _assert_rejected(
    outcome: result.Result[risk_authority.RiskBudgetEvaluation, risk_authority.RiskError],
    code: risk_authority.RiskReasonCode,
) -> risk_authority.RiskBudgetEvaluation:
    evaluation = _ok(outcome)
    assert evaluation.admitted is False
    assert evaluation.reduced is False
    assert evaluation.authorized_quantity is None
    assert evaluation.bounded_loss_at_stop is None
    assert evaluation.reason.code is code
    return evaluation


def _assert_failure(
    outcome: result.Result[risk_authority.RiskBudgetEvaluation, risk_authority.RiskError],
    error_type: type[risk_authority.RiskError],
) -> risk_authority.RiskError:
    assert isinstance(outcome, result.Failure)
    assert isinstance(outcome.error, error_type)
    return outcome.error


# --- pure helper functions -------------------------------------------------


def test_compute_effective_limit_bps_uses_min_or_internal() -> None:
    assert risk_budgets.compute_effective_limit_bps(100, 50) == 50
    assert risk_budgets.compute_effective_limit_bps(50, 100) == 50
    assert risk_budgets.compute_effective_limit_bps(100, None) == 100
    assert risk_budgets.compute_effective_limit_bps(100, 100) == 100


def test_compute_effective_limit_bps_rejects_bool_and_bad_types() -> None:
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.compute_effective_limit_bps(True, None)
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.compute_effective_limit_bps(100, cast(int, "50"))


def test_apply_safety_buffer_bps_floors_and_clamps() -> None:
    assert risk_budgets.apply_safety_buffer_bps(10_000, 1_000) == 9_000
    assert risk_budgets.apply_safety_buffer_bps(100, 500) == 95
    assert risk_budgets.apply_safety_buffer_bps(1, 1) == 0
    assert risk_budgets.apply_safety_buffer_bps(0, 0) == 0
    assert risk_budgets.apply_safety_buffer_bps(100, 10_000) == 0


def test_apply_safety_buffer_bps_rejects_bool_and_bad_buffer() -> None:
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.apply_safety_buffer_bps(True, 0)
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.apply_safety_buffer_bps(100, 10_001)


# --- value object construction --------------------------------------------


def test_correlation_group_rejects_empty_and_non_unique_instruments() -> None:
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        _group("52000000-0000-0000-0000-0000000000a1", (), 100)
    dup = (_instrument("EURUSD"), _instrument("EURUSD"))
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        _group("52000000-0000-0000-0000-0000000000a1", dup, 100)


def test_correlation_group_rejects_bool_limit_and_bad_uuid() -> None:
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.CorrelationGroup(
            group_id=cast(UUID, "not-a-uuid"),
            instruments=(_instrument(),),
            limit_bps=100,
        )
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        _group(
            "52000000-0000-0000-0000-0000000000a2",
            (_instrument(),),
            True,
        )
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        _group("52000000-0000-0000-0000-0000000000a3", (_instrument(),), 0)


def test_risk_budget_policy_rejects_invalid_config() -> None:
    for bad in (0, -1, 10_001):
        with pytest.raises(risk_budgets.RiskBudgetValidationError):
            _policy(per_trade_limit_bps=bad)
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        _policy(per_trade_limit_bps=True)
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        _policy(safety_buffer_bps=10_001)
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        _policy(require_stop_loss=cast(bool, 1))
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        _policy(stress_enabled=cast(bool, 0))


def test_risk_budget_policy_rejects_overlapping_and_duplicate_groups() -> None:
    shared = _instrument("EURUSD")
    g1 = _group(
        "52000000-0000-0000-0000-0000000000b1",
        (shared,),
        100,
    )
    g2 = _group(
        "52000000-0000-0000-0000-0000000000b2",
        (shared, _instrument("GBPUSD")),
        100,
    )
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        _policy(correlation_groups=(g1, g2))
    same_id = (
        _group("52000000-0000-0000-0000-0000000000b3", (_instrument("EURUSD"),), 100),
        _group("52000000-0000-0000-0000-0000000000b3", (_instrument("GBPUSD"),), 100),
    )
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        _policy(correlation_groups=same_id)


def test_external_account_risk_limits_validation() -> None:
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.ExternalAccountRiskLimits(
            max_drawdown_bps=-1,
            daily_loss_limit_bps=0,
        )
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.ExternalAccountRiskLimits(
            max_drawdown_bps=0,
            daily_loss_limit_bps=10_001,
        )
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.ExternalAccountRiskLimits(
            max_drawdown_bps=0,
            daily_loss_limit_bps=0,
            max_notional=cast(proprietary_accounts.MoneyAmount, "bad"),
        )
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.ExternalAccountRiskLimits(
            max_drawdown_bps=0,
            daily_loss_limit_bps=0,
            max_quantity=cast(order_intent.OrderQuantity, "bad"),
        )
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.ExternalAccountRiskLimits(
            max_drawdown_bps=0,
            daily_loss_limit_bps=0,
            require_stop_loss=cast(bool, 1),
        )


# --- engine structural and boundary behaviour ------------------------------


def test_engine_implements_protocol() -> None:
    engine = _engine(_policy())
    assert isinstance(engine, risk_authority.RiskBudgetEvaluator)
    assert engine.policy_fingerprint == _policy().fingerprint


def test_policy_fingerprint_mismatch_failure() -> None:
    policy = _policy()
    engine = _engine(policy)
    evidence = _evidence()
    snapshot = risk_authority.RiskPolicySnapshot(
        policy_id=policy.policy_id,
        version=policy.version,
        fingerprint=_fp("internal-policy"),
        budget_config_fingerprint=_fp("different-budget-config"),
        arm=risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
    )
    outcome = engine.evaluate(evidence, snapshot, evaluated_at=evidence.evaluated_at)
    _assert_failure(outcome, risk_authority.RiskValidationError)


def test_evaluated_at_mismatch_failure() -> None:
    engine = _engine(_policy())
    evidence = _evidence()
    outcome = engine.evaluate(
        evidence, _snapshot_for(engine.policy), evaluated_at=_T0 + timedelta(seconds=1)
    )
    _assert_failure(outcome, risk_authority.RiskValidationError)


def test_stale_account_state_failure() -> None:
    engine = _engine(_policy())
    evidence = _evidence(
        account_state=_account_state(observed_at=_T0 + timedelta(minutes=1))
    )
    outcome = _run(engine, evidence)
    _assert_failure(outcome, risk_authority.RiskValidationError)


def test_boundary_equality_allows_without_reduction() -> None:
    policy = _policy(per_trade_limit_bps=100)  # 100 bps -> 1000 notional
    engine = _engine(policy)
    evidence = _evidence(requested_notional=_money("1000"))
    evaluation = _ok(_run(engine, evidence))
    assert evaluation.admitted is True
    assert evaluation.reduced is False
    assert evaluation.authorized_quantity == _quantity("1.0")


def test_one_basis_point_above_reduces_one_unit_below_allows() -> None:
    policy = _policy(per_trade_limit_bps=100)
    engine = _engine(policy)
    above = _ok(_run(engine, _evidence(requested_notional=_money("1010"))))
    assert above.admitted is True
    assert above.reduced is True
    assert above.authorized_quantity is not None
    assert above.authorized_quantity.value < _quantity("1.0").value
    below = _ok(_run(engine, _evidence(requested_notional=_money("990"))))
    assert below.admitted is True
    assert below.reduced is False
    assert below.authorized_quantity == _quantity("1.0")


def test_reduction_floors_to_eight_decimals_and_never_exceeds_limit() -> None:
    policy = _policy(per_trade_limit_bps=100)  # available notional == 1000
    engine = _engine(policy)
    # requested_notional == 3000 with quantity 1.0 -> price 3000 per unit
    evidence = _evidence(requested_notional=_money("3000"))
    evaluation = _ok(_run(engine, evidence))
    assert evaluation.reduced is True
    authorized = evaluation.authorized_quantity
    assert authorized is not None
    assert authorized.value == Decimal("0.33333333")
    # implied notional must never exceed the available limit
    assert authorized.value * Decimal("3000") <= Decimal("1000")


# --- mandatory stop and stress ---------------------------------------------


def test_missing_stop_with_require_stop_loss() -> None:
    policy = _policy(require_stop_loss=True)
    engine = _engine(policy)
    evidence = _evidence(stop_loss=None, bounded_loss_at_stop=None)
    _assert_rejected(_run(engine, evidence), risk_authority.RiskReasonCode.missing_stop)


def test_stop_present_but_bounded_loss_missing_fails_closed() -> None:
    policy = _policy(require_stop_loss=True)
    engine = _engine(policy)
    evidence = _evidence(stop_loss=_price("1.05"), bounded_loss_at_stop=None)
    _assert_rejected(_run(engine, evidence), risk_authority.RiskReasonCode.missing_stop)


def test_stress_breach_daily_loss_limit() -> None:
    policy = _policy(stress_enabled=True)
    external = risk_budgets.ExternalAccountRiskLimits(
        max_drawdown_bps=500,
        daily_loss_limit_bps=50,
    )
    engine = _engine(policy, external)
    # bounded loss 1000 on 100000 equity == 100 bps > 50 bps daily limit
    evidence = _evidence(bounded_loss_at_stop=_money("1000"))
    _assert_rejected(_run(engine, evidence), risk_authority.RiskReasonCode.stress_breach)


def test_stress_within_limits_admits() -> None:
    policy = _policy(stress_enabled=True)
    external = risk_budgets.ExternalAccountRiskLimits(
        max_drawdown_bps=500,
        daily_loss_limit_bps=200,
    )
    engine = _engine(policy, external)
    evidence = _evidence(bounded_loss_at_stop=_money("1000"))
    evaluation = _ok(_run(engine, evidence))
    assert evaluation.admitted is True


def test_stress_internal_capacity_ceiling_when_external_none() -> None:
    policy = _policy(stress_enabled=True, account_risk_capacity_bps=1000)
    engine = _engine(policy)
    # bounded loss 10010 on 100000 equity == 1001 bps > 1000 bps ceiling
    evidence = _evidence(bounded_loss_at_stop=_money("10010"))
    _assert_rejected(_run(engine, evidence), risk_authority.RiskReasonCode.stress_breach)


def test_stress_fractional_loss_above_limit_fails_closed() -> None:
    # A bounded loss that lands a fraction of a basis point above the daily-loss
    # limit must still be rejected: the projected loss is rounded UP to the next
    # integer basis point (ROUND_CEILING), never down.
    policy = _policy(stress_enabled=True)
    external = risk_budgets.ExternalAccountRiskLimits(
        max_drawdown_bps=500,
        daily_loss_limit_bps=100,
    )
    engine = _engine(policy, external)
    # 1000.01 on 100000 equity == 100.001 bps -> ceil == 101 bps > 100 bps limit.
    evidence = _evidence(bounded_loss_at_stop=_money("1000.01"))
    _assert_rejected(_run(engine, evidence), risk_authority.RiskReasonCode.stress_breach)


def test_stress_exact_integer_basis_point_boundary_admits() -> None:
    # Boundary equality is not a breach: an exact integer-bps loss equal to the
    # daily-loss limit is admitted.
    policy = _policy(stress_enabled=True)
    external = risk_budgets.ExternalAccountRiskLimits(
        max_drawdown_bps=500,
        daily_loss_limit_bps=100,
    )
    engine = _engine(policy, external)
    # 1000.00 on 100000 equity == exactly 100 bps == the daily-loss limit.
    evidence = _evidence(bounded_loss_at_stop=_money("1000.00"))
    evaluation = _ok(_run(engine, evidence))
    assert evaluation.admitted is True


def test_bounded_loss_none_without_require_stop_admits() -> None:
    policy = _policy(stress_enabled=True)
    engine = _engine(policy)
    evidence = _evidence(stop_loss=_price("1.05"), bounded_loss_at_stop=None)
    evaluation = _ok(_run(engine, evidence))
    assert evaluation.admitted is True


# --- independent exposure rejections ---------------------------------------


def test_per_trader_exposure_rejects() -> None:
    policy = _policy(per_trader_limit_bps=500)  # 5000 notional budget
    engine = _engine(policy)
    evidence = _evidence(per_trader_exposure=_money("4500"))
    _assert_rejected(_run(engine, evidence), risk_authority.RiskReasonCode.budget_exceeded)


def test_per_instrument_exposure_rejects() -> None:
    policy = _policy(per_instrument_limit_bps=200)  # 2000 notional budget
    engine = _engine(policy)
    evidence = _evidence(per_instrument_exposure=_money("1500"))
    _assert_rejected(
        _run(engine, evidence), risk_authority.RiskReasonCode.concentration_exceeded
    )


def test_correlation_group_exposure_rejects() -> None:
    group = _group(
        "52000000-0000-0000-0000-0000000000c1",
        (_instrument("EURUSD"),),
        100,  # 1000 notional group budget
    )
    policy = _policy(correlation_groups=(group,))
    engine = _engine(policy)
    evidence = _evidence(group_exposure=_money("500"))
    _assert_rejected(
        _run(engine, evidence), risk_authority.RiskReasonCode.concentration_exceeded
    )


def test_concentration_undercount_two_instruments_same_group() -> None:
    # Adversarial: the traded instrument is the SECOND member of a two-instrument
    # correlation group; a naive "first-instrument-only" check would undercount.
    group = _group(
        "52000000-0000-0000-0000-0000000000c2",
        (_instrument("AAPL"), _instrument("MSFT")),
        100,  # 1000 notional group budget
    )
    policy = _policy(correlation_groups=(group,))
    engine = _engine(policy)
    evidence = _evidence(instrument=_instrument("MSFT"), group_exposure=_money("500"))
    _assert_rejected(
        _run(engine, evidence), risk_authority.RiskReasonCode.concentration_exceeded
    )


def test_portfolio_heat_rejects() -> None:
    policy = _policy(portfolio_heat_limit_bps=300)  # 3000 notional budget
    engine = _engine(policy)
    evidence = _evidence(portfolio_heat=_money("2500"))
    _assert_rejected(_run(engine, evidence), risk_authority.RiskReasonCode.heat_exceeded)


def test_account_capacity_rejects() -> None:
    policy = _policy(account_risk_capacity_bps=100)  # 1000 notional capacity
    engine = _engine(policy)
    evidence = _evidence(committed_capacity=_money("500"))
    _assert_rejected(
        _run(engine, evidence), risk_authority.RiskReasonCode.capacity_exhausted
    )


# --- external limits --------------------------------------------------------


def test_external_max_notional_rejects() -> None:
    policy = _policy()
    external = risk_budgets.ExternalAccountRiskLimits(
        max_drawdown_bps=0,
        daily_loss_limit_bps=0,
        max_notional=_money("500"),
    )
    engine = _engine(policy, external)
    _assert_rejected(
        _run(engine, _evidence()), risk_authority.RiskReasonCode.external_limit_exceeded
    )


def test_external_max_quantity_rejects() -> None:
    policy = _policy()
    external = risk_budgets.ExternalAccountRiskLimits(
        max_drawdown_bps=0,
        daily_loss_limit_bps=0,
        max_quantity=_quantity("0.5"),
    )
    engine = _engine(policy, external)
    _assert_rejected(
        _run(engine, _evidence()), risk_authority.RiskReasonCode.external_limit_exceeded
    )


def test_external_max_concentration_composes_with_per_instrument() -> None:
    # Internal per-instrument is 5000 bps (50000 notional); external 200 bps
    # (2000 notional) is stricter, so the effective bound must be the external one.
    policy = _policy()
    external = risk_budgets.ExternalAccountRiskLimits(
        max_drawdown_bps=10_000,
        daily_loss_limit_bps=10_000,
        max_concentration_bps=200,
    )
    engine = _engine(policy, external)
    evidence = _evidence(per_instrument_exposure=_money("1500"))
    _assert_rejected(
        _run(engine, evidence), risk_authority.RiskReasonCode.concentration_exceeded
    )


def test_external_max_notional_currency_mismatch_fails() -> None:
    policy = _policy()
    external = risk_budgets.ExternalAccountRiskLimits(
        max_drawdown_bps=0,
        daily_loss_limit_bps=0,
        max_notional=_money("500", currency=_EUR),
    )
    engine = _engine(policy, external)
    outcome = _run(engine, _evidence())
    _assert_failure(outcome, risk_authority.RiskValidationError)


def test_external_require_stop_loss_missing_stop() -> None:
    policy = _policy()
    external = risk_budgets.ExternalAccountRiskLimits(
        max_drawdown_bps=0,
        daily_loss_limit_bps=0,
        require_stop_loss=True,
    )
    engine = _engine(policy, external)
    evidence = _evidence(stop_loss=None, bounded_loss_at_stop=None)
    _assert_rejected(_run(engine, evidence), risk_authority.RiskReasonCode.missing_stop)


def test_engine_constructor_rejects_bad_types() -> None:
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.RiskBudgetEngine(cast(risk_budgets.RiskBudgetPolicy, "bad"))
    with pytest.raises(risk_budgets.RiskBudgetValidationError):
        risk_budgets.RiskBudgetEngine(
            _policy(), cast(risk_budgets.ExternalAccountRiskLimits, "bad")
        )
