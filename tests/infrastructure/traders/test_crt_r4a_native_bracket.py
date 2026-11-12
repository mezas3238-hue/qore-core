"""Synthetic cTrader-native protection *planning*, never order submission."""
from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

import pytest

from qore.infrastructure.traders.crt_r4a_native_bracket import (
    CRTNativeBracketDistances,
    native_protection_for_crt_market,
)
from qore.infrastructure.traders.crt_r4a_protected_candidate import (
    CRTBrokerContract,
    CRTCandidateError,
    CRTFamily,
    CRTProtectedProposal,
)


def _case() -> tuple[CRTProtectedProposal, CRTBrokerContract]:
    base = CRTProtectedProposal(
        signal_id="evt-1", family=CRTFamily.TWO_C_MSS_C2, symbol="EURUSD",
        symbol_id=123, direction=1,
        entry_reference=Decimal("1.10300"),
        stop_loss=Decimal("1.09600"),
        take_profit=Decimal("1.12000"),
        quantity=Decimal("14000"),
        money_risk_including_slippage=Decimal("100"),
        gross_reward_risk_ratio=Decimal("2.2"),
        idempotency_key=uuid5(NAMESPACE_URL, "event-1"),
    )
    spec = CRTBrokerContract(
        symbol="EURUSD", symbol_id=123, price_tick=Decimal("0.00001"),
        value_per_tick_per_unit=Decimal("0.00001"),
        volume_step=Decimal("1000"), volume_min=Decimal("1000"),
        volume_max=Decimal("200000"), account_currency="USD",
        verified_at=datetime(2026, 11, 12, 8, tzinfo=UTC),
        provider_evidence_sha256="e" * 64,
    )
    return base, spec


def test_buy_relative_distances_exact_provider_unit() -> None:
    trade, spec = _case()
    protection = native_protection_for_crt_market(trade, spec)
    assert protection.relative_stop_loss == 700
    assert protection.relative_take_profit == 1700
    assert not protection.wire_submission_authorized
    assert protection.provider_ack_required
    assert protection.idempotency_key == trade.idempotency_key


def test_sell_relative_distances_exact_provider_unit() -> None:
    trade, spec = _case()
    trade = replace(
        trade, direction=-1, entry_reference=Decimal("1.11600"),
        stop_loss=Decimal("1.12300"), take_profit=Decimal("1.10000"),
    )
    result = native_protection_for_crt_market(trade, spec)
    assert result.relative_stop_loss == 700
    assert result.relative_take_profit == 1600


def test_unrepresentable_native_price_distance_refused() -> None:
    trade, spec = _case()
    with pytest.raises(CRTCandidateError, match="precision"):
        native_protection_for_crt_market(
            replace(trade, stop_loss=Decimal("1.096001")), spec
        )


def test_negative_stop_and_wrong_direction_refused() -> None:
    trade, spec = _case()
    for bad in (
        replace(trade, stop_loss=Decimal("1.11000")),
        replace(trade, take_profit=Decimal("1.10000")),
    ):
        with pytest.raises(CRTCandidateError, match="crosses"):
            native_protection_for_crt_market(bad, spec)


def test_broker_contract_mismatch_refused() -> None:
    trade, spec = _case()
    with pytest.raises(CRTCandidateError, match="binding mismatch"):
        native_protection_for_crt_market(trade, replace(spec, symbol_id=124))


def test_candidate_cannot_be_marked_ready_to_send() -> None:
    trade, spec = _case()
    with pytest.raises(CRTCandidateError):
        native_protection_for_crt_market(replace(trade, can_submit=True), spec)


def test_native_bracket_cannot_authorize_wire() -> None:
    trade, spec = _case()
    plan = native_protection_for_crt_market(trade, spec)
    with pytest.raises(CRTCandidateError):
        replace(plan, wire_submission_authorized=True)


def test_zero_stop_or_tp_refused() -> None:
    trade, spec = _case()
    for bad in (
        replace(trade, stop_loss=trade.entry_reference),
        replace(trade, take_profit=trade.entry_reference),
    ):
        with pytest.raises(CRTCandidateError):
            native_protection_for_crt_market(bad, spec)


def test_native_limits_are_strict_int64() -> None:
    trade, spec = _case()
    with pytest.raises(CRTCandidateError):
        replace(
            native_protection_for_crt_market(trade, spec),
            relative_stop_loss=(1 << 63),
        )


def test_native_module_is_read_only_and_never_sends() -> None:
    source = inspect.getsource(native_protection_for_crt_market)
    assert "ProtoOANewOrderReq" not in source
    assert "submit_authorized" not in source
    assert "relative_stop_loss=int(native_stop)" in source
    assert "relative_take_profit=int(native_target)" in source
    assert issubclass(CRTNativeBracketDistances, object)
