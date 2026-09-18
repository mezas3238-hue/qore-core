"""Sovereign account-wide Risk for the two-Trader FundedNext pilot.

Both VT08_FOREX and VT08_INDEX consume one atomic loss/margin budget.  CIBO may
request exposure, but only this engine issues RiskAuthorization.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum
from hashlib import sha256
from threading import RLock

from qore.infrastructure.fundednext_stellar_instant import StellarInstantRiskBudget
from qore.kernel.errors import InfrastructureError


class AccountWideRiskError(InfrastructureError):
    """Account-wide risk state or transition violates a fail-closed invariant."""

    __slots__ = ()


class TraderLineage(StrEnum):
    VT08_FOREX = "VT08_FOREX"
    VT08_INDEX = "VT08_INDEX"
    R34_XAUUSD = "R34_XAUUSD"
    R38_EURUSD = "R38_EURUSD"
    R43_GBPUSD = "R43_GBPUSD"
    R43_GBPUSD = "R43_GBPUSD"


class RiskDecision(StrEnum):
    ALLOW = "ALLOW"
    REDUCE = "REDUCE"
    REJECT = "REJECT"


class ReservationState(StrEnum):
    RESERVED = "reserved"
    PARTIALLY_FILLED = "partially-filled"
    FILLED_UNRECONCILED = "filled-unreconciled"
    RELEASED = "released"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class AccountRiskSnapshot:
    """External account state before adding QORE in-flight reservations."""

    account_binding_id: str
    equity: Decimal
    margin_used: Decimal
    free_margin: Decimal
    open_stop_worst_case_loss: Decimal
    open_floating_loss: Decimal
    pending_broker_worst_case_loss: Decimal
    qore_authorizable_headroom: Decimal
    provider_budget: StellarInstantRiskBudget
    reconciled_at: datetime

    def __post_init__(self) -> None:
        if not self.account_binding_id:
            raise AccountWideRiskError("account_binding_id must be opaque and non-empty")
        for name, decimal_value in (
            ("equity", self.equity),
            ("margin_used", self.margin_used),
            ("free_margin", self.free_margin),
            ("open_stop_worst_case_loss", self.open_stop_worst_case_loss),
            ("open_floating_loss", self.open_floating_loss),
            ("pending_broker_worst_case_loss", self.pending_broker_worst_case_loss),
            ("qore_authorizable_headroom", self.qore_authorizable_headroom),
        ):
            _nonnegative(decimal_value, name)
        _aware(self.reconciled_at, "reconciled_at")
        if not isinstance(self.provider_budget, StellarInstantRiskBudget):
            raise AccountWideRiskError("provider_budget must be StellarInstantRiskBudget")
        if self.qore_authorizable_headroom > self.provider_budget.provider_headroom:
            raise AccountWideRiskError("QORE headroom cannot exceed provider headroom")


@dataclass(frozen=True, slots=True)
class CiboRiskRequest:
    request_id: str
    trader_id: TraderLineage
    signal_fingerprint: str
    qore_symbol: str
    provider_symbol: str
    side: str
    entry_type: str
    intended_entry: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    requested_volume: Decimal
    volume_step: Decimal
    minimum_volume: Decimal
    stop_loss_per_volume: Decimal
    margin_per_volume: Decimal
    requested_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        for name, text_value in (
            ("request_id", self.request_id),
            ("signal_fingerprint", self.signal_fingerprint),
            ("qore_symbol", self.qore_symbol),
            ("provider_symbol", self.provider_symbol),
            ("side", self.side),
            ("entry_type", self.entry_type),
        ):
            if not text_value:
                raise AccountWideRiskError(f"{name} must be non-empty")
        if type(self.trader_id) is not TraderLineage:
            raise AccountWideRiskError("trader_id must be a frozen pilot lineage")
        for name, decimal_value in (
            ("intended_entry", self.intended_entry),
            ("stop_loss", self.stop_loss),
            ("take_profit", self.take_profit),
            ("requested_volume", self.requested_volume),
            ("volume_step", self.volume_step),
            ("minimum_volume", self.minimum_volume),
            ("stop_loss_per_volume", self.stop_loss_per_volume),
            ("margin_per_volume", self.margin_per_volume),
        ):
            _positive(decimal_value, name)
        _aware(self.requested_at, "requested_at")
        _aware(self.expires_at, "expires_at")
        if self.expires_at <= self.requested_at:
            raise AccountWideRiskError("expires_at must follow requested_at")
        if self.minimum_volume < self.volume_step:
            raise AccountWideRiskError("minimum_volume cannot be below volume_step")
        if self.side not in {"long", "short"}:
            raise AccountWideRiskError("side must be long or short")
        if self.side == "long" and not self.stop_loss < self.intended_entry < self.take_profit:
            raise AccountWideRiskError("long geometry must be stop < entry < target")
        if self.side == "short" and not self.take_profit < self.intended_entry < self.stop_loss:
            raise AccountWideRiskError("short geometry must be target < entry < stop")

    @property
    def requested_stop_risk(self) -> Decimal:
        return self.requested_volume * self.stop_loss_per_volume

    @property
    def requested_margin(self) -> Decimal:
        return self.requested_volume * self.margin_per_volume


@dataclass(frozen=True, slots=True)
class RiskAuthorization:
    authorization_id: str
    account_binding_id: str
    trader_id: TraderLineage
    request_id: str
    signal_fingerprint: str
    qore_symbol: str
    provider_symbol: str
    side: str
    entry_type: str
    intended_entry: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    requested_volume: Decimal
    authorized_volume: Decimal
    monetary_stop_loss: Decimal
    aggregate_pre_order_worst_case: Decimal
    aggregate_post_order_worst_case: Decimal
    provider_headroom: Decimal
    internal_qore_headroom: Decimal
    margin_reserved: Decimal
    decision: RiskDecision
    reason: str
    issued_at: datetime
    expires_at: datetime
    authorization_fingerprint: str

    def __post_init__(self) -> None:
        if type(self.decision) is not RiskDecision:
            raise AccountWideRiskError("decision must be canonical")
        if self.decision is RiskDecision.REJECT:
            if self.authorized_volume != 0 or self.monetary_stop_loss != 0:
                raise AccountWideRiskError("rejected authorization cannot reserve exposure")
        if self.decision in {RiskDecision.ALLOW, RiskDecision.REDUCE}:
            if self.authorized_volume <= 0 or self.monetary_stop_loss <= 0:
                raise AccountWideRiskError("approved authorization must reserve exposure")
        if self.decision is RiskDecision.ALLOW and self.authorized_volume != self.requested_volume:
            raise AccountWideRiskError("ALLOW must preserve requested volume")
        if self.decision is RiskDecision.REDUCE and self.authorized_volume >= self.requested_volume:
            raise AccountWideRiskError("REDUCE must lower requested volume")
        if len(self.authorization_fingerprint) != 64:
            raise AccountWideRiskError("authorization_fingerprint must be SHA-256")
        _aware(self.issued_at, "issued_at")
        _aware(self.expires_at, "expires_at")


@dataclass(frozen=True, slots=True)
class RiskReservation:
    authorization: RiskAuthorization
    pending_stop_risk: Decimal
    pending_margin: Decimal
    filled_unreconciled_stop_risk: Decimal
    state: ReservationState

    @property
    def total_unreconciled_stop_risk(self) -> Decimal:
        return self.pending_stop_risk + self.filled_unreconciled_stop_risk


class AccountWideRiskEngine:
    """Serialize Forex and Index requests against one shared account budget."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._reservations: dict[str, RiskReservation] = {}
        self._signal_to_authorization: dict[str, str] = {}

    def authorize(
        self,
        request: CiboRiskRequest,
        snapshot: AccountRiskSnapshot,
        *,
        now: datetime,
    ) -> RiskAuthorization:
        _aware(now, "now")
        if not isinstance(request, CiboRiskRequest):
            raise AccountWideRiskError("request must be CiboRiskRequest")
        if not isinstance(snapshot, AccountRiskSnapshot):
            raise AccountWideRiskError("snapshot must be AccountRiskSnapshot")
        with self._lock:
            self._expire_locked(now)
            previous_id = self._signal_to_authorization.get(request.signal_fingerprint)
            if previous_id is not None:
                previous = self._reservations.get(previous_id)
                if previous is not None and previous.state not in {
                    ReservationState.RELEASED,
                    ReservationState.EXPIRED,
                }:
                    return previous.authorization
            authorization = self._evaluate_locked(request, snapshot, now)
            if authorization.decision is RiskDecision.REJECT:
                return authorization
            reservation = RiskReservation(
                authorization=authorization,
                pending_stop_risk=authorization.monetary_stop_loss,
                pending_margin=authorization.margin_reserved,
                filled_unreconciled_stop_risk=Decimal(0),
                state=ReservationState.RESERVED,
            )
            self._reservations[authorization.authorization_id] = reservation
            self._signal_to_authorization[request.signal_fingerprint] = (
                authorization.authorization_id
            )
            return authorization

    def cancel(self, authorization_id: str) -> None:
        with self._lock:
            item = self._require_active(authorization_id)
            self._reservations[authorization_id] = replace(
                item,
                pending_stop_risk=Decimal(0),
                pending_margin=Decimal(0),
                filled_unreconciled_stop_risk=Decimal(0),
                state=ReservationState.RELEASED,
            )

    def record_partial_fill(
        self,
        authorization_id: str,
        *,
        filled_volume: Decimal,
    ) -> None:
        _positive(filled_volume, "filled_volume")
        with self._lock:
            item = self._require_active(authorization_id)
            auth = item.authorization
            if filled_volume >= auth.authorized_volume:
                raise AccountWideRiskError("partial fill must be below authorized volume")
            fill_fraction = filled_volume / auth.authorized_volume
            filled_risk = auth.monetary_stop_loss * fill_fraction
            filled_margin = auth.margin_reserved * fill_fraction
            self._reservations[authorization_id] = replace(
                item,
                pending_stop_risk=auth.monetary_stop_loss - filled_risk,
                pending_margin=auth.margin_reserved - filled_margin,
                filled_unreconciled_stop_risk=filled_risk,
                state=ReservationState.PARTIALLY_FILLED,
            )

    def record_full_fill(self, authorization_id: str) -> None:
        with self._lock:
            item = self._require_active(authorization_id)
            self._reservations[authorization_id] = replace(
                item,
                pending_stop_risk=Decimal(0),
                pending_margin=Decimal(0),
                filled_unreconciled_stop_risk=item.total_unreconciled_stop_risk,
                state=ReservationState.FILLED_UNRECONCILED,
            )

    def reconcile_fill(self, authorization_id: str) -> None:
        """Release internal fill shadow only after broker open risk is in snapshot state."""
        with self._lock:
            item = self._require_active(authorization_id)
            if item.state is not ReservationState.FILLED_UNRECONCILED:
                raise AccountWideRiskError("fill can reconcile only from filled-unreconciled")
            self._reservations[authorization_id] = replace(
                item,
                filled_unreconciled_stop_risk=Decimal(0),
                state=ReservationState.RELEASED,
            )

    def expire(self, *, now: datetime) -> None:
        _aware(now, "now")
        with self._lock:
            self._expire_locked(now)

    def active_reserved_stop_risk(self) -> Decimal:
        with self._lock:
            return sum(
                (
                    item.total_unreconciled_stop_risk
                    for item in self._reservations.values()
                    if item.state not in {ReservationState.RELEASED, ReservationState.EXPIRED}
                ),
                Decimal(0),
            )

    def _evaluate_locked(
        self,
        request: CiboRiskRequest,
        snapshot: AccountRiskSnapshot,
        now: datetime,
    ) -> RiskAuthorization:
        pre = (
            snapshot.open_stop_worst_case_loss
            + snapshot.pending_broker_worst_case_loss
            + self._active_risk_locked()
        )
        provider = snapshot.provider_budget
        if now > request.expires_at:
            return self._reject(request, snapshot, now, pre, "request-expired")
        if provider.hard_breach:
            return self._reject(request, snapshot, now, pre, "provider-hard-breach")
        if snapshot.equity <= provider.active_mll:
            return self._reject(request, snapshot, now, pre, "no-provider-equity-headroom")

        risk_capacity = min(
            max(Decimal(0), provider.provider_headroom - pre),
            max(Decimal(0), snapshot.qore_authorizable_headroom - pre),
            max(Decimal(0), provider.max_risk_at_any_time - pre),
        )
        margin_reserved = self._active_margin_locked()
        margin_capacity = max(Decimal(0), snapshot.free_margin - margin_reserved)
        by_risk = risk_capacity / request.stop_loss_per_volume
        by_margin = margin_capacity / request.margin_per_volume
        raw_volume = min(request.requested_volume, by_risk, by_margin)
        volume = _floor_to_step(raw_volume, request.volume_step)
        if volume < request.minimum_volume:
            reason = "insufficient-shared-risk-or-margin-headroom"
            return self._reject(request, snapshot, now, pre, reason)
        volume = min(volume, request.requested_volume)
        stop_risk = volume * request.stop_loss_per_volume
        margin = volume * request.margin_per_volume
        decision = (
            RiskDecision.ALLOW
            if volume == request.requested_volume
            else RiskDecision.REDUCE
        )
        post = pre + stop_risk
        if post > provider.max_risk_at_any_time:
            return self._reject(request, snapshot, now, pre, "provider-max-risk-cap")
        if post > snapshot.qore_authorizable_headroom:
            return self._reject(request, snapshot, now, pre, "qore-headroom-exceeded")
        if post > provider.provider_headroom:
            return self._reject(request, snapshot, now, pre, "provider-headroom-exceeded")
        return _authorization(
            request=request,
            snapshot=snapshot,
            issued_at=now,
            authorized_volume=volume,
            monetary_stop_loss=stop_risk,
            aggregate_pre=pre,
            aggregate_post=post,
            margin_reserved=margin,
            decision=decision,
            reason=(
                "request-fits-shared-account-budget"
                if decision is RiskDecision.ALLOW
                else "request-reduced-to-shared-account-budget"
            ),
        )

    def _reject(
        self,
        request: CiboRiskRequest,
        snapshot: AccountRiskSnapshot,
        now: datetime,
        pre: Decimal,
        reason: str,
    ) -> RiskAuthorization:
        return _authorization(
            request=request,
            snapshot=snapshot,
            issued_at=now,
            authorized_volume=Decimal(0),
            monetary_stop_loss=Decimal(0),
            aggregate_pre=pre,
            aggregate_post=pre,
            margin_reserved=Decimal(0),
            decision=RiskDecision.REJECT,
            reason=reason,
        )

    def _active_risk_locked(self) -> Decimal:
        return sum(
            (
                item.total_unreconciled_stop_risk
                for item in self._reservations.values()
                if item.state not in {ReservationState.RELEASED, ReservationState.EXPIRED}
            ),
            Decimal(0),
        )

    def _active_margin_locked(self) -> Decimal:
        return sum(
            (
                item.pending_margin
                for item in self._reservations.values()
                if item.state not in {ReservationState.RELEASED, ReservationState.EXPIRED}
            ),
            Decimal(0),
        )

    def _expire_locked(self, now: datetime) -> None:
        for key, item in tuple(self._reservations.items()):
            if (
                item.state is ReservationState.RESERVED
                and now > item.authorization.expires_at
            ):
                self._reservations[key] = replace(
                    item,
                    pending_stop_risk=Decimal(0),
                    pending_margin=Decimal(0),
                    state=ReservationState.EXPIRED,
                )

    def _require_active(self, authorization_id: str) -> RiskReservation:
        item = self._reservations.get(authorization_id)
        if item is None or item.state in {ReservationState.RELEASED, ReservationState.EXPIRED}:
            raise AccountWideRiskError("authorization reservation is not active")
        return item


def _authorization(
    *,
    request: CiboRiskRequest,
    snapshot: AccountRiskSnapshot,
    issued_at: datetime,
    authorized_volume: Decimal,
    monetary_stop_loss: Decimal,
    aggregate_pre: Decimal,
    aggregate_post: Decimal,
    margin_reserved: Decimal,
    decision: RiskDecision,
    reason: str,
) -> RiskAuthorization:
    canonical = "|".join(
        (
            snapshot.account_binding_id,
            request.trader_id.value,
            request.signal_fingerprint,
            request.provider_symbol,
            request.side,
            request.entry_type,
            str(request.intended_entry),
            str(request.stop_loss),
            str(request.take_profit),
            str(authorized_volume),
            issued_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )
    )
    fingerprint = sha256(canonical.encode("utf-8")).hexdigest()
    authorization_id = f"risk-{fingerprint[:24]}"
    return RiskAuthorization(
        authorization_id=authorization_id,
        account_binding_id=snapshot.account_binding_id,
        trader_id=request.trader_id,
        request_id=request.request_id,
        signal_fingerprint=request.signal_fingerprint,
        qore_symbol=request.qore_symbol,
        provider_symbol=request.provider_symbol,
        side=request.side,
        entry_type=request.entry_type,
        intended_entry=request.intended_entry,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        requested_volume=request.requested_volume,
        authorized_volume=authorized_volume,
        monetary_stop_loss=monetary_stop_loss,
        aggregate_pre_order_worst_case=aggregate_pre,
        aggregate_post_order_worst_case=aggregate_post,
        provider_headroom=snapshot.provider_budget.provider_headroom,
        internal_qore_headroom=snapshot.qore_authorizable_headroom,
        margin_reserved=margin_reserved,
        decision=decision,
        reason=reason,
        issued_at=issued_at,
        expires_at=request.expires_at,
        authorization_fingerprint=fingerprint,
    )


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    _nonnegative(value, "value")
    _positive(step, "step")
    units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise AccountWideRiskError(f"{name} must be timezone-aware")


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise AccountWideRiskError(f"{name} must be positive finite Decimal")


def _nonnegative(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise AccountWideRiskError(f"{name} must be non-negative finite Decimal")
