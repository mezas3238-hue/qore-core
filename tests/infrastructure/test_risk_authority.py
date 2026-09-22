from __future__ import annotations

from dataclasses import fields
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
import qore.kernel.result as result

_USD = proprietary_accounts.CurrencyCode("USD")
_EUR = proprietary_accounts.CurrencyCode("EUR")
_ACCOUNT = client_accounts.TradingAccountId(UUID("51000000-0000-0000-0000-000000000001"))
_OTHER_ACCOUNT = client_accounts.TradingAccountId(UUID("51000000-0000-0000-0000-000000000002"))
_T0 = datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)

_DECISION_ID = risk_authority.RiskDecisionId(UUID("51000000-0000-0000-0000-000000000070"))
_AUTH_ID = risk_authority.RiskAuthorizationId(UUID("51000000-0000-0000-0000-000000000080"))
_RESERVATION_ID = risk_authority.RiskReservationId(UUID("51000000-0000-0000-0000-000000000090"))

_MISSING = object()

_DEFAULT_STOP = order_intent.OrderPrice(Decimal("1.05"))
_DEFAULT_BOUNDED_LOSS = proprietary_accounts.MoneyAmount(_USD, Decimal("50"))
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


def _instrument() -> order_intent.ExecutionInstrument:
    return order_intent.ExecutionInstrument("EURUSD")


def _trader() -> risk_authority.RiskTraderIdentity:
    return risk_authority.RiskTraderIdentity(
        trader_id=UUID("51000000-0000-0000-0000-000000000010"),
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


def _account_state(
    *,
    equity: str = "100000",
    account_id: client_accounts.TradingAccountId = _ACCOUNT,
    observed_at: datetime = _T0,
) -> risk_authority.RiskAccountObservedState:
    return risk_authority.RiskAccountObservedState(
        observation_id=UUID("51000000-0000-0000-0000-000000000020"),
        account_id=account_id,
        observed_at=observed_at,
        balance=_money(equity),
        equity=_money(equity),
        margin_used=_money("0"),
        drawdown=proprietary_accounts.DrawdownBps(0),
        daily_loss=proprietary_accounts.DrawdownBps(0),
    )


def _market_evidence(observed_at: datetime = _T0) -> risk_authority.RiskMarketEvidence:
    return risk_authority.RiskMarketEvidence(
        observed_at=observed_at,
        fingerprint=_fp("market"),
    )


def _evidence(
    *,
    environment: risk_authority.RiskEnvironment = risk_authority.RiskEnvironment.DEMO,
    stop_loss: order_intent.OrderPrice | None = _DEFAULT_STOP,
    bounded_loss_at_stop: proprietary_accounts.MoneyAmount | None = _DEFAULT_BOUNDED_LOSS,
    requested_notional: proprietary_accounts.MoneyAmount = _DEFAULT_NOTIONAL,
    evaluated_at: datetime = _T0,
    scope: risk_authority.RiskScopeSnapshot | None = None,
    account_state: risk_authority.RiskAccountObservedState | None = None,
    market_evidence: risk_authority.RiskMarketEvidence | None = None,
) -> risk_authority.RiskEvidence:
    return risk_authority.RiskEvidence(
        environment=environment,
        account_id=_ACCOUNT,
        trader=_trader(),
        intent_id=order_intent.OrderIntentId(UUID("51000000-0000-0000-0000-000000000030")),
        intent_digest=_fp("intent"),
        instrument=_instrument(),
        side=order_intent.OrderSide.BUY,
        requested_quantity=_quantity("1.0"),
        requested_notional=requested_notional,
        stop_loss=stop_loss,
        bounded_loss_at_stop=bounded_loss_at_stop,
        open_positions=(),
        per_trader_exposure=_money("5000"),
        per_instrument_exposure=_money("2000"),
        group_exposure=_money("1000"),
        portfolio_heat=_money("3000"),
        account_state=_account_state() if account_state is None else account_state,
        account_policy_snapshot_id=account_policy.AccountPolicySnapshotId(
            UUID("51000000-0000-0000-0000-000000000040")
        ),
        account_policy_ref=client_accounts.AccountPolicyReference(
            UUID("51000000-0000-0000-0000-000000000050")
        ),
        account_policy_version=account_policy.AccountPolicyVersion(3),
        internal_risk_policy_id=risk_authority.RiskPolicyId(
            UUID("51000000-0000-0000-0000-000000000060")
        ),
        internal_risk_policy_version=risk_authority.RiskPolicyVersion(1),
        market_evidence=_market_evidence() if market_evidence is None else market_evidence,
        committed_capacity=_money("100"),
        scope=_scope() if scope is None else scope,
        evaluated_at=evaluated_at,
        arm=risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
    )


def _internal_policy() -> risk_authority.RiskPolicySnapshot:
    return risk_authority.RiskPolicySnapshot(
        policy_id=risk_authority.RiskPolicyId(UUID("51000000-0000-0000-0000-000000000060")),
        version=risk_authority.RiskPolicyVersion(1),
        fingerprint=_fp("internal-policy"),
        budget_config_fingerprint=_fp("budget-config"),
        arm=risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
    )


def _corrupted_evidence(
    field_name: str, new_value: object = _MISSING
) -> risk_authority.RiskEvidence:
    base = _evidence()
    raw = object.__new__(risk_authority.RiskEvidence)
    for field in fields(risk_authority.RiskEvidence):
        if field.name == field_name and new_value is _MISSING:
            continue
        value = new_value if field.name == field_name else getattr(base, field.name)
        object.__setattr__(raw, field.name, value)
    return raw


class _FakeBudgetEvaluator:
    policy_fingerprint: risk_authority.RiskFingerprint

    def __init__(
        self,
        *,
        admitted: bool = True,
        reduced: bool = False,
        authorized_quantity: order_intent.OrderQuantity | None = None,
        bounded_loss_at_stop: proprietary_accounts.MoneyAmount | None = None,
        reason: risk_authority.RiskReason | None = None,
        failure: risk_authority.RiskError | None = None,
    ) -> None:
        self.policy_fingerprint = _fp("budget-policy")
        self._admitted = admitted
        self._reduced = reduced
        self._authorized_quantity = authorized_quantity
        self._bounded_loss_at_stop = bounded_loss_at_stop
        self._reason = reason or risk_authority.RiskReason(
            (
                risk_authority.RiskReasonCode.reduced
                if reduced
                else risk_authority.RiskReasonCode.admitted
            ),
            "reduced" if reduced else "admitted",
        )
        self._failure = failure

    def evaluate(
        self,
        evidence: risk_authority.RiskEvidence,
        policy: risk_authority.RiskPolicySnapshot,
        *,
        evaluated_at: datetime,
    ) -> result.Result[risk_authority.RiskBudgetEvaluation, risk_authority.RiskError]:
        if self._failure is not None:
            return result.Failure(self._failure)
        return result.Success(
            risk_authority.RiskBudgetEvaluation(
                admitted=self._admitted,
                reduced=self._reduced,
                authorized_quantity=self._authorized_quantity,
                bounded_loss_at_stop=self._bounded_loss_at_stop,
                reason=self._reason,
            )
        )


class _FakeCapacityStore:
    def __init__(self, *, reserve_failure: risk_authority.RiskError | None = None) -> None:
        self._reserve_failure = reserve_failure
        self.reservations: list[risk_authority.RiskReservation] = []

    def reserve(
        self, reservation: risk_authority.RiskReservation
    ) -> result.Result[risk_authority.RiskReservation, risk_authority.RiskError]:
        if self._reserve_failure is not None:
            return result.Failure(self._reserve_failure)
        self.reservations.append(reservation)
        return result.Success(reservation)

    def commit(
        self, reservation_id: risk_authority.RiskReservationId
    ) -> result.Result[risk_authority.RiskReservation, risk_authority.RiskError]:
        return result.Failure(risk_authority.RiskResolutionError("commit not implemented"))

    def release(
        self, reservation_id: risk_authority.RiskReservationId
    ) -> result.Result[risk_authority.RiskReservation, risk_authority.RiskError]:
        return result.Failure(risk_authority.RiskResolutionError("release not implemented"))

    def expire(
        self, reservation_id: risk_authority.RiskReservationId
    ) -> result.Result[risk_authority.RiskReservation, risk_authority.RiskError]:
        return result.Failure(risk_authority.RiskResolutionError("expire not implemented"))

    def get(
        self, reservation_id: risk_authority.RiskReservationId
    ) -> result.Result[risk_authority.RiskReservation | None, risk_authority.RiskError]:
        return result.Success(None)


def _run_admission(
    evidence: risk_authority.RiskEvidence | None = None,
    budget: _FakeBudgetEvaluator | None = None,
    capacity: _FakeCapacityStore | None = None,
    *,
    reservation_generation: int = 0,
) -> result.Result[risk_authority.RiskDecision, risk_authority.RiskError]:
    return risk_authority.evaluate_risk_admission(
        _evidence() if evidence is None else evidence,
        _internal_policy(),
        _FakeBudgetEvaluator(admitted=True, authorized_quantity=_quantity("1.0"))
        if budget is None
        else budget,
        _FakeCapacityStore() if capacity is None else capacity,
        decision_id=_DECISION_ID,
        authorization_id=_AUTH_ID,
        reservation_id=_RESERVATION_ID,
        reservation_generation=reservation_generation,
    )


def _allow_decision() -> risk_authority.RiskDecision:
    outcome = _run_admission()
    assert isinstance(outcome, result.Success)
    return outcome.value


def _assert_reject(
    outcome: result.Result[risk_authority.RiskDecision, risk_authority.RiskError],
    reason_code: risk_authority.RiskReasonCode,
) -> risk_authority.RiskDecision:
    assert isinstance(outcome, result.Success)
    decision = outcome.value
    assert decision.outcome is risk_authority.RiskOutcome.REJECT
    assert decision.authorization is None
    assert decision.reasons[0].code is reason_code
    return decision


def test_outcome_severity_is_monotonic() -> None:
    ordering = [
        risk_authority.RiskOutcome.ALLOW,
        risk_authority.RiskOutcome.REDUCE,
        risk_authority.RiskOutcome.REJECT,
        risk_authority.RiskOutcome.FREEZE_TRADER,
        risk_authority.RiskOutcome.CONTAIN_ACCOUNT,
        risk_authority.RiskOutcome.KILL,
    ]
    assert [risk_authority.OUTCOME_SEVERITY[outcome] for outcome in ordering] == [0, 1, 2, 3, 4, 5]
    assert set(risk_authority.OUTCOME_SEVERITY) == set(ordering)


def test_value_objects_reject_bad_uuid_type() -> None:
    for cls in (
        risk_authority.RiskDecisionId,
        risk_authority.RiskAuthorizationId,
        risk_authority.RiskReservationId,
        risk_authority.RiskPolicyId,
    ):
        with pytest.raises(risk_authority.RiskValidationError):
            cls(cast(UUID, "not-a-uuid"))


def test_fingerprint_rejects_bad_format() -> None:
    for bad in ("", "abc", "G" * 64, "a" * 63, "a" * 65, "0" * 32):
        with pytest.raises(risk_authority.RiskValidationError):
            risk_authority.RiskFingerprint(bad)
    assert risk_authority.RiskFingerprint("0" * 64).value == "0" * 64


def test_policy_version_rejects_zero_negative_and_bool() -> None:
    for bad in (0, -1, -100):
        with pytest.raises(risk_authority.RiskValidationError):
            risk_authority.RiskPolicyVersion(bad)
    # bool is rejected as int (exact runtime type)
    with pytest.raises(risk_authority.RiskValidationError):
        risk_authority.RiskPolicyVersion(True)


def test_trader_version_and_scope_generation_reject_bool() -> None:
    with pytest.raises(risk_authority.RiskValidationError):
        risk_authority.RiskTraderIdentity(
            trader_id=UUID("51000000-0000-0000-0000-000000000010"),
            trader_version=True,
            config_fingerprint=_fp("trader-config"),
        )
    with pytest.raises(risk_authority.RiskValidationError):
        _scope(generation=True)


def test_evidence_construction_success_and_complete() -> None:
    evidence = _evidence()
    assert evidence.is_complete() is True
    assert isinstance(evidence.logical_values(), tuple)


def test_evidence_missing_mandatory_field_is_incomplete() -> None:
    base = _evidence()
    raw = object.__new__(risk_authority.RiskEvidence)
    for field in fields(risk_authority.RiskEvidence):
        if field.name == "account_policy_ref":
            continue
        object.__setattr__(raw, field.name, getattr(base, field.name))
    assert raw.is_complete() is False
    assert base.is_complete() is True


def test_evidence_rejects_bounded_loss_without_stop() -> None:
    with pytest.raises(risk_authority.RiskValidationError):
        _evidence(stop_loss=None, bounded_loss_at_stop=_money("50"))


def test_evidence_allows_stop_without_bounded_loss() -> None:
    evidence = _evidence(stop_loss=_price("1.05"), bounded_loss_at_stop=None)
    assert evidence.is_complete() is True


def test_evidence_rejects_currency_mismatch() -> None:
    with pytest.raises(risk_authority.RiskValidationError):
        _evidence(requested_notional=_money("1000", currency=_EUR))


def test_evidence_rejects_timezone_naive_evaluated_at() -> None:
    with pytest.raises(risk_authority.RiskValidationError):
        _evidence(evaluated_at=datetime(2026, 8, 9, 12, 0, 0))


def test_transition_scope_forward_escalation() -> None:
    current = _scope(state=risk_authority.RiskScopeState.NORMAL, generation=0)
    outcome = risk_authority.transition_scope(
        current,
        risk_authority.RiskScopeState.FREEZE_TRADER,
        scope_id=_ACCOUNT.value,
        kind=risk_authority.RiskScopeKind.ACCOUNT,
        since=_T0,
        reason=risk_authority.RiskReasonCode.scope_frozen,
        generation=1,
    )
    assert isinstance(outcome, result.Success)
    snapshot = outcome.value
    assert snapshot.state is risk_authority.RiskScopeState.FREEZE_TRADER
    assert snapshot.generation == 1


def test_transition_scope_allows_direct_kill_jump() -> None:
    current = _scope(state=risk_authority.RiskScopeState.NORMAL, generation=0)
    outcome = risk_authority.transition_scope(
        current,
        risk_authority.RiskScopeState.KILL,
        scope_id=_ACCOUNT.value,
        kind=risk_authority.RiskScopeKind.ACCOUNT,
        since=_T0,
        reason=risk_authority.RiskReasonCode.kill,
        generation=1,
    )
    assert isinstance(outcome, result.Success)
    assert outcome.value.state is risk_authority.RiskScopeState.KILL


def test_transition_scope_allows_same_state_reassertion() -> None:
    current = _scope(state=risk_authority.RiskScopeState.NORMAL, generation=0)
    outcome = risk_authority.transition_scope(
        current,
        risk_authority.RiskScopeState.NORMAL,
        scope_id=_ACCOUNT.value,
        kind=risk_authority.RiskScopeKind.ACCOUNT,
        since=_T0,
        reason=risk_authority.RiskReasonCode.reduced_capacity,
        generation=1,
    )
    assert isinstance(outcome, result.Success)


def test_transition_scope_rejects_same_or_lower_generation() -> None:
    current = _scope(state=risk_authority.RiskScopeState.NORMAL, generation=5)
    for generation in (5, 4):
        outcome = risk_authority.transition_scope(
            current,
            risk_authority.RiskScopeState.NORMAL,
            scope_id=_ACCOUNT.value,
            kind=risk_authority.RiskScopeKind.ACCOUNT,
            since=_T0,
            reason=risk_authority.RiskReasonCode.reduced_capacity,
            generation=generation,
        )
        assert isinstance(outcome, result.Failure)


def test_transition_scope_rejects_de_escalation() -> None:
    current = _scope(state=risk_authority.RiskScopeState.FREEZE_TRADER, generation=2)
    outcome = risk_authority.transition_scope(
        current,
        risk_authority.RiskScopeState.NORMAL,
        scope_id=_ACCOUNT.value,
        kind=risk_authority.RiskScopeKind.ACCOUNT,
        since=_T0,
        reason=risk_authority.RiskReasonCode.reduced_capacity,
        generation=3,
    )
    assert isinstance(outcome, result.Failure)
    assert isinstance(outcome.error, risk_authority.RiskResolutionError)


def test_recover_scope_de_escalation() -> None:
    current = _scope(state=risk_authority.RiskScopeState.CONTAIN_ACCOUNT, generation=4)
    outcome = risk_authority.recover_scope(
        current,
        risk_authority.RiskScopeState.REDUCED_CAPACITY,
        scope_id=_ACCOUNT.value,
        kind=risk_authority.RiskScopeKind.ACCOUNT,
        since=_T0,
        reason=risk_authority.RiskReasonCode.reduced_capacity,
        generation=5,
        evidence_ref=_fp("recovery-evidence"),
    )
    assert isinstance(outcome, result.Success)
    assert outcome.value.state is risk_authority.RiskScopeState.REDUCED_CAPACITY


def test_recover_scope_kill_is_non_recoverable() -> None:
    current = _scope(state=risk_authority.RiskScopeState.KILL, generation=9)
    outcome = risk_authority.recover_scope(
        current,
        risk_authority.RiskScopeState.NORMAL,
        scope_id=_ACCOUNT.value,
        kind=risk_authority.RiskScopeKind.ACCOUNT,
        since=_T0,
        reason=risk_authority.RiskReasonCode.reduced_capacity,
        generation=10,
        evidence_ref=_fp("recovery-evidence"),
    )
    assert isinstance(outcome, result.Failure)


def test_scope_blocks_new_admission_only_for_terminal_states() -> None:
    expectations = {
        risk_authority.RiskScopeState.NORMAL: False,
        risk_authority.RiskScopeState.REDUCED_CAPACITY: False,
        risk_authority.RiskScopeState.FREEZE_TRADER: True,
        risk_authority.RiskScopeState.CONTAIN_ACCOUNT: True,
        risk_authority.RiskScopeState.KILL: True,
    }
    for state, expected in expectations.items():
        assert _scope(state=state).blocks_new_admission is expected


def test_void_authorization_returns_void_copy_without_mutation() -> None:
    decision = _allow_decision()
    auth = decision.authorization
    assert auth is not None
    voided = risk_authority.void_authorization(
        auth,
        reason=risk_authority.RiskReason(
            risk_authority.RiskReasonCode.authorization_mutation,
            "authorization voided",
        ),
        voided_at=_T0,
    )
    assert voided.status is risk_authority.RiskAuthorizationStatus.VOID
    assert auth.status is risk_authority.RiskAuthorizationStatus.ISSUED
    assert voided is not auth
    assert risk_authority.RiskReasonCode.authorization_mutation in voided.reason_codes


def test_void_authorization_requires_mutation_reason_and_not_predating_issue() -> None:
    decision = _allow_decision()
    auth = decision.authorization
    assert auth is not None
    with pytest.raises(risk_authority.RiskValidationError):
        risk_authority.void_authorization(
            auth,
            reason=risk_authority.RiskReason(risk_authority.RiskReasonCode.admitted, "wrong"),
            voided_at=_T0,
        )
    with pytest.raises(risk_authority.RiskValidationError):
        risk_authority.void_authorization(
            auth,
            reason=risk_authority.RiskReason(
                risk_authority.RiskReasonCode.authorization_mutation, "voided"
            ),
            voided_at=_T0 - timedelta(seconds=1),
        )


def test_is_authorization_reusable() -> None:
    decision = _allow_decision()
    auth = decision.authorization
    assert auth is not None
    scope = _scope(generation=0)
    policy_version = account_policy.AccountPolicyVersion(3)
    assert (
        risk_authority.is_authorization_reusable(
            auth, scope=scope, account_policy_version=policy_version, evaluated_at=_T0
        )
        is True
    )
    assert auth.valid_until == _T0 + timedelta(seconds=300)
    assert (
        risk_authority.is_authorization_reusable(
            auth,
            scope=scope,
            account_policy_version=policy_version,
            evaluated_at=auth.valid_until + timedelta(microseconds=1),
        )
        is False
    )
    assert (
        risk_authority.is_authorization_reusable(
            auth,
            scope=_scope(generation=1),
            account_policy_version=policy_version,
            evaluated_at=_T0,
        )
        is False
    )
    assert (
        risk_authority.is_authorization_reusable(
            auth,
            scope=scope,
            account_policy_version=account_policy.AccountPolicyVersion(4),
            evaluated_at=_T0,
        )
        is False
    )
    voided = risk_authority.void_authorization(
        auth,
        reason=risk_authority.RiskReason(
            risk_authority.RiskReasonCode.authorization_mutation, "voided"
        ),
        voided_at=_T0,
    )
    assert (
        risk_authority.is_authorization_reusable(
            voided, scope=scope, account_policy_version=policy_version, evaluated_at=_T0
        )
        is False
    )


def test_evaluate_full_allow_path() -> None:
    outcome = _run_admission()
    assert isinstance(outcome, result.Success)
    decision = outcome.value
    assert decision.outcome is risk_authority.RiskOutcome.ALLOW
    auth = decision.authorization
    assert auth is not None
    assert auth.status is risk_authority.RiskAuthorizationStatus.ISSUED
    assert auth.decision_id == decision.decision_id
    assert auth.authorized_quantity == _quantity("1.0")
    assert auth.scope_generation == 0
    assert decision.reasons[0].code is risk_authority.RiskReasonCode.admitted


def test_evaluate_reduce_path() -> None:
    budget = _FakeBudgetEvaluator(
        admitted=True,
        reduced=True,
        authorized_quantity=_quantity("0.5"),
    )
    outcome = _run_admission(budget=budget)
    assert isinstance(outcome, result.Success)
    decision = outcome.value
    assert decision.outcome is risk_authority.RiskOutcome.REDUCE
    assert decision.authorization is not None
    assert decision.authorization.authorized_quantity == _quantity("0.5")
    assert decision.reasons[0].code is risk_authority.RiskReasonCode.reduced


def test_evaluate_rejects_production_environment() -> None:
    outcome = _run_admission(
        evidence=_evidence(environment=risk_authority.RiskEnvironment.PRODUCTION)
    )
    _assert_reject(outcome, risk_authority.RiskReasonCode.evidence_missing)


def test_evaluate_rejects_scope_frozen() -> None:
    outcome = _run_admission(
        evidence=_evidence(scope=_scope(state=risk_authority.RiskScopeState.FREEZE_TRADER))
    )
    _assert_reject(outcome, risk_authority.RiskReasonCode.scope_frozen)


def test_evaluate_rejects_incomplete_evidence() -> None:
    outcome = _run_admission(evidence=_corrupted_evidence("account_policy_ref"))
    _assert_reject(outcome, risk_authority.RiskReasonCode.evidence_missing)


def test_evaluate_rejects_stale_evidence() -> None:
    stale_at = _T0 - timedelta(seconds=301)
    evidence = _evidence(
        account_state=_account_state(observed_at=stale_at),
        market_evidence=_market_evidence(observed_at=stale_at),
    )
    outcome = _run_admission(evidence=evidence)
    _assert_reject(outcome, risk_authority.RiskReasonCode.evidence_stale)


def test_evaluate_rejects_currency_mismatch() -> None:
    evidence = _corrupted_evidence("requested_notional", _money("1000", currency=_EUR))
    outcome = _run_admission(evidence=evidence)
    _assert_reject(outcome, risk_authority.RiskReasonCode.currency_mismatch)


def test_evaluate_rejects_when_budget_not_admitted() -> None:
    budget = _FakeBudgetEvaluator(
        admitted=False,
        reason=risk_authority.RiskReason(
            risk_authority.RiskReasonCode.budget_exceeded, "budget exceeded"
        ),
    )
    outcome = _run_admission(budget=budget)
    _assert_reject(outcome, risk_authority.RiskReasonCode.budget_exceeded)


def test_evaluate_rejects_on_capacity_reserve_failure() -> None:
    capacity = _FakeCapacityStore(
        reserve_failure=risk_authority.RiskResolutionError("capacity exhausted")
    )
    outcome = _run_admission(capacity=capacity)
    _assert_reject(outcome, risk_authority.RiskReasonCode.capacity_exhausted)


def test_evaluate_type_checks_arguments() -> None:
    outcome = risk_authority.evaluate_risk_admission(
        cast(risk_authority.RiskEvidence, "not-evidence"),
        _internal_policy(),
        _FakeBudgetEvaluator(admitted=True, authorized_quantity=_quantity("1.0")),
        _FakeCapacityStore(),
        decision_id=_DECISION_ID,
        authorization_id=_AUTH_ID,
        reservation_id=_RESERVATION_ID,
        reservation_generation=0,
    )
    assert isinstance(outcome, result.Failure)
    assert isinstance(outcome.error, risk_authority.RiskValidationError)


def _policy_with(
    *,
    policy_id: UUID | None = None,
    version: int = 1,
    arm: risk_authority.RiskArm = risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
) -> risk_authority.RiskPolicySnapshot:
    effective_id = (
        UUID("51000000-0000-0000-0000-000000000060") if policy_id is None else policy_id
    )
    return risk_authority.RiskPolicySnapshot(
        policy_id=risk_authority.RiskPolicyId(effective_id),
        version=risk_authority.RiskPolicyVersion(version),
        fingerprint=_fp("internal-policy"),
        budget_config_fingerprint=_fp("budget-config"),
        arm=arm,
    )


def _run_admission_with_policy(
    policy: risk_authority.RiskPolicySnapshot,
) -> result.Result[risk_authority.RiskDecision, risk_authority.RiskError]:
    return risk_authority.evaluate_risk_admission(
        _evidence(),
        policy,
        _FakeBudgetEvaluator(admitted=True, authorized_quantity=_quantity("1.0")),
        _FakeCapacityStore(),
        decision_id=_DECISION_ID,
        authorization_id=_AUTH_ID,
        reservation_id=_RESERVATION_ID,
        reservation_generation=0,
    )


def test_evaluate_rejects_arm_mismatch() -> None:
    outcome = _run_admission_with_policy(
        _policy_with(arm=risk_authority.RiskArm.TRADERS_RISK_ONLY)
    )
    _assert_reject(outcome, risk_authority.RiskReasonCode.arm_mismatch)


def test_evaluate_rejects_internal_policy_version_mismatch() -> None:
    outcome = _run_admission_with_policy(_policy_with(version=2))
    _assert_reject(outcome, risk_authority.RiskReasonCode.policy_version_mismatch)


def test_evaluate_rejects_internal_policy_identity_mismatch() -> None:
    outcome = _run_admission_with_policy(
        _policy_with(policy_id=UUID("51000000-0000-0000-0000-0000000000a2"))
    )
    _assert_reject(outcome, risk_authority.RiskReasonCode.policy_version_mismatch)


def _record(record_id: UUID) -> risk_authority.RiskCounterfactualRecord:
    return risk_authority.RiskCounterfactualRecord(
        record_id=record_id,
        decision_id=_DECISION_ID,
        authorization_id=_AUTH_ID,
        arm=risk_authority.RiskArm.CIBO_MANAGED_TRADERS_RISK,
        outcome=risk_authority.RiskOutcome.REJECT,
        reason_codes=(risk_authority.RiskReasonCode.budget_exceeded,),
        intent_digest=_fp("intent"),
        account_id=_ACCOUNT,
        evaluated_at=_T0,
    )


def test_counterfactual_ledger_append_is_immutable() -> None:
    record = _record(UUID("51000000-0000-0000-0000-0000000000b0"))
    ledger = risk_authority.RiskCounterfactualLedger(())
    next_ledger = ledger.append(record)
    assert ledger.records == ()
    assert next_ledger.records == (record,)


def test_counterfactual_ledger_rejects_duplicate_record_ids() -> None:
    record = _record(UUID("51000000-0000-0000-0000-0000000000b1"))
    with pytest.raises(risk_authority.RiskValidationError):
        risk_authority.RiskCounterfactualLedger((record, record))


def test_link_outcome_returns_new_record() -> None:
    record = _record(UUID("51000000-0000-0000-0000-0000000000b2"))
    linked = risk_authority.link_outcome(
        record,
        risk_authority.RiskRealizedOutcome.REJECTED_WINNER,
        linked_at=_T0,
    )
    assert linked.realized is risk_authority.RiskRealizedOutcome.REJECTED_WINNER
    assert record.realized is None
    assert linked is not record


def test_compute_fingerprint_is_stable_and_order_sensitive() -> None:
    assert risk_authority.compute_fingerprint("a", "b") == risk_authority.compute_fingerprint(
        "a", "b"
    )
    assert risk_authority.compute_fingerprint("a", "b") != risk_authority.compute_fingerprint(
        "b", "a"
    )


def test_compute_evidence_state_fingerprint_changes_with_equity() -> None:
    first = risk_authority.compute_evidence_state_fingerprint(
        _evidence(account_state=_account_state(equity="100000"))
    )
    second = risk_authority.compute_evidence_state_fingerprint(
        _evidence(account_state=_account_state(equity="100001"))
    )
    assert first != second
    assert first == risk_authority.compute_evidence_state_fingerprint(
        _evidence(account_state=_account_state(equity="100000"))
    )


def test_no_secret_material_in_repr() -> None:
    decision = _allow_decision()
    auth = decision.authorization
    assert auth is not None
    for forbidden in ("token", "password", "secret", "bearer"):
        assert forbidden not in repr(decision)
        assert forbidden not in repr(auth)
