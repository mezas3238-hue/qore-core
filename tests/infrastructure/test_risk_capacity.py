from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as client_accounts
import qore.infrastructure.order_intent as order_intent
import qore.infrastructure.proprietary_accounts as proprietary_accounts
import qore.infrastructure.risk_authority as risk_authority
import qore.infrastructure.risk_capacity as risk_capacity
import qore.kernel.result as result

_USD = proprietary_accounts.CurrencyCode("USD")
_EUR = proprietary_accounts.CurrencyCode("EUR")
_ACCOUNT = client_accounts.TradingAccountId(UUID("52000000-0000-0000-0000-000000000001"))
_T0 = datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)


def _rid(n: int) -> risk_authority.RiskReservationId:
    return risk_authority.RiskReservationId(UUID(f"52000000-0000-0000-0000-{n:012d}"))


def _fp(seed: str) -> risk_authority.RiskFingerprint:
    return risk_authority.compute_fingerprint(seed)


def _money(
    amount: str,
    currency: proprietary_accounts.CurrencyCode = _USD,
) -> proprietary_accounts.MoneyAmount:
    return proprietary_accounts.MoneyAmount(currency, Decimal(amount))


def _reservation(
    *,
    rid: int,
    generation: int,
    notional: str = "100",
    currency: proprietary_accounts.CurrencyCode = _USD,
    status: risk_authority.RiskReservationStatus = risk_authority.RiskReservationStatus.RESERVED,
    reserved_at: datetime = _T0,
) -> risk_authority.RiskReservation:
    return risk_authority.RiskReservation(
        reservation_id=_rid(rid),
        generation=generation,
        account_id=_ACCOUNT,
        intent_digest=_fp(f"intent-{rid}"),
        policy_fingerprint=_fp("policy"),
        state_fingerprint=_fp("state"),
        authorized_quantity=order_intent.OrderQuantity(Decimal("1")),
        notional=_money(notional, currency),
        status=status,
        reserved_at=reserved_at,
    )


def test_reserve_prevents_concurrent_double_spend() -> None:
    ledger = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    first = _reservation(rid=1, generation=1, notional="600")
    second = _reservation(rid=2, generation=2, notional="600")

    first_result = ledger.reserve(first)
    assert isinstance(first_result, result.Success)

    second_result = first_result.value.reserve(second)
    assert isinstance(second_result, result.Failure)
    assert isinstance(second_result.error, risk_capacity.RiskCapacityConflictError)


def test_reserve_capacity_exhausted_has_no_free_fabrication() -> None:
    ledger = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    first = _reservation(rid=1, generation=1, notional="1000")
    second = _reservation(rid=2, generation=2, notional="1")

    first_result = ledger.reserve(first)
    assert isinstance(first_result, result.Success)

    second_result = first_result.value.reserve(second)
    assert isinstance(second_result, result.Failure)
    assert isinstance(second_result.error, risk_capacity.RiskCapacityConflictError)


def test_reserve_rejects_stale_generation() -> None:
    base = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    reserved = base.reserve(_reservation(rid=1, generation=5, notional="100"))
    assert isinstance(reserved, result.Success)
    ledger = reserved.value

    same = ledger.reserve(_reservation(rid=2, generation=5, notional="100"))
    lower = ledger.reserve(_reservation(rid=3, generation=4, notional="100"))

    assert isinstance(same, result.Failure)
    assert isinstance(same.error, risk_capacity.RiskCapacityConflictError)
    assert isinstance(lower, result.Failure)
    assert isinstance(lower.error, risk_capacity.RiskCapacityConflictError)


def test_commit_rejects_stale_generation() -> None:
    base = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    a = _reservation(rid=1, generation=5, notional="100")
    b = _reservation(rid=2, generation=6, notional="100")

    after_a = base.reserve(a)
    assert isinstance(after_a, result.Success)
    after_b = after_a.value.reserve(b)
    assert isinstance(after_b, result.Success)

    stale_commit = after_b.value.commit(a.reservation_id)
    assert isinstance(stale_commit, result.Failure)
    assert isinstance(stale_commit.error, risk_capacity.RiskCapacityConflictError)


def test_commit_is_idempotent() -> None:
    base = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    a = _reservation(rid=1, generation=1, notional="500")

    reserved = base.reserve(a)
    assert isinstance(reserved, result.Success)
    committed = reserved.value.commit(a.reservation_id)
    assert isinstance(committed, result.Success)
    committed_ledger = committed.value

    again = committed_ledger.commit(a.reservation_id)
    assert isinstance(again, result.Success)
    assert again.value is committed_ledger

    stored = committed_ledger.get(a.reservation_id)
    assert stored is not None
    assert stored.status is risk_authority.RiskReservationStatus.COMMITTED


def test_release_is_idempotent() -> None:
    base = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    a = _reservation(rid=1, generation=1, notional="600")

    reserved = base.reserve(a)
    assert isinstance(reserved, result.Success)
    released = reserved.value.release(a.reservation_id)
    assert isinstance(released, result.Success)
    released_ledger = released.value

    again = released_ledger.release(a.reservation_id)
    assert isinstance(again, result.Success)
    assert again.value is released_ledger

    stored = released_ledger.get(a.reservation_id)
    assert stored is not None
    assert stored.status is risk_authority.RiskReservationStatus.RELEASED


def test_release_frees_notional_exactly_once() -> None:
    base = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    a = _reservation(rid=1, generation=1, notional="600")

    reserved = base.reserve(a)
    assert isinstance(reserved, result.Success)
    released = reserved.value.release(a.reservation_id)
    assert isinstance(released, result.Success)
    ledger = released.value

    refill = ledger.reserve(_reservation(rid=2, generation=2, notional="600"))
    assert isinstance(refill, result.Success)

    overflow = refill.value.reserve(_reservation(rid=3, generation=3, notional="600"))
    assert isinstance(overflow, result.Failure)
    assert isinstance(overflow.error, risk_capacity.RiskCapacityConflictError)


def test_expire_only_reserved_and_idempotent() -> None:
    base = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    a = _reservation(rid=1, generation=1, notional="100")

    reserved = base.reserve(a)
    assert isinstance(reserved, result.Success)
    expired = reserved.value.expire(a.reservation_id)
    assert isinstance(expired, result.Success)
    expired_ledger = expired.value

    stored = expired_ledger.get(a.reservation_id)
    assert stored is not None
    assert stored.status is risk_authority.RiskReservationStatus.EXPIRED
    assert expired_ledger.reserved_notional().amount == Decimal(0)

    again = expired_ledger.expire(a.reservation_id)
    assert isinstance(again, result.Success)
    assert again.value is expired_ledger


def test_expire_rejects_committed_and_released() -> None:
    base = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))

    committed_res = _reservation(rid=1, generation=1, notional="100")
    reserved = base.reserve(committed_res)
    assert isinstance(reserved, result.Success)
    committed = reserved.value.commit(committed_res.reservation_id)
    assert isinstance(committed, result.Success)
    committed_fail = committed.value.expire(committed_res.reservation_id)
    assert isinstance(committed_fail, result.Failure)
    assert isinstance(committed_fail.error, risk_capacity.RiskCapacityConflictError)

    released_res = _reservation(rid=2, generation=2, notional="100")
    reserved2 = committed.value.reserve(released_res)
    assert isinstance(reserved2, result.Success)
    released = reserved2.value.release(released_res.reservation_id)
    assert isinstance(released, result.Success)
    released_fail = released.value.expire(released_res.reservation_id)
    assert isinstance(released_fail, result.Failure)
    assert isinstance(released_fail.error, risk_capacity.RiskCapacityConflictError)


def test_ledger_is_immutable_and_replay_deterministic() -> None:
    base = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    a = _reservation(rid=1, generation=1, notional="100")

    reserved = base.reserve(a)
    assert isinstance(reserved, result.Success)
    ledger = reserved.value

    assert base.reservations == ()
    assert ledger.reservations == (a,)
    assert ledger.logical_values() == ledger.logical_values()

    replayed = base.reserve(a)
    assert isinstance(replayed, result.Success)
    assert replayed.value.logical_values() == ledger.logical_values()


def test_notional_accounting_distinguishes_reserved_and_committed() -> None:
    base = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    a = _reservation(rid=1, generation=1, notional="300")
    b = _reservation(rid=2, generation=2, notional="400")

    after_a = base.reserve(a)
    assert isinstance(after_a, result.Success)
    assert after_a.value.reserved_notional().amount == Decimal("300")
    assert after_a.value.committed_notional().amount == Decimal("0")

    committed = after_a.value.commit(a.reservation_id)
    assert isinstance(committed, result.Success)
    assert committed.value.reserved_notional().amount == Decimal("300")
    assert committed.value.committed_notional().amount == Decimal("300")

    after_b = committed.value.reserve(b)
    assert isinstance(after_b, result.Success)
    assert after_b.value.reserved_notional().amount == Decimal("700")
    assert after_b.value.committed_notional().amount == Decimal("300")


def test_generation_rejects_bool() -> None:
    with pytest.raises(risk_capacity.RiskCapacityValidationError):
        risk_capacity.RiskCapacityLedger((), True, _money("1000"))


def test_reservation_rejects_naive_timestamp() -> None:
    with pytest.raises(risk_authority.RiskValidationError):
        _reservation(rid=1, generation=1, reserved_at=datetime(2026, 8, 9, 12, 0, 0))


def test_ledger_rejects_mixed_currency() -> None:
    eur_reservation = _reservation(rid=1, generation=1, notional="100", currency=_EUR)
    with pytest.raises(risk_capacity.RiskCapacityValidationError):
        risk_capacity.RiskCapacityLedger((eur_reservation,), 1, _money("1000"))


def test_reserve_rejects_currency_mismatch() -> None:
    ledger = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    eur = _reservation(rid=1, generation=1, notional="100", currency=_EUR)
    outcome = ledger.reserve(eur)
    assert isinstance(outcome, result.Failure)
    assert isinstance(outcome.error, risk_capacity.RiskCapacityValidationError)


def test_get_returns_none_for_unknown_id() -> None:
    ledger = risk_capacity.RiskCapacityLedger((), 0, _money("1000"))
    assert ledger.get(_rid(99)) is None


def test_store_satisfies_capacity_protocol() -> None:
    store = risk_capacity.InMemoryRiskCapacityStore(_money("1000"))
    assert isinstance(store, risk_authority.RiskCapacityStore)


def test_store_delegates_and_updates_ledger() -> None:
    store = risk_capacity.InMemoryRiskCapacityStore(_money("1000"))
    assert store.ledger.generation == 0
    assert store.capacity.amount == Decimal("1000")

    a = _reservation(rid=1, generation=1, notional="600")
    reserved = store.reserve(a)
    assert isinstance(reserved, result.Success)
    assert reserved.value is a
    assert store.ledger.reserved_notional().amount == Decimal("600")

    got = store.get(a.reservation_id)
    assert isinstance(got, result.Success)
    stored = got.value
    assert stored is not None
    assert stored.reservation_id == a.reservation_id

    committed = store.commit(a.reservation_id)
    assert isinstance(committed, result.Success)
    assert committed.value.status is risk_authority.RiskReservationStatus.COMMITTED

    unknown = store.get(_rid(99))
    assert isinstance(unknown, result.Success)
    assert unknown.value is None


def test_store_reserve_double_spend_fails_closed() -> None:
    store = risk_capacity.InMemoryRiskCapacityStore(_money("1000"))
    first = _reservation(rid=1, generation=1, notional="600")
    second = _reservation(rid=2, generation=2, notional="600")

    assert isinstance(store.reserve(first), result.Success)
    failed = store.reserve(second)
    assert isinstance(failed, result.Failure)
    assert isinstance(failed.error, risk_capacity.RiskCapacityConflictError)
    assert store.ledger.reserved_notional().amount == Decimal("600")
