from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.pretrade_safety import (
    AuthorizedOrderIntent,
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
    PreTradeAuthorization,
    PreTradeAuthorizationId,
    PreTradeDecision,
    PreTradePolicyId,
    PreTradeSafetyBlockedError,
    PreTradeSafetyValidationError,
    authorize_order_intent,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 6, 40, tzinfo=UTC)
_INTENT_ID = OrderIntentId(UUID("af000000-0000-0000-0000-000000000001"))
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("af000000-0000-0000-0000-000000000002")),
    causation_id=CausationId(UUID("af000000-0000-0000-0000-000000000003")),
)


def _intent(intent_id: OrderIntentId = _INTENT_ID) -> OrderIntent:
    return OrderIntent(
        intent_id=intent_id,
        idempotency_key=ExecutionIdempotencyKey(
            UUID("af000000-0000-0000-0000-000000000004")
        ),
        instrument=ExecutionInstrument("EURUSD"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=_NOW,
        metadata=_METADATA,
    )


def _authorization(
    *,
    intent_id: OrderIntentId = _INTENT_ID,
    decision: PreTradeDecision = PreTradeDecision.APPROVED,
    evaluated_at: datetime = _NOW + timedelta(seconds=1),
    expires_at: datetime = _NOW + timedelta(seconds=10),
) -> PreTradeAuthorization:
    return PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(
            UUID("af000000-0000-0000-0000-000000000005")
        ),
        policy_id=PreTradePolicyId("risk.pretrade.v1"),
        intent_id=intent_id,
        decision=decision,
        evaluated_at=evaluated_at,
        expires_at=expires_at,
        reason="pre-trade policy evaluation completed",
    )


def _switch(
    state: ExecutionSwitchState = ExecutionSwitchState.ENABLED,
    observed_at: datetime = _NOW + timedelta(seconds=2),
) -> ExecutionSafetySwitchSnapshot:
    return ExecutionSafetySwitchSnapshot(
        state=state,
        observed_at=observed_at,
        reason="execution switch state declared",
    )


def test_approved_intent_with_enabled_switch_is_authorized() -> None:
    result = authorize_order_intent(
        _intent(),
        _authorization(),
        _switch(),
        authorized_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Success)
    assert result.value.intent.intent_id == _INTENT_ID
    assert result.value.authorization.decision is PreTradeDecision.APPROVED
    assert result.value.switch.allows_execution is True


def test_blocked_pretrade_decision_fails_closed() -> None:
    result = authorize_order_intent(
        _intent(),
        _authorization(decision=PreTradeDecision.BLOCKED),
        _switch(),
        authorized_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, PreTradeSafetyBlockedError)


def test_expired_authorization_fails_closed() -> None:
    result = authorize_order_intent(
        _intent(),
        _authorization(expires_at=_NOW + timedelta(seconds=2)),
        _switch(observed_at=_NOW + timedelta(seconds=1)),
        authorized_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, PreTradeSafetyBlockedError)


def test_intent_identity_mismatch_fails_closed() -> None:
    other_id = OrderIntentId(UUID("af000000-0000-0000-0000-000000000009"))
    result = authorize_order_intent(
        _intent(),
        _authorization(intent_id=other_id),
        _switch(),
        authorized_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, PreTradeSafetyBlockedError)


def test_blocked_execution_switch_fails_closed() -> None:
    result = authorize_order_intent(
        _intent(),
        _authorization(),
        _switch(ExecutionSwitchState.BLOCKED),
        authorized_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, PreTradeSafetyBlockedError)


def test_switch_snapshot_cannot_postdate_authorization_instant() -> None:
    result = authorize_order_intent(
        _intent(),
        _authorization(),
        _switch(observed_at=_NOW + timedelta(seconds=4)),
        authorized_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, PreTradeSafetyBlockedError)


def test_authorized_at_cannot_predate_policy_evaluation() -> None:
    result = authorize_order_intent(
        _intent(),
        _authorization(evaluated_at=_NOW + timedelta(seconds=4)),
        _switch(observed_at=_NOW + timedelta(seconds=1)),
        authorized_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, PreTradeSafetyBlockedError)


def test_direct_authorized_intent_construction_cannot_bypass_blocked_decision() -> None:
    with pytest.raises(PreTradeSafetyValidationError):
        AuthorizedOrderIntent(
            intent=_intent(),
            authorization=_authorization(decision=PreTradeDecision.BLOCKED),
            switch=_switch(),
            authorized_at=_NOW + timedelta(seconds=3),
        )


def test_direct_authorized_intent_construction_rejects_identity_mismatch() -> None:
    other_id = OrderIntentId(UUID("af000000-0000-0000-0000-000000000009"))
    with pytest.raises(PreTradeSafetyValidationError):
        AuthorizedOrderIntent(
            intent=_intent(),
            authorization=_authorization(intent_id=other_id),
            switch=_switch(),
            authorized_at=_NOW + timedelta(seconds=3),
        )


def test_direct_authorized_intent_construction_rejects_expired_authorization() -> None:
    with pytest.raises(PreTradeSafetyValidationError):
        AuthorizedOrderIntent(
            intent=_intent(),
            authorization=_authorization(expires_at=_NOW + timedelta(seconds=2)),
            switch=_switch(observed_at=_NOW + timedelta(seconds=1)),
            authorized_at=_NOW + timedelta(seconds=3),
        )


def test_safety_reason_rejects_sensitive_material() -> None:
    with pytest.raises(PreTradeSafetyValidationError):
        PreTradeAuthorization(
            authorization_id=PreTradeAuthorizationId(
                UUID("af000000-0000-0000-0000-000000000005")
            ),
            policy_id=PreTradePolicyId("risk.pretrade.v1"),
            intent_id=_INTENT_ID,
            decision=PreTradeDecision.BLOCKED,
            evaluated_at=_NOW + timedelta(seconds=1),
            expires_at=_NOW + timedelta(seconds=2),
            reason="Bearer must-not-appear",
        )
