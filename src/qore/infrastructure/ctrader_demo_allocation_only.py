"""Allocation-only cTrader DEMO authority for unrestricted Trader/CIBO execution.

This account path is completely separate from FundedNext sovereign Risk. Risk assigns
virtual capital to each Trader lineage for attribution only; Trader and CIBO own
setup selection, risk fraction, sizing and lifecycle. The allocator never reduces
or rejects a valid CIBO size because of another Trader or assigned-capital usage.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from types import MappingProxyType
from uuid import NAMESPACE_URL, uuid5

from qore.domain.events import CorrelationId
from qore.infrastructure.account_wide_risk import CiboRiskRequest, TraderLineage
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
    ExecutionSwitchState,
    PreTradeAuthorization,
    PreTradeAuthorizationId,
    PreTradeDecision,
    PreTradePolicyId,
)
from qore.kernel.errors import InfrastructureError

_POLICY_ID = PreTradePolicyId("ctrader.demo.allocation-only.v1")
_ACTIVE_TRADERS = (
    TraderLineage.VT08_FOREX,
    TraderLineage.R34_XAUUSD,
    TraderLineage.R38_EURUSD,
    TraderLineage.R43_GBPUSD,
    TraderLineage.R38_GBPJPY,
    TraderLineage.R42_AUDJPY,
    TraderLineage.VT31_NAS100,
)


class CTraderDemoAllocationError(InfrastructureError):
    __slots__ = ()


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise CTraderDemoAllocationError(f"{name} must be a positive finite Decimal")


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CTraderDemoAllocationError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class DemoCapitalAllocationBook:
    total_capital: Decimal
    allocations: Mapping[TraderLineage, Decimal]

    def __post_init__(self) -> None:
        _positive(self.total_capital, "total_capital")
        if not isinstance(self.allocations, Mapping) or not self.allocations:
            raise CTraderDemoAllocationError("allocations must be a non-empty mapping")
        canonical: dict[TraderLineage, Decimal] = {}
        for trader, capital in self.allocations.items():
            if type(trader) is not TraderLineage:
                raise CTraderDemoAllocationError("allocation key must be TraderLineage")
            _positive(capital, f"{trader.value} allocation")
            canonical[trader] = capital
        if sum(canonical.values(), Decimal("0")) > self.total_capital:
            raise CTraderDemoAllocationError(
                "virtual Trader allocations cannot exceed DEMO capital"
            )
        object.__setattr__(
            self,
            "allocations",
            MappingProxyType(dict(sorted(canonical.items(), key=lambda item: item[0].value))),
        )

    def capital_for(self, trader: TraderLineage) -> Decimal:
        try:
            return self.allocations[trader]
        except KeyError as error:
            raise CTraderDemoAllocationError(
                f"no DEMO capital allocation for {trader.value}"
            ) from error


def equal_active_trader_allocations(total_capital: Decimal) -> DemoCapitalAllocationBook:
    _positive(total_capital, "total_capital")
    slice_capital = total_capital / Decimal(len(_ACTIVE_TRADERS))
    return DemoCapitalAllocationBook(
        total_capital=total_capital,
        allocations={trader: slice_capital for trader in _ACTIVE_TRADERS},
    )


@dataclass(frozen=True, slots=True)
class DemoAllocationAuthorization:
    request: CiboRiskRequest
    assigned_capital: Decimal
    authorized_volume: Decimal
    policy_id: str
    authorization_fingerprint: str
    authorized_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.request, CiboRiskRequest):
            raise CTraderDemoAllocationError("authorization request must be CiboRiskRequest")
        _positive(self.assigned_capital, "assigned_capital")
        if self.authorized_volume != self.request.requested_volume:
            raise CTraderDemoAllocationError(
                "allocation-only authority must preserve CIBO requested volume"
            )
        _aware(self.authorized_at, "authorized_at")
        if len(self.authorization_fingerprint) != 64:
            raise CTraderDemoAllocationError("authorization fingerprint must be SHA-256")


def authorize_allocation_only(
    request: CiboRiskRequest,
    *,
    book: DemoCapitalAllocationBook,
    now: datetime,
) -> DemoAllocationAuthorization:
    if not isinstance(request, CiboRiskRequest):
        raise CTraderDemoAllocationError("CIBO request is required")
    _aware(now, "now")
    if now > request.expires_at:
        raise CTraderDemoAllocationError("CIBO request expired")
    capital = book.capital_for(request.trader_id)
    material = "|".join(
        (
            "ctrader-demo-allocation-only-v1",
            request.trader_id.value,
            request.request_id,
            request.signal_fingerprint,
            format(capital, "f"),
            format(request.requested_volume, "f"),
            now.isoformat(),
        )
    )
    return DemoAllocationAuthorization(
        request=request,
        assigned_capital=capital,
        authorized_volume=request.requested_volume,
        policy_id=_POLICY_ID.value,
        authorization_fingerprint=sha256(material.encode("utf-8")).hexdigest(),
        authorized_at=now,
    )


@dataclass(frozen=True, slots=True)
class CTraderDemoBrokerContract:
    qore_symbol: str
    provider_symbol: str
    source_contract_size_units: Decimal
    ctrader_lot_size_units: Decimal

    def __post_init__(self) -> None:
        if not self.qore_symbol or not self.provider_symbol:
            raise CTraderDemoAllocationError("broker contract symbol identity is required")
        _positive(self.source_contract_size_units, "source_contract_size_units")
        _positive(self.ctrader_lot_size_units, "ctrader_lot_size_units")

    @property
    def source_to_ctrader_lot_ratio(self) -> Decimal:
        """How many cTrader lots reproduce one source-broker lot of exposure."""
        return self.source_contract_size_units / self.ctrader_lot_size_units


def build_allocation_only_submission(
    authorization: DemoAllocationAuthorization,
    *,
    contract: CTraderDemoBrokerContract,
    submitted_at: datetime,
) -> ExecutionSubmission:
    if not isinstance(authorization, DemoAllocationAuthorization):
        raise CTraderDemoAllocationError("allocation authorization is required")
    _aware(submitted_at, "submitted_at")
    request = authorization.request
    if submitted_at > request.expires_at:
        raise CTraderDemoAllocationError("CIBO request expired before cTrader submission")
    if contract.qore_symbol != request.qore_symbol:
        raise CTraderDemoAllocationError("cTrader broker contract symbol mismatch")

    quantity = authorization.authorized_volume * contract.source_contract_size_units
    _positive(quantity, "cTrader quantity units")
    side = OrderSide.BUY if request.side == "long" else OrderSide.SELL
    order_type = OrderType.MARKET if request.entry_type == "market" else OrderType.LIMIT
    identity = f"{request.trader_id.value}:{request.signal_fingerprint}:{request.request_id}"
    intent_uuid = uuid5(NAMESPACE_URL, "intent:" + identity)
    idempotency_uuid = uuid5(NAMESPACE_URL, "idempotency:" + identity)
    request_uuid = uuid5(NAMESPACE_URL, "request:" + identity)
    receipt_uuid = uuid5(NAMESPACE_URL, "receipt:" + identity)
    authorization_uuid = uuid5(NAMESPACE_URL, "authorization:" + identity)
    metadata = ExternalRequestMetadata(
        correlation_id=CorrelationId(uuid5(NAMESPACE_URL, "correlation:" + identity)),
        attributes={
            "ctrader_reference_entry": format(request.intended_entry, "f"),
            "ctrader_order_expires_at": request.expires_at.isoformat(),
            "demo_policy": "allocation-only",
            "trader_id": request.trader_id.value,
        },
    )
    intent = OrderIntent(
        intent_id=OrderIntentId(intent_uuid),
        idempotency_key=ExecutionIdempotencyKey(idempotency_uuid),
        instrument=ExecutionInstrument(request.qore_symbol),
        side=side,
        order_type=order_type,
        quantity=OrderQuantity(quantity),
        created_at=request.requested_at,
        metadata=metadata,
        limit_price=(OrderPrice(request.intended_entry) if order_type is OrderType.LIMIT else None),
        stop_loss=OrderPrice(request.stop_loss),
        take_profit=OrderPrice(request.take_profit),
    )
    evaluated_at = max(authorization.authorized_at, request.requested_at)
    expires_at = min(request.expires_at, evaluated_at + timedelta(seconds=30))
    pretrade = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(authorization_uuid),
        policy_id=_POLICY_ID,
        intent_id=intent.intent_id,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=evaluated_at,
        expires_at=expires_at,
        reason="DEMO capital assigned; CIBO size preserved without shared-risk reduction",
    )
    technical_switch = ExecutionSafetySwitchSnapshot(
        state=ExecutionSwitchState.ENABLED,
        observed_at=evaluated_at,
        reason="cTrader DEMO allocation-only technical execution enabled",
    )
    authorized_intent = AuthorizedOrderIntent(
        intent=intent,
        authorization=pretrade,
        switch=technical_switch,
        authorized_at=evaluated_at,
    )
    return ExecutionSubmission(
        request_id=ExecutionRequestId(request_uuid),
        receipt_id=ExecutionReceiptId(receipt_uuid),
        authorized_intent=authorized_intent,
        submitted_at=submitted_at,
    )


def allocation_fence_values(
    authorization: DemoAllocationAuthorization,
) -> tuple[str, str, str]:
    """Return non-secret provenance accepted by the durable mutation fence."""
    identity = (
        f"allocation:{authorization.request.trader_id.value}:{authorization.request.request_id}"
    )
    return (
        identity,
        authorization.authorization_fingerprint,
        identity,
    )
