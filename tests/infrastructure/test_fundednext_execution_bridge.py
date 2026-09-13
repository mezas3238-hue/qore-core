from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import (
    RiskAuthorization,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.fundednext_execution_bridge import (
    FundedNextExecutionBridgeError,
    build_fundednext_execution_submission,
    extract_risk_provenance,
)
from qore.infrastructure.order_intent import OrderSide, OrderType
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
)

_NOW = datetime(2026, 9, 13, 18, 0, tzinfo=UTC)


def _authorization(
    fingerprint: str = "a" * 64,
    *,
    decision: RiskDecision = RiskDecision.ALLOW,
    entry_type: str = "market",
) -> RiskAuthorization:
    return RiskAuthorization(
        authorization_id=f"risk-{fingerprint[:24]}",
        account_binding_id="fn-si-opaque-001",
        trader_id=TraderLineage.VT08_FOREX,
        request_id="request-1",
        signal_fingerprint="signal-1",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        side="long",
        entry_type=entry_type,
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        requested_volume=Decimal("1"),
        authorized_volume=(
            Decimal("1") if decision is not RiskDecision.REJECT else Decimal("0")
        ),
        monetary_stop_loss=(
            Decimal("20") if decision is not RiskDecision.REJECT else Decimal("0")
        ),
        aggregate_pre_order_worst_case=Decimal("0"),
        aggregate_post_order_worst_case=(
            Decimal("20") if decision is not RiskDecision.REJECT else Decimal("0")
        ),
        provider_headroom=Decimal("120"),
        internal_qore_headroom=Decimal("25"),
        margin_reserved=(
            Decimal("50") if decision is not RiskDecision.REJECT else Decimal("0")
        ),
        decision=decision,
        reason="test",
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=2),
        authorization_fingerprint=fingerprint,
    )


def _switch() -> ExecutionSafetySwitchSnapshot:
    return ExecutionSafetySwitchSnapshot(
        state=ExecutionSwitchState.ENABLED,
        observed_at=_NOW,
        reason="fundednext demo execution switch enabled",
    )


def test_bridge_preserves_risk_identity_and_is_deterministic() -> None:
    authorization = _authorization()
    first = build_fundednext_execution_submission(
        authorization,
        switch=_switch(),
        authorized_at=_NOW,
        submitted_at=_NOW,
    )
    second = build_fundednext_execution_submission(
        authorization,
        switch=_switch(),
        authorized_at=_NOW,
        submitted_at=_NOW,
    )
    assert first == second
    intent = first.authorized_intent.intent
    assert intent.instrument.value == "GBPUSD"
    assert intent.side is OrderSide.BUY
    assert intent.order_type is OrderType.MARKET
    assert intent.stop_loss is not None and intent.stop_loss.value == Decimal("99")
    assert intent.take_profit is not None and intent.take_profit.value == Decimal("102")
    assert first.authorized_intent.authorization.expires_at == authorization.expires_at
    assert extract_risk_provenance(first) == (
        authorization.authorization_id,
        authorization.authorization_fingerprint,
        authorization.authorization_id,
    )


def test_limit_authorization_becomes_canonical_limit_intent() -> None:
    submission = build_fundednext_execution_submission(
        _authorization(entry_type="limit"),
        switch=_switch(),
        authorized_at=_NOW,
        submitted_at=_NOW,
    )
    intent = submission.authorized_intent.intent
    assert intent.order_type is OrderType.LIMIT
    assert intent.limit_price is not None
    assert intent.limit_price.value == Decimal("100")


def test_rejected_or_unsupported_authorization_cannot_cross_bridge() -> None:
    with pytest.raises(FundedNextExecutionBridgeError, match="rejected"):
        build_fundednext_execution_submission(
            _authorization(decision=RiskDecision.REJECT),
            switch=_switch(),
            authorized_at=_NOW,
            submitted_at=_NOW,
        )
    with pytest.raises(FundedNextExecutionBridgeError, match="market or limit"):
        build_fundednext_execution_submission(
            _authorization(entry_type="stop"),
            switch=_switch(),
            authorized_at=_NOW,
            submitted_at=_NOW,
        )


def test_stale_risk_authorization_cannot_be_materialized() -> None:
    with pytest.raises(FundedNextExecutionBridgeError, match="expired"):
        build_fundednext_execution_submission(
            _authorization(),
            switch=_switch(),
            authorized_at=_NOW + timedelta(minutes=3),
            submitted_at=_NOW + timedelta(minutes=3),
        )
