"""Bridge account-wide RiskAuthorization into QORE canonical execution contracts.

The bridge creates no new trading authority.  It converts an already-approved
shared-account Risk decision into the provider-neutral OrderIntent /
PreTradeAuthorization / ExecutionSubmission chain used by existing QORE safety,
idempotency, environment guards and execution reconciliation.
"""

from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.domain.events import CorrelationId
from qore.infrastructure.account_wide_risk import RiskAuthorization, RiskDecision
from qore.infrastructure.execution_boundary import (
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionSubmission,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderPrice,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.pretrade_safety import (
    AuthorizedOrderIntent,
    ExecutionSafetySwitchSnapshot,
    PreTradeAuthorization,
    PreTradeAuthorizationId,
    PreTradeDecision,
    PreTradePolicyId,
)
from qore.kernel.errors import InfrastructureError


class FundedNextExecutionBridgeError(InfrastructureError):
    """Risk authorization cannot be materialized into canonical execution."""

    __slots__ = ()


_PRETRADE_POLICY = PreTradePolicyId("qore.fundednext.account-wide-risk")


def _stable_uuid(fingerprint: str, purpose: str) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"qore:fundednext-stellar-instant:{fingerprint}:{purpose}",
    )


def build_fundednext_execution_submission(
    authorization: RiskAuthorization,
    *,
    switch: ExecutionSafetySwitchSnapshot,
    authorized_at: datetime,
    submitted_at: datetime,
) -> ExecutionSubmission:
    """Build one deterministic canonical submission from shared Risk evidence."""

    if not isinstance(authorization, RiskAuthorization):
        raise FundedNextExecutionBridgeError(
            "authorization must be account-wide RiskAuthorization"
        )
    if authorization.decision not in {RiskDecision.ALLOW, RiskDecision.REDUCE}:
        raise FundedNextExecutionBridgeError(
            "rejected RiskAuthorization cannot become execution"
        )
    if not isinstance(switch, ExecutionSafetySwitchSnapshot):
        raise FundedNextExecutionBridgeError(
            "canonical ExecutionSafetySwitchSnapshot is required"
        )
    _aware(authorized_at, "authorized_at")
    _aware(submitted_at, "submitted_at")
    if authorized_at < authorization.issued_at:
        raise FundedNextExecutionBridgeError(
            "canonical authorization cannot predate account-wide Risk"
        )
    if submitted_at < authorized_at:
        raise FundedNextExecutionBridgeError("submission cannot predate authorization")
    if authorized_at > authorization.expires_at or submitted_at > authorization.expires_at:
        raise FundedNextExecutionBridgeError("RiskAuthorization is expired")

    fingerprint = authorization.authorization_fingerprint
    if len(fingerprint) != 64:
        raise FundedNextExecutionBridgeError(
            "RiskAuthorization fingerprint must be raw SHA-256 hex"
        )
    order_type = _order_type(authorization.entry_type)
    side = _order_side(authorization.side)
    intent_id = OrderIntentId(_stable_uuid(fingerprint, "intent"))
    metadata = ExternalRequestMetadata(
        correlation_id=CorrelationId(_stable_uuid(fingerprint, "correlation")),
        attributes={
            "account-binding": authorization.account_binding_id,
            "qore-symbol": authorization.qore_symbol,
            "risk-authorization-fingerprint": fingerprint,
            "risk-authorization-id": authorization.authorization_id,
            "risk-reservation-id": authorization.authorization_id,
            "risk-monetary-stop-loss": str(authorization.monetary_stop_loss),
            "risk-intended-entry": str(authorization.intended_entry),
            "risk-authorized-volume": str(authorization.authorized_volume),
            "signal-fingerprint": authorization.signal_fingerprint,
            "trader-id": authorization.trader_id.value,
        },
    )
    intent = OrderIntent(
        intent_id=intent_id,
        idempotency_key=ExecutionIdempotencyKey(
            _stable_uuid(fingerprint, "idempotency")
        ),
        instrument=ExecutionInstrument(authorization.qore_symbol),
        side=side,
        order_type=order_type,
        quantity=OrderQuantity(authorization.authorized_volume),
        created_at=authorization.issued_at,
        metadata=metadata,
        limit_price=(
            OrderPrice(authorization.intended_entry)
            if order_type is OrderType.LIMIT
            else None
        ),
        stop_loss=OrderPrice(authorization.stop_loss),
        take_profit=OrderPrice(authorization.take_profit),
    )
    pretrade = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(
            _stable_uuid(fingerprint, "pretrade-authorization")
        ),
        policy_id=_PRETRADE_POLICY,
        intent_id=intent_id,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=authorization.issued_at,
        expires_at=authorization.expires_at,
        reason="account wide risk authorization approved",
    )
    authorized = AuthorizedOrderIntent(
        intent=intent,
        authorization=pretrade,
        switch=switch,
        authorized_at=authorized_at,
    )
    return ExecutionSubmission(
        request_id=ExecutionRequestId(_stable_uuid(fingerprint, "execution-request")),
        receipt_id=ExecutionReceiptId(_stable_uuid(fingerprint, "execution-receipt")),
        authorized_intent=authorized,
        submitted_at=submitted_at,
    )


def extract_risk_provenance(
    submission: ExecutionSubmission,
) -> tuple[str, str, str]:
    """Return durable Risk binding from canonical immutable metadata."""

    if not isinstance(submission, ExecutionSubmission):
        raise FundedNextExecutionBridgeError(
            "risk provenance requires canonical ExecutionSubmission"
        )
    attributes = submission.authorized_intent.intent.metadata.attributes
    values = tuple(
        attributes.get(key)
        for key in (
            "risk-authorization-id",
            "risk-authorization-fingerprint",
            "risk-reservation-id",
        )
    )
    if any(not isinstance(value, str) or not value for value in values):
        raise FundedNextExecutionBridgeError(
            "canonical submission is missing Risk provenance"
        )
    authorization_id, fingerprint, reservation_id = values
    assert isinstance(authorization_id, str)
    assert isinstance(fingerprint, str)
    assert isinstance(reservation_id, str)
    if len(fingerprint) != 64:
        raise FundedNextExecutionBridgeError(
            "Risk provenance fingerprint must be raw SHA-256 hex"
        )
    return authorization_id, fingerprint, reservation_id


def _order_side(value: str) -> OrderSide:
    if value == "long":
        return OrderSide.BUY
    if value == "short":
        return OrderSide.SELL
    raise FundedNextExecutionBridgeError("unsupported RiskAuthorization side")


def _order_type(value: str) -> OrderType:
    normalized = value.lower().strip()
    if normalized == "market":
        return OrderType.MARKET
    if normalized == "limit":
        return OrderType.LIMIT
    raise FundedNextExecutionBridgeError(
        "FundedNext execution supports only canonical market or limit entry types"
    )


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise FundedNextExecutionBridgeError(f"{name} must be timezone-aware")
