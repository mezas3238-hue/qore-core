"""Prepare broker-native cTrader MARKET SL/TP *distances*, without sending.

Spotware ProtoOANewOrderReq supports relativeStopLoss and relativeTakeProfit
in 1/100000 of one quote price unit, whereas absolute stopLoss/takeProfit
cannot be used for MARKET. This module is a typed codec proposal ONLY.
QORE's current cTrader gateway/transport DOES NOT wire these fields yet.
No order, position, authorization, or execution side effects are possible.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from qore.infrastructure.traders.crt_r4a_protected_candidate import (
    CRTBrokerContract,
    CRTCandidateError,
    CRTProtectedProposal,
)

_NATIVE_SCALE = Decimal("100000")
_MAX_NATIVE = (1 << 63) - 1


@dataclass(frozen=True, slots=True)
class CRTNativeBracketDistances:
    """Auditable protective instructions. Not a cTrader wire/order request."""

    symbol_id: int
    direction: int
    reference_entry: Decimal
    relative_stop_loss: int
    relative_take_profit: int
    idempotency_key: UUID
    provider_ack_required: bool = True
    wire_submission_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.symbol_id) is not int
            or self.symbol_id <= 0
            or self.direction not in (1, -1)
            or type(self.relative_stop_loss) is not int
            or type(self.relative_take_profit) is not int
            or not (0 < self.relative_stop_loss <= _MAX_NATIVE)
            or not (0 < self.relative_take_profit <= _MAX_NATIVE)
            or not self.provider_ack_required
            or self.wire_submission_authorized
        ):
            raise CRTCandidateError("invalid or unauthorized native bracket intent")


def native_protection_for_crt_market(
    proposal: CRTProtectedProposal,
    contract: CRTBrokerContract,
) -> CRTNativeBracketDistances:
    """Translate a hypothetical STOP/TP to MARKET-relative 1e-5 distances.

    A future protected gateway MUST verify the broker response actually
    attached both SL/TP to the filled position; it must never interpret this
    object as proof of protection. Slippage changes the actual absolute
    levels because native distances are relative to the *actual fill*.
    """
    if not isinstance(proposal, CRTProtectedProposal) or not isinstance(
        contract, CRTBrokerContract
    ):
        raise CRTCandidateError("typed protected CRT proposal and contract required")
    if (
        proposal.symbol != contract.symbol
        or proposal.symbol_id != contract.symbol_id
        or not proposal.native_bracket_required
        or proposal.can_submit
    ):
        raise CRTCandidateError("source and broker protection binding mismatch")
    if (
        not isinstance(proposal.entry_reference, Decimal)
        or not proposal.entry_reference.is_finite()
        or proposal.direction not in (1, -1)
    ):
        raise CRTCandidateError("no reliable entry/side evidence")
    if proposal.direction == 1:
        stop_distance = proposal.entry_reference - proposal.stop_loss
        target_distance = proposal.take_profit - proposal.entry_reference
    else:
        stop_distance = proposal.stop_loss - proposal.entry_reference
        target_distance = proposal.entry_reference - proposal.take_profit
    if stop_distance <= 0 or target_distance <= 0:
        raise CRTCandidateError("stop or profit crosses the intended entry")
    if (
        stop_distance < contract.price_tick
        or target_distance < contract.price_tick
    ):
        raise CRTCandidateError("bracket distance below broker price tick")
    native_stop = stop_distance * _NATIVE_SCALE
    native_target = target_distance * _NATIVE_SCALE
    if (
        native_stop != native_stop.to_integral_value()
        or native_target != native_target.to_integral_value()
    ):
        raise CRTCandidateError("bracket loss of precision in native cTrader 1e-5 wire units")
    if native_stop > _MAX_NATIVE or native_target > _MAX_NATIVE:
        raise CRTCandidateError("bracket exceeds cTrader int64 range")
    return CRTNativeBracketDistances(
        symbol_id=proposal.symbol_id,
        direction=proposal.direction,
        reference_entry=proposal.entry_reference,
        relative_stop_loss=int(native_stop),
        relative_take_profit=int(native_target),
        idempotency_key=proposal.idempotency_key,
    )
